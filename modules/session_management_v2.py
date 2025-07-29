# NORMALIZED SESSION MANAGEMENT MODULE v2.0
# Uses efficient relational design instead of JSON blobs
# Provides seamless loading and instant progress calculation

import streamlit as st
import pandas as pd
import json
import uuid
from datetime import datetime
from modules.snowflake_utils import execute_query

def get_saved_sessions():
    """Get saved sessions with robust error handling and fallbacks"""
    try:
        user_email = st.session_state.get('user_email', 'demo_user@company.com')
        
        # Try the simplest approach first - check for old-style sessions
        try:
            # First, try the old snowpublic.streamlit.discovery_sessions table
            simple_query = """
            SELECT 
                session_id,
                session_name,
                company_name,
                created_at as updated_at
            FROM snowpublic.streamlit.discovery_sessions
            WHERE user_email = ?
            ORDER BY created_at DESC
            LIMIT 10
            """
            
            result = execute_query(simple_query, params=(user_email,))
            
            if not result.empty:
                # Success with old system - format for display
                result.columns = ['SESSION_ID', 'SESSION_NAME', 'COMPANY_NAME', 'UPDATED_AT']
                
                # Add default columns for compatibility
                result['COMPANY_WEBSITE'] = ''
                result['COMPETITOR'] = ''
                result['CONTACT_NAME'] = ''
                result['CONTACT_TITLE'] = ''
                result['TOTAL_QUESTIONS'] = 0
                result['ANSWERS_COUNT'] = 0
                result['COMPLETION_PERCENTAGE'] = 0
                result['CONTENT_COUNT'] = 0
                result['CONTACTS_COUNT'] = 0
                result['CONTENT_ITEMS'] = [[] for _ in range(len(result))]
                result['HAS_CONTENT'] = False
                
                st.info(f"✅ Found {len(result)} sessions in legacy system")
                return result
                
        except Exception as old_error:
            # Old system failed, try new normalized schema
            st.warning(f"⚠️ Legacy session system unavailable: {old_error}")
        
        # Try new normalized schema with very simple query
        try:
            new_query = """
            SELECT 
                session_id,
                session_name,
                company_name,
                updated_at
            FROM discovery_sessions
            WHERE user_email = ?
            ORDER BY updated_at DESC
            LIMIT 10
            """
            
            result = execute_query(new_query, params=(user_email,))
            
            if not result.empty:
                # Success with new system - format for display
                result.columns = ['SESSION_ID', 'SESSION_NAME', 'COMPANY_NAME', 'UPDATED_AT']
                
                # Add default columns for compatibility
                result['COMPANY_WEBSITE'] = ''
                result['COMPETITOR'] = ''
                result['CONTACT_NAME'] = ''
                result['CONTACT_TITLE'] = ''
                result['TOTAL_QUESTIONS'] = 0
                result['ANSWERS_COUNT'] = 0
                result['COMPLETION_PERCENTAGE'] = 0
                result['CONTENT_COUNT'] = 0
                result['CONTACTS_COUNT'] = 0
                result['CONTENT_ITEMS'] = [[] for _ in range(len(result))]
                result['HAS_CONTENT'] = False
                
                st.info(f"✅ Found {len(result)} sessions in new system")
                return result
                
        except Exception as new_error:
            # Both systems failed
            st.error(f"❌ New session system error: {new_error}")
            return pd.DataFrame()
        
        # No sessions found in either system
        st.info("📭 No saved sessions found")
        return pd.DataFrame()
        
    except Exception as e:
        # Complete failure - show error and return empty
        st.error(f"❌ Complete failure loading sessions: {e}")
        return pd.DataFrame()

