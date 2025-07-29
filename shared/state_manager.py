# Shared State Manager for Multi-Page Streamlit App
# Handles cross-page state management and initialization

import streamlit as st
import pandas as pd
import uuid
import json
from datetime import datetime

# Try to import Snowpark - only available in Streamlit in Snowflake
try:
    from snowflake.snowpark.context import get_active_session
    SNOWPARK_AVAILABLE = True
except ImportError:
    SNOWPARK_AVAILABLE = False

class StateManager:
    """Manages state across pages in the multi-page Streamlit app"""
    
    def __init__(self):
        self.init_session_state()
        self.handle_session_id_transition()
    
    def init_session_state(self):
        """Initialize session state variables only when needed"""
        session_defaults = {
            # Core company and discovery data
            'questions': {},
            'company_info': {},
            'company_summary': "",
            'notes_content': "",
            
            # Value and strategy data
            'value_strategy_content': "",
            'competitive_analysis_content': "",
            'initial_value_hypothesis': "",
            'roadmap_df': pd.DataFrame(),
            'recommended_initiatives': [],
            
            # Session management
            'session_loaded': False,
            'selected_session_id': "new",
            'selected_model': 'claude-3-5-sonnet',
            'research_stage': 0,
            
            # Communication data
            'outreach_emails': {},
            'linkedin_messages': {},
            'messages': [],
            
            # People research
            'people_research': [],
            
            # Expert data
            'expert_context': {},
            'expert_search_value': "",
            
            # UI state
            'token_error_flag': False,
            'show_briefing': False,
            'data_source': "Manual Entry"
        }
        
        for key, default_value in session_defaults.items():
            if key not in st.session_state:
                st.session_state[key] = default_value
    
    def handle_session_id_transition(self):
        """Handle setting the newly created session ID to prevent widget modification errors"""
        if 'just_created_session_id' in st.session_state:
            st.session_state.selected_session_id = st.session_state.just_created_session_id
            del st.session_state.just_created_session_id
    
    def get_company_context(self):
        """Get company information for cross-module context"""
        return st.session_state.get('company_info', {})
    
    def get_discovery_data(self):
        """Get discovery data for demo generation and expert context"""
        return {
            'questions': st.session_state.get('questions', {}),
            'roadmap': st.session_state.get('roadmap_df', pd.DataFrame()),
            'strategy': st.session_state.get('value_strategy_content', ''),
            'hypothesis': st.session_state.get('initial_value_hypothesis', ''),
            'people_research': st.session_state.get('people_research', []),
            'notes': st.session_state.get('notes_content', '')
        }
    
    def update_expert_context(self, expert_data):
        """Update context from expert findings"""
        st.session_state['expert_context'] = expert_data
    
    def get_expert_context(self):
        """Get expert context for demo generation"""
        return st.session_state.get('expert_context', {})
    
    def clear_session(self, preserve_loaded_session_id=False):
        """Clear session state while preserving key identifiers"""
        loaded_session_id = st.session_state.get('selected_session_id') if preserve_loaded_session_id else "new"
        current_user = st.session_state.get('current_user')
        selected_model = st.session_state.get('selected_model', 'claude-3-5-sonnet')
        
        # Clear all keys
        keys_to_clear = list(st.session_state.keys())
        for key in keys_to_clear:
            del st.session_state[key]
        
        # Restore preserved values
        st.session_state.selected_session_id = loaded_session_id
        st.session_state.selected_model = selected_model
        if current_user:
            st.session_state.current_user = current_user
        
        # Reinitialize with defaults
        self.init_session_state()
    
    def get_current_user(self):
        """Get current Snowflake user - lazy loaded to prevent startup queries"""
        if 'current_user' not in st.session_state:
            try:
                # Only fetch user if actually needed and after app is fully loaded
                if hasattr(st, 'session_state') and len(st.session_state) > 0:
                    # Import here to avoid circular imports
                    from modules.snowflake_utils import execute_query
                    user_df = execute_query("SELECT CURRENT_USER() as USER")
                    if not user_df.empty:
                        st.session_state.current_user = user_df.iloc[0]['USER']
                    else:
                        st.session_state.current_user = "Snowflake User"
                else:
                    # During startup, use fallback without database query
                    st.session_state.current_user = "Snowflake User"
            except Exception as e:
                # Fallback to a generic user name without showing error during startup
                st.session_state.current_user = "Snowflake User"
        return st.session_state.current_user
    
    def has_company_data(self):
        """Check if company data exists for flow control"""
        return bool(st.session_state.get('company_info', {}).get('website'))
    
    def has_discovery_data(self):
        """Check if discovery questions exist"""
        return bool(st.session_state.get('questions', {}))
    
    def has_roadmap_data(self):
        """Check if roadmap data exists"""
        return not st.session_state.get('roadmap_df', pd.DataFrame()).empty
    
    def get_session_summary(self):
        """Get a summary of the current session for display"""
        company_name = st.session_state.get('company_info', {}).get('website', 'None')
        question_count = sum(len(q_list) for q_list in st.session_state.get('questions', {}).values())
        roadmap_count = len(st.session_state.get('roadmap_df', pd.DataFrame()))
        expert_count = len(st.session_state.get('expert_context', {}).get('experts', []))
        
        return {
            'company': company_name,
            'questions': question_count,
            'roadmap_items': roadmap_count,
            'experts': expert_count
        } 