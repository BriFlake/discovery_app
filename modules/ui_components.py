# UI Components Module
# Reusable UI elements and common interface components

import streamlit as st
import pandas as pd
from datetime import datetime
import time

def render_session_header():
    """Render session information header"""
    if st.session_state.get('company_info', {}).get('website'):
        company_info = st.session_state.company_info
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Company", company_info.get('website', 'N/A'))
        
        with col2:
            st.metric("Industry", company_info.get('industry', 'N/A'))
        
        with col3:
            st.metric("Competitor", company_info.get('competitor', 'N/A'))
        
        with col4:
            st.metric("Persona", company_info.get('persona', 'N/A'))

def render_progress_indicator():
    """Render progress indicator for discovery process"""
    if not st.session_state.get('company_info', {}).get('website'):
        return
    
    # Calculate progress metrics
    questions = st.session_state.get('questions', {})
    total_questions = sum(len(q_list) for q_list in questions.values())
    answered_questions = sum(
        len([q for q in q_list if q.get('answer', '').strip()]) 
        for q_list in questions.values()
    )
    
    if total_questions > 0:
        progress = answered_questions / total_questions
        st.progress(progress)
        st.caption(f"Discovery Progress: {answered_questions}/{total_questions} questions answered ({progress:.1%})")

def render_question_card(question, category, question_index):
    """Render a single question card with answer input"""
    question_id = question.get('id', f"{category}_{question_index}")
    
    with st.container():
        # Question header
        col1, col2 = st.columns([0.9, 0.1])
        
        with col1:
            st.markdown(f"**Q{question_index + 1}:** {question['text']}")
        
        with col2:
            # Favorite toggle
            is_favorite = st.checkbox("⭐", 
                                    value=question.get('favorite', False),
                                    key=f"fav_{question_id}",
                                    help="Mark as favorite")
            question['favorite'] = is_favorite
        
        # Answer input
        answer = st.text_area(
            "Answer:",
            value=question.get('answer', ''),
            height=100,
            key=f"answer_{question_id}",
            placeholder="Enter your answer here..."
        )
        question['answer'] = answer
        
        # Add visual separator
        st.markdown("---")

def render_expert_card(expert_id, expert_data, show_details=False, in_expander=False):
    """Render an expert card with skills and experience"""
    with st.container():
        # Header with name and relevance score
        col1, col2 = st.columns([0.8, 0.2])
        
        with col1:
            st.markdown(f"### {expert_data['name']}")
            st.markdown(f"📧 {expert_data['email']}")
        
        with col2:
            relevance = expert_data.get('relevance_score', 0)
            color = "green" if relevance >= 70 else "orange" if relevance >= 50 else "red"
            st.markdown(f"<div style='text-align: center; color: {color}; font-size: 18px; font-weight: bold;'>{relevance}% Match</div>", 
                       unsafe_allow_html=True)
        
        # Skills summary
        skills = expert_data.get('skills', {})
        if skills.get('high_proficiency') or skills.get('specialties'):
            st.markdown("**Key Skills:**")
            skill_tags = []
            
            for skill in skills.get('high_proficiency', [])[:3]:
                skill_tags.append(f"🎯 {skill}")
            
            for specialty in skills.get('specialties', [])[:2]:
                skill_tags.append(f"⭐ {specialty}")
            
            if skill_tags:
                st.markdown(" • ".join(skill_tags))
        
        # Experience summary
        opportunities = expert_data.get('opportunities', [])
        if opportunities:
            opp_count = len(opportunities)
            industries = expert_data.get('industries', set())
            st.markdown(f"**Experience:** {opp_count} opportunities" + 
                       (f" across {len(industries)} industries" if industries else ""))
        
        # Detailed view
        if show_details:
            # Only create expander if we're not already in one
            if not in_expander:
                with st.expander("View Details"):
                    _render_expert_details(skills, opportunities)
            else:
                # If already in expander, render details directly
                st.markdown("---")
                st.markdown("**📋 Detailed Information:**")
                _render_expert_details(skills, opportunities)
        
        st.markdown("---")


def _render_expert_details(skills, opportunities):
    """Helper function to render expert details (skills and opportunities)"""
    # All skills
    if skills:
        st.markdown("**All Skills:**")
        for level, skill_list in skills.items():
            if skill_list:
                level_name = level.replace('_', ' ').title()
                st.markdown(f"- **{level_name}:** {', '.join(skill_list)}")
    
    # Recent opportunities
    if opportunities:
        st.markdown("**Recent Opportunities:**")
        for opp in opportunities[:5]:
            stage_color = "green" if "closed won" in opp.get('stage', '').lower() else "blue"
            amount_str = f"${opp.get('amount', 0):,.0f}" if opp.get('amount') else "N/A"
            st.markdown(f"- **{opp.get('name', 'N/A')}** ({opp.get('industry', 'N/A')}) - "
                      f"<span style='color: {stage_color}'>{opp.get('stage', 'N/A')}</span> - {amount_str}",
                      unsafe_allow_html=True)