def load_session_data(session_id):
    """Load complete session data with robust fallback handling"""
    try:
        # Clear existing session state first
        clear_session_data()
        
        # Try to load from legacy system first (most reliable)
        try:
            legacy_query = """
            SELECT SESSION_ID, SESSION_NAME, FULL_SESSION_STATE, CREATED_AT, USER_EMAIL, COMPANY_NAME
            FROM snowpublic.streamlit.discovery_sessions
            WHERE SESSION_ID = ?
            """
            
            legacy_result = execute_query(legacy_query, params=(session_id,))
            
            if not legacy_result.empty:
                session_row = legacy_result.iloc[0]
                
                # Parse session state (JSON format)
                session_state_str = session_row.get('FULL_SESSION_STATE', '{}')
                if isinstance(session_state_str, str):
                    try:
                        session_data = json.loads(session_state_str)
                    except json.JSONDecodeError:
                        session_data = {}
                else:
                    session_data = session_state_str if isinstance(session_state_str, dict) else {}
                
                # Restore session state from legacy format
                st.session_state.current_session_id = session_id
                
                # Restore company info
                company_info = session_data.get('company_info', {})
                if isinstance(company_info, str):
                    company_info = {'name': company_info, 'website': company_info}
                elif not isinstance(company_info, dict):
                    company_info = {'name': str(company_info) if company_info else 'Unknown Company'}
                st.session_state.company_info = company_info
                
                # Restore questions with robust format handling
                questions = session_data.get('questions', [])
                if isinstance(questions, dict):
                    # Convert old dictionary format to list format
                    questions_list = []
                    for category, category_questions in questions.items():
                        if isinstance(category_questions, list):
                            for q in category_questions:
                                if isinstance(q, dict):
                                    formatted_q = {
                                        'id': q.get('id', str(uuid.uuid4())),
                                        'text': q.get('text', q.get('question', '')),
                                        'category': q.get('category', category),
                                        'explanation': q.get('explanation', ''),
                                        'importance': q.get('importance', 'medium'),
                                        'answer': q.get('answer', '')
                                    }
                                    questions_list.append(formatted_q)
                    questions = questions_list
                elif isinstance(questions, list):
                    # Already in list format, ensure each question has required fields
                    formatted_questions = []
                    for q in questions:
                        if isinstance(q, dict):
                            formatted_q = {
                                'id': q.get('id', str(uuid.uuid4())),
                                'text': q.get('text', q.get('question', '')),
                                'category': q.get('category', 'Technical'),
                                'explanation': q.get('explanation', ''),
                                'importance': q.get('importance', 'medium'),
                                'answer': q.get('answer', '')
                            }
                            formatted_questions.append(formatted_q)
                        elif isinstance(q, str):
                            # Handle case where question is just a string
                            formatted_q = {
                                'id': str(uuid.uuid4()),
                                'text': q,
                                'category': 'Technical',
                                'explanation': '',
                                'importance': 'medium',
                                'answer': ''
                            }
                            formatted_questions.append(formatted_q)
                    questions = formatted_questions
                
                st.session_state.questions = questions
                
                # Restore other data with safe access
                for key, session_key in [
                    ('business_case', 'business_case'),
                    ('competitive_strategy', 'competitive_strategy'),
                    ('initial_value_hypothesis', 'initial_value_hypothesis'),
                    ('outreach_emails', 'outreach_emails'),
                    ('linkedin_messages', 'linkedin_messages'),
                    ('people_research', 'people_research'),
                    ('company_summary_data', 'company_summary_data')
                ]:
                    if key in session_data:
                        st.session_state[session_key] = session_data[key]
                
                # Handle roadmap data specially
                if 'roadmap_df' in session_data:
                    try:
                        roadmap_data = session_data['roadmap_df']
                        if isinstance(roadmap_data, list) and roadmap_data:
                            st.session_state.roadmap_df = pd.DataFrame(roadmap_data)
                        elif isinstance(roadmap_data, dict) and roadmap_data:
                            # Convert dict to DataFrame
                            st.session_state.roadmap_df = pd.DataFrame([roadmap_data])
                    except Exception:
                        pass  # Skip if roadmap data is corrupted
                
                # Calculate and show success message
                answered_count = len([q for q in questions if isinstance(q, dict) and q.get('answer', '').strip()])
                total_count = len(questions)
                completion = (answered_count / total_count * 100) if total_count > 0 else 0
                
                st.success(f"✅ **{session_row['SESSION_NAME']}** loaded successfully • {answered_count}/{total_count} questions ({completion:.0f}%)")
                
                return True
            
        except Exception as legacy_error:
            # Legacy system failed, try new normalized schema
            st.info(f"📝 Legacy system unavailable, trying new schema...")
            
            try:
                # 1. Load core session info from new schema
                session_query = """
                SELECT session_id, session_name, user_email, company_name, company_website,
                       competitor, contact_name, contact_title, notes
                FROM discovery_sessions 
                WHERE session_id = ?
                """
                
                session_result = execute_query(session_query, params=(session_id,))
                
                if not session_result.empty:
                    session_info = session_result.iloc[0]
                    
                    # 2. Load questions and answers efficiently - with error handling
                    try:
                        qa_query = """
                        SELECT 
                            q.question_id,
                            q.category,
                            q.question_text,
                            q.explanation,
                            q.importance,
                            q.question_order,
                            a.answer_text,
                            a.confidence_level
                        FROM discovery_questions q
                        LEFT JOIN discovery_answers a ON q.question_id = a.question_id
                        WHERE q.session_id = ?
                        ORDER BY q.question_order, q.question_id
                        """
                        
                        qa_result = execute_query(qa_query, params=(session_id,))
                    except Exception:
                        qa_result = pd.DataFrame()  # Empty if questions table doesn't exist
                    
                    # 3. Load strategic content - with error handling
                    try:
                        content_query = """
                        SELECT content_type, content_text, content_data
                        FROM session_content
                        WHERE session_id = ?
                        """
                        content_result = execute_query(content_query, params=(session_id,))
                    except Exception:
                        content_result = pd.DataFrame()
                    
                    # 4. Load contacts - with error handling
                    try:
                        contacts_query = """
                        SELECT contact_name, contact_title, contact_linkedin, 
                               background_notes, contact_type
                        FROM session_contacts
                        WHERE session_id = ?
                        ORDER BY CASE WHEN contact_type = 'primary' THEN 1 ELSE 2 END
                        """
                        contacts_result = execute_query(contacts_query, params=(session_id,))
                    except Exception:
                        contacts_result = pd.DataFrame()
                    
                    # 5. Restore session state systematically
                    st.session_state.current_session_id = session_id
                    
                    # Restore company info
                    st.session_state.company_info = {
                        'name': session_info.get('company_name', ''),
                        'website': session_info.get('company_website', ''),
                        'account_name': session_info.get('company_name', '')
                    }
                    
                    # Restore questions in the current format (list of dicts)
                    questions = []
                    if not qa_result.empty:
                        for _, row in qa_result.iterrows():
                            question = {
                                'id': row['question_id'],
                                'text': row['question_text'],
                                'category': row['category'],
                                'explanation': row.get('explanation', ''),
                                'importance': row.get('importance', 'medium'),
                                'answer': row.get('answer_text', '') if pd.notna(row.get('answer_text')) else ''
                            }
                            questions.append(question)
                    
                    st.session_state.questions = questions
                    
                    # Restore strategic content
                    if not content_result.empty:
                        for _, row in content_result.iterrows():
                            content_type = row['content_type']
                            
                            if content_type == 'business_case':
                                st.session_state.business_case = row.get('content_text', '')
                            elif content_type == 'competitive_strategy':
                                st.session_state.competitive_strategy = row.get('content_text', '')
                            elif content_type == 'value_hypothesis':
                                st.session_state.initial_value_hypothesis = row.get('content_text', '')
                            elif content_type == 'roadmap':
                                if row.get('content_data'):
                                    try:
                                        roadmap_data = json.loads(row['content_data']) if isinstance(row['content_data'], str) else row['content_data']
                                        roadmap_df = pd.DataFrame(roadmap_data)
                                        st.session_state.roadmap_df = roadmap_df
                                    except Exception:
                                        pass
                            elif content_type == 'outreach_emails':
                                if row.get('content_data'):
                                    try:
                                        emails_data = json.loads(row['content_data']) if isinstance(row['content_data'], str) else row['content_data']
                                        st.session_state.outreach_emails = emails_data
                                    except Exception:
                                        pass
                            elif content_type == 'linkedin_messages':
                                if row.get('content_data'):
                                    try:
                                        linkedin_data = json.loads(row['content_data']) if isinstance(row['content_data'], str) else row['content_data']
                                        st.session_state.linkedin_messages = linkedin_data
                                    except Exception:
                                        pass
                    
                    # Restore people research
                    if not contacts_result.empty:
                        people_research = []
                        for _, row in contacts_result.iterrows():
                            contact = {
                                'name': row.get('contact_name', ''),
                                'title': row.get('contact_title', ''),
                                'linkedin': row.get('contact_linkedin', ''),
                                'background': row.get('background_notes', ''),
                                'type': row.get('contact_type', 'stakeholder')
                            }
                            people_research.append(contact)
                        
                        st.session_state.people_research = people_research
                    
                    # Calculate and show success message
                    answered_count = len([q for q in questions if isinstance(q, dict) and q.get('answer', '').strip()])
                    total_count = len(questions)
                    completion = (answered_count / total_count * 100) if total_count > 0 else 0
                    
                    st.success(f"✅ **{session_info['session_name']}** loaded successfully (new format) • {answered_count}/{total_count} questions ({completion:.0f}%)")
                    
                    return True
                else:
                    st.error("❌ Session not found in new schema either")
                    return False
                    
            except Exception as new_schema_error:
                st.error(f"❌ Both systems failed - Legacy: {legacy_error}, New: {new_schema_error}")
                return False
        
        # If we get here, session wasn't found in either system
        st.error("❌ Session not found in any system")
        return False
        
    except Exception as e:
        st.error(f"❌ Critical error loading session: {e}")
        return False

