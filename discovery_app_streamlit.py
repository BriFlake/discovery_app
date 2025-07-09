# app.py

import streamlit as st
import pandas as pd
import uuid
import json
from fpdf import FPDF
from datetime import datetime
import re
from pptx import Presentation
from pptx.util import Inches
from io import BytesIO

# USER ACTION: You may need to add 'fpdf' and 'python-pptx' to your Streamlit in Snowflake environment.

# This block runs first to handle setting the newly created session ID
# before the selectbox widget is created, preventing the "cannot be modified" error.
if 'just_created_session_id' in st.session_state:
    st.session_state.selected_session_id = st.session_state.just_created_session_id
    del st.session_state.just_created_session_id


# ======================================================================================
# App Configuration
# ======================================================================================

st.set_page_config(
    page_title="Snowflake Sales Discovery Assistant",
    page_icon="❄️",
    layout="wide",
)

st.title("❄️ Snowflake Sales Discovery Assistant")
st.caption("An internal app for account research and discovery powered by Streamlit in Snowflake and Claude 3-5 Sonnet.")


# ======================================================================================
# Snowflake Connection and Data Functions
# ======================================================================================

# Establish a connection to Snowflake.
conn = st.connection("snowflake")

def get_current_user():
    """Gets the current Snowflake user and caches it in the session state."""
    if 'current_user' not in st.session_state:
        try:
            user_df = conn.query("SELECT CURRENT_USER() as user;")
            st.session_state.current_user = user_df.iloc[0]['USER']
        except Exception as e:
            st.error(f"Could not retrieve current user: {e}")
            st.session_state.current_user = "UNKNOWN_USER"
    return st.session_state.current_user


def save_answers_to_snowflake(df):
    """Saves the captured discovery answers to a Snowflake table."""
    if df.empty:
        st.warning("No answered questions to save.")
        return False
        
    try:
        df_to_save = df.copy()
        df_to_save.columns = [col.upper() for col in df_to_save.columns]
        conn.write_pandas(df_to_save, "SALES_DISCOVERY_ANSWERS_BETA")
        return True
    except Exception as e:
        st.error(f"Error saving to Snowflake: {e}")
        return False

def get_next_session_version(session_name_prefix, user):
    """Gets the next version number for a session name for the current user."""
    # This query is safe as inputs are controlled internally
    sql = f"SELECT MAX(REGEXP_SUBSTR(session_name, 'v(\\\\d+)$')) FROM SALES_DISCOVERY_SESSIONS WHERE session_name LIKE '{session_name_prefix}%' AND saved_by_user = '{user}'"
    try:
        cursor = conn.cursor()
        cursor.execute(sql)
        result = cursor.fetchone()
        if result and result[0]:
            return int(result[0]) + 1
        return 1
    except Exception as e:
        st.error(f"Error getting next session version: {e}")
        return 1

def save_session_to_snowflake(show_message=True):
    """Saves or updates the entire app state to the sessions table."""
    if not st.session_state.company_info.get('website'):
        if show_message:
            st.warning("Cannot save an empty session. Please generate questions for a company first.")
        return

    current_user = get_current_user()
    
    roadmap_json = st.session_state.roadmap_df.to_json(orient='split') if not st.session_state.roadmap_df.empty else None

    session_state_data = {
        "company_info": st.session_state.company_info,
        "questions": st.session_state.questions,
        "company_summary": st.session_state.company_summary,
        "notes_content": st.session_state.notes_content,
        "saved_by_user": current_user,
        "value_strategy_content": st.session_state.get('value_strategy_content', ''),
        "competitive_analysis_content": st.session_state.get('competitive_analysis_content', ''),
        "roadmap_json": roadmap_json
    }
    session_state_json = json.dumps(session_state_data)

    # If a session is already loaded, perform an UPDATE.
    if st.session_state.selected_session_id != "new":
        try:
            session_id = st.session_state.selected_session_id
            sql = """
            UPDATE SALES_DISCOVERY_SESSIONS
            SET session_state = PARSE_JSON(?)
            WHERE session_id = ? AND saved_by_user = ?
            """
            with conn.cursor() as cursor:
                cursor.execute(sql, (session_state_json, session_id, current_user))
                if cursor.rowcount > 0:
                    if show_message:
                        st.success("Session updated successfully!")
                else:
                    st.warning("Could not update. Session not found or you don't have permission.")
        except Exception as e:
            st.error(f"Failed to update session: {e}")
    
    # Otherwise, perform an INSERT for a new session.
    else:
        company_name = st.session_state.company_info['website'].replace('https://','').replace('www.','').split('.')[0]
        date_str = datetime.now().strftime('%Y-%m-%d')
        session_name_prefix = f"{company_name}_{date_str}"
        version = get_next_session_version(session_name_prefix, current_user)
        session_name = f"{session_name_prefix}"
        session_id = str(uuid.uuid4())
        
        sql = """
        INSERT INTO SALES_DISCOVERY_SESSIONS (session_id, session_name, session_state, saved_by_user)
        SELECT ?, ?, PARSE_JSON(?), ?
        """
        try:
            with conn.cursor() as cursor:
                cursor.execute(sql, (session_id, session_name, session_state_json, current_user))
            
            if show_message:
                st.success(f"Session '{session_name}' saved successfully!")
            
            st.session_state.just_created_session_id = session_id
            st.session_state.session_loaded = True

        except Exception as e:
            st.error(f"Failed to save new session: {e}")


