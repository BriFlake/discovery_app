# LLM Functions Module
# All AI/LLM related functionality using Snowflake Cortex

import streamlit as st
import json
import uuid
import pandas as pd
from modules.snowflake_utils import execute_query

def cortex_request(prompt, json_output=True, suppress_warnings=False):
    """Main function to call Snowflake Cortex Complete with the selected model"""
    selected_model = st.session_state.get('selected_model', 'claude-3-5-sonnet')
    
    llm_response_str = ""
    try:
        safe_prompt = prompt.replace("'", "''")
        sql_query = f"SELECT SNOWFLAKE.CORTEX.COMPLETE('{selected_model}', '{safe_prompt}') as response"
        
        # Use execute_query instead of cursor
        response_df = execute_query(sql_query)
        if response_df.empty or response_df.iloc[0]['RESPONSE'] is None:
            st.error("The AI model returned an empty response.")
            return None
        llm_response_str = response_df.iloc[0]['RESPONSE']
    except Exception as e:
        if "max tokens" in str(e) and "exceeded" in str(e):
            st.session_state.token_error_flag = True
        else:
            st.error(f"An error occurred while calling the LLM: {e}")
        return None

    if not json_output:
        return llm_response_str

    try:
        # Try to find JSON object first
        json_start = llm_response_str.find('{')
        json_end = llm_response_str.rfind('}') + 1
        
        # If no object found, try to find JSON array
        if json_start == -1:
            json_start = llm_response_str.find('[')
            json_end = llm_response_str.rfind(']') + 1
        
        if json_start != -1 and json_end != 0:
            json_str = llm_response_str[json_start:json_end]
            return json.loads(json_str)
        else:
            raise json.JSONDecodeError("No JSON object or array found in response", llm_response_str, 0)
    except json.JSONDecodeError:
        if not suppress_warnings:
            st.warning("Initial JSON parsing failed. Attempting to repair with another LLM call...")
        
        repair_prompt_text = f"Fix this JSON and return ONLY the corrected JSON with no other text:\n\n{llm_response_str}\n\nReturn ONLY valid JSON:"
        safe_repair_prompt = repair_prompt_text.replace("'", "''")
        
        try:
            repair_sql_query = f"SELECT SNOWFLAKE.CORTEX.COMPLETE('{selected_model}', '{safe_repair_prompt}') as response"
            
            # Use execute_query instead of cursor
            repair_response_df = execute_query(repair_sql_query)
            if repair_response_df.empty or repair_response_df.iloc[0]['RESPONSE'] is None:
                if not suppress_warnings:
                    st.error("LLM repair attempt returned an empty response.")
                return None
            
            repaired_llm_str = repair_response_df.iloc[0]['RESPONSE'].strip()
            
            # Enhanced JSON extraction with multiple attempts
            def extract_and_parse_json(text):
                # Try 1: Look for JSON array first
                array_start = text.find('[')
                if array_start != -1:
                    # Find matching closing bracket
                    bracket_count = 0
                    for i, char in enumerate(text[array_start:], array_start):
                        if char == '[':
                            bracket_count += 1
                        elif char == ']':
                            bracket_count -= 1
                            if bracket_count == 0:
                                try:
                                    return json.loads(text[array_start:i+1])
                                except:
                                    break
                
                # Try 2: Look for JSON object
                obj_start = text.find('{')
                if obj_start != -1:
                    # Find matching closing brace
                    brace_count = 0
                    for i, char in enumerate(text[obj_start:], obj_start):
                        if char == '{':
                            brace_count += 1
                        elif char == '}':
                            brace_count -= 1
                            if brace_count == 0:
                                try:
                                    return json.loads(text[obj_start:i+1])
                                except:
                                    break
                
                # Try 3: Split by lines and try each line
                for line in text.split('\n'):
                    line = line.strip()
                    if line.startswith('[') or line.startswith('{'):
                        try:
                            return json.loads(line)
                        except:
                            continue
                
                return None
            
            result = extract_and_parse_json(repaired_llm_str)
            if result:
                return result
            else:
                if not suppress_warnings:
                    st.error("JSON repair failed - could not extract valid JSON.")
                return None
                
        except Exception as repair_e:
            if not suppress_warnings:
                st.error(f"An error occurred during JSON repair: {repair_e}")
            return None

def research_person(name, title, company_info):
    """Generates conversation starters for a specific person."""
    company_name = company_info.get('website', 'their company')
    prompt = f"""
    You are a professional relationship-building assistant. Your goal is to find insightful and relevant conversation starters.
    Based on your public knowledge about a person named **{name}**, who holds the title of **{title}** at **{company_name}**, generate potential topics for discussion.

    Return your response as a single, valid JSON object with the following keys:
    - "summary": A concise, one-paragraph summary of this person's likely professional focus and expertise, based on their title and company.
    - "insights": A list of 3-5 bullet points identifying key technical skills (e.g., Python, SQL, AWS, AI/ML) and business expertise (e.g., e-commerce, risk management, supply chain) this person might have.
    - "topics": A JSON object with three keys: "business", "technical", and "personal". Each key should contain a list of 2-3 suggested questions or topics you could discuss with them to build rapport. For "personal", suggest topics based on common interests for someone in their role and industry (e.g., recent industry conferences, popular tech books, local events).
    """
    return cortex_request(prompt)

