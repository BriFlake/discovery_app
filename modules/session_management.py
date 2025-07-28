# Session Management Module - NEW CLEAN VERSION
# Uses purpose-built snowpublic.streamlit.discovery_sessions table

import streamlit as st
import pandas as pd
import json
import uuid
from datetime import datetime
from modules.snowflake_utils import execute_query

def clear_session_data():
    """Simple function to clear session data - used as fallback"""
    session_keys_to_clear = [
        'questions', 'company_info', 'selected_sf_account', 'current_session_id',
        'company_summary_data', 'roadmap', 'roadmap_df', 'competitive_strategy',
        'outreach_content', 'people_research', 'business_case', 'initial_value_hypothesis',
        'outreach_emails', 'linkedin_messages', 'notes_content', 'recommended_initiatives',
        'contact_name', 'contact_title', 'competitor'
    ]
    
    for key in session_keys_to_clear:
        if key in st.session_state:
            del st.session_state[key]
    
    return True

def generate_session_name(company_info):
    """Generate a human-readable session name"""
    # Handle case where company_info might be a string
    if isinstance(company_info, str):
        try:
            company_info = json.loads(company_info)
        except:
            company_info = {'website': company_info}
    
    # Ensure company_info is a dict
    if not isinstance(company_info, dict):
        company_info = {}
    
    if company_info.get('name'):
        company_name = company_info['name']
    elif company_info.get('website'):
        website = company_info['website']
        company_name = website.replace('https://', '').replace('http://', '').replace('www.', '').split('.')[0].title()
    else:
        company_name = "Unknown Company"
    
    # Use local timezone for user-friendly timestamps
    import pytz
    from datetime import timezone
    
    try:
        # Try to get user's local timezone
        local_tz = datetime.now().astimezone().tzinfo
        local_time = datetime.now(local_tz)
        timestamp = local_time.strftime('%m/%d/%Y %I:%M %p %Z')
    except:
        # Fallback to basic local time if timezone detection fails
        timestamp = datetime.now().strftime('%m/%d/%Y %I:%M %p')
    
    return f"{company_name} - Discovery Session ({timestamp})"