def load_sessions_from_snowflake():
    """Loads the list of saved sessions from Snowflake for the current user."""
    current_user = get_current_user()
    try:
        query = "SELECT session_id, session_name FROM SALES_DISCOVERY_SESSIONS WHERE saved_by_user = ? ORDER BY created_at DESC;"
        df = conn.query(query, params=(current_user,), ttl=0)
        return df
    except Exception as e:
        if "does not exist" in str(e):
            st.sidebar.warning("SALES_DISCOVERY_SESSIONS table not found. Creating it now. Please refresh.")
            create_sessions_table_sql = """
            CREATE OR REPLACE TABLE SALES_DISCOVERY_SESSIONS (
                session_id VARCHAR PRIMARY KEY,
                session_name VARCHAR,
                created_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
                session_state VARIANT,
                saved_by_user VARCHAR
            );
            """
            with conn.cursor() as cursor:
                cursor.execute(create_sessions_table_sql)
            return pd.DataFrame(columns=['SESSION_ID', 'SESSION_NAME'])
        else:
            st.error(f"Error loading sessions: {e}")
            return pd.DataFrame(columns=['SESSION_ID', 'SESSION_NAME'])


def load_selected_session(session_id):
    """Loads a selected session's state from Snowflake."""
    current_user = get_current_user()
    try:
        query = "SELECT session_state FROM SALES_DISCOVERY_SESSIONS WHERE session_id = ? AND saved_by_user = ?;"
        df = conn.query(query, params=(session_id, current_user), ttl=0)
        if not df.empty:
            session_data_str = df.iloc[0]['SESSION_STATE']
            session_data = json.loads(session_data_str)
            
            clear_session(preserve_loaded_session_id=True)
            
            st.session_state.company_info = session_data.get('company_info', {})
            st.session_state.questions = session_data.get('questions', {})
            st.session_state.company_summary = session_data.get('company_summary', "")
            st.session_state.notes_content = session_data.get('notes_content', "")
            st.session_state.value_strategy_content = session_data.get('value_strategy_content', "")
            st.session_state.competitive_analysis_content = session_data.get('competitive_analysis_content', "")
            
            roadmap_json = session_data.get('roadmap_json')
            if roadmap_json:
                st.session_state.roadmap_df = pd.read_json(roadmap_json, orient='split')
            else:
                st.session_state.roadmap_df = pd.DataFrame()

            st.session_state.session_loaded = True
        else:
            st.warning("Could not find the selected session or you do not have permission to access it.")
    except Exception as e:
        st.error(f"Error loading session state: {e}")

def delete_session_from_snowflake(session_id):
    """Deletes a session from Snowflake, ensuring user ownership."""
    current_user = get_current_user()
    sql = "DELETE FROM SALES_DISCOVERY_SESSIONS WHERE session_id = ? AND saved_by_user = ?"
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql, (session_id, current_user))
            if cursor.rowcount > 0:
                st.success("Session deleted.")
            else:
                st.warning("Session not found or you don't have permission to delete it.")
        
        st.session_state.selected_session_id = "new" 

    except Exception as e:
        st.error(f"Failed to delete session: {e}")

# ======================================================================================
# LLM Functions
# ======================================================================================

def cortex_request(prompt, json_output=True):
    """Generic function to make a request to Cortex."""
    safe_prompt = prompt.replace("'", "''")
    sql_query = f"SELECT SNOWFLAKE.CORTEX.COMPLETE('claude-3-5-sonnet', '{safe_prompt}') as response;"
    
    try:
        cursor = conn.cursor()
        cursor.execute(sql_query)
        response_row = cursor.fetchone()
        
        if not (response_row and response_row[0]):
            st.error("The AI model returned an empty response.")
            return None

        llm_response_str = response_row[0]
        
        if not json_output:
            return llm_response_str

        json_start = llm_response_str.find('{')
        json_end = llm_response_str.rfind('}') + 1
        
        if json_start != -1 and json_end != 0:
            json_str = llm_response_str[json_start:json_end]
            return json.loads(json_str)
        else:
            st.error("Could not find a valid JSON object in the LLM's response.")
            st.text_area("LLM Raw Response", llm_response_str, height=200)
            return None
            
    except json.JSONDecodeError as e:
        st.error(f"Error decoding JSON from LLM response: {e}")
        st.text_area("LLM Raw Response that failed parsing", llm_response_str, height=200)
        return None
    except Exception as e:
        st.error(f"An error occurred while calling the LLM or parsing the response: {e}")
        return None

# MODIFIED: This function now sorts the question categories to a fixed order.
def generate_discovery_questions(website, industry, competitor, persona):
    """Generates initial discovery questions."""
    prompt = f"""
    You are an expert Snowflake sales engineer. Generate discovery questions for a potential customer with the title of **{persona}**.
    Company Information: Website: {website}, Industry: {industry}, Assumed Primary Competitor: {competitor}.
    Generate three categories: **Technical Discovery**, **Business Discovery**, and exactly 10 questions for **Competitive Positioning vs. {competitor}**.
    The total number of questions must not exceed 30. Return as a single, valid JSON object.
    """
    questions_dict = cortex_request(prompt)
    if questions_dict:
        # First, process the LLM output into a standardized dictionary
        temp_processed = {}
        competitive_key_name = f"Competitive Positioning vs. {competitor}"
        for category, qs in questions_dict.items():
            # Standardize the competitive key name, as the LLM might vary it slightly
            if "Competitive Positioning" in category:
                temp_processed[competitive_key_name] = [
                    {"id": str(uuid.uuid4()), "text": q, "answer": "", "favorite": False} for q in qs
                ]
            else:
                # Use a title case for consistency
                temp_processed[category.title()] = [
                    {"id": str(uuid.uuid4()), "text": q, "answer": "", "favorite": False} for q in qs
                ]
        
        # Now, create the final dictionary in the desired order
        ordered_questions = {}
        # Define the explicit order
        category_order = ["Technical Discovery", "Business Discovery", competitive_key_name]

        for category in category_order:
            if category in temp_processed:
                ordered_questions[category] = temp_processed[category]
        
        # Add any unexpected categories generated by the LLM at the end to be safe
        for category, questions in temp_processed.items():
            if category not in ordered_questions:
                ordered_questions[category] = questions
                
        return ordered_questions
    return {}