def generate_discovery_questions(website, industry, competitor, persona):
    """Generate discovery questions for a potential customer"""
    prompt = f"""
    You are an expert Snowflake sales engineer. Generate discovery questions for a potential customer with the title of **{persona}**.
    Company Information: Website: {website}, Industry: {industry}, Assumed Primary Competitor: {competitor}.
    
    Generate three categories: **Technical Discovery**, **Business Discovery**, and exactly 10 questions for **Competitive Positioning vs. {competitor}**.
    The total number of questions must not exceed 30.
    
    For each question, provide:
    1. The question text
    2. A brief explanation of why this question is important to answer (1-2 sentences)
    
    Return as a single, valid JSON object with this structure:
    {{
        "Technical Discovery": [
            {{"text": "Question text here", "explanation": "Why this question is important to answer"}},
            {{"text": "Another question", "explanation": "Explanation for importance"}}
        ],
        "Business Discovery": [
            {{"text": "Business question", "explanation": "Why this matters for business understanding"}}
        ],
        "Competitive Positioning vs. {competitor}": [
            {{"text": "Competitive question", "explanation": "Why understanding this competitive aspect is crucial"}}
        ]
    }}
    """
    questions_dict = cortex_request(prompt)
    if questions_dict:
        temp_processed = {}
        competitive_key_name = f"Competitive Positioning vs. {competitor}"
        for category, qs in questions_dict.items():
            if "Competitive Positioning" in category or competitor in category:
                temp_processed[competitive_key_name] = [
                    {
                        "id": str(uuid.uuid4()),
                        "text": q.get("text", q) if isinstance(q, dict) else q,
                        "explanation": q.get("explanation", "Understanding this helps qualify the opportunity") if isinstance(q, dict) else "Understanding this helps qualify the opportunity",
                        "answer": "",
                        "favorite": False
                    } for q in qs
                ]
            else:
                temp_processed[category.title()] = [
                    {
                        "id": str(uuid.uuid4()),
                        "text": q.get("text", q) if isinstance(q, dict) else q,
                        "explanation": q.get("explanation", "This question provides valuable sales insights") if isinstance(q, dict) else "This question provides valuable sales insights",
                        "answer": "",
                        "favorite": False
                    } for q in qs
                ]
        
        ordered_questions = {}
        category_order = ["Technical Discovery", "Business Discovery", competitive_key_name]

        for category in category_order:
            if category.title() in temp_processed:
                ordered_questions[category.title()] = temp_processed[category.title()]
            elif category in temp_processed:
                ordered_questions[category] = temp_processed[category]
        
        for category, questions in temp_processed.items():
            if category not in ordered_questions:
                ordered_questions[category] = questions
                
        return ordered_questions
    return {}

def generate_company_summary(website, industry, contact_title):
    """Generate company overview with key initiative suggestions"""
    prompt = f"""
    Analyze the company at {website} in the {industry} industry. The contact is a {contact_title}.
    
    Provide a comprehensive company overview including:
    1. Brief company description and business model
    2. Key challenges they likely face in their industry
    3. Technology and data priorities for someone in the {contact_title} role
    
    Then suggest 2 key business initiatives that would be most relevant for a {contact_title} at a {industry} company:
    
    Format your response as a JSON object:
    {{
        "company_overview": "Detailed overview paragraph",
        "suggested_initiatives": [
            {{
                "title": "Initiative 1 Title",
                "description": "Brief description of why this initiative matters",
                "relevance": "Why this is relevant for the contact's role"
            }},
            {{
                "title": "Initiative 2 Title", 
                "description": "Brief description of why this initiative matters",
                "relevance": "Why this is relevant for the contact's role"
            }}
        ]
    }}
    """
    
    result = cortex_request(prompt, json_output=True)
    if result:
        return result
    else:
        # Fallback response
        return {
            "company_overview": f"A {industry} company with website {website}. The {contact_title} likely focuses on data strategy, technology implementation, and business growth initiatives.",
            "suggested_initiatives": [
                {
                    "title": "Data Modernization",
                    "description": "Upgrade data infrastructure and analytics capabilities",
                    "relevance": "Critical for data-driven decision making"
                },
                {
                    "title": "AI/ML Implementation",
                    "description": "Implement artificial intelligence and machine learning solutions",
                    "relevance": "Essential for competitive advantage and automation"
                }
            ]
        }

def generate_initiative_questions(website, industry, contact_title, initiative_title, initiative_description):
    """Generate discovery questions for a specific business initiative"""
    prompt = f"""You are a sales discovery expert. Generate exactly 5 targeted discovery questions for the business initiative: "{initiative_title}".

Company: {website}
Industry: {industry}
Contact: {contact_title}
Initiative: {initiative_description}

Your questions should:
1. Uncover current state challenges
2. Identify pain points and gaps  
3. Explore timeline and priorities
4. Understand decision-making process
5. Reveal success criteria

Format your response as a JSON array containing exactly 5 question objects. Each object must have "text", "context", and "importance" fields.

Example format:
[
  {{"text": "What specific challenges are you facing with [topic]?", "context": "Understanding pain points", "importance": "high"}},
  {{"text": "What's your timeline for addressing [topic]?", "context": "Project urgency", "importance": "medium"}}
]

Return only the JSON array with no additional text or explanation:"""
    
    result = cortex_request(prompt, json_output=True, suppress_warnings=True)
    
    # Handle different response formats
    if result:
        if isinstance(result, list):
            # Direct array response
            return result[:5]  # Ensure exactly 5 questions
        elif isinstance(result, dict) and 'questions' in result:
            # Object with questions key
            return result['questions'][:5]
        elif isinstance(result, dict):
            # Try to extract array from any key
            for key, value in result.items():
                if isinstance(value, list):
                    return value[:5]
    
    # Return empty list if LLM fails to generate questions - no fallback questions
    return []

def generate_custom_topic_questions(website, industry, contact_title, custom_topic):
    """Generate 5 discovery questions for a custom topic"""
    prompt = f"""You are a sales discovery expert. Generate exactly 5 discovery questions for the custom topic: "{custom_topic}"

Company: {website}
Industry: {industry}
Contact: {contact_title}
Topic Focus: {custom_topic}

Requirements:
- Questions should be open-ended and thought-provoking
- Focus specifically on {custom_topic}
- Relevant to {industry}
- Appropriate for a {contact_title}

Format your response as a JSON array containing exactly 5 question objects. Each object must have "text", "context", and "importance" fields.

Example format:
[
  {{"text": "How are you currently handling [topic]?", "context": "Understanding current state", "importance": "high"}},
  {{"text": "What challenges do you face with [topic]?", "context": "Identifying pain points", "importance": "high"}}
]

Return only the JSON array with no additional text or explanation:"""
    
    result = cortex_request(prompt, json_output=True, suppress_warnings=True)
    
    # Handle different response formats
    if result:
        if isinstance(result, list):
            return result[:5]  # Ensure exactly 5 questions
        elif isinstance(result, dict) and 'questions' in result:
            return result['questions'][:5]
        elif isinstance(result, dict):
            # Try to extract array from any key
            for key, value in result.items():
                if isinstance(value, list):
                    return value[:5]
    
    # Return empty list if LLM fails to generate questions - no fallback questions
    return []