def save_current_session():
    """Save current session to the new discovery_sessions table"""
    try:
        # Validate we have company data
        company_info = st.session_state.get('company_info', {})
        
        # Handle case where company_info might be a string (defensive programming)
        if isinstance(company_info, str):
            try:
                company_info = json.loads(company_info)
            except:
                company_info = {'website': company_info}  # Fallback if it's just a URL string
        
        # Ensure company_info is a dict
        if not isinstance(company_info, dict):
            company_info = {}
        
        if not company_info.get('website') and not company_info.get('name'):
            st.warning("⚠️ No company data to save. Please load company information first.")
            return False
        
        # Generate or use existing session ID
        session_id = st.session_state.get('current_session_id')
        if not session_id:
            session_id = str(uuid.uuid4())
            st.session_state.current_session_id = session_id
        
        # Generate human-readable session name
        session_name = generate_session_name(company_info)
        
        # Count questions and answers - with defensive programming
        questions = st.session_state.get('questions', [])
        if not isinstance(questions, list):
            questions = []
        
        answered_questions = [q for q in questions if isinstance(q, dict) and q.get('answer', '').strip()]
        answers_count = len(answered_questions)
        total_questions = len(questions)
        completion_percentage = (answers_count / total_questions * 100) if total_questions > 0 else 0
        
        # Prepare all session data with defensive programming
        roadmap_data = st.session_state.get('roadmap', pd.DataFrame())
        if hasattr(roadmap_data, 'to_dict'):
            roadmap_records = roadmap_data.to_dict('records') if not roadmap_data.empty else []
        else:
            roadmap_records = []
        
        # Get other session variables safely
        business_case = st.session_state.get('business_case', '')
        if not isinstance(business_case, str):
            business_case = str(business_case) if business_case else ''
            
        competitor_strategy = st.session_state.get('competitor_strategy', '')
        if not isinstance(competitor_strategy, str):
            competitor_strategy = str(competitor_strategy) if competitor_strategy else ''
            
        initial_value_hypothesis = st.session_state.get('initial_value_hypothesis', '')
        if not isinstance(initial_value_hypothesis, str):
            initial_value_hypothesis = str(initial_value_hypothesis) if initial_value_hypothesis else ''
        
        # Get dict/list variables safely
        outreach_emails = st.session_state.get('outreach_emails', {})
        if not isinstance(outreach_emails, dict):
            outreach_emails = {}
            
        linkedin_messages = st.session_state.get('linkedin_messages', {})
        if not isinstance(linkedin_messages, dict):
            linkedin_messages = {}
            
        people_research = st.session_state.get('people_research', [])
        if not isinstance(people_research, list):
            people_research = []
            
        notes_content = st.session_state.get('notes_content', '')
        if not isinstance(notes_content, str):
            notes_content = str(notes_content) if notes_content else ''
            
        recommended_initiatives = st.session_state.get('recommended_initiatives', [])
        if not isinstance(recommended_initiatives, list):
            recommended_initiatives = []
        
        full_session_state = {
            'company_info': company_info,
            'company_summary_data': st.session_state.get('company_summary_data', {}),
            'questions': questions,
            'business_case': business_case,
            'roadmap': roadmap_records,
            'competitor_strategy': competitor_strategy,
            'initial_value_hypothesis': initial_value_hypothesis,
            'outreach_emails': outreach_emails,
            'linkedin_messages': linkedin_messages,
            'people_research': people_research,
            'notes_content': notes_content,
            'recommended_initiatives': recommended_initiatives
        }
        
        # Insert or update session
        query = """
        MERGE INTO snowpublic.streamlit.discovery_sessions AS target
        USING (
            SELECT 
                ? AS SESSION_ID,
                ? AS SESSION_NAME,
                ? AS USER_EMAIL,
                ? AS COMPANY_NAME,
                ? AS COMPANY_WEBSITE,
                ? AS COMPETITOR,
                ? AS CONTACT_NAME,
                ? AS CONTACT_TITLE,
                CURRENT_TIMESTAMP() AS UPDATED_AT,
                PARSE_JSON(?) AS DISCOVERY_QUESTIONS,
                ? AS ANSWERS_COUNT,
                ? AS COMPLETION_PERCENTAGE,
                ? AS BUSINESS_CASE,
                PARSE_JSON(?) AS ROADMAP_DATA,
                ? AS COMPETITOR_STRATEGY,
                ? AS VALUE_HYPOTHESIS,
                PARSE_JSON(?) AS OUTREACH_EMAILS,
                PARSE_JSON(?) AS LINKEDIN_MESSAGES,
                PARSE_JSON(?) AS PEOPLE_RESEARCH,
                PARSE_JSON(?) AS FULL_SESSION_STATE
        ) AS source ON target.SESSION_ID = source.SESSION_ID
        WHEN MATCHED THEN
            UPDATE SET
                SESSION_NAME = source.SESSION_NAME,
                COMPANY_NAME = source.COMPANY_NAME,
                COMPANY_WEBSITE = source.COMPANY_WEBSITE,
                COMPETITOR = source.COMPETITOR,
                CONTACT_NAME = source.CONTACT_NAME,
                CONTACT_TITLE = source.CONTACT_TITLE,
                UPDATED_AT = source.UPDATED_AT,
                DISCOVERY_QUESTIONS = source.DISCOVERY_QUESTIONS,
                ANSWERS_COUNT = source.ANSWERS_COUNT,
                COMPLETION_PERCENTAGE = source.COMPLETION_PERCENTAGE,
                BUSINESS_CASE = source.BUSINESS_CASE,
                ROADMAP_DATA = source.ROADMAP_DATA,
                COMPETITOR_STRATEGY = source.COMPETITOR_STRATEGY,
                VALUE_HYPOTHESIS = source.VALUE_HYPOTHESIS,
                OUTREACH_EMAILS = source.OUTREACH_EMAILS,
                LINKEDIN_MESSAGES = source.LINKEDIN_MESSAGES,
                PEOPLE_RESEARCH = source.PEOPLE_RESEARCH,
                FULL_SESSION_STATE = source.FULL_SESSION_STATE
        WHEN NOT MATCHED THEN
            INSERT (
                SESSION_ID, SESSION_NAME, USER_EMAIL, COMPANY_NAME, COMPANY_WEBSITE,
                COMPETITOR, CONTACT_NAME, CONTACT_TITLE, DISCOVERY_QUESTIONS,
                ANSWERS_COUNT, COMPLETION_PERCENTAGE, BUSINESS_CASE, ROADMAP_DATA,
                COMPETITOR_STRATEGY, VALUE_HYPOTHESIS, OUTREACH_EMAILS,
                LINKEDIN_MESSAGES, PEOPLE_RESEARCH, FULL_SESSION_STATE
            )
            VALUES (
                source.SESSION_ID, source.SESSION_NAME, source.USER_EMAIL, 
                source.COMPANY_NAME, source.COMPANY_WEBSITE, source.COMPETITOR,
                source.CONTACT_NAME, source.CONTACT_TITLE, source.DISCOVERY_QUESTIONS,
                source.ANSWERS_COUNT, source.COMPLETION_PERCENTAGE, source.BUSINESS_CASE,
                source.ROADMAP_DATA, source.COMPETITOR_STRATEGY, source.VALUE_HYPOTHESIS,
                source.OUTREACH_EMAILS, source.LINKEDIN_MESSAGES, source.PEOPLE_RESEARCH,
                source.FULL_SESSION_STATE
            )
        """
        
        params = (
            session_id,
            session_name,
            st.session_state.get('user_email', 'demo_user@company.com'),
            company_info.get('name', ''),
            company_info.get('website', ''),
            st.session_state.get('competitor', ''),
            st.session_state.get('contact_name', ''),
            st.session_state.get('contact_title', ''),
            json.dumps(questions),
            answers_count,
            completion_percentage,
            business_case,
            json.dumps(roadmap_records),
            competitor_strategy,
            initial_value_hypothesis,
            json.dumps(outreach_emails),
            json.dumps(linkedin_messages),
            json.dumps(people_research),
            json.dumps(full_session_state)
        )
        
        execute_query(query, params=params)
        
        st.success(f"✅ Session saved: {session_name} ({answers_count}/{total_questions} questions answered)")
        return True
        
    except Exception as e:
        st.error(f"Error saving session: {e}")
        import traceback
        st.error(f"Full traceback: {traceback.format_exc()}")
        return False