def render_roadmap_table(roadmap_df):
    """Render roadmap as an interactive table"""
    # Handle both DataFrame and list formats (loaded sessions come as lists)
    if roadmap_df is None:
        st.info("No roadmap data available.")
        return
    elif isinstance(roadmap_df, list):
        if len(roadmap_df) == 0:
            st.info("No roadmap data available.")
            return
        # Convert list to DataFrame for display
        roadmap_df = pd.DataFrame(roadmap_df)
    elif isinstance(roadmap_df, pd.DataFrame):
        if roadmap_df.empty:
            st.info("No roadmap data available.")
            return
    else:
        st.info("No roadmap data available.")
        return
    
    # Configure column display
    column_config = {
        "project_name": st.column_config.TextColumn("Project Name", width="medium"),
        "description": st.column_config.TextColumn("Description", width="large"),
        "business_value": st.column_config.SelectboxColumn("Business Value", 
                                                           options=["Low", "Medium", "High", "Very High"],
                                                           width="small"),
        "level_of_effort": st.column_config.SelectboxColumn("Level of Effort",
                                                            options=["Low", "Medium", "High"],
                                                            width="small")
    }
    
    # Display editable dataframe
    edited_df = st.data_editor(
        roadmap_df,
        column_config=column_config,
        hide_index=True,
        use_container_width=True,
        num_rows="dynamic"
    )
    
    # Update session state if edited
    if not edited_df.equals(roadmap_df):
        st.session_state.roadmap_df = edited_df

def render_people_research_cards():
    """Render people research as cards"""
    people_research = st.session_state.get('people_research', [])
    
    if not people_research:
        st.info("No people research available.")
        return
    
    for i, person in enumerate(people_research):
        with st.container():
            col1, col2 = st.columns([0.7, 0.3])
            
            with col1:
                st.markdown(f"### {person['name']}")
                st.markdown(f"**{person['title']}**")
                
                if person.get('summary'):
                    st.markdown(f"**Summary:** {person['summary']}")
            
            with col2:
                if st.button("Remove", key=f"remove_person_{i}"):
                    st.session_state.people_research.pop(i)
            
            # Insights
            if person.get('insights'):
                st.markdown("**Key Insights:**")
                for insight in person['insights']:
                    st.markdown(f"• {insight}")
            
            # Conversation topics
            if person.get('topics'):
                with st.expander("Conversation Topics"):
                    topics = person['topics']
                    
                    if topics.get('business'):
                        st.markdown("**Business Topics:**")
                        for topic in topics['business']:
                            st.markdown(f"• {topic}")
                    
                    if topics.get('technical'):
                        st.markdown("**Technical Topics:**")
                        for topic in topics['technical']:
                            st.markdown(f"• {topic}")
                    
                    if topics.get('personal'):
                        st.markdown("**Personal Topics:**")
                        for topic in topics['personal']:
                            st.markdown(f"• {topic}")
            
            st.markdown("---")

def render_email_preview(email_data, email_key):
    """Render email preview with edit capability"""
    with st.container():
        st.markdown(f"### {email_key.replace('_', ' ').title()}")
        
        # Subject line
        subject = st.text_input(
            "Subject:",
            value=email_data.get('subject', ''),
            key=f"subject_{email_key}"
        )
        
        # Body
        body = st.text_area(
            "Body:",
            value=email_data.get('body', ''),
            height=200,
            key=f"body_{email_key}"
        )
        
        # Update session state
        if email_key in st.session_state.get('outreach_emails', {}):
            st.session_state.outreach_emails[email_key]['subject'] = subject
            st.session_state.outreach_emails[email_key]['body'] = body
        
        # Action buttons
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Copy to Clipboard", key=f"copy_{email_key}"):
                full_email = f"Subject: {subject}\n\n{body}"
                st.write("Email copied! (Use Ctrl+C to copy the text below)")
                st.code(full_email)
        
        with col2:
            if st.button("Regenerate", key=f"regen_{email_key}"):
                # This would trigger regeneration in the calling code
                st.session_state[f"regenerate_{email_key}"] = True
        
        st.markdown("---")

def render_metric_cards(metrics_data):
    """Render metrics as cards"""
    if not metrics_data:
        return
    
    # Determine number of columns based on number of metrics
    num_metrics = len(metrics_data)
    cols = st.columns(min(num_metrics, 4))
    
    for i, (label, value) in enumerate(metrics_data.items()):
        with cols[i % len(cols)]:
            # Format value appropriately
            if isinstance(value, float):
                if label.lower().find('rate') != -1 or label.lower().find('percent') != -1:
                    display_value = f"{value:.1f}%"
                else:
                    display_value = f"{value:.1f}"
            elif isinstance(value, int):
                display_value = f"{value:,}"
            else:
                display_value = str(value)
            
            st.metric(label.replace('_', ' ').title(), display_value)

def render_data_table(df, title=None, show_download=True):
    """Render a data table with optional download"""
    if df.empty:
        st.info(f"No {title.lower() if title else 'data'} available.")
        return
    
    if title:
        st.markdown(f"### {title}")
    
    # Display table
    st.dataframe(df, use_container_width=True)
    
    # Download button
    if show_download:
        csv = df.to_csv(index=False)
        filename = f"{title.lower().replace(' ', '_')}.csv" if title else "data.csv"
        st.download_button(
            label="Download CSV",
            data=csv,
            file_name=filename,
            mime="text/csv"
        )

