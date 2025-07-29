# Data Visualization Module
# Charts, graphs, and visual representations of data

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta

def create_expert_relevance_chart(experts_data):
    """Create a chart showing expert relevance scores"""
    if not experts_data:
        return None
    
    # Prepare data
    names = []
    scores = []
    skills_count = []
    opp_count = []
    
    for expert_id, expert_info in experts_data[:20]:  # Top 20 experts
        names.append(expert_info['name'][:20] + "..." if len(expert_info['name']) > 20 else expert_info['name'])
        scores.append(expert_info.get('relevance_score', 0))
        
        # Count skills
        skills = expert_info.get('skills', {})
        total_skills = sum(len(skill_list) for skill_list in skills.values())
        skills_count.append(total_skills)
        
        opp_count.append(len(expert_info.get('opportunities', [])))
    
    # Create horizontal bar chart
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        y=names,
        x=scores,
        orientation='h',
        name='Relevance Score',
        marker=dict(
            color=scores,
            colorscale='RdYlGn',
            colorbar=dict(title="Relevance Score")
        ),
        text=[f"{score}%" for score in scores],
        textposition='inside',
        hovertemplate='<b>%{y}</b><br>' +
                      'Relevance: %{x}%<br>' +
                      'Skills: %{customdata[0]}<br>' +
                      'Opportunities: %{customdata[1]}<extra></extra>',
        customdata=list(zip(skills_count, opp_count))
    ))
    
    fig.update_layout(
        title="Expert Relevance Ranking",
        xaxis_title="Relevance Score (%)",
        yaxis_title="Experts",
        height=max(400, len(names) * 25),
        showlegend=False
    )
    
    return fig

def create_skills_distribution_chart(experts_data):
    """Create a chart showing skills distribution among experts"""
    if not experts_data:
        return None
    
    # Count skills across all experts
    skill_counts = {}
    
    for expert_id, expert_info in experts_data:
        skills = expert_info.get('skills', {})
        for level, skill_list in skills.items():
            if level == 'high_proficiency':  # Focus on high proficiency skills
                for skill in skill_list:
                    skill_counts[skill] = skill_counts.get(skill, 0) + 1
    
    if not skill_counts:
        return None
    
    # Get top skills
    sorted_skills = sorted(skill_counts.items(), key=lambda x: x[1], reverse=True)[:15]
    skills, counts = zip(*sorted_skills)
    
    # Create bar chart
    fig = px.bar(
        x=list(counts),
        y=list(skills),
        orientation='h',
        title="Top Skills Among Experts",
        labels={'x': 'Number of Experts', 'y': 'Skills'}
    )
    
    fig.update_layout(height=400)
    
    return fig

def create_opportunity_timeline_chart(experts_data):
    """Create a timeline chart of expert opportunities"""
    if not experts_data:
        return None
    
    # Collect opportunity data
    timeline_data = []
    
    for expert_id, expert_info in experts_data:
        opportunities = expert_info.get('opportunities', [])
        for opp in opportunities:
            if opp.get('close_date'):
                timeline_data.append({
                    'expert': expert_info['name'][:15] + "..." if len(expert_info['name']) > 15 else expert_info['name'],
                    'opportunity': opp.get('name', 'Unknown'),
                    'close_date': opp.get('close_date'),
                    'amount': opp.get('amount', 0),
                    'stage': opp.get('stage', 'Unknown'),
                    'industry': opp.get('industry', 'Unknown')
                })
    
    if not timeline_data:
        return None
    
    df = pd.DataFrame(timeline_data)
    
    # Create scatter plot timeline
    fig = px.scatter(
        df,
        x='close_date',
        y='expert',
        size='amount',
        color='stage',
        hover_data=['opportunity', 'industry'],
        title="Expert Opportunity Timeline",
        labels={'close_date': 'Close Date', 'expert': 'Expert'}
    )
    
    fig.update_layout(height=400)
    
    return fig

def create_discovery_progress_chart():
    """Create a chart showing discovery progress by category"""
    questions = st.session_state.get('questions', {})
    
    if not questions:
        return None
    
    # Calculate progress by category
    categories = []
    total_questions = []
    answered_questions = []
    
    for category, question_list in questions.items():
        if question_list:
            categories.append(category[:20] + "..." if len(category) > 20 else category)
            total_questions.append(len(question_list))
            answered_count = len([q for q in question_list if q.get('answer', '').strip()])
            answered_questions.append(answered_count)
    
    if not categories:
        return None
    
    # Create grouped bar chart
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        name='Total Questions',
        x=categories,
        y=total_questions,
        marker_color='lightblue'
    ))
    
    fig.add_trace(go.Bar(
        name='Answered Questions',
        x=categories,
        y=answered_questions,
        marker_color='darkblue'
    ))
    
    fig.update_layout(
        title="Discovery Progress by Category",
        xaxis_title="Categories",
        yaxis_title="Number of Questions",
        barmode='group',
        height=400
    )
    
    return fig