def generate_more_questions_for_category(website, industry, competitor, contact_title, category, existing_questions):
    """Generate additional questions for a specific category"""
    existing_texts = [q['text'] for q in existing_questions]
    existing_questions_str = '\n'.join(f"- {text}" for text in existing_texts)
    
    prompt = f"""
    You are an expert Snowflake sales engineer. Generate 3-5 additional discovery questions for the "{category}" category.
    
    Company Information: Website: {website}, Industry: {industry}, Competitor: {competitor}, Contact: {contact_title}
    
    Existing questions in this category:
    {existing_questions_str}
    
    Generate NEW questions that are different from the existing ones but still relevant to the "{category}" category.
    
    For each question, provide:
    1. The question text
    2. A brief explanation of why this question is important to answer (1-2 sentences)
    
    Return as a JSON array with this structure:
    [
        {{"text": "New question text here", "explanation": "Why this question is important to answer"}},
        {{"text": "Another new question", "explanation": "Explanation for importance"}}
    ]
    """
    
    questions_list = cortex_request(prompt, json_output=True)
    if questions_list:
        return [
            {
                "id": str(uuid.uuid4()),
                "text": q.get("text", q) if isinstance(q, dict) else q,
                "explanation": q.get("explanation", "This additional question provides deeper insights") if isinstance(q, dict) else "This additional question provides deeper insights",
                "answer": "",
                "favorite": False
            }
            for q in questions_list
        ]
    return []

def generate_roadmap(company_info, discovery_notes_str, priority):
    """Generate a strategic roadmap based on discovery notes"""
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
    """Get a chatbot response for solution chat"""
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

def autofill_answers_from_notes(notes_text, questions_input):
    """Auto-populate question answers from provided notes - processes ALL questions"""
    if not notes_text.strip() or not questions_input:
        return None
    
    # Handle both list and dictionary formats
    if isinstance(questions_input, list):
        # Convert list format to categorized format for processing
        questions_dict = {
            'Technical': [],
            'Business': [],
            'Competitive': []
        }
        
        for q in questions_input:
            if isinstance(q, dict):
                category = q.get('category', '').lower()
                text_field = q.get('text', '')
                
                # Handle case where 'text' might be a dictionary or other non-string type
                if isinstance(text_field, str):
                    text = text_field.lower()
                elif isinstance(text_field, dict):
                    # If text is a dict, try to extract string value
                    text = str(text_field.get('text', text_field.get('question', str(text_field)))).lower()
                else:
                    text = str(text_field).lower()
                
                if 'technical' in category or 'tech' in category:
                    questions_dict['Technical'].append(q)
                elif 'business' in category or 'biz' in category:
                    questions_dict['Business'].append(q)
                elif 'competitive' in category or 'competitor' in category or 'competition' in category:
                    questions_dict['Competitive'].append(q)
                elif any(word in text for word in ['technical', 'technology', 'system', 'integration', 'data', 'platform']):
                    questions_dict['Technical'].append(q)
                elif any(word in text for word in ['business', 'process', 'workflow', 'organization', 'team', 'department']):
                    questions_dict['Business'].append(q)
                elif any(word in text for word in ['competitor', 'competition', 'vendor', 'alternative', 'current solution']):
                    questions_dict['Competitive'].append(q)
                else:
                    questions_dict['Technical'].append(q)
        
        return_as_list = True  # Flag to return in original format
    else:
        # Already in dictionary format
        questions_dict = questions_input
        return_as_list = False
    
    # Process all questions in batches to handle large question sets
    updated_questions = {}
    categories_processed = 0
    categories_updated = 0
    
    for category, questions in questions_dict.items():
        categories_processed += 1
        print(f"Processing category: {category} with {len(questions)} questions")
        
        # Process each category separately to ensure complete coverage
        category_questions = []
        for i, q in enumerate(questions):
            category_questions.append({
                "index": i,
                "text": q.get('text', ''),
                "current_answer": q.get('answer', '')
            })
        
        # Create prompt for this category
        questions_summary = "\\n".join([
            f"{i+1}. {q['text']}"
            for i, q in enumerate(category_questions)
        ])
        
        prompt = f"""You are an expert analyst. Extract relevant answers from the provided notes for questions in the "{category}" category.

NOTES/RESEARCH:
{notes_text}

DISCOVERY QUESTIONS FOR {category}:
{questions_summary}

For each question above, provide a concise answer if you can find relevant information in the notes. If no relevant information is found, return null.

Return as JSON object with question numbers as keys:
{{
    "1": "Answer based on notes" or null,
    "2": "Answer based on notes" or null,
    "3": "Answer based on notes" or null
}}

Return only the JSON object with no additional text:"""
        
        result = cortex_request(prompt, json_output=True)
        
        # Apply results to this category
        updated_category_questions = questions.copy()
        answers_found = 0
        
        if result and isinstance(result, dict):
            for i, question in enumerate(updated_category_questions):
                answer_key = str(i + 1)
                if answer_key in result and result[answer_key] and result[answer_key] != "null":
                    # Only update if we don't already have an answer
                    if not question.get('answer', '').strip():
                        updated_category_questions[i]['answer'] = result[answer_key]
                        answers_found += 1
        
        if answers_found > 0:
            categories_updated += 1
            print(f"Updated {answers_found} answers in {category}")
        
        updated_questions[category] = updated_category_questions
    
    print(f"Auto-fill complete: {categories_updated}/{categories_processed} categories updated")
    
    # Return in the same format as the input
    if return_as_list:
        # Convert back to list format
        result_list = []
        for category_questions in updated_questions.values():
            result_list.extend(category_questions)
        return result_list
    else:
        return updated_questions 

def autofill_category_from_notes(notes_text, category, questions_in_category):
    """Auto-fill answers for a single category from notes"""
    max_chars = 12000 
    if len(notes_text) > max_chars:
        notes_text = notes_text[:max_chars]
    
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
    6. CRITICAL: The returned JSON must be perfectly formatted. Pay very close attention to adding a comma `,` between each object in the list. Do not include a trailing comma after the last object in the list.
    """
    response = cortex_request(prompt)
    if response and "answered_questions" in response:
        return response["answered_questions"]
    return None

def generate_initial_value_hypothesis(company_info):
    """Generate an initial value hypothesis before discovery"""
    prompt = f"""
    You are a senior business value consultant for Snowflake. Your task is to create an initial value hypothesis for a potential customer *before* a formal discovery call.
    **Customer Context:**
    - Company Website: {company_info.get('website', 'N/A')}
    - Industry: {company_info.get('industry', 'N/A')}
    **Instructions:**
    Based *only* on the publicly available information implied by the website and industry, generate a compelling value hypothesis. Structure your response in Markdown with the following sections:
    1.  **Executive Summary:** A brief overview of the likely value Snowflake can provide.
    2.  **Hypothesized Value Drivers:**
        * **Making Money:** How can this company likely leverage data with Snowflake to increase revenue or create new revenue streams?
        * **Reducing Costs:** What are the most probable areas where Snowflake could help reduce operational or infrastructure costs?
        * **Driving Innovation:** How might Snowflake enable them to innovate faster, for example, with AI/ML or new data applications?
    3.  **Potential Snowflake Use Cases & Suspected Value:**
        * Provide a list of 3-5 specific, high-impact use cases for Snowflake tailored to this company.
        * For each use case, provide a name, a brief explanation, and assign a 'Suspected Business Value' (e.g., Very High, High, Medium, Low). Format this as a list.
    This hypothesis is a starting point for a sales conversation. The entire response must be in well-formatted Markdown.
    """
    return cortex_request(prompt, json_output=False)

def generate_business_case(company_info, discovery_notes_str):
    """Generate a business case based on discovery notes"""
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
    """Generate competitive argument from competitor's perspective"""
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