def get_saved_sessions():
    """Get list of saved sessions for current user"""
    try:
        user_email = st.session_state.get('user_email', 'demo_user@company.com')
        
        query = """
        SELECT 
            SESSION_ID,
            SESSION_NAME,
            COMPANY_NAME,
            COMPANY_WEBSITE,
            COMPETITOR,
            ANSWERS_COUNT,
            COMPLETION_PERCENTAGE,
            CREATED_AT,
            UPDATED_AT,
            STATUS,
            DISCOVERY_QUESTIONS
        FROM snowpublic.streamlit.discovery_sessions
        WHERE USER_EMAIL = ?
        ORDER BY UPDATED_AT DESC
        """
        
        sessions_df = execute_query(query, params=(user_email,))
        
        # Calculate total questions from DISCOVERY_QUESTIONS JSON
        if not sessions_df.empty:
            total_questions_list = []
            for idx, row in sessions_df.iterrows():
                try:
                    if pd.notna(row.get('DISCOVERY_QUESTIONS')):
                        questions_data = json.loads(row['DISCOVERY_QUESTIONS'])
                        if isinstance(questions_data, list):
                            total_questions = len(questions_data)
                        elif isinstance(questions_data, dict):
                            total_questions = sum(len(q_list) for q_list in questions_data.values())
                        else:
                            total_questions = 0
                    else:
                        total_questions = 0
                except:
                    total_questions = 0
                total_questions_list.append(total_questions)
            
            sessions_df['TOTAL_QUESTIONS'] = total_questions_list
        
        return sessions_df
        
    except Exception as e:
        st.warning(f"Could not load saved sessions: {e}")
        return pd.DataFrame()

