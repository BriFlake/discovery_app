# Sales Functions Module
# Core sales functionality including company research, discovery questions, and outreach

import streamlit as st
import pandas as pd
import json
import uuid
from datetime import datetime
from modules.snowflake_utils import (
    get_connection, 
    get_salesforce_accounts, 
    get_salesforce_account_by_id,
    save_session_data,
    load_session_data
)
from modules.llm_functions import (
    generate_discovery_questions, generate_company_summary,
    generate_more_questions_for_category, generate_initiative_questions, research_person,
    generate_initial_value_hypothesis, generate_business_case, generate_competitive_argument,
    autofill_answers_from_notes, generate_roadmap, generate_outreach_emails, generate_linkedin_messages
)

def initialize_company_info(website, industry, competitor, persona):
    """Initialize company information in session state"""
    st.session_state.company_info = {
        'website': website,
        'industry': industry,
        'competitor': competitor,
        'persona': persona
    }
    
    # Generate company summary
    with st.spinner("🔍 Analyzing company..."):
        summary = generate_company_summary(website, industry, persona)
        if summary:
            st.session_state.company_summary = summary
    
    # Generate discovery questions
    with st.spinner("📋 Generating discovery questions..."):
        questions = generate_discovery_questions(website, industry, competitor, persona)
        if questions:
            st.session_state.questions = questions
    
    # Generate initial value hypothesis
    with st.spinner("💡 Creating initial value hypothesis..."):
        hypothesis = generate_initial_value_hypothesis(st.session_state.company_info)
        if hypothesis:
            st.session_state.initial_value_hypothesis = hypothesis

def load_company_from_salesforce(account_id):
    """Load company data from Salesforce"""
    account_data = get_salesforce_account_by_id(account_id)
    
    if not account_data.empty:
        # Get the first row of data
        account_row = account_data.iloc[0]
        
        # Store company info
        st.session_state.company_info = {
            'name': account_row.get('NAME', ''),
            'website': account_row.get('WEBSITE', ''),
            'industry': account_row.get('INDUSTRY', ''),
            'competitor': '',  # Not available from Salesforce
            'persona': 'Business Decision Maker'  # Default
        }
        
        # Generate company overview with initiatives
        with st.spinner("🔍 Analyzing company and generating overview..."):
            summary_data = generate_company_summary(
                account_row.get('WEBSITE', ''),
                account_row.get('INDUSTRY', ''),
                'Business Decision Maker'
            )
            st.session_state.company_summary_data = summary_data
        
        # Generate discovery questions
        with st.spinner("❓ Generating discovery questions..."):
            questions = generate_discovery_questions(
                account_row.get('WEBSITE', ''),
                account_row.get('INDUSTRY', ''),
                '',  # No competitor from Salesforce
                'Business Decision Maker'
            )
            st.session_state.questions = questions
        
        return True
    
    return False

def initialize_company_data():
    """Initialize company data and generate initial content"""
    company_info = st.session_state.company_info
    
    # Generate company overview with initiatives
    with st.spinner("🔍 Analyzing company and generating overview..."):
        summary_data = generate_company_summary(
            company_info.get('website', ''),
            company_info.get('industry', ''),
            company_info.get('persona', 'Business Decision Maker')
        )
        st.session_state.company_summary_data = summary_data
    
    # Generate discovery questions
    with st.spinner("❓ Generating discovery questions..."):
        questions = generate_discovery_questions(
            company_info.get('website', ''),
            company_info.get('industry', ''),
            company_info.get('competitor', ''),
            company_info.get('persona', 'Business Decision Maker')
        )
        st.session_state.questions = questions
    
    # Generate initial value hypothesis
    with st.spinner("💡 Creating initial value hypothesis..."):
        hypothesis = generate_initial_value_hypothesis(company_info)
        if hypothesis:
            st.session_state.initial_value_hypothesis = hypothesis

def add_new_questions_to_category(category):
    """Add new questions to a specific category"""
    company_info = st.session_state.company_info
    existing_questions = [q['text'] for q in st.session_state.questions.get(category, [])]
    
    with st.spinner(f"🧠 Generating new questions for {category}..."):
        new_questions = generate_more_questions_for_category(
            company_info['website'],
            company_info['industry'],
            company_info['competitor'],
            company_info['persona'],
            category,
            existing_questions
        )
        
        if new_questions:
            if category not in st.session_state.questions:
                st.session_state.questions[category] = []
            st.session_state.questions[category].extend(new_questions)
            st.success(f"✅ Added {len(new_questions)} new questions to {category}")
        else:
            st.warning("Could not generate new questions. Please try again.")