def generate_outreach_emails(company_info, discovery_notes_str, roadmap_df):
    """Generate outreach emails based on discovery and roadmap"""
    roadmap_str = roadmap_df.to_string() if roadmap_df is not None and not roadmap_df.empty else "No roadmap generated yet."
    prompt = f"""
    You are an expert enterprise software salesperson specializing in high-value business outcomes. Your goal is to draft 2 distinct, compelling outreach emails to a **{company_info.get('contact_title', company_info.get('persona', 'contact'))}** at **{company_info.get('website')}**.
    
    **Discovery Insights & Business Value Observations:**
    ---
    {discovery_notes_str}
    ---
    **High-Value Snowflake Opportunities:**
    ---
    {roadmap_str}
    ---
    
    **Instructions:**
    1.  Draft TWO different email versions focused on the HIGHEST business value opportunities identified in discovery.
    2.  Each email should be 120-150 words and reference specific quantifiable business impacts, cost savings, or revenue opportunities.
    3.  Tie each email to the most compelling pain points that represent significant business value if solved.
    4.  Focus on ROI, competitive advantage, and strategic business outcomes rather than just technical features.
    5.  Include a clear, specific call-to-action for the next meeting.
        6.  Return as JSON with keys "email_1" and "email_2". Each containing "subject" and "body".
    7.  IMPORTANT: Return only valid JSON. Escape special characters properly (\\n for newlines).
    """
    return cortex_request(prompt, suppress_warnings=True)

def regenerate_single_email(company_info, discovery_notes_str, roadmap_df, existing_emails, email_to_replace_key):
    """Regenerate a single email to be different from existing ones"""
    other_emails_str = ""
    for key, data in existing_emails.items():
        if key != email_to_replace_key:
            other_emails_str += f"Existing Draft ({key}):\nSubject: {data.get('subject')}\nBody: {data.get('body')}\n\n"
    roadmap_str = roadmap_df.to_string() if not roadmap_df.empty else "No roadmap generated yet."
    prompt = f"""
    You are an expert salesperson. Redraft a single, captivating outreach email for a {company_info.get('persona')} at {company_info.get('website')}.
    Here is the original context:
    - Customer Pains: {discovery_notes_str}
    - Proposed Projects: {roadmap_str}
    Here are the other email drafts you have already written. DO NOT REPEAT OR REUSE the style or content from these existing drafts:
    ---
    {other_emails_str}
    ---
    INSTRUCTION:
    Generate one new, completely distinct email version that is different from the existing drafts. It must be short and professional.
    Return it as a single, valid JSON object with "subject" and "body" keys.
    IMPORTANT: The final output must be only the JSON object. All strings within the JSON must be properly formatted with special characters like newlines escaped as \\n.
    """
    return cortex_request(prompt, suppress_warnings=True)

def regenerate_single_linkedin_message(company_info, discovery_notes_str, roadmap_df, existing_messages, message_to_replace_key):
    """Regenerate a single LinkedIn message to be different from existing ones"""
    other_messages_str = ""
    for key, data in existing_messages.items():
        if key != message_to_replace_key:
            if isinstance(data, dict):
                if 'body' in data:
                    content = data['body']
                elif 'opening' in data and 'body' in data:
                    content = f"{data['opening']} {data['body']}"
                else:
                    content = str(data)
            else:
                content = str(data)
            other_messages_str += f"Existing Message ({key}):\n{content}\n\n"
    
    roadmap_str = roadmap_df.to_string() if not roadmap_df.empty else "No roadmap generated yet."
    prompt = f"""
    You are an expert at LinkedIn outreach. Redraft a single, compelling LinkedIn message for a {company_info.get('contact_title', company_info.get('persona', 'contact'))} at {company_info.get('website')}.
    
    Context:
    - High-Value Discovery Insights: {discovery_notes_str}
    - Strategic Business Opportunities: {roadmap_str}
    
    Here are the other LinkedIn messages you have already written. DO NOT REPEAT OR REUSE the style or content from these existing messages:
    ---
    {other_messages_str}
    ---
    
    Generate one new, completely distinct LinkedIn message (60-80 words) that is different from the existing messages. Focus on high business value outcomes.
    Return as JSON with a "body" field only.
    
    IMPORTANT: Return only valid JSON. Escape newlines as \\n.
    """
    return cortex_request(prompt, suppress_warnings=True)

def generate_linkedin_messages(company_info, discovery_notes_str, roadmap_df):
    """Generate LinkedIn messages for outreach"""
    roadmap_str = roadmap_df.to_string() if roadmap_df is not None and not roadmap_df.empty else "No roadmap generated yet."
    prompt = f"""
    You are an expert at LinkedIn outreach focused on high-value business outcomes. Draft 2 distinct, concise LinkedIn messages to a **{company_info.get('contact_title', company_info.get('persona', 'contact'))}** at **{company_info.get('website')}**.
    
    **High-Value Discovery Insights:**
    - {discovery_notes_str}
    
    **Strategic Business Opportunities:**
    - {roadmap_str}
    
    **LinkedIn Message Requirements:**
    1. Each message 60-80 words maximum (LinkedIn limits)
    2. Professional but conversational tone 
    3. Lead with the HIGHEST business value observation from discovery (ROI, cost savings, competitive advantage)
    4. Focus on business outcomes, not technical features
    5. Include specific call-to-action for a strategic discussion
    6. Personalize to their role and company's industry
    
    Return two message versions as JSON with keys "message_1" and "message_2". Each containing "body" field only.
    
    IMPORTANT: Return only valid JSON. Escape newlines as \\n.
    """
    return cortex_request(prompt)