def create_roadmap_value_chart():
    """Create a chart showing roadmap projects by business value and effort"""
    roadmap_df = st.session_state.get('roadmap_df', pd.DataFrame())
    
    if roadmap_df.empty:
        return None
    
    try:
        # Map categorical values to numbers for plotting
        value_mapping = {'Low': 1, 'Medium': 2, 'High': 3, 'Very High': 4}
        effort_mapping = {'Low': 1, 'Medium': 2, 'High': 3}
        
        # Prepare data with safe defaults
        x_values = [effort_mapping.get(str(effort), 2) for effort in roadmap_df.get('level_of_effort', [])]
        y_values = [value_mapping.get(str(value), 2) for value in roadmap_df.get('business_value', [])]
        
        # Ensure we have valid data
        if not x_values or not y_values or len(x_values) != len(y_values):
            return None
        
        # Create scatter plot
        fig = px.scatter(
            x=x_values,
            y=y_values,
            hover_name=roadmap_df.get('project_name', [f"Project {i+1}" for i in range(len(x_values))]),
            title="Roadmap Projects: Business Value vs Level of Effort",
            labels={'x': 'Level of Effort', 'y': 'Business Value'}
        )
    except Exception as e:
        st.error(f"Error creating roadmap chart: {str(e)}")
        return None
    
    # Customize axes
    fig.update_layout(
        xaxis=dict(
            tickmode='array',
            tickvals=[1, 2, 3],
            ticktext=['Low', 'Medium', 'High']
        ),
        yaxis=dict(
            tickmode='array',
            tickvals=[1, 2, 3, 4],
            ticktext=['Low', 'Medium', 'High', 'Very High']
        )
    )
    
    # Add quadrant lines using add_shape (compatible with older Plotly)
    fig.add_shape(type="line", x0=0, x1=4, y0=2.5, y1=2.5, line=dict(dash="dash", color="gray", width=1), opacity=0.5)
    fig.add_shape(type="line", x0=2, x1=2, y0=0, y1=5, line=dict(dash="dash", color="gray", width=1), opacity=0.5)
    
    # Add quadrant labels
    fig.add_annotation(x=1.5, y=3.5, text="High Value<br>Low Effort<br>(Quick Wins)", showarrow=False, bgcolor="lightgreen", opacity=0.7)
    fig.add_annotation(x=2.5, y=3.5, text="High Value<br>High Effort<br>(Major Projects)", showarrow=False, bgcolor="yellow", opacity=0.7)
    fig.add_annotation(x=1.5, y=1.5, text="Low Value<br>Low Effort<br>(Fill-ins)", showarrow=False, bgcolor="lightblue", opacity=0.7)
    fig.add_annotation(x=2.5, y=1.5, text="Low Value<br>High Effort<br>(Avoid)", showarrow=False, bgcolor="lightcoral", opacity=0.7)
    
    fig.update_layout(height=500)
    
    return fig

def create_session_analytics_dashboard():
    """Create a dashboard of session analytics"""
    from modules.session_management import get_session_analytics, get_recent_activity
    
    analytics = get_session_analytics()
    
    if not analytics:
        return None
    
    # Create subplots
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=('Sessions Over Time', 'Industries Distribution', 
                       'Competitors Analysis', 'Answer Completion'),
        specs=[[{"secondary_y": False}, {"type": "pie"}],
               [{"type": "bar"}, {"type": "indicator"}]]
    )
    
    # Recent activity timeline (simplified for demo)
    recent_activity = get_recent_activity(30)
    if not recent_activity.empty:
        activity_counts = recent_activity.groupby(recent_activity['ANSWERED_DATE'].dt.date).size()
        fig.add_trace(
            go.Scatter(x=activity_counts.index, y=activity_counts.values, mode='lines+markers'),
            row=1, col=1
        )
    
    # Industry distribution (simplified)
    industries = ['Financial Services', 'Healthcare', 'Retail', 'Technology', 'Manufacturing']
    industry_counts = [15, 12, 8, 20, 10]  # Sample data
    fig.add_trace(
        go.Pie(labels=industries, values=industry_counts, name="Industries"),
        row=1, col=2
    )
    
    # Competitors analysis (simplified)
    competitors = ['Databricks', 'BigQuery', 'Redshift', 'Synapse', 'Others']
    competitor_counts = [25, 15, 12, 8, 10]  # Sample data
    fig.add_trace(
        go.Bar(x=competitors, y=competitor_counts, name="Competitors"),
        row=2, col=1
    )
    
    # Completion rate indicator
    completion_rate = analytics.get('avg_answers_per_session', 0) / 30 * 100  # Assuming 30 questions average
    fig.add_trace(
        go.Indicator(
            mode="gauge+number+delta",
            value=completion_rate,
            domain={'x': [0, 1], 'y': [0, 1]},
            title={'text': "Avg Completion Rate"},
            gauge={'axis': {'range': [None, 100]},
                   'bar': {'color': "darkblue"},
                   'steps': [
                       {'range': [0, 50], 'color': "lightgray"},
                       {'range': [50, 80], 'color': "yellow"},
                       {'range': [80, 100], 'color': "green"}],
                   'threshold': {'line': {'color': "red", 'width': 4},
                                'thickness': 0.75, 'value': 90}}
        ),
        row=2, col=2
    )
    
    fig.update_layout(height=600, showlegend=False)
    
    return fig