def save_current_session():
    """Save current session using normalized schema"""
    try:
        # Validate we have data to save
        company_info = st.session_state.get('company_info', {})
        
        # Ensure company_info is a dictionary
        if not isinstance(company_info, dict):
            if isinstance(company_info, str):
                # Convert string to dict format (assume it's a company name)
                company_info = {'name': company_info}
            else:
                company_info = {}
        
        if not company_info.get('website') and not company_info.get('name'):
            st.warning("⚠️ No company data to save. Please load company information first.")
            return False
        
        # Generate or use existing session ID
        session_id = st.session_state.get('current_session_id')
        if not session_id:
            session_id = str(uuid.uuid4())
            st.session_state.current_session_id = session_id
        
        # Generate session name
        company_name = company_info.get('name') or company_info.get('account_name')
        if not company_name and company_info.get('website'):
            website = company_info['website']
            company_name = website.replace('https://', '').replace('http://', '').replace('www.', '').split('.')[0].title()
        
        session_name = f"{company_name or 'Unknown Company'} - {datetime.now().strftime('%m/%d/%Y')}"
        
        user_email = st.session_state.get('user_email', 'demo_user@company.com')
        
        # 1. Save/update core session
        session_query = """
        MERGE INTO discovery_sessions AS target
        USING (
            SELECT ? AS session_id, ? AS session_name, ? AS user_email, 
                   ? AS company_name, ? AS company_website, ? AS competitor,
                   ? AS contact_name, ? AS contact_title, CURRENT_TIMESTAMP() AS updated_at
        ) AS source ON target.session_id = source.session_id
        WHEN MATCHED THEN
            UPDATE SET session_name = source.session_name, company_name = source.company_name,
                      company_website = source.company_website, competitor = source.competitor,
                      contact_name = source.contact_name, contact_title = source.contact_title,
                      updated_at = source.updated_at
        WHEN NOT MATCHED THEN
            INSERT (session_id, session_name, user_email, company_name, company_website,
                   competitor, contact_name, contact_title, created_at, updated_at)
            VALUES (source.session_id, source.session_name, source.user_email,
                   source.company_name, source.company_website, source.competitor,
                   source.contact_name, source.contact_title, CURRENT_TIMESTAMP(), source.updated_at)
        """
        
        execute_query(session_query, params=(
            session_id, session_name, user_email,
            company_name, company_info.get('website'),
            st.session_state.get('competitor'),
            st.session_state.get('contact_name'),
            st.session_state.get('contact_title')
        ))
        
        # 2. Save questions and answers
        questions = st.session_state.get('questions', [])
        if questions:
            # Clear existing questions for this session
            execute_query("DELETE FROM discovery_questions WHERE session_id = ?", params=(session_id,))
            execute_query("DELETE FROM discovery_answers WHERE session_id = ?", params=(session_id,))
            
            # Insert questions and answers
            for i, q in enumerate(questions):
                # Validate question format - handle both dict and string formats
                if isinstance(q, str):
                    # Convert string to dict format
                    q = {
                        'text': q,
                        'category': 'Technical',
                        'explanation': '',
                        'importance': 'medium',
                        'answer': ''
                    }
                elif not isinstance(q, dict):
                    # Skip invalid question formats
                    continue
                
                question_id = f"{session_id}-q-{i+1}"
                
                # Insert question
                q_query = """
                INSERT INTO discovery_questions 
                (question_id, session_id, category, question_text, explanation, importance, question_order)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """
                execute_query(q_query, params=(
                    question_id, session_id, q.get('category', 'Technical'),
                    q.get('text', ''), q.get('explanation', ''), 
                    q.get('importance', 'medium'), i + 1
                ))
                
                # Insert answer if exists
                if q.get('answer', '').strip():
                    answer_id = f"{session_id}-a-{i+1}"
                    a_query = """
                    INSERT INTO discovery_answers
                    (answer_id, question_id, session_id, answer_text, confidence_level)
                    VALUES (?, ?, ?, ?, ?)
                    """
                    execute_query(a_query, params=(
                        answer_id, question_id, session_id, q['answer'], 3
                    ))
        
        # 3. Save strategic content
        content_items = [
            ('business_case', st.session_state.get('business_case', ''), None),
            ('competitive_strategy', st.session_state.get('competitive_strategy', ''), None),
            ('value_hypothesis', st.session_state.get('initial_value_hypothesis', ''), None)
        ]
        
        # Handle complex content with JSON data
        roadmap = st.session_state.get('roadmap_df')
        if roadmap is not None and not roadmap.empty:
            content_items.append(('roadmap', None, roadmap.to_dict('records')))
        
        outreach_emails = st.session_state.get('outreach_emails')
        if outreach_emails:
            content_items.append(('outreach_emails', None, outreach_emails))
        
        linkedin_messages = st.session_state.get('linkedin_messages')
        if linkedin_messages:
            content_items.append(('linkedin_messages', None, linkedin_messages))
        
        # Clear existing content
        execute_query("DELETE FROM session_content WHERE session_id = ?", params=(session_id,))
        
        # Insert content
        for content_type, text_content, json_content in content_items:
            if (text_content and text_content.strip()) or json_content:
                content_id = f"{session_id}-content-{content_type}"
                
                if json_content:
                    content_query = """
                    INSERT INTO session_content (content_id, session_id, content_type, content_data)
                    VALUES (?, ?, ?, PARSE_JSON(?))
                    """
                    execute_query(content_query, params=(
                        content_id, session_id, content_type, json.dumps(json_content)
                    ))
                else:
                    content_query = """
                    INSERT INTO session_content (content_id, session_id, content_type, content_text)
                    VALUES (?, ?, ?, ?)
                    """
                    execute_query(content_query, params=(
                        content_id, session_id, content_type, text_content
                    ))
        
        # 4. Save people research
        people_research = st.session_state.get('people_research', [])
        if people_research:
            # Clear existing contacts
            execute_query("DELETE FROM session_contacts WHERE session_id = ?", params=(session_id,))
            
            # Insert contacts
            for i, person in enumerate(people_research):
                # Validate person format - handle both dict and string formats
                if isinstance(person, str):
                    # Convert string to dict format (assume it's a name)
                    person = {
                        'name': person,
                        'title': '',
                        'linkedin': '',
                        'background': '',
                        'type': 'stakeholder'
                    }
                elif not isinstance(person, dict):
                    # Skip invalid person formats
                    continue
                
                contact_id = f"{session_id}-contact-{i+1}"
                contact_query = """
                INSERT INTO session_contacts 
                (contact_id, session_id, contact_name, contact_title, contact_linkedin, 
                 background_notes, contact_type)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """
                execute_query(contact_query, params=(
                    contact_id, session_id, person.get('name', ''),
                    person.get('title', ''), person.get('linkedin', ''),
                    person.get('background', ''), person.get('type', 'stakeholder')
                ))
        
        return True
        
    except Exception as e:
        st.error(f"❌ Error saving session: {e}")
        return False