def generate_company_summary(website, industry, persona):
    """Generates a company summary."""
    prompt = f"""
    You are a skilled business analyst. Based on the company website '{website}' and its industry '{industry}', provide a concise, one-paragraph summary relevant to a person with the title of **{persona}**.
    Touch upon the company's likely business model, its target customers, and potential data-related opportunities or challenges.
    """
    return cortex_request(prompt, json_output=False)

def generate_more_questions_for_category(website, industry, competitor, persona, category, existing_questions):
    """Generates 5 more questions for a specific category."""
    existing_questions_str = "\n".join([f"- {q}" for q in existing_questions])
    prompt = f"""
    You are an expert Snowflake sales engineer. For a **{persona}** at a company with website {website}, generate exactly 5 new and distinct discovery questions for the category '{category}'.
    Do not repeat these existing questions: {existing_questions_str}.
    Return your response as a single, valid JSON object with a key "new_questions" containing a list of strings.
    """
    response_dict = cortex_request(prompt)
    if response_dict and "new_questions" in response_dict:
        return [
            {"id": str(uuid.uuid4()), "text": q, "answer": "", "favorite": False}
            for q in response_dict["new_questions"]
        ]
    return []

def generate_initiative_questions(website, industry, persona, initiative):
    """Generates questions for a specific key initiative."""
    prompt = f"""
    You are an expert Snowflake sales engineer. For a **{persona}** at a company with website {website}, generate 5-7 insightful discovery questions that directly relate to the business initiative: **{initiative}**.
    Return your response as a single, valid JSON object with a key "questions" containing a list of strings.
    """
    response_dict = cortex_request(prompt)
    if response_dict and "questions" in response_dict:
        return [
            {"id": str(uuid.uuid4()), "text": q, "answer": "", "favorite": False}
            for q in response_dict["questions"]
        ]
    return []

def generate_roadmap(company_info, discovery_notes_str, priority):
    """Generates a strategic roadmap."""
    prompt = f"""
    You are a world-class Snowflake Solution Architect creating a strategic roadmap for a potential customer.
    **Customer Context:** Website: {company_info.get('website', 'N/A')}, Industry: {company_info.get('industry', 'N/A')}, Persona: {company_info.get('persona', 'N/A')}.
    **Discovery Notes:**
    {discovery_notes_str}
    **Roadmap Requirements:**
    1. Analyze the notes to identify key pain points and business objectives.
    2. Propose a logical sequence of 2-4 implementation projects using Snowflake.
    3. For each project, provide a `project_name`, `description`, `business_value` ('Low', 'Medium', 'High', 'Very High'), and `level_of_effort` ('Low', 'Medium', 'High').
    4. Order the roadmap based on this priority: **{priority}**.
    5. You MUST return the output as a single, valid JSON object with a key "roadmap" which is a list of project objects.
    """
    response_dict = cortex_request(prompt)
    if response_dict and "roadmap" in response_dict:
        return pd.DataFrame(response_dict["roadmap"])
    return pd.DataFrame()

def get_chatbot_response(company_info, chat_history):
    """Generates a response for the chat interface."""
    history_str = ""
    for message in chat_history:
        role = "User" if message['role'] == 'user' else "Assistant"
        history_str += f"{role}: {message['content']}\n"

    prompt = f"""
    You are a helpful Snowflake sales assistant chatbot. Your goal is to answer user questions about how Snowflake's technology can help a specific company.
    You have the following context:
    - Company Website: {company_info.get('website', 'N/A')}
    - Industry: {company_info.get('industry', 'N/A')}
    - Assumed Primary Competitor: {company_info.get('competitor', 'N/A')}
    - Contact's Title: {company_info.get('persona', 'N/A')}
    You also have the conversation history:
    {history_str}
    Based on all of this context, provide a concise and helpful answer to the last user question.
    """
    return cortex_request(prompt, json_output=False)

def autofill_answers_from_notes(notes_text, questions_dict):
    """Orchestrates the auto-fill process by calling the LLM for each category."""
    populated_questions = {}
    for category, questions in questions_dict.items():
        if not questions:
            continue
        
        st.write(f"Analyzing notes for category: **{category}**...")
        answered_category = autofill_category_from_notes(notes_text, category, questions)
        
        if answered_category:
            populated_questions[category] = answered_category
        else:
            populated_questions[category] = questions
            st.warning(f"Could not auto-fill answers for category: {category}. Please review manually.")

    return populated_questions


def autofill_category_from_notes(notes_text, category, questions_in_category):
    """Uses LLM to populate answers for a single category of questions based on freeform notes."""
    prompt = f"""
    You are an intelligent assistant. Your task is to populate answers for a single category of discovery questions based on a provided block of freeform notes.
    **Source Notes:**
    ---
    {notes_text}
    ---
    **Questions for the '{category}' category to Answer (JSON format):**
    ---
    {json.dumps(questions_in_category, indent=2)}
    ---
    **Instructions:**
    1. Read through the **Source Notes** carefully.
    2. For each question in the provided JSON object, find the relevant information within the notes.
    3. Formulate a concise answer for each question based *only* on the information present in the notes.
    4. If no relevant information for a question is found, the value for the "answer" key for that question MUST be an empty string ("").
    5. Your final output MUST be a single, valid JSON object with a key named "answered_questions" that contains a list of the questions with their "answer" fields populated. The structure of each question object must be identical to the input.
    """
    response = cortex_request(prompt)
    if response and "answered_questions" in response:
        return response["answered_questions"]
    return None