def load_session_data(session_id):
    """Load a specific session - optimized with hybrid approach"""
    try:
        query = """
        SELECT FULL_SESSION_STATE, SESSION_NAME
        FROM snowpublic.streamlit.discovery_sessions
        WHERE SESSION_ID = ?
        """
        
        result = execute_query(query, params=(session_id,))
        
        if result.empty:
            st.warning(f"Session {session_id} not found")
            return False
        
        # Parse session data
        session_data_raw = result.iloc[0]['FULL_SESSION_STATE']
        session_name = result.iloc[0]['SESSION_NAME']
        
        if isinstance(session_data_raw, str):
            session_data = json.loads(session_data_raw)
        else:
            session_data = session_data_raw
        
        # Batch clear session state (optimized)
        keys_to_clear = ['company_info', 'company_summary_data', 'questions', 'business_case', 'roadmap', 
                         'competitor_strategy', 'initial_value_hypothesis', 'outreach_emails',
                         'linkedin_messages', 'people_research', 'notes_content', 'recommended_initiatives',
                         'competitor', 'contact_name', 'contact_title']
        
        for key in keys_to_clear:
            if key in st.session_state:
                del st.session_state[key]
        
        # Restore session data efficiently
        session_data['current_session_id'] = session_id
        
        for key, value in session_data.items():
            if key == 'roadmap' and value:
                # Handle roadmap data - convert to DataFrame and also set roadmap_df
                roadmap_df = pd.DataFrame(value)
                st.session_state['roadmap'] = roadmap_df
                st.session_state['roadmap_df'] = roadmap_df
            else:
                st.session_state[key] = value
        
        # Optimized success message with key info
        company_info = session_data.get('company_info', {})
        questions = session_data.get('questions', [])
        company_name = company_info.get('name') or company_info.get('website', 'Unknown') if isinstance(company_info, dict) else 'Unknown'
        
        if questions:
            answered_count = len([q for q in questions if isinstance(q, dict) and q.get('answer', '').strip()])
            st.success(f"✅ Loaded: {session_name} ({answered_count}/{len(questions)} questions answered)")
        else:
            st.success(f"✅ Loaded: {session_name}")
        
        # Optional debug details in collapsible section
        with st.expander("🔧 Load Details", expanded=False):
            st.info(f"**Company:** {company_name}")
            if questions:
                st.info(f"**Questions:** {len(questions)} total, {answered_count} answered")
            content_loaded = [k for k in ['business_case', 'roadmap', 'competitor_strategy', 'outreach_emails', 'people_research'] if session_data.get(k)]
            if content_loaded:
                st.info(f"**Content:** {', '.join(content_loaded)}")
        
        return True
        
    except Exception as e:
        st.error(f"Error loading session: {e}")
        return False

def delete_session(session_id):
    """Delete a session"""
    try:
        query = "DELETE FROM snowpublic.streamlit.discovery_sessions WHERE SESSION_ID = ?"
        execute_query(query, params=(session_id,))
        st.success("✅ Session deleted successfully")
        return True
    except Exception as e:
        st.error(f"Error deleting session: {e}")
        return False

def get_session_analytics():
    """Get analytics for current user's sessions"""
    try:
        user_email = st.session_state.get('user_email', 'demo_user@company.com')
        
        query = """
        SELECT 
            COUNT(*) as total_sessions,
            COUNT(DISTINCT COMPANY_NAME) as unique_companies,
            SUM(ANSWERS_COUNT) as total_questions_answered,
            AVG(COMPLETION_PERCENTAGE) as avg_completion,
            COUNT(CASE WHEN COMPLETION_PERCENTAGE = 100 THEN 1 END) as completed_sessions
        FROM snowpublic.streamlit.discovery_sessions
        WHERE USER_EMAIL = ?
        """
        
        result = execute_query(query, params=(user_email,))
        return result.iloc[0].to_dict() if not result.empty else {}
        
    except Exception as e:
        st.warning(f"Could not load analytics: {e}")
        return {}


def start_new_session():
    """Save current session if it has data, then start a fresh session"""
    try:
        # Check if there's any meaningful data to save
        has_company_data = bool(st.session_state.get('company_info', {}).get('website'))
        has_questions = bool(st.session_state.get('questions'))
        
        session_saved = False
        
        # If there's data worth saving, save it first
        if has_company_data or has_questions:
            try:
                save_current_session()
                session_saved = True
                st.success("✅ Current session saved successfully!")
            except Exception as e:
                st.warning(f"⚠️ Could not save current session: {e}")
        
        # Clear all session state variables for a fresh start
        session_keys_to_clear = [
            'questions',
            'company_info', 
            'selected_sf_account',
            'current_session_id',
            'company_summary_data',
            'roadmap',
            'roadmap_df',
            'competitive_strategy',
            'outreach_content',
            'people_research',
            'expert_context',
            'show_export_modal',
            '_last_save_hash',
            '_last_auto_save_time',
            '_show_save_indicator',
            'generated_mermaid',
            'architecture_type',
            'current_architecture_nodes',
            'future_architecture_nodes',
            'selected_node_id',
            'node_colors',
            'node_sizes',
            'node_positions'
        ]
        
        # Clear session state
        for key in session_keys_to_clear:
            if key in st.session_state:
                del st.session_state[key]
        
        # Show success message
        if session_saved:
            st.info("🆕 Ready to start a new discovery session!")
        else:
            st.info("🆕 Started fresh discovery session!")
        
        # Force a rerun to refresh the UI
        st.rerun()
        
        return True
        
    except Exception as e:
        st.error(f"❌ Error starting new session: {e}")
        return False