def create_expert_industry_heatmap(experts_data):
    """Create a heatmap of expert experience across industries"""
    if not experts_data:
        return None
    
    # Collect industry data
    expert_industries = {}
    all_industries = set()
    
    for expert_id, expert_info in experts_data[:15]:  # Top 15 experts
        expert_name = expert_info['name'][:15] + "..." if len(expert_info['name']) > 15 else expert_info['name']
        industries = expert_info.get('industries', set())
        expert_industries[expert_name] = industries
        all_industries.update(industries)
    
    if not all_industries:
        return None
    
    # Create matrix
    industry_list = sorted(list(all_industries))
    expert_list = list(expert_industries.keys())
    
    z = []
    for expert in expert_list:
        row = []
        for industry in industry_list:
            if industry in expert_industries[expert]:
                # Count opportunities in this industry
                opp_count = 0
                for expert_id, expert_info in experts_data:
                    if expert_info['name'].startswith(expert.split("...")[0]):
                        for opp in expert_info.get('opportunities', []):
                            if opp.get('industry') == industry:
                                opp_count += 1
                        break
                row.append(opp_count)
            else:
                row.append(0)
        z.append(row)
    
    # Create heatmap
    fig = go.Figure(data=go.Heatmap(
        z=z,
        x=industry_list,
        y=expert_list,
        colorscale='Blues',
        hoverongaps=False
    ))
    
    fig.update_layout(
        title="Expert Industry Experience (Opportunity Count)",
        xaxis_title="Industries",
        yaxis_title="Experts",
        height=400
    )
    
    return fig

def create_metric_trend_chart(metrics_history):
    """Create a trend chart for key metrics over time"""
    if not metrics_history:
        return None
    
    df = pd.DataFrame(metrics_history)
    
    fig = go.Figure()
    
    # Add traces for different metrics
    for column in df.columns:
        if column != 'date':
            fig.add_trace(go.Scatter(
                x=df['date'],
                y=df[column],
                mode='lines+markers',
                name=column.replace('_', ' ').title()
            ))
    
    fig.update_layout(
        title="Key Metrics Trend",
        xaxis_title="Date",
        yaxis_title="Value",
        height=400
    )
    
    return fig

def create_value_matrix_chart(projects_data):
    """Create a value matrix chart for projects or initiatives"""
    if not projects_data:
        return None
    
    # This is a generic function that can be used for roadmap or other project data
    fig = px.scatter(
        projects_data,
        x='effort_score',
        y='value_score',
        size='impact_score',
        color='category',
        hover_name='name',
        title="Value vs Effort Matrix"
    )
    
    # Add quadrant lines using add_shape (compatible with older Plotly)
    fig.add_shape(type="line", x0=0, x1=100, y0=50, y1=50, line=dict(dash="dash", color="gray", width=1))
    fig.add_shape(type="line", x0=50, x1=50, y0=0, y1=100, line=dict(dash="dash", color="gray", width=1))
    
    fig.update_layout(height=500)
    
    return fig

def render_chart_with_download(fig, title, filename_prefix="chart"):
    """Render a chart with download option"""
    if fig is None:
        st.info(f"No data available for {title}")
        return
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Download button for chart
    col1, col2 = st.columns([0.8, 0.2])
    with col2:
        if st.button(f"📊 Download {title}", key=f"download_{filename_prefix}"):
            # Convert to HTML
            html_str = fig.to_html()
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{filename_prefix}_{timestamp}.html"
            
            st.download_button(
                label="Download HTML",
                data=html_str,
                file_name=filename,
                mime="text/html",
                key=f"download_html_{filename_prefix}"
            ) 