def generate_business_case(company_info, discovery_notes_str):
    """Generates a business case and strategy from discovery notes."""
    prompt = f"""
    You are a senior business value consultant. Your task is to analyze the following discovery notes and build a compelling business case for adopting Snowflake.
    **Customer Context:**
    - Company: {company_info.get('website', 'N/A')}
    - Industry: {company_info.get('industry', 'N/A')}
    - Persona of Contact: {company_info.get('persona', 'N/A')}
    - Main Competitor: {company_info.get('competitor', 'N/A')}
    **Discovery Notes (Questions & Answers):**
    ---
    {discovery_notes_str}
    ---
    **Instructions:**
    Based on the notes, generate a response with three sections:
    1.  **Business Case:** Synthesize the notes into a business case. Use metrics and quantitative data from the answers where possible. Frame the value proposition around the key business initiatives discussed.
    2.  **Key Questions for Value Metrics:** Identify and list 3-5 critical follow-up questions that need to be asked to uncover stronger, quantifiable business value metrics.
    3.  **Recommended Strategy:** Suggest a high-level strategy to strengthen the business case and align with the customer's goals.
    Format your response in Markdown.
    """
    return cortex_request(prompt, json_output=False)

def generate_competitive_argument(company_info, discovery_notes_str):
    """Generates a 'steel man' argument for the competitor."""
    prompt = f"""
    You are a highly skilled, aggressive, and effective salesperson for **{company_info.get('competitor', 'the competitor')}**. 
    Your goal is to build the strongest possible "steel man" argument to convince a customer to choose your solution over Snowflake.
    **Customer Context:**
    - Company: {company_info.get('website', 'N/A')}
    - Industry: {company_info.get('industry', 'N/A')}
    - Persona of Contact: {company_info.get('persona', 'N/A')}
    **Your Competitor's Discovery Notes (Snowflake's perspective):**
    ---
    {discovery_notes_str}
    ---
    **Instructions:**
    Based on the notes, create the best possible competitive strategy and argument for **{company_info.get('competitor', 'your company')}**.
    1.  **Competitive Strategy:** What is your overall strategy to win this deal?
    2.  **Key Talking Points:** What are the 3-5 most powerful talking points you will use?
    3.  **How to Counter Snowflake:** How would you proactively counter Snowflake's main value propositions?
    Give the best, most compelling argument possible. Be specific and tactical. Format the response in Markdown.
    """
    return cortex_request(prompt, json_output=False)


# ======================================================================================
# Helper Functions for UI, State, and Exporting
# ======================================================================================

class PDF(FPDF):
    def __init__(self, orientation='P', unit='mm', format='A4', title=''):
        super().__init__(orientation, unit, format)
        self.title = title
    def header(self):
        self.set_font("Helvetica", "B", 12)
        self.cell(0, 10, self.title, 0, 0, 'C')
        self.ln(10)
    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')

def create_notes_pdf_bytes(export_df, company_info):
    """Generates a PDF for discovery notes."""
    pdf = PDF(title='Snowflake Discovery Notes')
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    clean_website = company_info.get('website', 'N/A').encode('latin-1', 'replace').decode('latin-1')
    pdf.cell(0, 10, f"Discovery Notes: {clean_website}", 0, 1, 'C')
    pdf.ln(5)
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 5, f"Industry: {company_info.get('industry', 'N/A')}", 0, 1)
    pdf.cell(0, 5, f"Persona: {company_info.get('persona', 'N/A')}", 0, 1)
    pdf.cell(0, 5, f"Assumed Competitor: {company_info.get('competitor', 'N/A')}", 0, 1)
    pdf.ln(10)
    for category, group in export_df.groupby('question_category'):
        pdf.set_font("Helvetica", "B", 12)
        clean_category = category.encode('latin-1', 'replace').decode('latin-1')
        pdf.cell(0, 10, clean_category, 0, 1, 'L', True)
        pdf.ln(2)
        for _, row in group.iterrows():
            fav_char = " (Favorite)" if row['favorite'] else ""
            question_text = f"Q: {row['question']}{fav_char}"
            answer_text = f"A: {row['answer'] if row['answer'] else 'No answer provided.'}"
            pdf.set_font("Helvetica", "B", 10)
            pdf.multi_cell(0, 5, question_text.encode('latin-1', 'replace').decode('latin-1'))
            pdf.set_font("Helvetica", "", 10)
            pdf.multi_cell(0, 5, answer_text.encode('latin-1', 'replace').decode('latin-1'))
            pdf.ln(5)
    return pdf.output(dest='S').encode('latin-1')

def create_roadmap_pdf_bytes(roadmap_df, company_info):
    """Generates a PDF for the strategic roadmap."""
    pdf = PDF(title=f"Strategic Roadmap for {company_info.get('website')}")
    pdf.add_page()
    for _, row in roadmap_df.iterrows():
        pdf.set_font("Helvetica", "B", 14)
        pdf.multi_cell(0, 7, f"Project: {row.get('project_name', 'N/A')}".encode('latin-1', 'replace').decode('latin-1'))
        pdf.ln(2)
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(40, 7, "Business Value:")
        pdf.set_font("Helvetica", "", 10)
        pdf.cell(0, 7, str(row.get('business_value', 'N/A')))
        pdf.ln()
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(40, 7, "Level of Effort:")
        pdf.set_font("Helvetica", "", 10)
        pdf.cell(0, 7, str(row.get('level_of_effort', 'N/A')))
        pdf.ln()
        pdf.set_font("Helvetica", "B", 10)
        pdf.multi_cell(0, 5, "Description:")
        pdf.set_font("Helvetica", "", 10)
        pdf.multi_cell(0, 5, str(row.get('description', 'N/A')).encode('latin-1', 'replace').decode('latin-1'))
        pdf.ln(7)
    return pdf.output(dest='S').encode('latin-1')