def add_initiative_questions(initiative_name):
    """Add questions for a specific business initiative"""
    company_info = st.session_state.company_info
    
    with st.spinner(f"🧠 Generating questions for {initiative_name}..."):
        initiative_questions = generate_initiative_questions(
            company_info['website'],
            company_info['industry'],
            company_info['persona'],
            initiative_name
        )
        
        if initiative_questions:
            if initiative_name not in st.session_state.questions:
                st.session_state.questions[initiative_name] = []
            st.session_state.questions[initiative_name].extend(initiative_questions)
            st.success(f"✅ Added {len(initiative_questions)} questions for {initiative_name}")
        else:
            st.warning("Could not generate initiative questions. Please try again.")

def perform_people_research(name, title):
    """Research a person and add to people research list"""
    with st.spinner(f"🔍 Researching {name}..."):
        research_result = research_person(name, title, st.session_state.company_info)
        
        if research_result:
            person_data = {
                'name': name,
                'title': title,
                'summary': research_result.get('summary', ''),
                'insights': research_result.get('insights', []),
                'topics': research_result.get('topics', {}),
                'research_date': datetime.now().isoformat()
            }
            
            # Add to people research list
            if 'people_research' not in st.session_state:
                st.session_state.people_research = []
            
            # Check if person already exists
            existing_index = None
            for i, person in enumerate(st.session_state.people_research):
                if person['name'].lower() == name.lower():
                    existing_index = i
                    break
            
            if existing_index is not None:
                st.session_state.people_research[existing_index] = person_data
                st.success(f"✅ Updated research for {name}")
            else:
                st.session_state.people_research.append(person_data)
                st.success(f"✅ Added research for {name}")
            
            return person_data
        else:
            st.warning(f"Could not research {name}. Please try again.")
            return None

def auto_populate_answers():
    """Auto-populate answers from meeting notes across all question sections"""
    notes = st.session_state.get('notes_content', '')
    questions = st.session_state.get('questions', {})
    
    if not notes.strip():
        st.warning("Please add meeting notes first.")
        return
    
    if not questions:
        st.warning("No discovery questions found.")
        return
    
    with st.spinner("🤖 Analyzing notes and populating answers..."):
        total_filled = 0
        
        # 1. Auto-fill main discovery questions
        populated_questions = autofill_answers_from_notes(notes, questions)
        
        if populated_questions:
            st.session_state.questions = populated_questions
            # Count how many answers were filled
            main_filled = len([q for q in populated_questions if isinstance(q, dict) and q.get('answer', '').strip()])
            original_filled = len([q for q in questions if isinstance(q, dict) and q.get('answer', '').strip()])
            total_filled += max(0, main_filled - original_filled)
        
        # 2. Auto-fill AI suggested initiative questions
        summary_data = st.session_state.get('company_summary_data', {})
        if isinstance(summary_data, dict) and 'suggested_initiatives' in summary_data:
            initiatives = summary_data['suggested_initiatives']
            if isinstance(initiatives, list):
                for i, initiative in enumerate(initiatives):
                    initiative_questions_key = f"initiative_questions_{i}"
                    initiative_questions = st.session_state.get(initiative_questions_key, [])
                    
                    if initiative_questions:
                        updated_initiative_questions = autofill_answers_from_notes(notes, initiative_questions)
                        if updated_initiative_questions:
                            st.session_state[initiative_questions_key] = updated_initiative_questions
                            # Count filled answers
                            new_filled = len([q for q in updated_initiative_questions if isinstance(q, dict) and q.get('answer', '').strip()])
                            orig_filled = len([q for q in initiative_questions if isinstance(q, dict) and q.get('answer', '').strip()])
                            total_filled += max(0, new_filled - orig_filled)
        
        # 3. Auto-fill custom initiative questions
        custom_questions = st.session_state.get('custom_initiative_questions', [])
        if custom_questions:
            updated_custom_questions = autofill_answers_from_notes(notes, custom_questions)
            if updated_custom_questions:
                st.session_state['custom_initiative_questions'] = updated_custom_questions
                # Count filled answers
                new_filled = len([q for q in updated_custom_questions if isinstance(q, dict) and q.get('answer', '').strip()])
                orig_filled = len([q for q in custom_questions if isinstance(q, dict) and q.get('answer', '').strip()])
                total_filled += max(0, new_filled - orig_filled)
        
        # Show comprehensive success message
        if total_filled > 0:
            st.success(f"✅ Auto-populated {total_filled} answers across all question sections!")
        elif populated_questions or any(st.session_state.get(f"initiative_questions_{i}") for i in range(10)) or st.session_state.get('custom_initiative_questions'):
            st.info("✅ Success! Thanks for doing great discovery.")
        else:
            st.warning("Could not auto-populate answers. Please review manually.")

