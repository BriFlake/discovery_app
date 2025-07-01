# app.py

import streamlit as st
import pandas as pd
import uuid
import json
from datetime import datetime
# USER ACTION: You may need to add 'fpdf' to your Streamlit in Snowflake environment.


# ======================================================================================
# App Configuration
# ======================================================================================

st.set_page_config(
    page_title="Snowflake Sales Discovery Assistant",
    page_icon="❄️",
    layout="wide",
)

st.title("❄️ Snowflake Sales Discovery Assistant")
st.caption("An internal app for account research and discovery powered by Streamlit in Snowflake and Claude 3.5 Sonnet.")


# ======================================================================================
# Snowflake Connection and Data Functions
# ======================================================================================

# Establish a connection to Snowflake.
# Streamlit in Snowflake handles the authentication securely.
# USER INPUT REQUIRED: Ensure your Snowflake connection is configured.
conn = st.connection("snowflake")

def save_answers_to_snowflake(df):
    """Saves the captured discovery answers to a Snowflake table."""
    try:
        # FIX: Create a copy of the DataFrame to avoid changing the original.
        df_to_save = df.copy()

        # Convert all column names to uppercase to match Snowflake's default behavior.
        df_to_save.columns = [col.upper() for col in df_to_save.columns]

        # USER INPUT REQUIRED: You must create/update the 'SALES_DISCOVERY_ANSWERS' table in Snowflake.
        # Ensure it includes an 'IS_FAVORITE' BOOLEAN column to match the exported data.
        conn.write_pandas(df_to_save, "SALES_DISCOVERY_ANSWERS")
        return True
    except Exception as e:
        st.error(f"Error saving to Snowflake: {e}")
        return False

# ======================================================================================
# LLM Functions powered by Snowflake Cortex (Claude 3.5 Sonnet)
# ======================================================================================

def generate_discovery_questions(website, industry, competitor, persona):
    """
    This function calls the Claude 3.5 Sonnet model via Snowflake Cortex
    to generate discovery questions tailored to a specific persona.
    """
    
    prompt = f"""
    You are an expert Snowflake sales engineer. Your task is to generate a list of discovery questions for a potential customer, specifically tailored for a conversation with a person holding the title of **{persona}**.

    Company Information:
    - Website: {website}
    - Industry: {industry}
    - Assumed Primary Competitor: {competitor}
    - Persona / Title of contact: {persona}

    Based on the information above, please generate three categories of questions. The tone and focus of the questions should be highly relevant to the **{persona}**. For example, C-Level questions should be strategic, while engineer questions should be more technical.
    
    1.  **Technical Discovery**: Questions related to their current data architecture (ingestion, transformation, storage, usage).
    2.  **Business Discovery**: Questions related to likely business challenges they face due to their industry and scale.
    3.  **Competitive Positioning**: Exactly 10 questions designed to highlight Snowflake's advantages over '{competitor}'.

    Constraints:
    - The total number of questions across all categories must not exceed 30.
    - You MUST return the output as a single, valid JSON object.
    - The JSON object should have keys for the categories. The competitive category key should be named "Competitive Positioning: {competitor}".

    Now, generate the persona-tailored questions for the company at {website}.
    """

    try:
        # Manually escape single quotes for SQL and construct the query
        safe_prompt = prompt.replace("'", "''")
        sql_query = f"SELECT SNOWFLAKE.CORTEX.COMPLETE('claude-3-5-sonnet', '{safe_prompt}') as response;"
        
        cursor = conn.cursor()
        cursor.execute(sql_query)
        response_row = cursor.fetchone()
        
        if response_row and response_row[0]:
            llm_response_str = response_row[0]
            json_start = llm_response_str.find('{')
            json_end = llm_response_str.rfind('}') + 1
            
            if json_start != -1 and json_end != 0:
                json_str = llm_response_str[json_start:json_end]
                questions_dict = json.loads(json_str)
                processed_questions = {}
                for category, qs in questions_dict.items():
                    processed_questions[category] = [
                        {"id": str(uuid.uuid4()), "text": q, "answer": "", "favorite": False} for q in qs
                    ]
                return processed_questions
            else:
                st.error("Could not find a valid JSON object in the LLM's response.")
                return {}
        else:
            st.error("The LLM returned an empty response.")
            return {}

    except Exception as e:
        st.error(f"An error occurred while calling the LLM or parsing the response: {e}")
        return {}