def generate_people_insights(company_info, contact_name, contact_title, background_notes, discovery_notes_str):
    """Generate priority and engagement insights for a specific contact"""
    prompt = f"""
    You are an expert sales strategist analyzing a key contact for effective engagement. Based on the provided information, generate insights to help with strategic outreach.

    **Company Context:**
    - Website: {company_info.get('website', 'N/A')}
    - Industry: {company_info.get('industry', 'N/A')}
    - Primary Contact: {company_info.get('contact_name', 'N/A')}

    **Target Contact:**
    - Name: {contact_name}
    - Title: {contact_title}
    - Background: {background_notes}

    **Discovery Insights:**
    {discovery_notes_str}

    **Analysis Required:**
    Generate specific, actionable insights in JSON format with exactly these fields:

    {{
        "likely_priorities": [
            "Priority 1 based on role and company context",
            "Priority 2 specific to their title and responsibilities", 
            "Priority 3 derived from background and industry"
        ],
        "engagement_strategies": [
            "Specific approach 1 tailored to their role",
            "Communication style 2 based on their background",
            "Timing/method 3 optimized for their priorities"
        ],
        "key_talking_points": [
            "Business value point 1 relevant to their role",
            "Technical consideration 2 aligned with their priorities",
            "Strategic initiative 3 that would interest them"
        ]
    }}

    Focus on practical, role-specific insights that demonstrate understanding of their position and challenges.
    """
    
    return cortex_request(prompt, json_output=True, suppress_warnings=True)

def generate_demo_prompt_with_llm(company_info, discovery_notes_str, roadmap_df, value_hypothesis, strategy_content, people_research):
    """Generate a dynamic demo prompt using the selected LLM via Cortex Complete."""
    
    # Prepare context data
    roadmap_str = roadmap_df.to_string() if not roadmap_df.empty else "No roadmap available."
    
    people_context = ""
    if people_research:
        people_context = "Key stakeholders:\n"
        for person in people_research:
            people_context += f"- {person.get('name', 'N/A')} ({person.get('title', 'N/A')}): {person.get('summary', 'N/A')}\n"
    
    # Create the LLM prompt for generating the demo prompt
    llm_input_prompt = f"""You are an expert Snowflake Solutions Engineer creating a comprehensive demo prompt for Cursor AI. Your task is to generate a detailed, actionable prompt that will help build a complete demo environment.

COMPANY CONTEXT:
- Company: {company_info.get('website', 'N/A')}
- Industry: {company_info.get('industry', 'N/A')}
- Primary Contact: {company_info.get('persona', 'N/A')}
- Main Competitor: {company_info.get('competitor', 'N/A')}

DISCOVERY INSIGHTS:
{discovery_notes_str}

STRATEGIC ROADMAP:
{roadmap_str}

VALUE HYPOTHESIS & STRATEGY:
{value_hypothesis}
{strategy_content}

PEOPLE CONTEXT:
{people_context}

Generate a comprehensive prompt for Cursor AI that will create:
1. A realistic data architecture using Snowflake
2. Two relevant Streamlit apps (executive dashboard + operational/analytical app)
3. Sample data specific to the {company_info.get('industry', 'industry')}
4. A compelling demo story and script
5. Complete setup instructions

The prompt should be:
- Specific to this company's industry and use cases
- Actionable with clear technical requirements
- Include realistic sample data scenarios
- Address the discovered pain points and roadmap priorities
- Position against the competitor {company_info.get('competitor', 'mentioned')}
- Be ready to copy-paste into Cursor AI

Generate a detailed, professional prompt that will result in a complete, working demo environment."""

    # Call the LLM using cortex_request with json_output=False for text response
    return cortex_request(llm_input_prompt, json_output=False)