def generate_strategic_content(content_type="all"):
    """Generate business case, competitive analysis, and roadmap"""
    company_info = st.session_state.company_info
    
    # Prepare discovery notes
    discovery_notes = prepare_discovery_notes()
    
    if not discovery_notes.strip():
        st.warning("Please answer some discovery questions first.")
        return
    
    if content_type == "value_hypothesis" or content_type == "all":
        # Generate value hypothesis
        with st.spinner("💡 Generating value hypothesis..."):
            value_hypothesis = generate_initial_value_hypothesis(company_info)
            if value_hypothesis:
                st.session_state.value_hypothesis = value_hypothesis
    
    if content_type == "business_case" or content_type == "all":
        # Generate business case
        with st.spinner("📊 Generating business case..."):
            business_case = generate_business_case(company_info, discovery_notes)
            if business_case:
                st.session_state.value_strategy_content = business_case
    
    if content_type == "competitive" or content_type == "all":
        # Generate competitive analysis
        with st.spinner("⚔️ Analyzing competitive landscape..."):
            competitive_analysis = generate_competitive_argument(company_info, discovery_notes)
            if competitive_analysis:
                st.session_state.competitive_analysis_content = competitive_analysis
    
    if content_type == "roadmap" or content_type == "all":
        # Generate roadmap
        with st.spinner("🗺️ Creating strategic roadmap..."):
            roadmap_df = generate_roadmap(company_info, discovery_notes, "Business Value")
            if not roadmap_df.empty:
                st.session_state.roadmap = roadmap_df

def prepare_discovery_notes(questions=None):
    """Prepare discovery notes string from answered questions"""
    if questions is None:
        questions = st.session_state.get('questions', {})
    
    notes_parts = []
    
    # Handle both list and dictionary formats
    if isinstance(questions, list):
        # Convert list format to categorized format
        categories = {
            'Technical': [],
            'Business': [],
            'Competitive': []
        }
        
        for q in questions:
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
        questions_dict = questions
    
    for category, question_list in questions_dict.items():
        if question_list:
            answered_questions = [q for q in question_list if q.get('answer', '').strip()]
            if answered_questions:
                notes_parts.append(f"\n=== {category} ===")
                for q in answered_questions:
                    notes_parts.append(f"Q: {q['text']}")
                    notes_parts.append(f"A: {q['answer']}")
                    notes_parts.append("")
    
    return "\n".join(notes_parts)

def generate_outreach_content(content_type="all"):
    """Generate outreach emails and LinkedIn messages"""
    company_info = st.session_state.company_info
    discovery_notes = prepare_discovery_notes()
    roadmap_df = st.session_state.get('roadmap', pd.DataFrame())
    
    if not discovery_notes.strip():
        st.warning("Please answer some discovery questions first to generate personalized outreach.")
        return
    
    if content_type == "email" or content_type == "all":
        # Generate emails
        with st.spinner("📧 Generating personalized email..."):
            emails = generate_outreach_emails(company_info, discovery_notes, roadmap_df)
            if emails:
                # Handle different response formats
                email_data = None
                
                if isinstance(emails, dict):
                    # Check if it's the expected format with email_1, email_2, etc.
                    if 'email_1' in emails:
                        email_data = emails['email_1']
                    elif len(emails) > 0:
                        # Take the first email from any key
                        first_key = list(emails.keys())[0]
                        email_data = emails[first_key]
                elif isinstance(emails, list) and emails:
                    email_data = emails[0]
                else:
                    email_data = emails
                
                # Ensure email_data has the correct format
                if isinstance(email_data, dict) and 'subject' in email_data and 'body' in email_data:
                    st.session_state.email = email_data
                elif isinstance(email_data, str):
                    # If it's just a string, create proper structure
                    st.session_state.email = {
                        'subject': 'Follow-up: Snowflake Discussion',
                        'body': email_data
                    }
                else:
                    # Fallback email
                    st.session_state.email = {
                        'subject': 'Follow-up: Snowflake Opportunity Discussion',
                        'body': f"Hi there,\n\nThank you for our conversation about {company_info.get('website', 'your company')}. Based on our discussion, I believe Snowflake could help address some of the challenges we talked about.\n\nI'd love to schedule a follow-up call to explore this further.\n\nBest regards"
                    }
    
    if content_type == "linkedin" or content_type == "all":
        # Generate LinkedIn messages
        with st.spinner("💼 Generating LinkedIn message..."):
            linkedin_messages = generate_linkedin_messages(company_info, discovery_notes, roadmap_df)
            if linkedin_messages:
                # Handle different response formats
                linkedin_data = None
                
                if isinstance(linkedin_messages, dict):
                    # Check if it's the expected format with message_1, message_2, etc.
                    if 'message_1' in linkedin_messages:
                        linkedin_data = linkedin_messages['message_1']
                    elif len(linkedin_messages) > 0:
                        # Take the first message from any key
                        first_key = list(linkedin_messages.keys())[0]
                        linkedin_data = linkedin_messages[first_key]
                elif isinstance(linkedin_messages, list) and linkedin_messages:
                    linkedin_data = linkedin_messages[0]
                else:
                    linkedin_data = linkedin_messages
                
                # Extract message text from LinkedIn data
                if isinstance(linkedin_data, dict):
                    if 'body' in linkedin_data:
                        st.session_state.linkedin = linkedin_data['body']
                    elif 'opening' in linkedin_data and 'body' in linkedin_data:
                        st.session_state.linkedin = f"{linkedin_data['opening']} {linkedin_data['body']}"
                    else:
                        # Try to get any text value
                        for value in linkedin_data.values():
                            if isinstance(value, str):
                                st.session_state.linkedin = value
                                break
                elif isinstance(linkedin_data, str):
                    st.session_state.linkedin = linkedin_data
                else:
                    # Fallback LinkedIn message
                    st.session_state.linkedin = f"Hi! I'd love to connect and discuss how Snowflake could help {company_info.get('website', 'your company')} with your data initiatives. Would you be open to a brief call?"

