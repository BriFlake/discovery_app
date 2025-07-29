# Export Page
# Dedicated to exporting all session data in various formats

import streamlit as st
import pandas as pd
import json
from datetime import datetime
from modules.ui_components import render_navigation_sidebar

st.set_page_config(
    page_title="Export Session Data",
    page_icon="📤",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Render sidebar
render_navigation_sidebar()

def generate_session_summary():
    """Generate a comprehensive markdown summary of the current session"""
    company_info = st.session_state.get('company_info', {})
    questions = st.session_state.get('questions', [])
    
    if isinstance(company_info, dict):
        company_name = company_info.get('name') or company_info.get('website', 'Unknown Company')
    else:
        company_name = "Unknown Company"
    
    summary = f"""# Discovery Session Export - {company_name}

**Export Date:** {datetime.now().strftime('%B %d, %Y at %I:%M %p')}
**Session Completion:** {len([q for q in questions if isinstance(q, dict) and q.get('answer', '').strip()])}/{len(questions)} questions answered

---

## 🏢 Company Information
"""
    
    if isinstance(company_info, dict):
        if company_info.get('name'):
            summary += f"**Company Name:** {company_info['name']}\n\n"
        if company_info.get('website'):
            summary += f"**Website:** {company_info['website']}\n\n"
        if company_info.get('industry'):
            summary += f"**Industry:** {company_info['industry']}\n\n"
        if company_info.get('description'):
            summary += f"**Description:** {company_info['description']}\n\n"
    
    # Contact Information
    contact_name = st.session_state.get('contact_name', '')
    contact_title = st.session_state.get('contact_title', '')
    if contact_name or contact_title:
        summary += f"**Primary Contact:** {contact_name} - {contact_title}\n\n"
    
    # Competitive Context
    competitor = st.session_state.get('competitor', '')
    if competitor:
        summary += f"**Primary Competitor:** {competitor}\n\n"
    
    # Company Overview
    company_summary_data = st.session_state.get('company_summary_data', {})
    if company_summary_data and company_summary_data.get('company_overview'):
        summary += f"---\n\n## 📋 Company Overview\n\n{company_summary_data['company_overview']}\n\n"
    
    # Discovery Questions & Answers
    summary += "---\n\n## ❓ Discovery Questions & Answers\n\n"
    
    if isinstance(questions, list):
        for i, question in enumerate(questions, 1):
            if isinstance(question, dict):
                q_text = question.get('text', f"Question {i}")
                answer = question.get('answer', '').strip()
                importance = question.get('importance', 'medium')
                importance_emoji = "🔥" if importance == "high" else "⚡" if importance == "medium" else "💡"
                
                summary += f"### {importance_emoji} Q{i}: {q_text}\n\n"
                if answer:
                    summary += f"**Answer:** {answer}\n\n"
                else:
                    summary += f"**Answer:** *Not answered*\n\n"
                
                if question.get('explanation'):
                    summary += f"*Why this matters: {question['explanation']}*\n\n"
    elif isinstance(questions, dict):
        for category, question_list in questions.items():
            summary += f"### 📋 {category}\n\n"
            for i, question in enumerate(question_list, 1):
                q_text = question.get('text', f"Question {i}")
                answer = question.get('answer', '').strip()
                importance = question.get('importance', 'medium')
                importance_emoji = "🔥" if importance == "high" else "⚡" if importance == "medium" else "💡"
                
                summary += f"**{importance_emoji} {q_text}**\n\n"
                if answer:
                    summary += f"Answer: {answer}\n\n"
                else:
                    summary += f"Answer: *Not answered*\n\n"
    
    # Strategic Content
    business_case = st.session_state.get('business_case', '')
    if business_case:
        summary += f"---\n\n## 💼 Business Case\n\n{business_case}\n\n"
    
    competitor_strategy = st.session_state.get('competitor_strategy', '')
    if competitor_strategy:
        summary += f"---\n\n## 🎯 Competitive Strategy\n\n{competitor_strategy}\n\n"
    
    initial_value_hypothesis = st.session_state.get('initial_value_hypothesis', '')
    if initial_value_hypothesis:
        summary += f"---\n\n## 💡 Initial Value Hypothesis\n\n{initial_value_hypothesis}\n\n"
    
    # Strategic Roadmap
    roadmap_df = st.session_state.get('roadmap_df', pd.DataFrame())
    if not roadmap_df.empty:
        summary += f"---\n\n## 🗺️ Strategic Roadmap\n\n"
        for _, item in roadmap_df.iterrows():
            summary += f"**{item.get('initiative', 'Initiative')}**\n"
            summary += f"- Priority: {item.get('priority', 'N/A')}\n"
            summary += f"- Timeline: {item.get('timeline', 'N/A')}\n"
            summary += f"- Business Value: {item.get('business_value', 'N/A')}\n\n"
    
    # Outreach Content
    outreach_emails = st.session_state.get('outreach_emails', '')
    if outreach_emails:
        summary += f"---\n\n## 📧 Follow-up Emails\n\n{outreach_emails}\n\n"
    
    linkedin_messages = st.session_state.get('linkedin_messages', '')
    if linkedin_messages:
        summary += f"---\n\n## 💼 LinkedIn Messages\n\n{linkedin_messages}\n\n"
    
    # People Research
    people_research = st.session_state.get('people_research', '')
    if people_research:
        summary += f"---\n\n## 👥 People Research\n\n{people_research}\n\n"
    
    # Expert Context
    expert_context = st.session_state.get('expert_context', {})
    if expert_context and expert_context.get('experts'):
        summary += f"---\n\n## 🎯 Recommended Experts\n\n"
        for expert in expert_context['experts'][:5]:  # Top 5 experts
            summary += f"**{expert.get('name', 'Unknown')}** - {expert.get('title', 'N/A')}\n"
            summary += f"- Relevance Score: {expert.get('relevance_score', 'N/A')}\n"
            summary += f"- Skills: {expert.get('skills', 'N/A')}\n\n"
    
    summary += f"---\n\n*Export generated on {datetime.now().strftime('%B %d, %Y at %I:%M %p')}*"
    
    return summary

def generate_json_export():
    """Generate a complete JSON export of all session data"""
    export_data = {
        'export_metadata': {
            'export_date': datetime.now().isoformat(),
            'version': '1.0'
        },
        'company_info': st.session_state.get('company_info', {}),
        'company_summary_data': st.session_state.get('company_summary_data', {}),
        'contact_info': {
            'contact_name': st.session_state.get('contact_name', ''),
            'contact_title': st.session_state.get('contact_title', ''),
            'competitor': st.session_state.get('competitor', '')
        },
        'discovery_questions': st.session_state.get('questions', []),
        'strategic_content': {
            'business_case': st.session_state.get('business_case', ''),
            'competitor_strategy': st.session_state.get('competitor_strategy', ''),
            'initial_value_hypothesis': st.session_state.get('initial_value_hypothesis', ''),
            'roadmap': st.session_state.get('roadmap_df', pd.DataFrame()).to_dict('records') if not st.session_state.get('roadmap_df', pd.DataFrame()).empty else []
        },
        'outreach_content': {
            'outreach_emails': st.session_state.get('outreach_emails', ''),
            'linkedin_messages': st.session_state.get('linkedin_messages', ''),
            'people_research': st.session_state.get('people_research', '')
        },
        'expert_context': st.session_state.get('expert_context', {}),
        'session_metadata': {
            'current_session_id': st.session_state.get('current_session_id', ''),
            'last_updated': datetime.now().isoformat()
        }
    }
    return export_data

st.title("📤 Export Session Data")
st.markdown("**Export all your discovery session data in multiple formats**")

# Check if there's data to export
company_info = st.session_state.get('company_info', {})
questions = st.session_state.get('questions', [])

if not company_info or not questions:
    st.info("💡 No session data to export. Please complete a discovery session first.")
    if st.button("🏢 Go to Sales Activities", type="primary"):
        st.switch_page("pages/01_🏢_Sales_Activities.py")
else:
    # Display current session overview
    if isinstance(company_info, dict):
        company_name = company_info.get('name') or company_info.get('website', 'Unknown Company')
    else:
        company_name = "Unknown Company"
        
    answered_questions = [q for q in questions if isinstance(q, dict) and q.get('answer', '').strip()]
    
    st.markdown("### 📊 Current Session Overview")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Company", company_name)
    with col2:
        st.metric("Questions Answered", f"{len(answered_questions)}/{len(questions)}")
    with col3:
        completion = (len(answered_questions) / len(questions) * 100) if questions else 0
        st.metric("Completion", f"{completion:.1f}%")
    with col4:
        export_time = datetime.now().strftime('%I:%M %p')
        st.metric("Export Time", export_time)
    
    st.divider()
    
    # Export options
    st.markdown("### 📄 Export Formats")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 📋 Formatted Summary")
        st.caption("Human-readable summary with all discovery data")
        
        if st.button("📋 Generate Summary", use_container_width=True, type="primary"):
            summary = generate_session_summary()
            st.markdown("**Your complete session summary:**")
            st.code(summary, language="markdown")
            st.success("✅ Summary generated! Copy the text above to share or save.")
            st.rerun()  # Refresh to show summary immediately
    
    with col2:
        st.markdown("#### 📊 Raw Data (JSON)")
        st.caption("Complete data export for technical use")
        
        if st.button("📊 Generate JSON", use_container_width=True):
            json_data = generate_json_export()
            json_string = json.dumps(json_data, indent=2, default=str)
            st.markdown("**Complete session data in JSON format:**")
            st.code(json_string, language="json")
            st.success("✅ JSON export generated! Copy the data above.")
            st.rerun()  # Refresh to show JSON immediately
    
    st.divider()
    
    # Quick export sections
    st.markdown("### ⚡ Quick Export Sections")
    
    quick_col1, quick_col2, quick_col3 = st.columns(3)
    
    with quick_col1:
        if st.button("❓ Discovery Q&A Only", use_container_width=True):
            qa_export = "# Discovery Questions & Answers\n\n"
            if isinstance(questions, list):
                for i, question in enumerate(questions, 1):
                    if isinstance(question, dict):
                        q_text = question.get('text', f"Question {i}")
                        answer = question.get('answer', '').strip()
                        qa_export += f"**Q{i}: {q_text}**\n"
                        qa_export += f"Answer: {answer or '*Not answered*'}\n\n"
            st.code(qa_export, language="markdown")
    
    with quick_col2:
        if st.button("🎯 Strategy Content Only", use_container_width=True):
            strategy_export = "# Strategic Content\n\n"
            
            business_case = st.session_state.get('business_case', '')
            if business_case:
                strategy_export += f"## Business Case\n{business_case}\n\n"
            
            competitor_strategy = st.session_state.get('competitor_strategy', '')
            if competitor_strategy:
                strategy_export += f"## Competitive Strategy\n{competitor_strategy}\n\n"
            
            if not business_case and not competitor_strategy:
                strategy_export += "*No strategic content generated yet.*"
            
            st.code(strategy_export, language="markdown")
    
    with quick_col3:
        if st.button("📧 Outreach Content Only", use_container_width=True):
            outreach_export = "# Outreach Content\n\n"
            
            outreach_emails = st.session_state.get('outreach_emails', '')
            if outreach_emails:
                outreach_export += f"## Follow-up Emails\n{outreach_emails}\n\n"
            
            linkedin_messages = st.session_state.get('linkedin_messages', '')
            if linkedin_messages:
                outreach_export += f"## LinkedIn Messages\n{linkedin_messages}\n\n"
            
            if not outreach_emails and not linkedin_messages:
                outreach_export += "*No outreach content generated yet.*"
            
            st.code(outreach_export, language="markdown")

# Footer
st.markdown("---")
st.markdown("**💡 Tip:** Save your exported content to a document or share with your team for collaboration!")

 