def generate_powerpoint_bytes(company_info, business_case, competitive_analysis):
    """Generates a PowerPoint presentation from the strategic content."""
    prs = Presentation()
    title_slide_layout = prs.slide_layouts[0]
    slide = prs.slides.add_slide(title_slide_layout)
    title = slide.shapes.title
    subtitle = slide.placeholders[1]
    title.text = f"Strategic Business Case for {company_info.get('website', 'the Company')}"
    subtitle.text = f"Prepared for: {company_info.get('persona', 'Valued Stakeholder')}\nDate: {datetime.today().strftime('%B %d, %Y')}"
    bullet_slide_layout = prs.slide_layouts[1]
    slide = prs.slides.add_slide(bullet_slide_layout)
    shapes = slide.shapes
    title_shape = shapes.title
    body_shape = shapes.placeholders[1]
    title_shape.text = "Business Case & Recommended Strategy"
    tf = body_shape.text_frame
    tf.text = business_case if business_case else "Not generated."
    if competitive_analysis:
        slide = prs.slides.add_slide(bullet_slide_layout)
        shapes = slide.shapes
        title_shape = shapes.title
        body_shape = shapes.placeholders[1]
        title_shape.text = f"Anticipating the {company_info.get('competitor', 'Competitor')} Argument"
        tf = body_shape.text_frame
        tf.text = competitive_analysis
    ppt_stream = BytesIO()
    prs.save(ppt_stream)
    ppt_stream.seek(0)
    return ppt_stream.getvalue()


def format_for_gdocs(export_df, company_info):
    """Formats notes for Google Docs, respecting answered/unanswered sorting."""
    doc_text = [f"# Discovery Notes: {company_info.get('website')}\n"]
    if 'answer' not in export_df.columns:
        export_df['answer'] = ''
    export_df['answer'] = export_df['answer'].fillna('').astype(str)
    answered_df = export_df[export_df['answer'].str.strip() != ''].copy()
    unanswered_df = export_df[export_df['answer'].str.strip() == ''].copy()
    if not answered_df.empty:
        doc_text.append("\n## Answered Questions\n")
        for category, group in answered_df.groupby('question_category'):
            doc_text.append(f"### {category}\n")
            for _, row in group.iterrows():
                fav_char = " **(Favorite)**" if row['favorite'] else ""
                doc_text.append(f"**Q: {row['question']}**{fav_char}\n")
                answer = str(row['answer']).replace('\n', '\n> ')
                doc_text.append(f"> {answer}\n")
    if not unanswered_df.empty:
        doc_text.append("\n---\n## Unanswered Questions\n")
        for category, group in unanswered_df.groupby('question_category'):
            doc_text.append(f"### {category}\n")
            for _, row in group.iterrows():
                doc_text.append(f"- {row['question']}\n")
    return "\n".join(doc_text)

# ======================================================================================
# Session State and UI Helper Functions
# ======================================================================================

# Initialize session state
if 'questions' not in st.session_state: st.session_state.questions = {}
if 'company_info' not in st.session_state: st.session_state.company_info = {}
if 'company_summary' not in st.session_state: st.session_state.company_summary = ""
if 'roadmap_df' not in st.session_state: st.session_state.roadmap_df = pd.DataFrame()
if 'messages' not in st.session_state: st.session_state.messages = []
if 'notes_content' not in st.session_state: st.session_state.notes_content = ""
if 'value_strategy_content' not in st.session_state: st.session_state.value_strategy_content = ""
if 'competitive_analysis_content' not in st.session_state: st.session_state.competitive_analysis_content = ""
if 'session_loaded' not in st.session_state: st.session_state.session_loaded = False
if 'selected_session_id' not in st.session_state: st.session_state.selected_session_id = "new"


def move_question(category, index, direction):
    """Swaps a question with the one above or below it."""
    questions_list = st.session_state.questions[category]
    if direction == 'up' and index > 0:
        questions_list[index], questions_list[index - 1] = questions_list[index - 1], questions_list[index]
    elif direction == 'down' and index < len(questions_list) - 1:
        questions_list[index], questions_list[index + 1] = questions_list[index + 1], questions_list[index]

def toggle_favorite(q_id):
    for category in st.session_state.questions:
        for question in st.session_state.questions[category]:
            if question['id'] == q_id:
                question['favorite'] = not question.get('favorite', False)
                return

def delete_question(q_id):
    for category, q_list in st.session_state.questions.items():
        st.session_state.questions[category] = [q for q in q_list if q['id'] != q_id]


def add_custom_question(category, text_input_key):
    question_text = st.session_state[text_input_key]
    if question_text:
        new_question = {
            "id": str(uuid.uuid4()),
            "text": question_text,
            "answer": "",
            "favorite": False
        }
        if category in st.session_state.questions:
            st.session_state.questions[category].append(new_question)
        st.session_state[text_input_key] = ""


def clear_session(preserve_loaded_session_id=False):
    """Clears the session state, with an option to preserve the loaded session ID."""
    loaded_session_id = st.session_state.get('selected_session_id') if preserve_loaded_session_id else "new"
    current_user = st.session_state.get('current_user')
    
    keys_to_clear = list(st.session_state.keys())
    for key in keys_to_clear:
        del st.session_state[key]
        
    st.session_state.selected_session_id = loaded_session_id
    if current_user:
        st.session_state.current_user = current_user