def save_discovery_answers():
    """Save answered discovery questions to Snowflake"""
    questions = st.session_state.get('questions', {})
    company_info = st.session_state.get('company_info', {})
    
    if not questions:
        st.warning("No questions to save.")
        return False
    
    # Prepare data for saving
    rows = []
    current_time = datetime.now().isoformat()
    session_id = st.session_state.get('selected_session_id', 'new')
    
    for category, question_list in questions.items():
        for question in question_list:
            if question.get('answer', '').strip():  # Only save answered questions
                row = {
                    'session_id': session_id,
                    'company_website': company_info.get('website', ''),
                    'industry': company_info.get('industry', ''),
                    'competitor': company_info.get('competitor', ''),
                    'persona': company_info.get('persona', ''),
                    'category': category,
                    'question_id': question.get('id', str(uuid.uuid4())),
                    'question_text': question.get('text', ''),
                    'answer': question.get('answer', ''),
                    'is_favorite': question.get('favorite', False),
                    'answered_date': current_time
                }
                rows.append(row)
    
    if not rows:
        st.warning("No answered questions to save.")
        return False
    
    # Save session data in correct format
    session_data = {
        'company_info': company_info,
        'questions': questions,
        'saved_date': current_time,
        'answer_count': len(rows)
    }
    
    success = save_session_data(session_id, session_data)
    
    if success:
        st.success(f"✅ Saved {len(rows)} answered questions to Snowflake!")
        return True
    else:
        st.error("❌ Failed to save to Snowflake.")
        return False

def export_session_data():
    """Export current session data as JSON"""
    session_data = {
        'export_date': datetime.now().isoformat(),
        'company_info': st.session_state.get('company_info', {}),
        'company_summary': st.session_state.get('company_summary', ''),
        'questions': st.session_state.get('questions', {}),
        'notes_content': st.session_state.get('notes_content', ''),
        'initial_value_hypothesis': st.session_state.get('initial_value_hypothesis', ''),
        'value_strategy_content': st.session_state.get('value_strategy_content', ''),
        'competitive_analysis_content': st.session_state.get('competitive_analysis_content', ''),
        'roadmap_df': st.session_state.get('roadmap_df', pd.DataFrame()).to_dict('records') if not st.session_state.get('roadmap_df', pd.DataFrame()).empty else [],
        'people_research': st.session_state.get('people_research', []),
        'outreach_emails': st.session_state.get('outreach_emails', {}),
        'linkedin_messages': st.session_state.get('linkedin_messages', {}),
        'recommended_initiatives': st.session_state.get('recommended_initiatives', [])
    }
    
    return json.dumps(session_data, indent=2)

def get_session_summary():
    """Get a summary of the current session for display"""
    company_name = st.session_state.get('company_info', {}).get('website', 'No company selected')
    
    # Count answered questions
    questions = st.session_state.get('questions', {})
    total_questions = sum(len(q_list) for q_list in questions.values())
    answered_questions = sum(
        len([q for q in q_list if q.get('answer', '').strip()]) 
        for q_list in questions.values()
    )
    
    # Check other content
    has_notes = bool(st.session_state.get('notes_content', '').strip())
    has_roadmap = not st.session_state.get('roadmap_df', pd.DataFrame()).empty
    has_strategy = bool(st.session_state.get('value_strategy_content', '').strip())
    has_people = bool(st.session_state.get('people_research', []))
    has_outreach = bool(st.session_state.get('outreach_emails', {}))
    
    return {
        'company': company_name,
        'total_questions': total_questions,
        'answered_questions': answered_questions,
        'completion_rate': round((answered_questions / total_questions * 100) if total_questions > 0 else 0, 1),
        'has_notes': has_notes,
        'has_roadmap': has_roadmap,
        'has_strategy': has_strategy,
        'has_people': has_people,
        'has_outreach': has_outreach
    } 