def generate_company_summary(website, industry, persona):
    """
    Calls Claude 3.5 Sonnet to generate a brief summary of a company, tailored to a persona.
    """
    prompt = f"""
    You are a skilled business analyst. Based on the company website '{website}' and its industry '{industry}', please provide a concise, one-paragraph summary. 
    The summary should be framed in a way that is most relevant and impactful for a person with the title of **{persona}**. It should touch upon the company's likely business model, its target customers, and potential data-related opportunities or challenges it might face.
    """
    try:
        # Manually escape single quotes for SQL and construct the query
        safe_prompt = prompt.replace("'", "''")
        sql_query = f"SELECT SNOWFLAKE.CORTEX.COMPLETE('claude-3-5-sonnet', '{safe_prompt}') as response;"

        cursor = conn.cursor()
        cursor.execute(sql_query)
        response_row = cursor.fetchone()
        if response_row and response_row[0]:
            return response_row[0]
        else:
            return "Could not generate company summary."
    except Exception as e:
        st.error(f"Error generating company summary: {e}")
        return "An error occurred while generating the summary."

def get_chatbot_response(company_info, chat_history):
    """
    This function calls Claude 3.5 Sonnet via Snowflake Cortex to generate a response for the chat interface.
    """
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

    Based on all of this context, provide a concise and helpful answer to the last user question, keeping the contact's title in mind. Address the user directly. Do not repeat the question.
    """

    try:
        # Manually escape single quotes for SQL and construct the query
        safe_prompt = prompt.replace("'", "''")
        sql_query = f"SELECT SNOWFLAKE.CORTEX.COMPLETE('claude-3-5-sonnet', '{safe_prompt}') as response;"

        cursor = conn.cursor()
        cursor.execute(sql_query)
        response_row = cursor.fetchone()
        
        if response_row and response_row[0]:
            return response_row[0]
        else:
            return "I'm sorry, I couldn't generate a response. Please try again."

    except Exception as e:
        st.error(f"Error calling LLM: {e}")
        return "There was an error communicating with the assistant."

def generate_more_questions_for_category(website, industry, competitor, persona, category, existing_questions):
    """
    Calls Claude 3.5 Sonnet to generate additional questions for a specific category.
    """
    existing_questions_str = "\n".join([f"- {q}" for q in existing_questions])

    prompt = f"""
    You are an expert Snowflake sales engineer. Your task is to generate additional discovery questions for a potential customer, specifically for the category '{category}' and tailored for a conversation with a **{persona}**.

    Company Information:
    - Website: {website}
    - Industry: {industry}
    - Assumed Primary Competitor: {competitor}
    - Persona / Title of contact: {persona}

    You have already generated the following questions for the '{category}' category:
    {existing_questions_str}

    Now, please generate exactly 5 **new and distinct** questions for this category. These questions should not repeat the ones listed above. The new questions should maintain the same focus and tone appropriate for the persona.

    Return your response as a single, valid JSON object containing a list of strings.
    Example JSON structure:
    {{
      "new_questions": [
        "New Question 1...",
        "New Question 2...",
        "New Question 3...",
        "New Question 4...",
        "New Question 5..."
      ]
    }}
    """

    try:
        # Manually escape single quotes for SQL and construct the query
        safe_prompt = prompt.replace("'", "''")
        sql_query = f"SELECT SNOWFLAKE.CORTEX.COMPLETE('claude-3-5-sonnet', '{safe_prompt}') as response;"
        
        cursor = conn.cursor()
        cursor.execute(sql_query)
        response_row = cursor.fetchone()
        
        if response_row and response_row[0]:
            llm_response_str = response_row[0]
            json_start = llm_response_str.find('{')
            json_end = llm_response_str.rfind('}') + 1
            
            if json_start != -1 and json_end != 0:
                json_str = llm_response_str[json_start:json_end]
                new_questions_dict = json.loads(json_str)
                new_qs_list = new_questions_dict.get("new_questions", [])
                
                # Process into the standard format
                processed_questions = [
                    {"id": str(uuid.uuid4()), "text": q, "answer": "", "favorite": False} for q in new_qs_list
                ]
                return processed_questions
            else:
                st.error("Could not find a valid JSON object in the LLM's response for additional questions.")
                return []
        else:
            st.error("The LLM returned an empty response when generating more questions.")
            return []

    except Exception as e:
        st.error(f"An error occurred while generating more questions: {e}")
        return []

# ======================================================================================
# Helper Functions for Exporting
# ======================================================================================

def create_pdf(export_df, company_info):
    """Generates a PDF from the exported data."""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, f"Discovery Notes: {company_info.get('website')}", 0, 1, 'C')
    pdf.ln(10)

    # Group data by category to structure the PDF
    for category, group in export_df.groupby('question_category'):
        pdf.set_font("Helvetica", "B", 12)
        # Encode to latin-1, replacing unsupported characters
        clean_category = category.encode('latin-1', 'replace').decode('latin-1')
        pdf.cell(0, 10, clean_category, 0, 1)
        
        for index, row in group.iterrows():
            # Handle favorite status
            fav_char = " (Favorite)" if row['favorite'] else ""
            question_text = f"Q: {row['question']}{fav_char}"
            answer_text = f"A: {row['answer']}"

            pdf.set_font("Helvetica", "B", 10)
            pdf.multi_cell(0, 5, question_text.encode('latin-1', 'replace').decode('latin-1'))
            pdf.set_font("Helvetica", "", 10)
            pdf.multi_cell(0, 5, answer_text.encode('latin-1', 'replace').decode('latin-1'))
            pdf.ln(5)
    
    return pdf.output(dest='S').encode('latin-1')

def format_for_gdocs(export_df, company_info):
    """Formats the data into a markdown string for easy copy-pasting."""
    doc_text = [f"# Discovery Notes: {company_info.get('website')}\n"]
    for category, group in export_df.groupby('question_category'):
        doc_text.append(f"## {category}\n")
        for index, row in group.iterrows():
            fav_char = " **(Favorite)**" if row['favorite'] else ""
            doc_text.append(f"**Q: {row['question']}**{fav_char}\n")
            # Handle multi-line answers
            answer = row['answer'].replace('\n', '\n> ')
            doc_text.append(f"> {answer if answer else 'No answer provided.'}\n")
        doc_text.append("---\n")
    return "\n".join(doc_text)

# ======================================================================================
# Main App Logic
# ======================================================================================

# Initialize session state
if 'questions' not in st.session_state:
    st.session_state.questions = {}
if 'company_info' not in st.session_state:
    st.session_state.company_info = {}
if "messages" not in st.session_state:
    st.session_state.messages = []
if "company_summary" not in st.session_state:
    st.session_state.company_summary = ""

# Callback functions
def toggle_favorite(q_id):
    for category in st.session_state.questions:
        for question in st.session_state.questions[category]:
            if question['id'] == q_id:
                question['favorite'] = not question['favorite']
                return

def delete_question(q_id):
    for category, questions_list in st.session_state.questions.items():
        st.session_state.questions[category] = [q for q in questions_list if q['id'] != q_id]

def clear_session():
    keys_to_clear = ['questions', 'company_info', 'messages', 'company_summary']
    for key in keys_to_clear:
        if key in st.session_state:
            del st.session_state[key]
    # Also clear widget states
    for key in list(st.session_state.keys()):
        if key.startswith("ans_") or key.startswith("fav_") or key.startswith("del_"):
            del st.session_state[key]


# Create tabs
tab1, tab2 = st.tabs(["Account Research & Discovery", "Snowflake Solution Chatter"])

# --------------------------------------------------------------------------------------
# TAB 1: Account Research & Discovery
# --------------------------------------------------------------------------------------
with tab1:
    col_header1, col_header2 = st.columns([4, 1])
    with col_header1:
        st.header("Step 1: Research an Account")
    with col_header2:
        if st.button("Clear & Restart Session", use_container_width=True):
            clear_session()
            st.rerun()

    st.markdown("Enter the company's details to generate a persona-tailored summary and discovery questions.")
    
    with st.form("research_form"):
        website = st.text_input("**Company Website**", placeholder="e.g., https://www.example.com", value=st.session_state.company_info.get('website', ''))
        industry = st.text_input("**Industry**", placeholder="e.g., Retail, Financial Services", value=st.session_state.company_info.get('industry', ''))
        
        persona_options = ["C-Level (CEO, CIO, CDO)", "VP of Engineering / Data", "Director of Analytics / BI", "Data Scientist / ML Engineer", "Data/Analytics Engineer"]
        persona = st.selectbox(
            "**Select Title of Person You're Meeting With**",
            persona_options,
            index=persona_options.index(st.session_state.company_info.get('persona', "C-Level (CEO, CIO, CDO)"))
        )

        competitor = st.selectbox(
            "**Select Primary Competitor**",
            ("Databricks", "Microsoft Fabric", "AWS", "Do Nothing (i.e., keep existing technology)"),
            index=["Databricks", "Microsoft Fabric", "AWS", "Do Nothing (i.e., keep existing technology)"].index(st.session_state.company_info.get('competitor', 'Databricks'))
        )
        research_button = st.form_submit_button("Generate Summary & Questions", type="primary")

    if research_button:
        if not website or not industry:
            st.warning("Please provide both a website and an industry.")
        else:
            with st.spinner("Researching company and generating content..."):
                st.session_state.company_info = {'website': website, 'industry': industry, 'competitor': competitor, 'persona': persona}
                st.session_state.company_summary = generate_company_summary(website, industry, persona)
                st.session_state.questions = generate_discovery_questions(website, industry, competitor, persona)
                if not st.session_state.questions:
                    st.error("Failed to generate questions. Please check the error messages above.")
                st.rerun()

    st.divider()

    if st.session_state.company_summary or st.session_state.questions:
        if st.session_state.company_summary:
            st.header(f"Company Overview for a {st.session_state.company_info.get('persona', 'Contact')}")
            st.info(st.session_state.company_summary)

        if st.session_state.questions:
            st.header("Step 2: Ask Questions and Capture Responses")
            st.markdown(f"Discovery questions for **{st.session_state.company_info.get('website')}**")

            # Update answers from widget state before displaying
            for category, questions_list in st.session_state.questions.items():
                for question in questions_list:
                    widget_key = f"ans_{question['id']}"
                    if widget_key in st.session_state:
                        question['answer'] = st.session_state[widget_key]

            for category, questions_list in st.session_state.questions.items():
                if not questions_list: continue
                
                cat_col1, cat_col2 = st.columns([3, 1])
                with cat_col1:
                    st.subheader(category)
                with cat_col2:
                    # Button to generate more questions for the current category
                    if st.button(f"Generate 5 More", key=f"more_{category.replace(' ', '_')}", use_container_width=True):
                        with st.spinner(f"Generating more questions for {category}..."):
                            existing_q_texts = [q['text'] for q in questions_list]
                            new_questions = generate_more_questions_for_category(
                                st.session_state.company_info['website'],
                                st.session_state.company_info['industry'],
                                st.session_state.company_info['competitor'],
                                st.session_state.company_info['persona'],
                                category,
                                existing_q_texts
                            )
                            if new_questions:
                                st.session_state.questions[category].extend(new_questions)
                                st.rerun()
                            else:
                                st.warning("Could not generate additional questions.")
                
                for i, question in enumerate(questions_list):
                    q_col1, q_col2 = st.columns([1, 15])
                    with q_col1:
                        fav_icon = "⭐" if question['favorite'] else "☆"
                        st.button(fav_icon, key=f"fav_{question['id']}", on_click=toggle_favorite, args=(question['id'],), help="Toggle Favorite")
                        st.button("🗑️", key=f"del_{question['id']}", on_click=delete_question, args=(question['id'],), help="Delete Question")
                    with q_col2:
                        st.markdown(f"**Q: {question['text']}**")
                        st.text_area(
                            "Capture Answer", 
                            value=question['answer'],
                            key=f"ans_{question['id']}",
                            label_visibility="collapsed"
                        )
            
            st.divider()

            st.header("Step 3: Export or Save Responses")
            st.markdown("Once you have captured the answers, you can export them or save them directly to Snowflake.")

            # Prepare data for export, ensuring all answers are captured from the latest state
            export_data = []
            company_name = st.session_state.company_info.get('website', 'N/A').replace('https://','').replace('www.','').split('.')[0].capitalize()
            for category, questions_list in st.session_state.questions.items():
                for question in questions_list:
                    # Get the most recent answer from the widget's state
                    answer = st.session_state.get(f"ans_{question['id']}", question['answer'])
                    export_data.append({
                        "id": question['id'],
                        "company_name": company_name,
                        "company_website": st.session_state.company_info.get('website', 'N/A'),
                        "question_category": category,
                        "question": question['text'],
                        "answer": answer,
                        "favorite": question['favorite'],
                        "saved_at": datetime.utcnow()
                    })
            
            if export_data:
                export_df = pd.DataFrame(export_data)

                col1, col2, col3 = st.columns(3)
                with col1:
                    st.download_button(
                        label="📥 Download as CSV",
                        data=export_df.to_csv(index=False).encode('utf-8'),
                        file_name=f"discovery_notes_{company_name}.csv",
                        mime='text/csv',
                    )
                with col2:
                    if st.button("💾 Save to Snowflake"):
                        with st.spinner("Saving to Snowflake..."):
                            if save_answers_to_snowflake(export_df):
                                st.success("Successfully saved responses to Snowflake!")

                with col3:
                    if st.button("✅ Copy for Google Docs"):
                        gdocs_text = format_for_gdocs(export_df, st.session_state.company_info)
                        st.text_area("Formatted Text", value=gdocs_text, height=1000)
                        st.info("Use Ctrl+C or Cmd+C to copy the text above.", icon="📋")


# --------------------------------------------------------------------------------------
# TAB 2: Snowflake Solution Chatter
# --------------------------------------------------------------------------------------
with tab2:
    st.header("Chat About Snowflake Solutions")

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
                    full_response = get_chatbot_response(
                        st.session_state.company_info, 
                        st.session_state.messages
                    )
                    message_placeholder.markdown(full_response)
            
            st.session_state.messages.append({"role": "assistant", "content": full_response})