# ======================================================================================
# Main App Logic
# ======================================================================================

st.sidebar.subheader(f"User: {get_current_user()}")
st.sidebar.subheader("Discovery Session Management")

saved_sessions_df = load_sessions_from_snowflake()

session_options = {"new": "Start a New Session"}
if saved_sessions_df is not None and not saved_sessions_df.empty:
    session_options.update(pd.Series(saved_sessions_df.SESSION_NAME.values, index=saved_sessions_df.SESSION_ID).to_dict())
else:
    st.sidebar.info("ℹ️ No saved sessions found for your user.")

def on_session_change():
    """Callback function to handle session selection."""
    session_id = st.session_state.selected_session_id
    if session_id == "new":
        clear_session()
    else:
        load_selected_session(session_id)

st.sidebar.selectbox(
    "Load a session or start new:",
    options=list(session_options.keys()),
    key='selected_session_id',
    on_change=on_session_change,
    format_func=lambda x: session_options.get(x, "Unknown Session"),
    label_visibility="collapsed"
)

if st.session_state.selected_session_id != "new":
    st.sidebar.button(
        "💾 Update Current Session", 
        on_click=save_session_to_snowflake, 
        use_container_width=True, 
        help="Save changes to the currently loaded session."
    )
else:
    st.sidebar.button(
        "💾 Save as New Session", 
        on_click=save_session_to_snowflake, 
        use_container_width=True, 
        help="Save the current state as a brand new session."
    )


if st.session_state.selected_session_id != "new":
    st.sidebar.button("🗑️ Delete Selected Session", use_container_width=True, on_click=delete_session_from_snowflake, args=(st.session_state.selected_session_id,))

st.sidebar.divider()

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "**1. Account Research & Discovery**", 
    "**2. Freeform Notes & Auto-fill**",
    "**3. Value & Strategy**",
    "**4. Roadmap Builder**",
    "**5. Snowflake Solution Chat**"
])

