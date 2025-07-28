# Snowflake Sales Discovery Assistant - Multi-Page Architecture
# Main entry point and welcome page

import streamlit as st
import pandas as pd
from shared.state_manager import StateManager

# Initialize the state manager
state_manager = StateManager()

# Page configuration
st.set_page_config(
    page_title="Snowflake Sales Discovery Assistant",
    page_icon="❄️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Mark app as fully loaded - now safe to execute queries
from modules.snowflake_utils import mark_app_loaded
mark_app_loaded()

# Custom CSS for better UI
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .feature-card {
        background-color: #f8f9fa;
        padding: 1.5rem;
        border-radius: 10px;
        border-left: 4px solid #1f77b4;
        margin: 1rem 0;
        height: 150px;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
    }
    .session-container {
        background-color: #f8f9fa;
        padding: 1.5rem;
        border-radius: 10px;
        border: 2px solid #e9ecef;
        margin: 1rem 0;
    }
    .metric-card {
        background-color: white;
        padding: 1rem;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        text-align: center;
    }
</style>
""", unsafe_allow_html=True)

# Main header
st.markdown('<h1 class="main-header">❄️ Snowflake Sales Discovery Assistant</h1>', unsafe_allow_html=True)
st.markdown("**A comprehensive platform for sales discovery, expert finding, and demo automation**")

# Introduction section
st.markdown("---")
st.markdown("## Welcome to Your Sales Discovery Platform")

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("""
    <div class="feature-card">
        <h3>🏢 Sales Activities</h3>
        <p>Complete sales workflow including company research, value hypothesis, outreach, and session management.</p>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown("""
    <div class="feature-card">
        <h3>🔍 Expert Hub</h3>
        <p>Find the right experts for your deals with freestyle skills search, SE directory, and competitive experience.</p>
    </div>
    """, unsafe_allow_html=True)

with col3:
    st.markdown("""
    <div class="feature-card">
        <h3>🚀 Demo Builder</h3>
        <p>Generate comprehensive demo environments with data architecture design and demo scripts.</p>
    </div>
    """, unsafe_allow_html=True)

# Aligned buttons below the feature cards
col1, col2, col3 = st.columns(3)

with col1:
    if st.button("🏢 Start Sales Activities", use_container_width=True, type="primary"):
        st.switch_page("pages/01_🏢_Sales_Activities.py")

with col2:
    if st.button("🔍 Find Experts", use_container_width=True, type="primary"):
        st.switch_page("pages/02_🔍_Expert_Hub.py")

with col3:
    if st.button("🚀 Build Demo", use_container_width=True, type="primary"):
        st.switch_page("pages/03_🚀_Demo_Builder.py")

# Sidebar information
with st.sidebar:
    # AI Model
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

# Footer
st.markdown("---")
st.markdown("**Powered by Streamlit in Snowflake | Built for Snowflake Sales Teams**") 