def generate_mermaid_architecture(discovery_data, company_context, architecture_type="Both States"):
    """Generate Mermaid diagram syntax for architecture using AI analysis"""
    
    # Prepare discovery data summary
    discovery_summary = ""
    
    # Extract discovery questions and answers
    questions_data = discovery_data.get('questions', {})
    
    # Handle both list and dictionary formats
    if isinstance(questions_data, list):
        # Convert list format to categorized format
        categories = {
            'Technical': [],
            'Business': [],
            'Competitive': []
        }
        
        for q in questions_data:
            if isinstance(q, dict):
                category = q.get('category', '').lower()
                text = q.get('text', '').lower()
                
                if 'technical' in category or 'tech' in category:
                    categories['Technical'].append(q)
                elif 'business' in category or 'biz' in category:
                    categories['Business'].append(q)
                elif 'competitive' in category or 'competitor' in category or 'competition' in category:
                    categories['Competitive'].append(q)
                elif any(word in text for word in ['technical', 'technology', 'system', 'integration', 'data', 'platform']):
                    categories['Technical'].append(q)
                elif any(word in text for word in ['business', 'process', 'workflow', 'organization', 'team', 'department']):
                    categories['Business'].append(q)
                elif any(word in text for word in ['competitor', 'competition', 'vendor', 'alternative', 'current solution']):
                    categories['Competitive'].append(q)
                else:
                    categories['Technical'].append(q)
        questions_dict = categories
    else:
        # Already in dictionary format
        questions_dict = questions_data
    
    for category, q_list in questions_dict.items():
        if q_list:
            discovery_summary += f"\n{category.title()} Insights:\n"
            for qa in q_list:
                if qa.get('answer'):
                    discovery_summary += f"- Q: {qa.get('text', 'N/A')[:100]}...\n"
                    discovery_summary += f"  A: {qa['answer'][:150]}...\n"
    
    # Add notes if available
    notes = discovery_data.get('notes', '')
    if notes:
        discovery_summary += f"\nAdditional Notes:\n{notes[:500]}...\n"
    
    # Add company context
    company_info = f"""
Company: {company_context.get('website', 'N/A')}
Industry: {company_context.get('industry', 'N/A')}
Competitor: {company_context.get('competitor', 'N/A')}
Contact: {company_context.get('persona', 'N/A')}
    """.strip()
    
    if architecture_type == "Current State":
        prompt = f"""
Analyze the following discovery data and create a CURRENT STATE data architecture diagram using professional Snowflake branding.

{company_info}

Discovery Data:
{discovery_summary}

Create a LEFT-TO-RIGHT flow diagram with clear sections, matching professional Snowflake style:
- Clean, rounded rectangles with professional color scheme
- Orange/amber colors for legacy systems and pain points
- Left-to-right flow with logical groupings
- Emphasis on current limitations and manual processes

Return ONLY the Mermaid code in this professional format:

```mermaid
graph LR
    subgraph "DATA SOURCES"
        A1[Legacy Databases]:::legacySystem
        A2[Excel Spreadsheets]:::legacyData
        A3[Manual Processes]:::painPoint
        A4[Disparate Systems]:::legacySystem
    end
    
    subgraph "INTEGRATION"
        B1[Manual ETL Scripts]:::painPoint
        B2[Batch Processing]:::legacyProcess
        B3[FTP Transfers]:::legacyIntegration
    end
    
    subgraph "CURRENT PLATFORM"
        C1[Siloed Databases]:::legacyPlatform
        C2[Limited Analytics]:::constraint
        C3[Data Marts]:::legacyData
    end
    
    subgraph "OUTPUTS"
        D1[Excel Reports]:::legacyOutput
        D2[Email Distribution]:::legacyDelivery
        D3[Static Dashboards]:::legacyBI
    end
    
    %% Data Flow
    A1 --> B1
    A2 --> B1
    A3 --> B2
    A4 --> B2
    B1 --> C1
    B2 --> C2
    B3 --> C3
    C1 --> D1
    C2 --> D2
    C3 --> D3
    
    %% Professional Snowflake-style Branding for Current State
    classDef legacySystem fill:#FFE0B2,stroke:#FF7043,stroke-width:2px,color:#E65100,font-weight:bold
    classDef legacyData fill:#FFF3E0,stroke:#FFA726,stroke-width:2px,color:#F57C00
    classDef painPoint fill:#FFCDD2,stroke:#E53935,stroke-width:3px,color:#C62828,font-weight:bold
    classDef legacyProcess fill:#FFECB3,stroke:#FFB300,stroke-width:2px,color:#FF8F00
    classDef legacyIntegration fill:#F3E5F5,stroke:#AB47BC,stroke-width:2px,color:#7B1FA2
    classDef legacyPlatform fill:#E8F5E8,stroke:#66BB6A,stroke-width:2px,color:#388E3C
    classDef constraint fill:#FFCDD2,stroke:#F44336,stroke-width:2px,color:#D32F2F
    classDef legacyOutput fill:#F1F8E9,stroke:#8BC34A,stroke-width:2px,color:#689F38
    classDef legacyDelivery fill:#E0F2F1,stroke:#4CAF50,stroke-width:2px,color:#388E3C
    classDef legacyBI fill:#E3F2FD,stroke:#2196F3,stroke-width:2px,color:#1976D2
```

Focus on identifying current limitations, manual processes, and system silos from the discovery data.
        """
    
    elif architecture_type == "Future State (Snowflake-Optimized)":
        prompt = f"""
Design a FUTURE STATE Snowflake-optimized architecture using professional Snowflake branding.

{company_info}

Discovery Data:
{discovery_summary}

Create a modern data cloud architecture with LEFT-TO-RIGHT flow, following Snowflake's reference architecture:
- Five clear sections: Sources → Integration → Data Cloud → Use Cases → Consumers
- Snowflake signature blue colors (#29B6F6) for core platform
- Raw → Refined → Present data layers
- Prominent Cortex AI and Streamlit features
- Modern, professional styling

Return ONLY the Mermaid code in this Snowflake-branded format:

```mermaid
graph LR
    subgraph "DATA SOURCES"
        A1[SaaS Applications]:::modernSource
        A2[Cloud Databases]:::modernSource
        A3[Real-time Streams]:::streamingData
        A4[APIs & Webhooks]:::modernAPI
    end
    
    subgraph "INTEGRATION"
        B1[Snowflake Streaming]:::snowflakeCore
        B2[Snowpipe Auto-Ingest]:::snowflakeFeature
        B3[Partner Connectors]:::snowflakeIntegration
        B4[Data Pipelines]:::snowflakeIngestion
    end
    
    subgraph "SNOWFLAKE DATA CLOUD"
        C1[(Raw Data Layer)]:::dataLayer
        C2[(Refined Data Layer)]:::dataLayer
        C3[(Present Data Layer)]:::dataLayer
        C4[Snowpark Python]:::snowflakeFeature
        C5[Cortex AI & ML]:::cortexAI
        C6[Data Governance]:::governance
    end
    
    subgraph "USE CASES"
        D1[Streamlit Apps]:::streamlitApp
        D2[BI & Analytics]:::analytics
        D3[ML & GenAI]:::aiFeatures
        D4[Real-time APIs]:::modernAPI
    end
    
    subgraph "CONSUMERS"
        E1[Data Scientists]:::userPersona
        E2[Business Users]:::userPersona
        E3[External Apps]:::integration
        E4[Partner Systems]:::integration
    end
    
    %% Modern Data Flow
    A1 --> B2
    A2 --> B4
    A3 --> B1
    A4 --> B4
    B1 --> C1
    B2 --> C1
    B3 --> C1
    B4 --> C1
    C1 --> C2
    C2 --> C3
    C4 --> D1
    C5 --> D3
    C6 --> C2
    C3 --> D1
    C3 --> D2
    C3 --> D4
    D1 --> E2
    D2 --> E2
    D3 --> E1
    D4 --> E3
    D4 --> E4
    
    %% Professional Snowflake Branding
    classDef modernSource fill:#E3F2FD,stroke:#1976D2,stroke-width:2px,color:#0D47A1,font-weight:bold
    classDef streamingData fill:#E0F2F1,stroke:#00695C,stroke-width:2px,color:#004D40,font-weight:bold
    classDef modernAPI fill:#F3E5F5,stroke:#7B1FA2,stroke-width:2px,color:#4A148C
    classDef snowflakeCore fill:#29B6F6,stroke:#0277BD,stroke-width:4px,color:#FFFFFF,font-weight:bold
    classDef snowflakeFeature fill:#4FC3F7,stroke:#0288D1,stroke-width:2px,color:#01579B,font-weight:bold
    classDef snowflakeIntegration fill:#81C784,stroke:#388E3C,stroke-width:2px,color:#1B5E20
    classDef snowflakeIngestion fill:#90CAF9,stroke:#1976D2,stroke-width:2px,color:#0D47A1
    classDef dataLayer fill:#B3E5FC,stroke:#0277BD,stroke-width:3px,color:#01579B,font-weight:bold
    classDef cortexAI fill:#CE93D8,stroke:#8E24AA,stroke-width:3px,color:#4A148C,font-weight:bold
    classDef governance fill:#FFCC02,stroke:#F57F17,stroke-width:2px,color:#E65100
    classDef streamlitApp fill:#A5D6A7,stroke:#43A047,stroke-width:3px,color:#1B5E20,font-weight:bold
    classDef analytics fill:#90CAF9,stroke:#1976D2,stroke-width:2px,color:#0D47A1
    classDef aiFeatures fill:#F8BBD9,stroke:#C2185B,stroke-width:2px,color:#880E4F,font-weight:bold
    classDef userPersona fill:#DCEDC8,stroke:#689F38,stroke-width:2px,color:#33691E
    classDef integration fill:#FFCDD2,stroke:#D32F2F,stroke-width:2px,color:#B71C1C
```

Emphasize Snowflake's modern capabilities: unified data platform, Cortex AI, real-time processing, and Streamlit applications.
        """
    
    else:  # Both States
        prompt = f"""
Create a comprehensive CURRENT vs FUTURE STATE comparison using professional Snowflake branding.

{company_info}

Discovery Data:
{discovery_summary}

Generate a comparison showing transformation from legacy systems to modern Snowflake Data Cloud:
- Clear visual distinction between current (legacy colors) and future (Snowflake blue)
- Professional styling matching Snowflake's brand standards
- Emphasis on modernization benefits

Return ONLY the Mermaid code:

```mermaid
graph TD
    subgraph "🔻 CURRENT STATE - Legacy Architecture"
        direction LR
        A1[Siloed Databases]:::legacyPrimary
        A2[Manual ETL Scripts]:::painPoint
        A3[Data Warehouses]:::legacyData
        A4[Excel Reports]:::legacyOutput
        A5[Email Distribution]:::legacyDelivery
        
        A1 --> A2
        A2 --> A3
        A3 --> A4
        A4 --> A5
    end
    
    subgraph "🔺 FUTURE STATE - Snowflake Data Cloud"
        direction LR
        B1[Unified Data Sources]:::modernSource
        B2[Snowflake Streaming]:::snowflakeCore
        B3[Snowflake Data Cloud]:::snowflakePlatform
        B4[Cortex AI & Analytics]:::cortexAI
        B5[Streamlit Applications]:::streamlitApp
        B6[Real-time Insights]:::modernOutput
        
        B1 --> B2
        B2 --> B3
        B3 --> B4
        B3 --> B5
        B4 --> B6
        B5 --> B6
    end
    
    %% Professional Snowflake Branding
    %% Current State - Muted legacy colors
    classDef legacyPrimary fill:#FFECB3,stroke:#FF8F00,stroke-width:2px,color:#E65100
    classDef painPoint fill:#FFCDD2,stroke:#D32F2F,stroke-width:3px,color:#B71C1C,font-weight:bold
    classDef legacyData fill:#F8BBD9,stroke:#C2185B,stroke-width:2px,color:#880E4F
    classDef legacyOutput fill:#DCEDC8,stroke:#689F38,stroke-width:2px,color:#33691E
    classDef legacyDelivery fill:#E0F2F1,stroke:#26A69A,stroke-width:2px,color:#00695C
    
    %% Future State - Vibrant Snowflake branding
    classDef modernSource fill:#E3F2FD,stroke:#1976D2,stroke-width:2px,color:#0D47A1,font-weight:bold
    classDef snowflakeCore fill:#4FC3F7,stroke:#0288D1,stroke-width:3px,color:#01579B,font-weight:bold
    classDef snowflakePlatform fill:#29B6F6,stroke:#0277BD,stroke-width:4px,color:#FFFFFF,font-weight:bold
    classDef cortexAI fill:#CE93D8,stroke:#8E24AA,stroke-width:3px,color:#4A148C,font-weight:bold
    classDef streamlitApp fill:#A5D6A7,stroke:#43A047,stroke-width:3px,color:#1B5E20,font-weight:bold
    classDef modernOutput fill:#90CAF9,stroke:#1976D2,stroke-width:2px,color:#0D47A1
```

Show the clear transformation path from fragmented legacy systems to unified, AI-powered Snowflake architecture.
        """
    
    # Call AI to generate Mermaid syntax
    try:
        mermaid_response = cortex_request(prompt, json_output=False)
        
        if mermaid_response:
            # Extract Mermaid code from response
            if "```mermaid" in mermaid_response:
                start = mermaid_response.find("```mermaid") + 10
                end = mermaid_response.find("```", start)
                mermaid_code = mermaid_response[start:end].strip()
                return mermaid_code
            else:
                # If no code blocks, return the response as-is (fallback)
                return mermaid_response.strip()
        
        return None
        
    except Exception as e:
        print(f"Error generating Mermaid architecture: {e}")
        return None