with tab1:
    col_header1, col_header2 = st.columns([4, 1])
    with col_header1:
        st.header("Step 1: Research Account & Generate Questions")
    with col_header2:
        if st.button("Clear & Restart Session", use_container_width=True, help="Clears all data and starts a fresh session."):
            clear_session()
            st.rerun()

    st.markdown("Enter the company's details to generate a persona-tailored summary and discovery questions. To start over with a new company, select 'Start a New Session' from the menu on the left.")

    is_disabled = st.session_state.session_loaded

    with st.form("research_form"):
        website = st.text_input("**Company Website**", placeholder="e.g., https://www.example.com", value=st.session_state.company_info.get('website', ''), disabled=is_disabled)
        industry = st.text_input("**Industry**", placeholder="e.g., Retail, Financial Services", value=st.session_state.company_info.get('industry', ''), disabled=is_disabled)
        persona_options = ["C-Level (CEO, CIO, CDO)", "VP of Engineering / Data", "Director of Analytics / BI", "Data Scientist / ML Engineer", "Data/Analytics Engineer"]
        persona_idx = persona_options.index(st.session_state.company_info.get('persona', "C-Level (CEO, CIO, CDO)")) if st.session_state.company_info.get('persona') in persona_options else 0
        persona = st.selectbox("**Select Title of Person You're Meeting With**", persona_options, index=persona_idx, disabled=is_disabled)
        competitor_options = ["Databricks", "Microsoft Fabric", "AWS", "GCP", "Do Nothing (i.e., keep existing technology)"]
        competitor_idx = competitor_options.index(st.session_state.company_info.get('competitor', 'Databricks')) if st.session_state.company_info.get('competitor') in competitor_options else 0
        competitor = st.selectbox("**Select Primary Competitor**", competitor_options, index=competitor_idx, disabled=is_disabled)
        st.markdown("---")
        initiatives_options = ["Grow Revenue", "Reduce Risk", "Manage Costs", "Innovate", "Other"]
        selected_initiatives = st.multiselect("**Select Suspected Key Initiatives (Optional)**", options=initiatives_options, help="This will generate an additional section of questions for each selected initiative.", disabled=is_disabled)
        other_initiative = st.text_input("**If 'Other', please specify:**", placeholder="e.g., Improve Customer Experience", disabled=is_disabled)
        st.markdown("---")
        research_button = st.form_submit_button("Generate Summary & Questions", type="primary", disabled=is_disabled)

    if research_button:
        if not website or not industry:
            st.warning("Please provide both a website and an industry.")
        else:
            with st.spinner("Researching company, generating questions, and saving session..."):
                st.session_state.company_info = {'website': website, 'industry': industry, 'competitor': competitor, 'persona': persona}
                st.session_state.company_summary = generate_company_summary(website, industry, persona)
                all_questions = generate_discovery_questions(website, industry, competitor, persona)
                final_initiatives = [init for init in selected_initiatives if init != "Other"]
                if "Other" in selected_initiatives and other_initiative:
                    final_initiatives.append(other_initiative)
                for initiative in final_initiatives:
                    initiative_questions = generate_initiative_questions(website, industry, persona, initiative)
                    if initiative_questions:
                        all_questions[f"Initiative: {initiative}"] = initiative_questions
                    else:
                        st.warning(f"Could not generate questions for the '{initiative}' initiative.")
                st.session_state.questions = all_questions
                save_session_to_snowflake(show_message=False)
                st.rerun()

    st.divider()

    if st.session_state.company_summary or st.session_state.questions:
        if st.session_state.company_summary:
            st.header(f"Company Overview for a {st.session_state.company_info.get('persona', 'Contact')}")
            st.info(st.session_state.company_summary)

        if st.session_state.questions:
            st.header("Step 2: Ask Questions and Capture Responses")
            st.markdown(f"Discovery questions for **{st.session_state.company_info.get('website')}**")

            for cat, q_list in st.session_state.questions.items():
                for q in q_list:
                    widget_key = f"ans_{q['id']}"
                    if widget_key in st.session_state:
                        q['answer'] = st.session_state[widget_key]

            for category, questions_list in st.session_state.questions.items():
                if not questions_list: continue
                toggle_key = f"toggle_{category.replace(' ', '_')}"
                is_expanded = st.toggle(f"**{category}** ({len(questions_list)} questions)", key=toggle_key, value=st.session_state.get(toggle_key, False))
                if is_expanded:
                    with st.container(border=True):
                        for i, question in enumerate(questions_list):
                            q_col1, q_col2, q_col3 = st.columns([0.5, 0.7, 10])
                            with q_col1:
                                st.button("▲", key=f"up_{question['id']}", on_click=move_question, args=(category, i, 'up'), disabled=(i == 0), help="Move question up")
                                st.button("▼", key=f"down_{question['id']}", on_click=move_question, args=(category, i, 'down'), disabled=(i == len(questions_list) - 1), help="Move question down")
                            with q_col2:
                                fav_icon = "⭐" if question.get('favorite', False) else "☆"
                                st.button(fav_icon, key=f"fav_{question['id']}", on_click=toggle_favorite, args=(question['id'],), help="Toggle Favorite")
                                st.button("🗑️", key=f"del_{question['id']}", on_click=delete_question, args=(question['id'],), help="Delete Question")
                            with q_col3:
                                st.markdown(f"**Q: {question['text']}**")
                                st.text_area("Capture Answer", value=question.get('answer', ''), key=f"ans_{question['id']}", label_visibility="collapsed")
                        st.markdown("---")
                        st.write("##### Add a Custom Question")
                        custom_q_key = f"custom_q_{category.replace(' ', '_')}"
                        st.text_input("Enter your question:", key=custom_q_key, placeholder="Type your custom question here...", label_visibility="collapsed")
                        st.button("Add Question", key=f"add_q_{category.replace(' ', '_')}", on_click=add_custom_question, args=(category, custom_q_key))
                        if st.button(f"Generate 5 More AI Questions", key=f"more_{category.replace(' ', '_')}", use_container_width=True):
                            with st.spinner(f"Generating more questions for {category}..."):
                                existing_q_texts = [q['text'] for q in questions_list]
                                new_questions = generate_more_questions_for_category(st.session_state.company_info['website'], st.session_state.company_info['industry'], st.session_state.company_info['competitor'], st.session_state.company_info['persona'], category, existing_q_texts)
                                if new_questions:
                                    st.session_state.questions[category].extend(new_questions)
                                    st.rerun() 
                                else:
                                    st.warning("Could not generate additional questions.")
            st.divider()

        st.header("Step 3: Export or Save Responses")
        st.markdown("Once you have captured the answers, you can export them or save them directly to the `SALES_DISCOVERY_ANSWERS_BETA` table in Snowflake for broader analytics.")
        export_data = []
        company_name = st.session_state.company_info.get('website', 'N/A').replace('https://','').replace('www.','').split('.')[0].capitalize()
        for category, questions_list in st.session_state.questions.items():
            for question in questions_list:
                export_data.append({
                    "id": question['id'],
                    "company_name": company_name,
                    "company_website": st.session_state.company_info.get('website', 'N/A'),
                    "question_category": category,
                    "question": question['text'],
                    "answer": question.get('answer', ''),
                    "favorite": question.get('favorite', False),
                    "saved_at": datetime.utcnow()
                })
        if export_data:
            export_df = pd.DataFrame(export_data)
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.download_button("📄 Generate PDF", data=create_notes_pdf_bytes(export_df, st.session_state.company_info), file_name=f"discovery_notes_{company_name}.pdf", mime="application/pdf", use_container_width=True)
            with col2:
                st.download_button("📥 Download as CSV", data=export_df.to_csv(index=False).encode('utf-8'), file_name=f"discovery_notes_{company_name}.csv", mime='text/csv', use_container_width=True)
            with col3:
                if st.button("💾 Save to Answers Table", use_container_width=True, help="Saves all answered questions to the SALES_DISCOVERY_ANSWERS_BETA table"):
                    answered_df = export_df[export_df['answer'].str.strip() != ''].copy()
                    if not answered_df.empty:
                        with st.spinner("Saving answered questions..."):
                            if save_answers_to_snowflake(answered_df):
                                st.success("✅ Answers saved to Snowflake!")
                    else:
                        st.warning("No answered questions to save.")
            with col4:
                if st.button("📋 Copy for Google Docs", use_container_width=True):
                    gdocs_text = format_for_gdocs(export_df, st.session_state.company_info)
                    st.text_area("Formatted Text", value=gdocs_text, height=300)
                    st.info("Use Ctrl+C or Cmd+C to copy the text above.", icon="📋")