def clear_session_data():
    """Clear session data for fresh start"""
    session_keys_to_clear = [
        'questions', 'company_info', 'selected_sf_account', 'current_session_id',
        'company_summary_data', 'roadmap', 'roadmap_df', 'competitive_strategy',
        'business_case', 'initial_value_hypothesis', 'outreach_emails',
        'linkedin_messages', 'people_research', 'notes_content',
        'recommended_initiatives', 'competitor', 'contact_name', 'contact_title',
        'outreach_content', 'expert_context'
    ]
    
    for key in session_keys_to_clear:
        if key in st.session_state:
            del st.session_state[key]
    
    return True

def start_new_session():
    """Save current session if it has data, then start fresh"""
    try:
        has_company_data = bool(st.session_state.get('company_info', {}).get('website'))
        has_questions = bool(st.session_state.get('questions'))
        
        if has_company_data or has_questions:
            try:
                save_current_session()
                st.success("✅ Current session saved successfully!")
            except Exception as e:
                st.warning(f"⚠️ Could not save current session: {e}")
        
        clear_session_data()
        st.info("🆕 Started fresh discovery session!")
        st.rerun()
        return True
        
    except Exception as e:
        st.error(f"❌ Error starting new session: {e}")
        return False

def delete_session(session_id):
    """Delete a session and all related data"""
    try:
        # Delete in reverse dependency order
        execute_query("DELETE FROM discovery_answers WHERE session_id = ?", params=(session_id,))
        execute_query("DELETE FROM discovery_questions WHERE session_id = ?", params=(session_id,))
        execute_query("DELETE FROM session_content WHERE session_id = ?", params=(session_id,))
        execute_query("DELETE FROM session_contacts WHERE session_id = ?", params=(session_id,))
        execute_query("DELETE FROM discovery_sessions WHERE session_id = ?", params=(session_id,))
        
        st.success("✅ Session deleted successfully")
        return True
        
    except Exception as e:
        st.error(f"❌ Error deleting session: {e}")
        return False