def convert_mermaid_to_drawio_xml(mermaid_code):
    """Convert Mermaid syntax to basic Draw.io XML format"""
    
    # This is a simplified conversion - for production, you'd want a more robust parser
    xml_template = '''<?xml version="1.0" encoding="UTF-8"?>
<mxfile host="app.diagrams.net">
  <diagram name="Architecture" id="architecture">
    <mxGraphModel dx="1422" dy="794" grid="1" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="827" pageHeight="1169">
      <root>
        <mxCell id="0" />
        <mxCell id="1" parent="0" />
        <!-- Mermaid diagram converted to Draw.io format -->
        <mxCell id="mermaid-note" value="Generated from Mermaid code - Edit in Draw.io for professional styling" style="text;html=1;strokeColor=none;fillColor=none;align=center;verticalAlign=middle;whiteSpace=wrap;rounded=0;" vertex="1" parent="1">
          <mxGeometry x="40" y="40" width="400" height="30" as="geometry" />
        </mxCell>
        <mxCell id="mermaid-code" value="{mermaid_code}" style="text;html=1;strokeColor=#666666;fillColor=#f5f5f5;align=left;verticalAlign=top;whiteSpace=wrap;rounded=0;fontFamily=Courier New;" vertex="1" parent="1">
          <mxGeometry x="40" y="80" width="700" height="400" as="geometry" />
        </mxCell>
      </root>
    </mxGraphModel>
  </diagram>
</mxfile>'''.format(mermaid_code=mermaid_code.replace('\n', '&#10;').replace('"', '&quot;'))
    
    return xml_template


def generate_export_urls(mermaid_code, company_name="architecture"):
    """Generate URLs for professional diagram editing platforms"""
    
    import urllib.parse
    
    # Clean company name for filename
    safe_company = company_name.replace('.', '_').replace(' ', '_').lower()
    
    # Draft1.ai URL with pre-filled prompt
    draft1_prompt = f"""
Create a professional architecture diagram based on this Mermaid code:

{mermaid_code}

Make it visually appealing with:
- Clean, professional styling
- High contrast colors
- Clear component labels
- Proper spacing and alignment
- Export-ready quality

Focus on creating a beautiful, presentation-ready diagram.
    """.strip()
    
    draft1_url = f"https://draft1.ai/?prompt={urllib.parse.quote(draft1_prompt)}"
    
    # Whimsical URL (they support Mermaid import)
    whimsical_url = "https://whimsical.com/ai/ai-text-to-flowchart"
    
    return {
        "mermaid_file": f"snowflake_architecture_{safe_company}.mmd",
        "drawio_file": f"snowflake_architecture_{safe_company}.drawio", 
        "draft1_url": draft1_url,
        "whimsical_url": whimsical_url,
        "lucidchart_instructions": "Copy Mermaid code → Lucidchart → Insert → Diagram as Code → Mermaid"
    } 

