# Session Management Page
# Dedicated to viewing, loading, and managing saved discovery sessions

import streamlit as st
import pandas as pd
from modules.ui_components import render_navigation_sidebar
from modules.session_management import get_saved_sessions, load_session_data, delete_session, get_session_analytics

st.set_page_config(
    page_title="Session Management",
    page_icon="💾",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Render sidebar
render_navigation_sidebar()

st.title("💾 Session Management")
st.markdown("**View, load, and manage your saved discovery sessions**")

# Create tabs
tab1, tab2 = st.tabs(["📂 Your Sessions", "📊 Analytics"])

with tab1:
    st.header("📂 Your Saved Sessions")
    st.caption("Load previous sessions or delete old ones")
    
    # Load saved sessions
    try:
        sessions_df = get_saved_sessions()
        
        if sessions_df.empty:
            st.info("📝 No saved sessions found. Complete and save a discovery session to see it here.")
            if st.button("🏢 Start New Discovery Session", type="primary"):
                st.switch_page("pages/01_🏢_Sales_Activities.py")
        else:
            st.subheader(f"📋 Found {len(sessions_df)} Sessions")
            
            # Display sessions in a nice format
            for idx, session in sessions_df.iterrows():
                with st.container(border=True):
                    col1, col2, col3, col4 = st.columns([3, 2, 1, 1])
    
                    with col1:
                        st.write(f"**{session['SESSION_NAME']}**")
                        if session.get('COMPANY_NAME'):
                            st.caption(f"🏢 {session['COMPANY_NAME']}")
                        if session.get('COMPETITOR'):
                            st.caption(f"🏆 vs. {session['COMPETITOR']}")
                    
                    with col2:
                        st.write(f"📊 {session.get('COMPLETION_PERCENTAGE', 0):.1f}% Complete")
                        answered_count = session.get('ANSWERS_COUNT', 0)
                        total_count = session.get('TOTAL_QUESTIONS', 0)
                        st.caption(f"📝 {answered_count}/{total_count} questions answered")
                    
                    with col3:
                        if st.button("📂 Load", key=f"load_{session['SESSION_ID']}", use_container_width=True):
                            if load_session_data(session['SESSION_ID']):
                                # Navigate directly to Sales Activities after loading
                                st.switch_page("pages/01_🏢_Sales_Activities.py")
                    
                    with col4:
                        if st.button("🗑️ Delete", key=f"delete_{session['SESSION_ID']}", use_container_width=True):
                            if st.session_state.get(f"confirm_delete_{session['SESSION_ID']}", False):
                                if delete_session(session['SESSION_ID']):
                                    st.rerun()
                            else:
                                st.session_state[f"confirm_delete_{session['SESSION_ID']}"] = True
                                st.rerun()
                    
                    # Show session details
                    if session.get('CREATED_AT'):
                        created_date = pd.to_datetime(session['CREATED_AT']).strftime('%m/%d/%Y %I:%M %p')
                        st.caption(f"📅 Created: {created_date}")
                    
                    if session.get('UPDATED_AT'):
                        updated_date = pd.to_datetime(session['UPDATED_AT']).strftime('%m/%d/%Y %I:%M %p')
                        st.caption(f"🔄 Updated: {updated_date}")
    
    except Exception as e:
        st.error(f"Error loading sessions: {e}")

with tab2:
    st.header("📊 Discovery Analytics")
    st.caption("Your discovery session statistics and insights")
    
    try:
        analytics = get_session_analytics()
        
        if not analytics:
            st.info("📊 Complete some discovery sessions to see your analytics.")
        else:
            # Display analytics metrics
            col1, col2, col3, col4 = st.columns(4)
    
            with col1:
                st.metric(
                    "Total Sessions", 
                    analytics.get('total_sessions', 0)
                )
            
            with col2:
                st.metric(
                    "Companies Discovered", 
                    analytics.get('unique_companies', 0)
                )
            
            with col3:
                st.metric(
                    "Questions Answered", 
                    analytics.get('total_questions_answered', 0)
                )
            
            with col4:
                avg_completion = analytics.get('avg_completion', 0)
                st.metric(
                    "Avg. Completion", 
                    f"{avg_completion:.1f}%"
                )
            
            # Additional insights
            st.divider()
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("🎯 Session Quality")
                completed_sessions = analytics.get('completed_sessions', 0)
                total_sessions = analytics.get('total_sessions', 1)
                completion_rate = (completed_sessions / total_sessions * 100) if total_sessions > 0 else 0
                
                st.metric("Fully Completed Sessions", f"{completed_sessions}/{total_sessions}")
                st.metric("Completion Rate", f"{completion_rate:.1f}%")
            
            with col2:
                st.subheader("📈 Progress Summary")
                st.write(f"• **{analytics.get('total_sessions', 0)}** discovery sessions initiated")
                st.write(f"• **{analytics.get('unique_companies', 0)}** unique companies researched")
                st.write(f"• **{analytics.get('total_questions_answered', 0)}** total questions answered")
                if avg_completion > 0:
                    st.write(f"• **{avg_completion:.1f}%** average session completion")
    
    except Exception as e:
        st.error(f"Error loading analytics: {e}")

# Footer
st.markdown("---")
st.markdown("**💡 Tip:** Load a session to continue where you left off, or start a new discovery session from Sales Activities!") 