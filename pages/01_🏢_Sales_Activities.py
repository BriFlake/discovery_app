# Sales Activities Page
# Complete sales discovery workflow

import streamlit as st
import pandas as pd
import uuid
import time
from modules.ui_components import render_navigation_sidebar
from modules.llm_functions import (generate_discovery_questions, generate_company_summary, generate_initiative_questions,
                                 generate_business_case, generate_roadmap, generate_competitive_argument, 
                                 generate_initial_value_hypothesis, generate_outreach_emails, generate_linkedin_messages,
                                 generate_people_insights)
from modules.sales_functions import prepare_discovery_notes

st.set_page_config(
    page_title="Sales Activities", 
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Mark app as fully loaded for database queries
from modules.snowflake_utils import mark_app_loaded
mark_app_loaded()

# Check if there's a session to load from homepage
if 'session_to_load' in st.session_state:
    session_id = st.session_state.session_to_load
    session_name = st.session_state.get('session_name_to_load', 'Unknown Session')
    
    # Clear the flags
    del st.session_state.session_to_load
    if 'session_name_to_load' in st.session_state:
        del st.session_state.session_name_to_load
    
    # Load the session data
    with st.spinner(f"📂 Loading session: {session_name}..."):
        from modules.session_management_v2 import load_session_data
        if load_session_data(session_id):
            # Add a brief loading message for questions processing
            with st.spinner("📋 Restoring discovery questions and answers..."):
                pass
            st.success(f"✅ Successfully loaded: {session_name}")
        else:
            st.error(f"❌ Failed to load session: {session_name}")

# Render sidebar
render_navigation_sidebar()

st.title("🏢 Sales Activities")
st.markdown("**Complete sales discovery workflow**")

# Main workflow tabs at the top
tab1, tab2, tab3, tab4 = st.tabs([
    "🔍 Discovery", 
    "📈 Value & Strategy", 
    "📧 Outreach", 
    "👥 People Research"
])

with tab1:
    # === DISCOVERY TAB ===
    
    # Start New Session - Above everything else
    st.markdown("### 🆕 Session Management")
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("🔄 Clear and Restart", use_container_width=True, help="Save current work and start fresh", key="start_new_main"):
            try:
                from modules.session_management_v2 import start_new_session
                start_new_session()
            except ImportError as e:
                # Fallback implementation if import fails
                try:
                    from modules.session_management_v2 import clear_session_data, save_current_session
                    
                    # Check if there's data to save
                    has_company_data = bool(st.session_state.get('company_info', {}).get('website'))
                    has_questions = bool(st.session_state.get('questions'))
                    
                    if has_company_data or has_questions:
                        try:
                            success = save_current_session()
                            if success:
                                st.success("✅ Current session saved successfully!")
                        except Exception as save_error:
                            st.warning(f"⚠️ Could not save current session: {save_error}")
                    
                    clear_session_data()
                    st.info("🆕 Started fresh discovery session!")
                    st.rerun()
                    
                except ImportError:
                    # Ultimate fallback - manual clear
                    for key in ['company_info', 'questions', 'company_summary_data', 'business_case', 'competitive_strategy', 'initial_value_hypothesis', 'roadmap_df', 'outreach_emails', 'linkedin_messages', 'people_research']:
                        if key in st.session_state:
                            del st.session_state[key]
                    st.info("🆕 Session cleared manually!")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Error starting new session: {e}")
    
    with col2:
        # Save Progress Button moved here
        if st.session_state.get('company_info', {}).get('website'):
            if st.button("💾 Save Progress", use_container_width=True, key="save_progress_main"):
                try:
                    from modules.session_management_v2 import save_current_session
                    success = save_current_session()
                except ImportError:
                    st.error("❌ Session management system unavailable")
                except Exception as e:
                    st.error(f"❌ Error saving session: {e}")
        else:
            st.caption("💡 Save current session to continue later")
    
    st.markdown("---")
    
    # 1. SAVED SESSIONS - Collapsible
    with st.expander("📂 **Saved Sessions**", expanded=False):
        st.markdown("**Continue your previous discovery sessions**")
        
        # Quick check for session availability without loading all data
        user_email = st.session_state.get('user_email', 'demo_user@company.com')
        has_sessions = True  # Default assumption (enable button if unsure)
        
        try:
            from modules.snowflake_utils import execute_query
            
            # Try old system first
            try:
                old_count_query = "SELECT COUNT(*) as session_count FROM snowpublic.streamlit.discovery_sessions WHERE user_email = ? LIMIT 1"
                count_result = execute_query(old_count_query, params=(user_email,))
                has_sessions = not count_result.empty and count_result.iloc[0]['session_count'] > 0
            except:
                # Try new system
                try:
                    new_count_query = "SELECT COUNT(*) as session_count FROM discovery_sessions WHERE user_email = ? LIMIT 1" 
                    count_result = execute_query(new_count_query, params=(user_email,))
                    has_sessions = not count_result.empty and count_result.iloc[0]['session_count'] > 0
                except:
                    # Both failed, assume sessions might exist (enable button)
                    has_sessions = True
        except:
            # Complete failure, assume sessions might exist (enable button)
            has_sessions = True
        
        # Show appropriate button state
        try:
            if has_sessions:
                button_disabled = False
                button_text = "🔄 Load My Sessions"
                button_help = "Click to load your saved discovery sessions"
            else:
                button_disabled = True  
                button_text = "📭 No Sessions Available"
                button_help = "Create your first discovery session to see saved sessions here"
            
            # Add the button with conditional state
            if st.button(button_text, use_container_width=True, key="load_sessions_btn", 
                        disabled=button_disabled, help=button_help):
                st.session_state['show_sessions'] = True
                
        except Exception as e:
            # Fallback to always enabled if check fails
            if st.button("🔄 Load My Sessions", use_container_width=True, key="load_sessions_btn"):
                st.session_state['show_sessions'] = True
        
        # Only load and display sessions if requested
        if st.session_state.get('show_sessions', False):
            try:
                from modules.session_management_v2 import get_saved_sessions, load_session_data
                
                with st.spinner("📂 Loading your saved sessions..."):
                    sessions_df = get_saved_sessions()
                
                if not sessions_df.empty:
                    st.markdown(f"**Found {len(sessions_df)} sessions:**")
                    
                    # Display sessions
                    for idx, session in sessions_df.iterrows():
                        with st.container():
                            col1, col2, col3 = st.columns([3, 2, 1])
                            
                            with col1:
                                st.markdown(f"**{session['SESSION_NAME']}**")
                                company_name = session.get('COMPANY_NAME', 'Unknown Company')
                                contact_name = session.get('CONTACT_NAME', '')
                                if contact_name:
                                    st.caption(f"🏢 {company_name} • 👤 {contact_name}")
                                else:
                                    st.caption(f"🏢 {company_name}")
                            
                            with col2:
                                completion = session.get('COMPLETION_PERCENTAGE', 0)
                                answered = session.get('ANSWERS_COUNT', 0)
                                total = session.get('TOTAL_QUESTIONS', 0)
                                
                                if total > 0:
                                    st.caption(f"📊 Progress: {completion:.0f}% ({answered}/{total})")
                                else:
                                    st.caption("📋 New session")
                            
                            with col3:
                                if st.button("📂", key=f"load_session_{session['SESSION_ID']}", 
                                           help=f"Load {session['SESSION_NAME']}", use_container_width=True):
                                    st.session_state.session_to_load = session['SESSION_ID']
                                    st.session_state.session_name_to_load = session['SESSION_NAME']
                                    st.rerun()
                            
                            st.markdown("---")
                
                else:
                    st.info("📭 No saved sessions found. Complete a discovery session to see your history here.")
                    
            except Exception as e:
                st.error(f"❌ Session management error: {e}")
        
        else:
            # Show instructions when sessions haven't been loaded yet
            if has_sessions:
                st.info("💡 Click **Load My Sessions** to view your saved discovery sessions.")
            else:
                st.warning("📭 **No saved sessions found.** Start your first discovery session below!")
    
    st.markdown("---")
    
    # 2. SMART SALESFORCE ACCOUNT SEARCH - Collapsible
    with st.expander("🔍 **Smart Salesforce Account Search**", expanded=False):
        st.markdown("Search for companies in Salesforce to start discovery")
        
        search_term = st.text_input("🔍 Search Company Name", placeholder="Enter company name to search Salesforce...", key="sf_search")
        
        if search_term:
            try:
                from modules.snowflake_utils import execute_query
                
                def search_salesforce_accounts_live(term, limit=10):
                    query = """
                    SELECT 
                        id as ACCOUNT_ID,
                        name as ACCOUNT_NAME,
                        website as WEBSITE,
                        industry as INDUSTRY,
                        billing_city as BILLING_CITY,
                        type as TYPE,
                        number_of_employees as NUMBER_OF_EMPLOYEES
                    FROM FIVETRAN.SALESFORCE.ACCOUNT 
                    WHERE UPPER(name) LIKE UPPER(?)
                    ORDER BY name
                    LIMIT ?
                    """
                    return execute_query(query, params=(f"%{search_term}%", limit))
                
                with st.spinner(f"🔍 Searching Salesforce for '{search_term}'..."):
                    search_results = search_salesforce_accounts_live(search_term, 20)
                
                if not search_results.empty:
                    st.markdown(f"**Found {len(search_results)} results:**")
                    
                    # Enhanced results table with selection
                    selected_row = st.dataframe(
                        search_results[['ACCOUNT_NAME', 'INDUSTRY', 'BILLING_CITY', 'TYPE', 'NUMBER_OF_EMPLOYEES']],
                        hide_index=True,
                        use_container_width=True,
                        on_select="rerun",
                        selection_mode="single-row"
                    )
                    
                    # Check if any row is selected
                    if selected_row['selection']['rows']:
                        # Get the selected account
                        selected_index = selected_row['selection']['rows'][0]
                        selected_account = search_results.iloc[selected_index]
                        
                        # Show detailed account information
                        st.markdown("#### 📊 Selected Account Details")
                        
                        company_name = selected_account.get('ACCOUNT_NAME', 'N/A')
                        website = selected_account.get('WEBSITE', 'N/A')
                        industry = selected_account.get('INDUSTRY', 'N/A')
                        city = selected_account.get('BILLING_CITY', 'N/A')
                        account_type = selected_account.get('TYPE', 'N/A')
                        employees = selected_account.get('NUMBER_OF_EMPLOYEES', 'N/A')
                        account_id = selected_account.get('ACCOUNT_ID', 'N/A')
                        
                        # Comprehensive info display
                        col1, col2 = st.columns(2)
                        with col1:
                            st.info(f"**Company:** {company_name}")
                            st.info(f"**Industry:** {industry}")
                            st.info(f"**Website:** {website}")
                        with col2:
                            st.info(f"**City:** {city}")
                            st.info(f"**Type:** {account_type}")
                            st.info(f"**Employees:** {employees}")
                        
                        # Store selected account in session state
                        st.session_state.selected_sf_account = selected_account
                        
                        # Discovery setup form
                        st.markdown("#### 🎯 Discovery Setup")
                        col1, col2 = st.columns(2)
                        with col1:
                            contact_name = st.text_input("👤 Contact Name", placeholder="John Smith", key="sf_contact_name")
                            competitor = st.text_input("🏆 Primary Competitor", placeholder="Main competitor (optional)", key="sf_competitor")
                        with col2:
                            contact_title = st.text_input("💼 Contact Title", placeholder="VP of Engineering", key="sf_contact_title")
                        
                        if st.button("🚀 Start Discovery", use_container_width=True, type="primary", key="sf_start_discovery"):
                            if contact_title:
                                # Store comprehensive company info from Salesforce
                                company_data = {
                                    'website': selected_account.get('WEBSITE', ''),
                                    'industry': selected_account.get('INDUSTRY', ''),
                                    'contact_name': contact_name,
                                    'contact_title': contact_title,
                                    'competitor': competitor,
                                    'name': company_name,
                                    'account_name': company_name,
                                    'salesforce_id': account_id
                                }
                                
                                # Generate AI content
                                with st.spinner("🔍 Analyzing company and generating discovery questions..."):
                                    # Generate enhanced company overview with initiatives
                                    summary_data = generate_company_summary(
                                        selected_account.get('WEBSITE', company_name), 
                                        selected_account.get('INDUSTRY', ''), 
                                        contact_title
                                    )
                                    
                                    # Generate targeted discovery questions
                                    questions = generate_discovery_questions(
                                        selected_account.get('WEBSITE', company_name),
                                        selected_account.get('INDUSTRY', ''),
                                        competitor if competitor else '',
                                        contact_title
                                    )
                                    
                                    # Convert dictionary format to list format for display
                                    if isinstance(questions, dict):
                                        questions_list = []
                                        for category, category_questions in questions.items():
                                            if isinstance(category_questions, list):
                                                for q in category_questions:
                                                    if isinstance(q, dict):
                                                        q['category'] = category
                                                        questions_list.append(q)
                                        questions = questions_list
                                
                                st.session_state.company_info = company_data
                                st.session_state.company_summary_data = summary_data
                                st.session_state.questions = questions
                                
                                st.success("✅ Company research complete! Discovery questions generated.")
                                st.rerun()
                            else:
                                st.error("❌ Please enter the contact title to continue")
                else:
                    st.info(f"🔍 No results found for '{search_term}'. Try a different search term or use Manual Company Setup below.")
                    
            except Exception as e:
                st.error(f"❌ Error searching Salesforce: {e}")
                st.info("💡 Please try again or use Manual Company Setup below.")
    
    # 3. MANUAL COMPANY SETUP - Collapsible (FIXED INDENTATION)
    with st.expander("🏢 **Manual Company Setup**", expanded=False):
        st.markdown("Enter company information manually if not found in Salesforce")
        
        with st.form("company_form"):
            st.markdown("#### Manual Company Setup")
            
            col1, col2 = st.columns(2)
            with col1:
                website = st.text_input("🌐 Company Website", placeholder="company.com")
                industry = st.text_input("🏭 Industry", placeholder="Technology, Healthcare, etc.")
            
            with col2:
                contact_name = st.text_input("👤 Contact Name", placeholder="John Smith")
                contact_title = st.text_input("💼 Contact Title", placeholder="VP of Engineering")
        
            competitor = st.text_input("🏆 Primary Competitor", placeholder="Main competitor (optional)")
        
            submitted = st.form_submit_button("🚀 Start Discovery", use_container_width=True, type="primary")
        
        if submitted:
            if website and industry and contact_title:
                # Store company info
                company_data = {
                    'website': website.strip(),
                    'industry': industry.strip(),
                    'contact_name': contact_name.strip() if contact_name else '',
                    'contact_title': contact_title.strip(),
                    'competitor': competitor.strip() if competitor else ''
                }
                
                # Auto-generate company summary and discovery questions
                with st.spinner("🔍 Analyzing company and generating discovery questions..."):
                    # Generate enhanced company overview with initiatives
                    summary_data = generate_company_summary(
                        website.strip(), 
                        industry.strip(), 
                        contact_title.strip()
                    )
                    
                    # Generate targeted discovery questions
                    questions = generate_discovery_questions(
                        website.strip(),
                        industry.strip(),
                        competitor.strip() if competitor else '',
                        contact_title.strip()
                    )
                    
                    # Convert dictionary format to list format for display
                    if isinstance(questions, dict):
                        questions_list = []
                        for category, category_questions in questions.items():
                            if isinstance(category_questions, list):
                                for q in category_questions:
                                    if isinstance(q, dict):
                                        q['category'] = category
                                        questions_list.append(q)
                        questions = questions_list
                    
                    st.session_state.company_info = company_data
                    st.session_state.company_summary_data = summary_data
                    st.session_state.questions = questions
                    
                st.success("✅ Company research complete! Discovery questions generated.")
                st.rerun()
            else:
                st.error("❌ Please fill in Company Website, Industry, and Contact Title")
    
    # Company Overview & Key Initiatives Section (LLM-Generated)
    if 'company_summary_data' in st.session_state and st.session_state.company_summary_data:
        st.markdown("---")
        st.markdown("### 🏢 Company Overview & Key Initiatives")
        
        summary_data = st.session_state.company_summary_data
        company_info = st.session_state.get('company_info', {})
        
        with st.container(border=True):
            st.markdown("#### 📋 Company Analysis")
            if isinstance(summary_data, dict) and 'company_overview' in summary_data:
                st.markdown(summary_data['company_overview'])
            else:
                st.markdown("*Company overview will appear here after analysis...*")
        
        # Auto-populate discovery notes section
        with st.expander("📝 **Auto-populate Discovery Answers from Notes**", expanded=False):
            st.markdown("**Paste your meeting notes to automatically populate discovery answers**")
            
            # Notes input area
            notes_content = st.text_area(
                "📋 Paste Meeting Notes Here", 
                placeholder="Paste your meeting notes, call transcripts, or any relevant information here. The AI will automatically extract answers to populate your discovery questions.",
                height=150,
                key="discovery_notes"
            )
            
            # Auto-populate button
            if st.button("🤖 Auto-fill from Notes", use_container_width=True, key="autofill_btn"):
                if notes_content.strip():
                    with st.spinner("🤖 Analyzing notes and auto-filling answers..."):
                        from modules.llm_functions import autofill_answers_from_notes
                        
                        total_filled = 0
                        
                        # 1. Auto-fill main discovery questions
                        questions = st.session_state.questions
                        updated_questions = autofill_answers_from_notes(notes_content, questions)
                        
                        if updated_questions:
                            st.session_state.questions = updated_questions
                            main_filled = len([q for q in updated_questions if isinstance(q, dict) and q.get('answer', '').strip()])
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
                                        updated_initiative_questions = autofill_answers_from_notes(notes_content, initiative_questions)
                                        if updated_initiative_questions:
                                            st.session_state[initiative_questions_key] = updated_initiative_questions
                                            new_filled = len([q for q in updated_initiative_questions if isinstance(q, dict) and q.get('answer', '').strip()])
                                            orig_filled = len([q for q in initiative_questions if isinstance(q, dict) and q.get('answer', '').strip()])
                                            total_filled += max(0, new_filled - orig_filled)
                        
                        # 3. Auto-fill custom initiative questions
                        custom_questions = st.session_state.get('custom_initiative_questions', [])
                        if custom_questions:
                            updated_custom_questions = autofill_answers_from_notes(notes_content, custom_questions)
                            if updated_custom_questions:
                                st.session_state['custom_initiative_questions'] = updated_custom_questions
                                new_filled = len([q for q in updated_custom_questions if isinstance(q, dict) and q.get('answer', '').strip()])
                                orig_filled = len([q for q in custom_questions if isinstance(q, dict) and q.get('answer', '').strip()])
                                total_filled += max(0, new_filled - orig_filled)
                        
                                                # Show comprehensive success message
                        if total_filled > 0:
                            st.success(f"✅ Auto-populated {total_filled} answers across all question sections!")
                            st.rerun()
                        elif updated_questions or any(st.session_state.get(f"initiative_questions_{i}") for i in range(10)) or st.session_state.get('custom_initiative_questions'):
                            st.info("✅ Success! Thanks for doing great discovery.")
                        else:
                            st.error("❌ Failed to auto-populate answers. Please try again.")
                else:
                    st.warning("⚠️ Please enter some notes first")
        
        # Discovery Questions Section
        if 'questions' in st.session_state and st.session_state.questions:
            questions = st.session_state.questions
            
            # Calculate summary statistics
            if isinstance(questions, list):
                total_questions = len([q for q in questions if isinstance(q, dict)])
                answered_questions = len([q for q in questions if isinstance(q, dict) and q.get('answer', '').strip()])
                completion_percentage = (answered_questions / total_questions * 100) if total_questions > 0 else 0
                
                st.markdown("---")
                st.markdown(f"### 📋 Discovery Questions ({answered_questions}/{total_questions} answered - {completion_percentage:.0f}%)")
                
                # Categorize questions for organized display
                categorized_questions = {
                    'Technical': [],
                    'Business': [],
                    'Competitive': [],
                    'Initiative': []
                }
                
                for q in questions:
                    if isinstance(q, dict):
                        category = q.get('category', '').lower()
                        text = q.get('text', '').lower()
                        
                        if 'technical' in category or 'tech' in category:
                            categorized_questions['Technical'].append(q)
                        elif 'business' in category or 'biz' in category:
                            categorized_questions['Business'].append(q)
                        elif 'competitive' in category or 'competitor' in category or 'competition' in category:
                            categorized_questions['Competitive'].append(q)
                        else:
                            # Check text content for categorization
                            if any(keyword in text for keyword in ['technical', 'technology', 'system', 'integration', 'api', 'architecture']):
                                categorized_questions['Technical'].append(q)
                            elif any(keyword in text for keyword in ['budget', 'cost', 'roi', 'business', 'process', 'decision']):
                                categorized_questions['Business'].append(q)
                            elif any(keyword in text for keyword in ['competitor', 'alternative', 'vendor', 'solution']):
                                categorized_questions['Competitive'].append(q)
                    else:
                                categorized_questions['Initiative'].append(q)
                
                # Display questions by category
                for category_name, category_questions in categorized_questions.items():
                    if category_questions:
                        cat_total = len(category_questions)
                        cat_answered = len([q for q in category_questions if q.get('answer', '').strip()])
                        
                        with st.expander(f"🔍 **{category_name} Discovery** ({cat_answered}/{cat_total})", expanded=False):
                            
                            # Add ➕ 5 More and ✏️ Add Manual buttons
                            col1, col2 = st.columns(2)
                            with col1:
                                if st.button(f"➕ 5 More", key=f"more_{category_name.lower()}", help=f"Generate 5 more {category_name.lower()} questions"):
                                    try:
                                        from modules.llm_functions import generate_more_questions_for_category
                                        
                                        company_info = st.session_state.get('company_info', {})
                                        website = company_info.get('website', '')
                                        industry = company_info.get('industry', '')
                                        competitor = company_info.get('competitor', '')
                                        contact_title = company_info.get('contact_title', '')
                                        
                                        new_questions = generate_more_questions_for_category(
                                            website, industry, competitor, contact_title, category_name, category_questions
                                        )
                                        
                                        if new_questions:
                                            # Format new questions to match existing structure
                                            formatted_questions = []
                                            for q_obj in new_questions:
                                                # Extract text from question object
                                                if isinstance(q_obj, dict):
                                                    question_text = q_obj.get('text', str(q_obj))
                                                else:
                                                    question_text = str(q_obj)
                                                
                                                # Clean any unwanted markdown/formatting
                                                question_text = question_text.strip()
                                                
                                                formatted_q = {
                                                    'id': str(uuid.uuid4()),
                                                    'text': question_text,
                                                    'category': category_name,
                                                    'explanation': '',
                                                    'importance': q.get('importance', 'medium'),
                                                    'answer': ''
                                                }
                                                formatted_questions.append(formatted_q)
                                            
                                            # Add to existing questions (preserve existing ones)
                                            current_questions = st.session_state.questions.copy()
                                            current_questions.extend(formatted_questions)
                                            st.session_state.questions = current_questions
                                            
                                            st.success(f"✅ Added 5 more {category_name.lower()} questions! Total questions: {len(current_questions)}")
                                            st.rerun()
                                        else:
                                            st.error("❌ Failed to generate more questions")
                                            
                                    except Exception as e:
                                        st.error(f"❌ Error generating questions: {e}")
        
                            with col2:
                                if st.button(f"✏️ Add Manual", key=f"manual_{category_name.lower()}", help=f"Add your own {category_name.lower()} question"):
                                    st.session_state[f'show_manual_{category_name.lower()}'] = True
                                    st.rerun()
                            
                            # Show manual question form if requested
                            if st.session_state.get(f'show_manual_{category_name.lower()}', False):
                                with st.form(f"manual_question_{category_name.lower()}"):
                                    new_question_text = st.text_area("Question:", placeholder=f"Enter your {category_name.lower()} question here...")
                                    new_question_explanation = st.text_input("Explanation (optional):", placeholder="Why is this question important?")
                                    
                                    col1, col2 = st.columns(2)
                                    with col1:
                                        if st.form_submit_button("➕ Add Question"):
                                            if new_question_text.strip():
                                                # Create new question
                                                new_question = {
                                                    'id': str(uuid.uuid4()),
                                                    'text': new_question_text.strip(),
                                                    'category': category_name,
                                                    'explanation': new_question_explanation.strip(),
                                                    'importance': 'medium',
                                                    'answer': ''
                                                }
                                                
                                                # Add to questions
                                                current_questions = st.session_state.questions.copy()
                                                current_questions.append(new_question)
                                                st.session_state.questions = current_questions
                                                
                                                # Clear the form
                                                del st.session_state[f'show_manual_{category_name.lower()}']
                                                
                                                st.success(f"✅ Added new {category_name.lower()} question!")
                                            else:
                                                st.error("❌ Please enter a question")
                                    
                                    with col2:
                                        if st.form_submit_button("❌ Cancel"):
                                            del st.session_state[f'show_manual_{category_name.lower()}']
                                            st.rerun()
                            
                            # Display questions in this category
                            for i, question in enumerate(category_questions):
                                question_id = question.get('id', f"{category_name}_{i}")
                                question_text = question.get('text', 'No question text')
                                question_explanation = question.get('explanation', '')
                                current_answer = question.get('answer', '')
                                
                                # Question container
                                with st.container():
                                    # Question header with delete option
                                    q_col1, q_col2 = st.columns([10, 1])
                                    with q_col1:
                                        st.markdown(f"**Q{i+1}:** {question_text}")
                                        if question_explanation:
                                            st.caption(f"💡 {question_explanation}")
                                    with q_col2:
                                        if st.button("🗑️", key=f"delete_{question_id}", help="Delete this question"):
                                            # Remove question from session state
                                            updated_questions = [q for q in st.session_state.questions if q.get('id') != question_id]
                                            st.session_state.questions = updated_questions
                                            st.rerun()
                                    
                                    # Answer input
                                    answer_key = f"answer_{question_id}"
                                    answer = st.text_area(
                                        "Your Answer:",
                                        value=current_answer,
                                        placeholder="Enter your answer here...",
                                        key=answer_key,
                                        height=100
                                    )
                                    
                                    # Update answer in session state
                                    if answer != current_answer:
                                        # Find and update the question
                                        for q in st.session_state.questions:
                                            if q.get('id') == question_id:
                                                q['answer'] = answer
                                                break
                                    
                                    st.markdown("---")
                
                # Suggested Key Initiatives Section (AI-Generated) - Collapsible and Collapsed by Default
                if isinstance(summary_data, dict) and 'suggested_initiatives' in summary_data:
                    initiatives = summary_data['suggested_initiatives']
                    if isinstance(initiatives, list) and initiatives:
                        for i, initiative in enumerate(initiatives):
                            initiative_title = initiative.get('title', f'Initiative {i+1}')
                            initiative_description = initiative.get('description', '')
                            
                            with st.expander(f"🪄 **{initiative_title}**", expanded=False):
                                if initiative_description:
                                    st.markdown(f"**Description:** {initiative_description}")
                                    st.markdown("---")
                                
                                # Check if questions exist for this initiative
                                initiative_questions_key = f"initiative_questions_{i}"
                                initiative_questions = st.session_state.get(initiative_questions_key, [])
                                
                                if not initiative_questions:
                                    # Generate questions button
                                    if st.button(f"🔍 Generate 5 Discovery Questions", key=f"gen_init_{i}"):
                                        with st.spinner(f"Generating questions for {initiative_title}..."):
                                            from modules.llm_functions import generate_initiative_questions
                                            
                                            company_info = st.session_state.get('company_info', {})
                                            questions = generate_initiative_questions(
                                                company_info.get('website', ''),
                                                company_info.get('industry', ''),
                                                company_info.get('contact_title', ''),
                                                initiative_title,
                                                initiative_description
                                            )
                                            
                                            if questions:
                                                # Format questions
                                                formatted_questions = []
                                                for q_obj in questions:
                                                    # Extract text from question object
                                                    if isinstance(q_obj, dict):
                                                        question_text = q_obj.get('text', str(q_obj))
                                                    else:
                                                        question_text = str(q_obj)
                                                    
                                                    # Clean any unwanted markdown/formatting
                                                    question_text = question_text.strip()
                                                    
                                                    formatted_q = {
                                                        'id': str(uuid.uuid4()),
                                                        'text': question_text,
                                                        'category': 'Initiative',
                                                        'explanation': f'Related to {initiative_title}',
                                                        'importance': 'medium',
                                                        'answer': ''
                                                    }
                                                    formatted_questions.append(formatted_q)
                                                
                                                st.session_state[initiative_questions_key] = formatted_questions
                                                st.success(f"✅ Generated {len(formatted_questions)} questions for {initiative_title}")
                                        st.rerun()
                                else:
                                    # Display existing questions
                                    st.markdown(f"**📋 Discovery Questions ({len([q for q in initiative_questions if q.get('answer', '').strip()])}/{len(initiative_questions)} answered):**")
                                    
                                    for q_idx, question in enumerate(initiative_questions):
                                        question_id = question.get('id', f"init_{i}_q_{q_idx}")
                                        question_text = question.get('text', 'No question text')
                                        current_answer = question.get('answer', '')
                                        
                                        st.text(f"Q{q_idx+1}: {question_text}")
                                        
                                        answer_key = f"init_answer_{question_id}"
                                        answer = st.text_area(
                                            "Answer:",
                                            value=current_answer,
                                            placeholder="Enter your answer...",
                                            key=answer_key,
                                            height=80
                                        )
                                        
                                        # Update answer in session state
                                        if answer != current_answer:
                                            question['answer'] = answer
                                        
                                        st.markdown("---")
                                    
                                    # Generate 5 more questions for this initiative
                                    if st.button(f"➕ 5 More Questions", key=f"more_init_{i}"):
                                        with st.spinner(f"Generating more questions for {initiative_title}..."):
                                            from modules.llm_functions import generate_initiative_questions
                                            
                                            company_info = st.session_state.get('company_info', {})
                                            new_questions = generate_initiative_questions(
                                                company_info.get('website', ''),
                                                company_info.get('industry', ''),
                                                company_info.get('contact_title', ''),
                                                initiative_title,
                                                initiative_description
                                            )
                                            
                                            if new_questions:
                                                # Format new questions
                                                formatted_questions = []
                                                for q_obj in new_questions:
                                                    # Extract text from question object
                                                    if isinstance(q_obj, dict):
                                                        question_text = q_obj.get('text', str(q_obj))
                                                    else:
                                                        question_text = str(q_obj)
                                                    
                                                    # Clean any unwanted markdown/formatting
                                                    question_text = question_text.strip()
                                                    
                                                    formatted_q = {
                                                        'id': str(uuid.uuid4()),
                                                        'text': question_text,
                                                        'category': 'Initiative',
                                                        'explanation': f'Related to {initiative_title}',
                                                        'importance': 'medium',
                                                        'answer': ''
                                                    }
                                                    formatted_questions.append(formatted_q)
                                                
                                                # Add to existing questions for this initiative
                                                current_questions = st.session_state.get(initiative_questions_key, [])
                                                current_questions.extend(formatted_questions)
                                                st.session_state[initiative_questions_key] = current_questions
                                                
                                                st.success(f"✅ Added {len(formatted_questions)} more questions! Total: {len(current_questions)}")
                                                st.rerun()
                                            else:
                                                st.error("❌ Failed to generate more questions")
                
                # Add Your Own Initiative Section (Custom Initiatives)
                with st.expander("➕ **Add Your Own Initiative**", expanded=False):
                    st.markdown("Create custom initiatives and generate discovery questions for them")
                    
                    # Check if there are existing custom initiatives
                    custom_questions = st.session_state.get('custom_initiative_questions', [])
                    
                    if not custom_questions:
                        # Form to create new initiative
                        with st.form("custom_initiative_form"):
                            custom_title = st.text_input("🎯 Initiative Title", placeholder="e.g., Cloud Migration, Digital Transformation")
                            custom_description = st.text_area("📝 Description", placeholder="Describe the initiative and its goals...")
                            
                            if st.form_submit_button("🔍 Generate Questions"):
                                if custom_title.strip():
                                    with st.spinner(f"Generating questions for {custom_title}..."):
                                        from modules.llm_functions import generate_initiative_questions
                                        
                                        company_info = st.session_state.get('company_info', {})
                                        questions = generate_initiative_questions(
                                            company_info.get('website', ''),
                                            company_info.get('industry', ''),
                                            company_info.get('contact_title', ''),
                                            custom_title,
                                            custom_description
                                        )
                                        
                                        if questions:
                                            # Format questions
                                            formatted_questions = []
                                            for q_obj in questions:
                                                # Extract text from question object
                                                if isinstance(q_obj, dict):
                                                    question_text = q_obj.get('text', str(q_obj))
                                                else:
                                                    question_text = str(q_obj)
                                                
                                                # Clean any unwanted markdown/formatting
                                                question_text = question_text.strip()
                                                
                                                formatted_q = {
                                                    'id': str(uuid.uuid4()),
                                                    'text': question_text,
                                                    'category': 'Custom Initiative',
                                                    'explanation': f'Related to {custom_title}',
                                                    'importance': 'medium',
                                                    'answer': ''
                                                }
                                                formatted_questions.append(formatted_q)
                                            
                                            st.session_state['custom_initiative_questions'] = formatted_questions
                                            st.session_state['custom_initiative_title'] = custom_title
                                            st.session_state['custom_initiative_description'] = custom_description
                                            
                                            st.success(f"✅ Generated {len(formatted_questions)} questions for {custom_title}")
                                    st.rerun()
                                else:
                                    st.error("❌ Please enter an initiative title")
                    else:
                        # Display existing custom initiative questions
                        custom_title = st.session_state.get('custom_initiative_title', 'Custom Initiative')
                        custom_description = st.session_state.get('custom_initiative_description', '')
                        
                        st.markdown(f"**🎯 {custom_title}**")
                        if custom_description:
                            st.markdown(f"*{custom_description}*")
                        
                        st.markdown(f"**📋 Discovery Questions ({len([q for q in custom_questions if q.get('answer', '').strip()])}/{len(custom_questions)} answered):**")
                        
                        for q_idx, question in enumerate(custom_questions):
                            question_id = question.get('id', f"custom_q_{q_idx}")
                            question_text = question.get('text', 'No question text')
                            current_answer = question.get('answer', '')
                            
                            st.markdown(f"**Q{q_idx+1}:** {question_text}")
                            
                            answer_key = f"custom_answer_{question_id}"
                            answer = st.text_area(
                                "Answer:",
                                value=current_answer,
                                placeholder="Enter your answer...",
                                key=answer_key,
                                height=80
                            )
                            
                            # Update answer in session state
                            if answer != current_answer:
                                question['answer'] = answer
                            
                            st.markdown("---")
                        
                        # Button to generate more questions
                        col1, col2 = st.columns(2)
                        with col1:
                            if st.button("➕ 5 More Questions", key="more_custom"):
                                with st.spinner(f"Generating more questions for {custom_title}..."):
                                    from modules.llm_functions import generate_initiative_questions
                                    
                                    company_info = st.session_state.get('company_info', {})
                                    new_questions = generate_initiative_questions(
                                        company_info.get('website', ''),
                                        company_info.get('industry', ''),
                                        company_info.get('contact_title', ''),
                                        custom_title,
                                        custom_description
                                    )
                                    
                                    if new_questions:
                                        # Format new questions
                                        formatted_questions = []
                                        for q_obj in new_questions:
                                            # Extract text from question object
                                            if isinstance(q_obj, dict):
                                                question_text = q_obj.get('text', str(q_obj))
                                            else:
                                                question_text = str(q_obj)
                                            
                                            # Clean any unwanted markdown/formatting
                                            question_text = question_text.strip()
                                            
                                            formatted_q = {
                                                'id': str(uuid.uuid4()),
                                                'text': question_text,
                                                'category': 'Custom Initiative',
                                                'explanation': f'Related to {custom_title}',
                                                'importance': 'medium',
                                                'answer': ''
                                            }
                                            formatted_questions.append(formatted_q)
                                        
                                        # Add to existing questions
                                        current_questions = st.session_state.get('custom_initiative_questions', [])
                                        current_questions.extend(formatted_questions)
                                        st.session_state['custom_initiative_questions'] = current_questions
                                        
                                        st.success(f"✅ Added {len(formatted_questions)} more questions! Total: {len(current_questions)}")
                                        st.rerun()
                                    else:
                                        st.error("❌ Failed to generate more questions")
                        
                        with col2:
                            if st.button("🗑️ Clear Initiative", key="clear_custom"):
                                # Clear custom initiative
                                for key in ['custom_initiative_questions', 'custom_initiative_title', 'custom_initiative_description']:
                                    if key in st.session_state:
                                        del st.session_state[key]
                                st.success("✅ Custom initiative cleared")
                                st.rerun()

# Value & Strategy Tab
with tab2:
    st.markdown("### 📈 Value & Strategy")
    
    # Check if discovery is in progress
    if 'questions' in st.session_state and st.session_state.questions:
        # Calculate discovery progress
        questions = st.session_state.questions
        total_questions = len([q for q in questions if isinstance(q, dict)])
        answered_questions = len([q for q in questions if isinstance(q, dict) and q.get('answer', '').strip()])
        
        # Business Value section - unified approach
        st.markdown("### 💰 Business Value")
        
        # Check discovery progress for conditional rendering
        discovery_completed = answered_questions >= (total_questions * 0.3) if total_questions > 0 else False
        
        if not discovery_completed and not st.session_state.get('initial_value_hypothesis'):
            # Before discovery - show value hypothesis generator
            st.info("📋 **Generate Value Hypothesis** - Start with an initial value hypothesis before discovery")
            
            if st.button("🔮 Generate Value Hypothesis", use_container_width=True):
                with st.spinner("🔮 Generating initial value hypothesis..."):
                    from modules.llm_functions import generate_initial_value_hypothesis
                    
                    company_info = st.session_state.get('company_info', {})
                    summary_data = st.session_state.get('company_summary_data', {})
                    
                    new_hypothesis = generate_initial_value_hypothesis(
                                    company_info.get('website', ''),
                                    company_info.get('industry', ''),
                                    company_info.get('contact_title', ''),
                        summary_data
                    )
                    
                    if new_hypothesis:
                        st.session_state.initial_value_hypothesis = new_hypothesis
                        st.success("✅ Value hypothesis generated!")
                        st.rerun()
                    else:
                        st.error("❌ Failed to generate value hypothesis")
        
        # Show value hypothesis if it exists
        if st.session_state.get('initial_value_hypothesis'):
            with st.container(border=True):
                st.markdown("#### 🔮 Value Hypothesis")
                st.markdown(st.session_state['initial_value_hypothesis'])
        
        # Show business case generator if discovery is done
        if discovery_completed:
            st.markdown("---")
            st.info("✅ **Discovery Complete** - Ready to generate comprehensive business case")
            
            if st.button("💼 Generate Business Case", use_container_width=True):
                with st.spinner("💼 Generating comprehensive business case..."):
                    from modules.llm_functions import generate_business_case
                    
                    # Prepare discovery data
                    discovery_notes = prepare_discovery_notes()
                    company_info = st.session_state.get('company_info', {})
                    
                    business_case = generate_business_case(
                        company_info,
                        discovery_notes
                    )
                    
                    if business_case:
                        st.session_state.business_case = business_case
                        st.success("✅ Business case generated!")
                        st.rerun()
                    else:
                        st.error("❌ Failed to generate business case")
        
        # Show business case if it exists
        if st.session_state.get('business_case'):
            with st.container(border=True):
                st.markdown("#### 💼 Business Case")
                st.markdown(st.session_state['business_case'])
        
        # Roadmap Section
        st.markdown("---")
        st.markdown("### 🗺️ Strategic Roadmap")
        
        if not st.session_state.get('roadmap_df', pd.DataFrame()).empty:
            st.dataframe(st.session_state['roadmap_df'], use_container_width=True)
        else:
            st.info("📋 **Generate Strategic Roadmap** - Create a detailed implementation roadmap")
            
            if st.button("🗺️ Generate Roadmap", use_container_width=True):
                with st.spinner("🗺️ Generating strategic roadmap..."):
                    from modules.llm_functions import generate_roadmap
                    
                    # Prepare discovery data
                    discovery_notes = prepare_discovery_notes()
                    company_info = st.session_state.get('company_info', {})
                    
                    roadmap_data = generate_roadmap(
                        company_info,
                        discovery_notes,
                        "medium"
                    )
                    
                    if roadmap_data is not None:
                        if isinstance(roadmap_data, list) and len(roadmap_data) > 0:
                            roadmap_df = pd.DataFrame(roadmap_data)
                            st.session_state.roadmap_df = roadmap_df
                            st.success("✅ Roadmap generated!")
                            st.rerun()
                        elif isinstance(roadmap_data, pd.DataFrame) and not roadmap_data.empty:
                            st.session_state.roadmap_df = roadmap_data
                            st.success("✅ Roadmap generated!")
                            st.rerun()
                        else:
                            st.error("❌ Failed to generate roadmap")
                    else:
                        st.error("❌ Failed to generate roadmap")
        
        # Competitive Strategy Section
                        st.markdown("---")
        st.markdown("### ⚔️ Competitive Strategy")
        
        if st.session_state.get('competitive_strategy'):
            with st.container(border=True):
                st.markdown("#### ⚔️ Competitive Positioning")
                st.markdown(st.session_state['competitive_strategy'])
        else:
            st.info("📋 **Generate Competitive Strategy** - Develop competitive positioning and battle cards")
            
            if st.button("⚔️ Generate Competitive Strategy", use_container_width=True):
                with st.spinner("⚔️ Generating competitive strategy..."):
                    from modules.llm_functions import generate_competitive_argument
                    
                    # Prepare discovery data
                    discovery_notes = prepare_discovery_notes()
                    company_info = st.session_state.get('company_info', {})
                    
                    competitive_strategy = generate_competitive_argument(
                        company_info,
                        discovery_notes
                    )
                    
                    if competitive_strategy:
                        st.session_state.competitive_strategy = competitive_strategy
                        st.success("✅ Competitive strategy generated!")
                        st.rerun()
                    else:
                        st.error("❌ Failed to generate competitive strategy")
    
    else:
        st.info("📋 **Complete Discovery First** - Generate discovery questions and gather information to unlock strategic content")

# Outreach Tab
with tab3:
    st.markdown("### 📧 Outreach")
    
    # Check if discovery is in progress
    if 'questions' in st.session_state and st.session_state.questions:
        
        # Email Messages Section
        st.markdown("### 📧 Email Messages")
        
        if st.session_state.get('outreach_emails'):
            emails = st.session_state['outreach_emails']
            if isinstance(emails, list):
                for i, email in enumerate(emails):
                    if isinstance(email, dict):
                        with st.container(border=True):
                            st.info(f"📌 **Subject:** {email.get('subject', 'No Subject')}")
                            with st.container(border=True):
                                st.markdown("✉️ **Email Body:**")
                                st.markdown(email.get('body', 'No content'))
                            st.markdown("---")
            elif isinstance(emails, dict):
                for template_name, email_content in emails.items():
                    with st.container(border=True):
                        st.markdown(f"### 📧 {template_name}")
                        if isinstance(email_content, dict):
                            st.info(f"📌 **Subject:** {email_content.get('subject', 'No Subject')}")
                            with st.container(border=True):
                                st.markdown("✉️ **Email Body:**")
                                st.markdown(email_content.get('body', 'No content'))
                        else:
                            st.markdown(email_content)
                            st.markdown("---")
        else:
            st.info("🚀 **Generate All Outreach Materials** - Create personalized emails and LinkedIn messages")
            
            if st.button("🚀 Generate All Outreach", use_container_width=True):
                with st.spinner("🚀 Generating emails and LinkedIn messages..."):
                    from modules.llm_functions import generate_outreach_emails, generate_linkedin_messages
                    
                    # Prepare discovery data
                    discovery_notes = prepare_discovery_notes()
                    company_info = st.session_state.get('company_info', {})
                    roadmap_df = st.session_state.get('roadmap_df', None)
                    
                    success_count = 0
                    
                    # Generate Email Messages
                    try:
                        emails = generate_outreach_emails(
                            company_info,
                            discovery_notes,
                            roadmap_df
                        )
                        
                        if emails:
                            st.session_state.outreach_emails = emails
                            success_count += 1
                    except Exception as e:
                        st.error(f"❌ Failed to generate email messages: {e}")
                    
                    # Generate LinkedIn Messages
                    try:
                        messages = generate_linkedin_messages(
                            company_info,
                            discovery_notes,
                            roadmap_df
                        )
                        
                        if messages:
                            st.session_state.linkedin_messages = messages
                            success_count += 1
                    except Exception as e:
                        st.error(f"❌ Failed to generate LinkedIn messages: {e}")
                    
                    # Show results
                    if success_count == 2:
                        st.success("✅ All outreach materials generated! (2 emails + 2 LinkedIn messages)")
                        st.rerun()
                    elif success_count == 1:
                        st.warning("⚠️ Partially generated - some outreach materials created")
                        st.rerun()
                    else:
                        st.error("❌ Failed to generate outreach materials")
        
        # LinkedIn Messages Section
        st.markdown("---")
        st.markdown("### 💬 LinkedIn Messages")
        
        if st.session_state.get('linkedin_messages'):
            messages = st.session_state['linkedin_messages']
            if isinstance(messages, list):
                for i, message in enumerate(messages):
                    if isinstance(message, dict):
                        with st.container(border=True):
                            st.info(f"📌 **Subject:** {message.get('subject', 'No Subject')}")
                            with st.container(border=True):
                                st.markdown("💬 **Message:**")
                                st.markdown(message.get('body', 'No content'))
                            st.markdown("---")
            elif isinstance(messages, dict):
                for template_name, message_content in messages.items():
                    with st.container(border=True):
                        st.markdown(f"### 💬 {template_name}")
                        if isinstance(message_content, dict):
                            st.info(f"📌 **Subject:** {message_content.get('subject', 'No Subject')}")
                            with st.container(border=True):
                                st.markdown("💬 **Message:**")
                                st.markdown(message_content.get('body', 'No content'))
                        else:
                            st.markdown(message_content)
                        st.markdown("---")
        else:
            st.info("💬 LinkedIn messages will appear here after generation")
    
    else:
        st.info("📋 **Complete Discovery First** - Generate discovery questions and gather information to unlock outreach templates")

# People Research Tab
with tab4:
    st.markdown("### 👥 People Research")
    
    # Check if discovery is in progress
    if 'questions' in st.session_state and st.session_state.questions:
        
        # Display existing people research
        people_research = st.session_state.get('people_research', [])
        
        if people_research:
            st.markdown("### 👥 Contacts & AI Insights")
            
            for i, person in enumerate(people_research):
                if isinstance(person, dict):
                    with st.container(border=True):
                        col1, col2 = st.columns([4, 1])
                        
                        with col1:
                            st.markdown(f"**👤 {person.get('name', 'Unknown')}**")
                            st.caption(f"💼 {person.get('title', 'No title')}")
                            
                            if person.get('background'):
                                st.markdown(f"📝 **Background:** {person['background']}")
                            
                            # Display AI insights if available
                            if person.get('ai_insights'):
                                insights = person['ai_insights']
                                
                                with st.expander("🧠 AI Insights", expanded=True):
                                    if insights.get('likely_priorities'):
                                        st.markdown("**🎯 Likely Priorities:**")
                                        for priority in insights['likely_priorities']:
                                            st.markdown(f"• {priority}")
                                    
                                    if insights.get('engagement_strategies'):
                                        st.markdown("**🤝 Engagement Strategies:**")
                                        for strategy in insights['engagement_strategies']:
                                            st.markdown(f"• {strategy}")
                                    
                                    if insights.get('key_talking_points'):
                                        st.markdown("**💬 Key Talking Points:**")
                                        for point in insights['key_talking_points']:
                                            st.markdown(f"• {point}")
                            else:
                                st.info("🧠 AI insights will be generated automatically when you add contacts")
                        
                        with col2:
                            if st.button("🗑️", key=f"delete_person_{i}", help="Remove this contact"):
                                # Remove person from list
                                updated_people = [p for j, p in enumerate(people_research) if j != i]
                                st.session_state.people_research = updated_people
                                st.rerun()
            
            st.markdown("---")
        
        # Add new contact research
        st.markdown("### ➕ Add Contact")
        
        # Simplified contact form
        with st.form("add_contact_form"):
            st.markdown("**Add Contact Information**")
            
            col1, col2 = st.columns(2)
            with col1:
                contact_name = st.text_input("👤 Name", placeholder="John Smith")
            with col2:
                contact_title = st.text_input("💼 Title", placeholder="VP of Engineering")
            
            background_notes = st.text_area("📝 Background Notes", placeholder="Key information, interests, responsibilities, background...")
            
            if st.form_submit_button("➕ Add Contact & Generate AI Insights"):
                if contact_name.strip():
                    with st.spinner(f"Adding {contact_name} and generating AI insights..."):
                        try:
                            # Prepare discovery data
                            discovery_notes = prepare_discovery_notes()
                            company_info = st.session_state.get('company_info', {})
                            
                            # Generate AI insights
                            insights = generate_people_insights(
                                company_info,
                                contact_name.strip(),
                                contact_title.strip(),
                                background_notes.strip(),
                                discovery_notes
                            )
                            
                            # Create new contact with insights
                            new_contact = {
                                'name': contact_name.strip(),
                                'title': contact_title.strip(),
                                'background': background_notes.strip(),
                                'ai_insights': insights if insights else None
                            }
                            
                            # Add to people research
                            current_people = st.session_state.get('people_research', [])
                            current_people.append(new_contact)
                            st.session_state.people_research = current_people
                            
                            if insights:
                                st.success(f"✅ Added {contact_name} with AI insights!")
                            else:
                                st.warning(f"⚠️ Added {contact_name} but could not generate AI insights")
                            st.rerun()
                            
                        except Exception as e:
                            # Still add the contact even if insights fail
                            new_contact = {
                                'name': contact_name.strip(),
                                'title': contact_title.strip(),
                                'background': background_notes.strip()
                            }
                            
                            current_people = st.session_state.get('people_research', [])
                            current_people.append(new_contact)
                            st.session_state.people_research = current_people
                            
                            st.error(f"❌ Added {contact_name} but failed to generate insights: {e}")
                            st.rerun()
                else:
                    st.error("❌ Please enter a contact name")
        
    else:
        st.info("📋 **Complete Discovery First** - Generate discovery questions and gather information to unlock people research features")