def generate_xml_architecture(discovery_data, company_context, architecture_type="Both States"):
    """Generate draw.io XML diagram for architecture using AI analysis"""
    
    # Prepare discovery data summary (same as Mermaid function)
    discovery_summary = ""
    
    # Extract discovery questions and answers
    questions_data = discovery_data.get('questions', {})
    
    # Handle both list and dictionary formats
    if isinstance(questions_data, list):
        # Convert list format to categorized format
        categories = {
            'Technical': [],
            'Business': [],
            'Competitive': []
        }
        
        for q in questions_data:
            if isinstance(q, dict):
                category = q.get('category', '').lower()
                text = q.get('text', '').lower()
                
                if 'technical' in category or 'tech' in category:
                    categories['Technical'].append(q)
                elif 'business' in category or 'biz' in category:
                    categories['Business'].append(q)
                elif 'competitive' in category or 'competitor' in category or 'competition' in category:
                    categories['Competitive'].append(q)
                elif any(word in text for word in ['technical', 'technology', 'system', 'integration', 'data', 'platform']):
                    categories['Technical'].append(q)
                elif any(word in text for word in ['business', 'process', 'workflow', 'organization', 'team', 'department']):
                    categories['Business'].append(q)
                elif any(word in text for word in ['competitor', 'competition', 'vendor', 'alternative', 'current solution']):
                    categories['Competitive'].append(q)
                else:
                    categories['Technical'].append(q)
        questions_dict = categories
    else:
        # Already in dictionary format
        questions_dict = questions_data
    
    for category, q_list in questions_dict.items():
        if q_list:
            discovery_summary += f"\n{category.title()} Insights:\n"
            for qa in q_list:
                if qa.get('answer'):
                    discovery_summary += f"- Q: {qa.get('text', 'N/A')[:100]}...\n"
                    discovery_summary += f"  A: {qa['answer'][:150]}...\n"
    
    # Add notes if available
    notes = discovery_data.get('notes', '')
    if notes:
        discovery_summary += f"\nAdditional Notes:\n{notes[:500]}...\n"
    
    # Add company context
    company_info = f"""
Company: {company_context.get('website', 'N/A')}
Industry: {company_context.get('industry', 'N/A')}
Competitor: {company_context.get('competitor', 'N/A')}
Contact: {company_context.get('persona', 'N/A')}
    """.strip()
    
    if architecture_type == "Current State":
        prompt = f"""
Analyze the following discovery data and create a CURRENT STATE data architecture diagram as draw.io XML format.

{company_info}

Discovery Data:
{discovery_summary}

Create a professional draw.io XML diagram with:
- Rounded rectangles for systems/components
- Clear left-to-right flow
- Professional color scheme (orange/amber for legacy systems, red for pain points)
- Proper grouping with containers/swimlanes
- Professional Snowflake branding colors

Return ONLY the draw.io XML code starting with <?xml version="1.0" encoding="UTF-8"?> and the complete <mxfile> structure.

The XML should be a complete, valid draw.io diagram that shows the current state architecture with clear data flow from legacy sources through integration to outputs.

Use professional styling with:
- Legacy systems: Orange/amber (#FFE0B2, stroke #FF7043)
- Pain points: Red (#FFCDD2, stroke #E53935) 
- Data flow: Blue arrows
- Containers: Light gray backgrounds
- Professional fonts and spacing

Generate a complete draw.io XML file.
"""
    
    elif architecture_type == "Future State (Snowflake-Optimized)":
        prompt = f"""
Analyze the following discovery data and create a FUTURE STATE Snowflake-optimized architecture diagram as draw.io XML format.

{company_info}

Discovery Data:
{discovery_summary}

Create a professional draw.io XML diagram showing a modern Snowflake data cloud architecture with:
- Snowflake as the central data platform
- Streamlit apps for modern analytics
- Cortex AI/ML capabilities
- Modern data ingestion (Fivetran, etc.)
- Real-time data processing
- Self-service analytics

Use Snowflake brand colors:
- Snowflake components: Blue (#0043CE) and light blue (#E6F3FF)
- Modern components: Green (#4CAF50)
- AI/ML: Purple (#9C27B0)
- Data sources: Light blue
- Professional styling with rounded rectangles and clear flow

Return ONLY the draw.io XML code starting with <?xml version="1.0" encoding="UTF-8"?> and the complete <mxfile> structure.

Generate a complete draw.io XML file showing the future state architecture.
"""
    
    else:  # Both States
        prompt = f"""
Analyze the following discovery data and create a TRANSFORMATION diagram showing both CURRENT and FUTURE STATE architectures as draw.io XML format.

{company_info}

Discovery Data:
{discovery_summary}

Create a professional draw.io XML diagram with two sides:

LEFT SIDE - Current State:
- Legacy systems in orange/amber colors
- Manual processes in red (pain points)
- Siloed data architecture

RIGHT SIDE - Future State:
- Snowflake Data Cloud in blue
- Streamlit apps in green
- Cortex AI in purple
- Modern data pipelines

CENTER - Transformation Arrow:
- Large arrow showing migration path
- Key benefits and improvements

Use professional Snowflake branding:
- Current state: Orange/amber and red for problems
- Future state: Snowflake blue, green for modern apps, purple for AI
- Clear visual separation with transformation arrow
- Professional fonts and spacing

Return ONLY the draw.io XML code starting with <?xml version="1.0" encoding="UTF-8"?> and the complete <mxfile> structure.

Generate a complete draw.io XML file showing the transformation from current to future state.
"""
    
    # Generate XML using LLM
    try:
        xml_content = cortex_request(prompt, json_output=False)
        
        if xml_content and '<?xml' in xml_content:
            # Extract just the XML content
            xml_start = xml_content.find('<?xml')
            if xml_start != -1:
                xml_content = xml_content[xml_start:]
                # Clean up any trailing text after the closing tag
                if '</mxfile>' in xml_content:
                    xml_end = xml_content.find('</mxfile>') + len('</mxfile>')
                    xml_content = xml_content[:xml_end]
                
                return xml_content
        
        # Fallback if XML generation fails
        st.warning("AI XML generation failed. Using Mermaid-to-XML conversion as fallback.")
        mermaid_code = generate_mermaid_architecture(discovery_data, company_context, architecture_type)
        if mermaid_code:
            return convert_mermaid_to_drawio_xml(mermaid_code)
        
        return None
        
    except Exception as e:
        st.error(f"Error generating XML architecture: {e}")
        return None 