def get_session_analytics():
    """Get rich analytics using the new schema"""
    try:
        user_email = st.session_state.get('user_email', 'demo_user@company.com')
        
        analytics_query = """
        SELECT 
            COUNT(DISTINCT s.session_id) as total_sessions,
            COUNT(DISTINCT s.company_name) as unique_companies,
            AVG(sp.completion_percentage) as avg_completion,
            COUNT(DISTINCT q.question_id) as total_questions_asked,
            COUNT(DISTINCT a.answer_id) as total_answers_given,
            COUNT(DISTINCT sc.content_id) as total_content_created
        FROM discovery_sessions s
        LEFT JOIN session_progress sp ON s.session_id = sp.session_id
        LEFT JOIN discovery_questions q ON s.session_id = q.session_id
        LEFT JOIN discovery_answers a ON s.session_id = a.session_id
        LEFT JOIN session_content sc ON s.session_id = sc.session_id
        WHERE s.user_email = ?
        """
        
        result = execute_query(analytics_query, params=(user_email,))
        return result.iloc[0].to_dict() if not result.empty else {}
        
    except Exception as e:
        st.error(f"Error loading analytics: {e}")
        return {}

# Keep this for backward compatibility during transition
def generate_session_name(company_info):
    """Generate a human-readable session name - kept for compatibility"""
    if isinstance(company_info, str):
        try:
            company_info = json.loads(company_info)
        except:
            company_info = {'website': company_info}
    
    if not isinstance(company_info, dict):
        company_info = {}
    
    if company_info.get('name'):
        company_name = company_info['name']
    elif company_info.get('website'):
        website = company_info['website']
        company_name = website.replace('https://', '').replace('http://', '').replace('www.', '').split('.')[0].title()
    else:
        company_name = "Unknown Company"
    
    return f"{company_name} - {datetime.now().strftime('%m/%d/%Y')}" 