def render_status_indicators():
    """Render status indicators for different modules"""
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # Sales Activities status
        has_company = bool(st.session_state.get('company_info', {}).get('website'))
        questions = st.session_state.get('questions', {})
        answered_count = sum(
            len([q for q in q_list if q.get('answer', '').strip()]) 
            for q_list in questions.values()
        )
        
        status = "✅ Active" if has_company and answered_count > 0 else "🔄 Setup" if has_company else "⏳ Pending"
        st.markdown(f"**Sales Activities:** {status}")
        if has_company:
            st.caption(f"{answered_count} questions answered")
    
    with col2:
        # Expert Hub status
        expert_context = st.session_state.get('expert_context', {})
        expert_count = len(expert_context.get('experts', []))
        
        status = "✅ Active" if expert_count > 0 else "⏳ Pending"
        st.markdown(f"**Expert Hub:** {status}")
        if expert_count > 0:
            st.caption(f"{expert_count} experts found")
    
    with col3:
        # Demo Builder status
        has_roadmap = not st.session_state.get('roadmap_df', pd.DataFrame()).empty
        has_strategy = bool(st.session_state.get('value_strategy_content', '').strip())
        
        status = "✅ Ready" if has_roadmap and has_strategy else "🔄 Partial" if has_roadmap or has_strategy else "⏳ Pending"
        st.markdown(f"**Demo Builder:** {status}")
        if has_roadmap:
            st.caption("Demo data ready")

def render_navigation_sidebar():
    """Render sidebar navigation with current status"""
    with st.sidebar:
        # Quick actions
        st.markdown("### Quick Actions")
        
        # Save Session
        if st.session_state.get('company_info', {}).get('website'):
            if st.button("💾 Save Session", use_container_width=True, key="sidebar_save_session"):
                try:
                    # Try new normalized system first
                    from modules.session_management_v2 import save_current_session
                    success = save_current_session()
                except ImportError:
                    # Fallback to old system
                    try:
                        from modules.session_management import save_current_session
                        success = save_current_session()
                    except Exception as e:
                        st.error(f"❌ Could not save session: {e}")
                except Exception as e:
                    st.error(f"❌ Error saving session: {e}")
        else:
            st.button("💾 Save Session", disabled=True, use_container_width=True, help="Complete company setup first", key="sidebar_save_session_disabled")
        
        # Start New Session
        if st.button("🆕 Start New Session", use_container_width=True, key="sidebar_start_new_session"):
            try:
                # Try new normalized system first
                from modules.session_management_v2 import start_new_session
                start_new_session()
            except ImportError:
                # Fallback to old system
                try:
                    from modules.session_management import start_new_session
                    start_new_session()
                except ImportError:
                    # Manual fallback implementation
                    try:
                        from modules.session_management_v2 import clear_session_data
                        clear_session_data()
                        st.success("🆕 Started fresh session!")
                    except ImportError:
                        # Ultimate fallback
                        session_keys_to_clear = [
                            'questions', 'company_info', 'selected_sf_account', 'current_session_id',
                            'company_summary_data', 'roadmap', 'roadmap_df', 'competitive_strategy',
                            'business_case', 'initial_value_hypothesis', 'outreach_emails',
                            'linkedin_messages', 'people_research', 'notes_content',
                            'recommended_initiatives', 'competitor', 'contact_name', 'contact_title'
                        ]
                        for key in session_keys_to_clear:
                            if key in st.session_state:
                                del st.session_state[key]
                        st.success("🆕 Started fresh session!")
            except Exception as e:
                st.error(f"❌ Error starting new session: {e}")
        
        # AI Model at bottom
        st.markdown("---")
        st.markdown("### AI Model")
        model_options = ['claude-3-5-sonnet', 'reka-flash', 'mistral-large', 'llama3-70b']
        
        current_model = st.session_state.get('selected_model', 'claude-3-5-sonnet')
        selected_model = st.selectbox(
            "Model:",
            model_options,
            index=model_options.index(current_model) if current_model in model_options else 0,
            label_visibility="collapsed"
        )
        st.session_state.selected_model = selected_model

def render_alert_banner(message, alert_type="info"):
    """Render an alert banner"""
    colors = {
        "info": "#e7f3ff",
        "success": "#d4edda", 
        "warning": "#fff3cd",
        "error": "#f8d7da"
    }
    
    icons = {
        "info": "ℹ️",
        "success": "✅",
        "warning": "⚠️", 
        "error": "❌"
    }
    
    color = colors.get(alert_type, colors["info"])
    icon = icons.get(alert_type, icons["info"])
    
    st.markdown(
        f"""
        <div style="background-color: {color}; padding: 10px; border-radius: 5px; margin: 10px 0;">
            {icon} {message}
        </div>
        """,
        unsafe_allow_html=True
    ) 