with tab2:
    st.header("Freeform Notes & Auto-fill")
    st.markdown("Take your meeting notes here. When you're done, the AI can read your notes and automatically fill out the answers on the first tab.")
    if 'questions' not in st.session_state or not st.session_state.questions:
        st.info("Please generate questions on the **'1. Account Research & Discovery'** tab first.")
    else:
        notes = st.text_area("Meeting Notes", key='notes_content', placeholder="Start typing your meeting notes here...", height=400)
        if st.button("📝 Auto-fill Answers from Notes", type="primary"):
            if notes:
                with st.spinner("AI is reading your notes and filling out answers..."):
                    populated_questions = autofill_answers_from_notes(notes, st.session_state.questions)
                    if populated_questions:
                        st.session_state.questions = populated_questions
                        st.success("Auto-fill complete! Check the 'Account Research & Discovery' tab to see the results.")
                    else:
                        st.error("The AI could not process the notes to fill out the questions. Please try again.")
            else:
                st.warning("Please enter some notes before trying to auto-fill.")


with tab3:
    st.header("Value & Strategy")
    st.markdown("Generate a business case and a competitive analysis based on the discovery information you've gathered.")
    if 'questions' not in st.session_state or not st.session_state.questions:
        st.info("Please complete the research on the **'1. Account Research & Discovery'** tab first.")
    else:
        notes_list = []
        for category, questions_list in st.session_state.questions.items():
            for q in questions_list:
                answer = str(q.get('answer', '')).strip()
                if answer:
                    notes_list.append(f"Category: {category}\nQ: {q['text']}\nA: {answer}\n")
        discovery_notes_str = "\n".join(notes_list)
        if not discovery_notes_str:
            st.warning("Please answer at least one question on the first tab to generate content.")
        else:
            if st.button("📈 Generate Business Case & Strategy", type="primary"):
                with st.spinner("Building business case..."):
                    business_case = generate_business_case(st.session_state.company_info, discovery_notes_str)
                    st.session_state.value_strategy_content = business_case
                    st.session_state.competitive_analysis_content = ""
            if st.session_state.value_strategy_content:
                st.markdown(st.session_state.value_strategy_content)
                st.divider()
                st.subheader("Competitive Battlecard")
                if st.button(f"🛡️ Generate 'Steel Man' Argument for {st.session_state.company_info.get('competitor')}"):
                        with st.spinner(f"Preparing counter-arguments for {st.session_state.company_info.get('competitor')}..."):
                            competitive_arg = generate_competitive_argument(st.session_state.company_info, discovery_notes_str)
                            st.session_state.competitive_analysis_content = competitive_arg
                if st.session_state.competitive_analysis_content:
                    st.markdown(st.session_state.competitive_analysis_content)
                st.divider()
                st.subheader("Export Strategy")
                ppt_bytes = generate_powerpoint_bytes(st.session_state.company_info, st.session_state.value_strategy_content, st.session_state.competitive_analysis_content)
                st.download_button(label="📊 Download as PowerPoint", data=ppt_bytes, file_name=f"Strategy_{st.session_state.company_info.get('website', 'export').replace('https://','').replace('www.','').split('.')[0]}.pptx", mime="application/vnd.openxmlformats-officedocument.presentationml.presentation", use_container_width=True)


with tab4:
    st.header("Roadmap Builder")
    if not st.session_state.questions:
        st.info("Please complete the research on the **'1. Account Research & Discovery'** tab first.")
    else:
        notes_list = []
        for category, questions_list in st.session_state.questions.items():
            for q in questions_list:
                answer = str(q.get('answer', '')).strip()
                if answer:
                    notes_list.append(f"Category: {category}\nQ: {q['text']}\nA: {answer}\n")
        discovery_notes_str = "\n".join(notes_list)
        if not discovery_notes_str:
            st.warning("Please answer at least one question on the first tab to generate a roadmap.")
        else:
            st.markdown("Based on the captured discovery answers, generate a potential implementation plan.")
            priority = st.radio("**Prioritize roadmap by:**", ("Quick Wins (Lowest Effort First)", "Highest Business Value First"), horizontal=True)
            if st.button("🚀 Generate Strategic Roadmap", type="primary"):
                with st.spinner("Claude is architecting the solution..."):
                    st.session_state.roadmap_df = generate_roadmap(st.session_state.company_info, discovery_notes_str, priority)
    if not st.session_state.roadmap_df.empty:
        st.divider()
        st.subheader("Generated Roadmap")
        st.dataframe(st.session_state.roadmap_df, use_container_width=True)
        st.subheader("Export Roadmap")
        roadmap_col1, roadmap_col2 = st.columns(2)
        company_name = st.session_state.company_info.get('website', 'N/A').replace('https://','').replace('www.','').split('.')[0].capitalize()
        with roadmap_col1:
            pdf_bytes = create_roadmap_pdf_bytes(st.session_state.roadmap_df, st.session_state.company_info)
            st.download_button(label="📄 Download Roadmap as PDF", data=pdf_bytes, file_name=f"roadmap_{company_name}.pdf", mime="application/pdf", use_container_width=True)
        with roadmap_col2:
            csv_data = st.session_state.roadmap_df.to_csv(index=False).encode('utf-8')
            st.download_button(label="📥 Download Roadmap as CSV", data=csv_data, file_name=f"roadmap_{company_name}.csv", mime="text/csv", use_container_width=True)

with tab5:
    st.header("Snowflake Solution Chat")
    if not st.session_state.company_info:
        st.info("Please research an account on the first tab to activate the chat.")
    else:
        st.markdown(f"Ask questions about how Snowflake can help **{st.session_state.company_info.get('website')}**.")
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
        if prompt := st.chat_input("How can Snowflake help with their data challenges?"):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)
            with st.chat_message("assistant"):
                message_placeholder = st.empty()
                with st.spinner("Claude is thinking..."):
                    full_response = get_chatbot_response(st.session_state.company_info, st.session_state.messages)
                    message_placeholder.markdown(full_response)
            st.session_state.messages.append({"role": "assistant", "content": full_response})
