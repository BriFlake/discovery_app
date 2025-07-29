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
    """Get saved sessions with instant progress calculation via optimized view"""
    try:
        user_email = st.session_state.get('user_email', 'demo_user@company.com')
        
        # Use the pre-computed view for instant results
        query = """
        SELECT 
            session_id,
            session_name,
            company_name,
            company_website,
            competitor,
            contact_name,
            contact_title,
            updated_at,
            total_questions,
            answered_questions,
            completion_percentage,
            content_types_count,
            available_content,
            contacts_count
        FROM session_progress
        WHERE user_email = ?
        ORDER BY updated_at DESC
        """
        
        sessions_df = execute_query(query, params=(user_email,))
        
        if not sessions_df.empty:
            # Enhance display data
            enhanced_sessions = []
            
            for idx, row in sessions_df.iterrows():
                # Parse available content for display
                content_items = []
                if row.get('available_content'):
                    try:
                        content_array = json.loads(row['available_content']) if isinstance(row['available_content'], str) else row['available_content']
                        content_map = {
                            'business_case': '💼 Business Case',
                            'roadmap': '🗺️ Roadmap', 
                            'competitive_strategy': '⚔️ Competitive',
                            'value_hypothesis': '💡 Value Hypothesis',
                            'outreach_emails': '📧 Outreach',
                            'linkedin_messages': '💬 LinkedIn'
                        }
                        content_items = [content_map.get(item, item) for item in content_array if item in content_map]
                    except:
                        content_items = []
                
                enhanced_session = {
                    'SESSION_ID': row['session_id'],
                    'SESSION_NAME': row['session_name'],
                    'COMPANY_NAME': row.get('company_name', 'Unknown Company'),
                    'COMPANY_WEBSITE': row.get('company_website', ''),
                    'COMPETITOR': row.get('competitor', ''),
                    'CONTACT_NAME': row.get('contact_name', ''),
                    'CONTACT_TITLE': row.get('contact_title', ''),
                    'UPDATED_AT': row['updated_at'],
                    'TOTAL_QUESTIONS': int(row.get('total_questions', 0)),
                    'ANSWERS_COUNT': int(row.get('answered_questions', 0)),
                    'COMPLETION_PERCENTAGE': float(row.get('completion_percentage', 0)),
                    'CONTENT_ITEMS': content_items,
                    'CONTENT_COUNT': int(row.get('content_types_count', 0)),
                    'CONTACTS_COUNT': int(row.get('contacts_count', 0)),
                    'HAS_CONTENT': int(row.get('content_types_count', 0)) > 0
                }
                enhanced_sessions.append(enhanced_session)
            
            return pd.DataFrame(enhanced_sessions)
        
        return pd.DataFrame()
        
    except Exception as e:
        st.error(f"Error loading saved sessions: {e}")
        return pd.DataFrame()

def load_session_data(session_id):
    """Load complete session data with seamless UI restoration"""
    try:
        # Clear existing session state first
        clear_session_data()
        
        # 1. Load core session info
        session_query = """
        SELECT session_id, session_name, user_email, company_name, company_website,
               competitor, contact_name, contact_title, notes
        FROM discovery_sessions 
        WHERE session_id = ?
        """
        
        session_result = execute_query(session_query, params=(session_id,))
        
        if session_result.empty:
            st.error("❌ Session not found")
            return False
        
        session_info = session_result.iloc[0]
        
        # 2. Load questions and answers efficiently
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
        
        # 3. Load strategic content
        content_query = """
        SELECT content_type, content_text, content_data
        FROM session_content
        WHERE session_id = ?
        """
        
        content_result = execute_query(content_query, params=(session_id,))
        
        # 4. Load contacts
        contacts_query = """
        SELECT contact_name, contact_title, contact_linkedin, 
               background_notes, contact_type
        FROM session_contacts
        WHERE session_id = ?
        ORDER BY CASE WHEN contact_type = 'primary' THEN 1 ELSE 2 END
        """
        
        contacts_result = execute_query(contacts_query, params=(session_id,))
        
        # 5. Restore session state systematically
        st.session_state.current_session_id = session_id
        
        # Restore company info
        st.session_state.company_info = {
            'name': session_info.get('company_name'),
            'website': session_info.get('company_website'),
            'account_name': session_info.get('company_name')
        }
        
        # Restore contact info
        if session_info.get('contact_name'):
            st.session_state.contact_name = session_info['contact_name']
        if session_info.get('contact_title'):
            st.session_state.contact_title = session_info['contact_title']
        if session_info.get('competitor'):
            st.session_state.competitor = session_info['competitor']
        
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
                            st.session_state.roadmap = roadmap_df
                            st.session_state.roadmap_df = roadmap_df
                        except:
                            pass
                elif content_type == 'outreach_emails':
                    if row.get('content_data'):
                        try:
                            emails_data = json.loads(row['content_data']) if isinstance(row['content_data'], str) else row['content_data']
                            st.session_state.outreach_emails = emails_data
                        except:
                            pass
                elif content_type == 'linkedin_messages':
                    if row.get('content_data'):
                        try:
                            linkedin_data = json.loads(row['content_data']) if isinstance(row['content_data'], str) else row['content_data']
                            st.session_state.linkedin_messages = linkedin_data
                        except:
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
            
            # Set primary contact if exists
            primary_contact = next((c for c in people_research if c['type'] == 'primary'), None)
            if primary_contact:
                st.session_state.contact_name = primary_contact['name']
                st.session_state.contact_title = primary_contact['title']
        
        # Calculate and show success message
        answered_count = len([q for q in questions if q.get('answer', '').strip()])
        total_count = len(questions)
        completion = (answered_count / total_count * 100) if total_count > 0 else 0
        
        st.success(f"✅ **{session_info['session_name']}** loaded successfully • {answered_count}/{total_count} questions ({completion:.0f}%)")
        
        return True
        
    except Exception as e:
        st.error(f"❌ Error loading session: {e}")
        return False

def save_current_session():
    """Save current session using normalized schema"""
    try:
        # Validate we have data to save
        company_info = st.session_state.get('company_info', {})
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
        
        st.success(f"✅ Session saved: {session_name}")
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