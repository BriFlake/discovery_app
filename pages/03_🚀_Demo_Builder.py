# Demo Builder Page
# Demo automation, prompt generation, and demo environment creation

import streamlit as st
import pandas as pd
import json
import urllib.parse
from shared.state_manager import StateManager
from modules.llm_functions import generate_demo_prompt_with_llm, generate_mermaid_architecture, generate_xml_architecture, convert_mermaid_to_drawio_xml, generate_export_urls
from modules.ui_components import (
    render_navigation_sidebar, render_roadmap_table, render_data_table,
    render_metric_cards, render_alert_banner
)
from modules.data_visualization import create_roadmap_value_chart, render_chart_with_download
from modules.sales_functions import prepare_discovery_notes

# Initialize state manager
state_manager = StateManager()

# Page configuration
st.set_page_config(
    page_title="Demo Builder",
    page_icon="🚀",
    layout="wide"
)

# Mark app as fully loaded for database queries
from modules.snowflake_utils import mark_app_loaded
mark_app_loaded()

# Render sidebar navigation
render_navigation_sidebar()

# Main page header
st.title("🚀 Demo Builder")
st.markdown("**Generate comprehensive demo environments and prompts for Cursor AI**")

# Check if we have the necessary data for demo generation
company_context = state_manager.get_company_context()
discovery_data = state_manager.get_discovery_data()
expert_context = state_manager.get_expert_context()

has_company = bool(company_context.get('website'))
has_discovery = bool(discovery_data.get('questions')) or bool(discovery_data.get('notes'))
has_roadmap = not discovery_data.get('roadmap', pd.DataFrame()).empty
has_strategy = bool(discovery_data.get('strategy', '').strip())

# Main demo builder interface
if has_company:
    # Main tabs for demo building
    tab1, tab2, tab3 = st.tabs([
        "🎯 Demo Prompt Generator", 
        "📊 Demo Data Overview", 
        "🏗️ Architecture Builder"
    ])
    
    with tab1:
        st.markdown("## 🎯 Demo Prompt Generator")
        st.markdown("Generate comprehensive prompts for Cursor AI to build complete demo environments")
        
        # Demo generation options
        st.markdown("### Demo Generation Options")
        
        col1, col2 = st.columns(2)
        
        with col1:
            demo_type = st.selectbox(
                "Demo Type:",
                [
                    "Executive Dashboard + Operational App",
                    "Executive Dashboard Only", 
                    "Operational/Analytical App Only",
                    "Data Engineering Pipeline Demo",
                    "AI/ML Use Case Demo",
                    "Custom Demo"
                ],
                help="Select the type of demo environment to generate"
            )
            
            include_sample_data = st.checkbox(
                "Include Sample Data Generation", 
                value=True,
                help="Generate realistic sample data for the demo"
            )
            
            include_setup_instructions = st.checkbox(
                "Include Setup Instructions",
                value=True, 
                help="Include detailed setup and deployment instructions"
            )
        
        with col2:
            complexity_level = st.selectbox(
                "Complexity Level:",
                ["Basic", "Intermediate", "Advanced"],
                index=1,
                help="Adjust the complexity of the generated demo"
            )
            
            include_storytelling = st.checkbox(
                "Include Demo Story/Script",
                value=True,
                help="Generate a compelling demo story and presentation script"
            )
            
            target_audience = st.selectbox(
                "Target Audience:",
                ["Technical", "Business", "Mixed", "C-Level"],
                index=2,
                help="Tailor the demo for specific audience"
            )
        
        # Generate demo prompt
        st.markdown("---")
        
        generate_col1, generate_col2 = st.columns([1, 3])
        
        with generate_col1:
            if st.button("🚀 Generate Demo Prompt", type="primary", disabled=not (has_company and (has_discovery or has_roadmap))):
                # Prepare all context data
                discovery_notes = prepare_discovery_notes()
                roadmap_df = discovery_data.get('roadmap', pd.DataFrame())
                value_hypothesis = discovery_data.get('hypothesis', '')
                strategy_content = discovery_data.get('strategy', '')
                people_research = discovery_data.get('people_research', [])
                
                with st.spinner("🧠 Generating comprehensive demo prompt with AI..."):
                    demo_prompt = generate_demo_prompt_with_llm(
                        company_context,
                        discovery_notes,
                        roadmap_df,
                        value_hypothesis,
                        strategy_content,
                        people_research
                    )
                
                if demo_prompt:
                    st.session_state.generated_demo_prompt = demo_prompt
                    st.session_state.demo_generation_options = {
                        'demo_type': demo_type,
                        'complexity_level': complexity_level,
                        'target_audience': target_audience,
                        'include_sample_data': include_sample_data,
                        'include_setup_instructions': include_setup_instructions,
                        'include_storytelling': include_storytelling
                    }
                    st.success("✅ Demo prompt generated successfully!")
                else:
                    st.error("❌ Failed to generate demo prompt. Please try again.")
        
        with generate_col2:
            if not (has_company and (has_discovery or has_roadmap)):
                st.info("💡 Complete company setup and discovery to enable demo generation")
        
        # Display generated prompt
        if st.session_state.get('generated_demo_prompt'):
            st.markdown("---")
            st.markdown("### 📋 Generated Demo Prompt")
            
            # Show generation options
            options = st.session_state.get('demo_generation_options', {})
            if options:
                st.markdown("**Generation Options:**")
                option_cols = st.columns(3)
                with option_cols[0]:
                    st.caption(f"Type: {options.get('demo_type', 'N/A')}")
                    st.caption(f"Complexity: {options.get('complexity_level', 'N/A')}")
                with option_cols[1]:
                    st.caption(f"Audience: {options.get('target_audience', 'N/A')}")
                    st.caption(f"Sample Data: {'Yes' if options.get('include_sample_data') else 'No'}")
                with option_cols[2]:
                    st.caption(f"Setup Instructions: {'Yes' if options.get('include_setup_instructions') else 'No'}")
                    st.caption(f"Demo Script: {'Yes' if options.get('include_storytelling') else 'No'}")
            
            # Action buttons
            action_col1, action_col2, action_col3 = st.columns(3)
            
            with action_col1:
                if st.button("📋 Copy to Clipboard"):
                    st.success("✅ Prompt is ready to copy!")
                    st.info("💡 Use Ctrl+C to copy the prompt below")
            
            with action_col2:
                prompt_text = st.session_state.generated_demo_prompt
                st.download_button(
                    "💾 Download Prompt",
                    data=prompt_text,
                    file_name=f"demo_prompt_{company_context.get('website', 'company').replace('.', '_')}.txt",
                    mime="text/plain"
                )
            
            with action_col3:
                if st.button("🔄 Regenerate"):
                    if 'generated_demo_prompt' in st.session_state:
                        del st.session_state.generated_demo_prompt
                    st.rerun()
            
            # Display the prompt
            st.markdown("### 📄 Cursor AI Demo Prompt")
            st.code(st.session_state.generated_demo_prompt, language="text")
            
            # Usage instructions
            with st.expander("📖 How to Use This Prompt"):
                st.markdown("""
                **To use this prompt with Cursor AI:**
                
                1. **Copy the entire prompt** above
                2. **Open Cursor AI** in your development environment
                3. **Create a new project folder** for your demo
                4. **Paste the prompt** into Cursor AI chat
                5. **Follow the generated instructions** to build your demo
                6. **Iterate and refine** based on your specific needs
                
                **Tips for best results:**
                - Run the prompt in a clean project directory
                - Follow the setup instructions carefully
                - Test the demo before presenting
                - Customize the generated content for your specific use case
                """)
    
    with tab2:
        st.markdown("## 📊 Demo Data Overview")
        st.markdown("Review all available data for demo generation")
        
        # Company context
        st.markdown("### 🏢 Company Context")
        if company_context:
            context_df = pd.DataFrame([
                {"Field": "Website", "Value": company_context.get('website', 'N/A')},
                {"Field": "Industry", "Value": company_context.get('industry', 'N/A')},
                {"Field": "Primary Competitor", "Value": company_context.get('competitor', 'N/A')},
                {"Field": "Contact Persona", "Value": company_context.get('persona', 'N/A')}
            ])
            render_data_table(context_df, show_download=False)
        else:
            st.info("No company context available")
        
        # Discovery data
        st.markdown("### ❓ Discovery Data")
        questions = discovery_data.get('questions', {})
        if questions:
            # Summary of questions by category
            discovery_summary = []
            
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
                total_questions = len(question_list)
                answered_questions = len([q for q in question_list if q.get('answer', '').strip()])
                discovery_summary.append({
                    "Category": category,
                    "Total Questions": total_questions,
                    "Answered Questions": answered_questions,
                    "Completion %": f"{(answered_questions/total_questions*100):.1f}%" if total_questions > 0 else "0%"
                })
            
            discovery_df = pd.DataFrame(discovery_summary)
            render_data_table(discovery_df, "Discovery Progress", show_download=False)
            
            # Answered questions detail
            with st.expander("View Answered Questions"):
                answered_questions = []
                for category, question_list in questions_dict.items():
                    for q in question_list:
                        if q.get('answer', '').strip():
                            answered_questions.append({
                                "Category": category,
                                "Question": q['text'][:100] + "..." if len(q['text']) > 100 else q['text'],
                                "Answer": q['answer'][:100] + "..." if len(q['answer']) > 100 else q['answer']
                            })
                
                if answered_questions:
                    answered_df = pd.DataFrame(answered_questions)
                    render_data_table(answered_df, "Answered Questions", show_download=True)
                else:
                    st.info("No answered questions available")
        else:
            st.info("No discovery questions available")
        
        # Strategic roadmap
        st.markdown("### 🗺️ Strategic Roadmap")
        roadmap_df = discovery_data.get('roadmap', pd.DataFrame())
        if not roadmap_df.empty:
            render_roadmap_table(roadmap_df)
            
            # Roadmap chart
            roadmap_chart = create_roadmap_value_chart()
            if roadmap_chart:
                render_chart_with_download(roadmap_chart, "Roadmap Value Matrix", "demo_roadmap")
        else:
            st.info("No strategic roadmap available. Generate roadmap in Sales Activities.")
        
        # Expert context
        st.markdown("### 🔍 Expert Context")
        experts = expert_context.get('experts', [])
        if experts:
            expert_summary = []
            for expert_id, expert_info in experts[:10]:  # Top 10
                skills = expert_info.get('skills', {})
                total_skills = sum(len(skill_list) for skill_list in skills.values())
                
                expert_summary.append({
                    "Expert": expert_info['name'],
                    "Relevance Score": f"{expert_info.get('relevance_score', 0)}%",
                    "Total Skills": total_skills,
                    "Opportunities": len(expert_info.get('opportunities', [])),
                    "Industries": len(expert_info.get('industries', set()))
                })
            
            expert_df = pd.DataFrame(expert_summary)
            render_data_table(expert_df, "Expert Summary", show_download=False)
        else:
            st.info("No expert context available. Find experts in Expert Hub.")
        
        # People research
        st.markdown("### 👥 People Research")
        people_research = discovery_data.get('people_research', [])
        if people_research:
            people_summary = []
            for person in people_research:
                insights_count = len(person.get('insights', []))
                topics_count = sum(len(topics) for topics in person.get('topics', {}).values())
                
                people_summary.append({
                    "Name": person['name'],
                    "Title": person['title'],
                    "Insights": insights_count,
                    "Conversation Topics": topics_count
                })
            
            people_df = pd.DataFrame(people_summary)
            render_data_table(people_df, "People Research Summary", show_download=False)
        else:
            st.info("No people research available")
    
    with tab3:
        st.markdown("## 🏗️ AI Architecture Builder")
        st.markdown("Generate professional Mermaid architecture diagrams with AI and export to professional tools")
        
        # Check for discovery data
        if not discovery_data.get('questions') and not discovery_data.get('notes'):
            st.warning("⚠️ **Discovery Data Required** - Complete sales discovery first to generate AI architectures")
            if st.button("🏢 Go to Sales Activities", type="primary"):
                st.switch_page("pages/01_🏢_Sales_Activities.py")
        else:
            # Import required modules for Mermaid
            try:
                import streamlit_mermaid as stmd
            except ImportError as e:
                st.error(f"❌ Required packages not available: {e}")
                st.info("💡 Please install: `pip install streamlit-mermaid`")
                st.stop()
            
            # Main interface
            col1, col2 = st.columns([1, 2])
            
            with col1:
                st.markdown("### 🤖 AI Architecture Generation")
                
                # Architecture type selection
                architecture_type = st.radio(
                    "Architecture Type:",
                    ["Current State", "Future State (Snowflake-Optimized)", "Both States"],
                    index=2,
                    help="Choose which architecture to generate"
                )
                
                # Diagram format selection
                diagram_format = st.radio(
                    "Diagram Format:",
                    ["🧩 Mermaid + XML", "🧩 Mermaid Only", "📐 XML Only"],
                    index=0,
                    help="Choose which diagram formats to generate"
                )
                
                # Generate button
                if st.button("🧠 Generate Architecture", type="primary", use_container_width=True):
                    with st.spinner("🧠 Analyzing discovery data with Cortex Complete..."):
                        # Generate based on selected format
                        if diagram_format in ["🧩 Mermaid + XML", "🧩 Mermaid Only"]:
                            mermaid_code = generate_mermaid_architecture(
                                discovery_data, 
                                company_context, 
                                architecture_type
                            )
                            if mermaid_code:
                                st.session_state.generated_mermaid = mermaid_code
                                st.session_state.architecture_type = architecture_type
                        
                        if diagram_format in ["🧩 Mermaid + XML", "📐 XML Only"]:
                            xml_code = generate_xml_architecture(
                                discovery_data,
                                company_context,
                                architecture_type
                            )
                            if xml_code:
                                st.session_state.generated_xml = xml_code
                                st.session_state.architecture_type = architecture_type
                        
                        # Show success message
                        if ((diagram_format in ["🧩 Mermaid + XML", "🧩 Mermaid Only"] and st.session_state.get('generated_mermaid')) or
                            (diagram_format in ["🧩 Mermaid + XML", "📐 XML Only"] and st.session_state.get('generated_xml'))):
                            if diagram_format == "🧩 Mermaid + XML":
                                st.success("✅ Both Mermaid and XML diagrams generated!")
                            elif diagram_format == "🧩 Mermaid Only":
                                st.success("✅ Mermaid diagram generated!")
                            else:
                                st.success("✅ XML diagram generated!")
                        else:
                            st.error("❌ Failed to generate architecture. Please try again.")
                
                # Show current architecture info
                if st.session_state.get('generated_mermaid'):
                    st.markdown("### 📋 Current Architecture")
                    st.caption(f"Type: {st.session_state.get('architecture_type', 'Unknown')}")
                    st.caption(f"Generated: {pd.Timestamp.now().strftime('%H:%M')}")
                    
                    if st.button("🔄 Regenerate", use_container_width=True):
                        # Clear current diagram to regenerate
                        if 'generated_mermaid' in st.session_state:
                            del st.session_state.generated_mermaid
                        st.rerun()
                
                # Professional Export Options
                if st.session_state.get('generated_mermaid') or st.session_state.get('generated_xml'):
                    st.markdown("### 🎨 Professional Editing")
                    st.markdown("**Export to professional tools for final polish:**")
                    
                    # Get export URLs and files
                    company_name = company_context.get('website', 'company').replace('www.', '').replace('.com', '')
                    
                    # Mermaid downloads (if available)
                    if st.session_state.get('generated_mermaid'):
                        export_data = generate_export_urls(st.session_state.generated_mermaid, company_name)
                        
                        st.markdown("**🧩 Mermaid Format:**")
                        
                        # Mermaid file download
                        st.download_button(
                            "📐 Download Mermaid (.mmd)",
                            data=st.session_state.generated_mermaid,
                            file_name=export_data['mermaid_file'],
                            mime="text/plain",
                            help="For Lucidchart, Mermaid Live, or other Mermaid editors",
                            use_container_width=True
                        )
                        
                        # Convert Mermaid to Draw.io XML download
                        drawio_xml = convert_mermaid_to_drawio_xml(st.session_state.generated_mermaid)
                        st.download_button(
                            "🎨 Download Draw.io from Mermaid (.drawio)",
                            data=drawio_xml,
                            file_name=f"mermaid_converted_{export_data['drawio_file']}",
                            mime="application/xml",
                            help="Mermaid converted to Draw.io format",
                            use_container_width=True
                        )
                    
                    # XML downloads (if available)
                    if st.session_state.get('generated_xml'):
                        st.markdown("**📐 Native XML Format:**")
                        
                        # AI-generated XML download
                        st.download_button(
                            "🤖 Download AI-Generated XML (.xml)",
                            data=st.session_state.generated_xml,
                            file_name=f"ai_generated_{company_name}_architecture.xml",
                            mime="application/xml",
                            help="AI-generated native draw.io XML format",
                            use_container_width=True
                        )
                        
                        # Also provide as .drawio extension
                        st.download_button(
                            "🎨 Download AI XML as Draw.io (.drawio)",
                            data=st.session_state.generated_xml,
                            file_name=f"ai_generated_{company_name}_architecture.drawio",
                            mime="application/xml",
                            help="AI-generated XML with draw.io extension",
                            use_container_width=True
                        )
                    
                    # Professional platform links (if Mermaid is available)
                    if st.session_state.get('generated_mermaid'):
                        st.markdown("**🔗 Online Editing Platforms:**")
                        
                        export_data = generate_export_urls(st.session_state.generated_mermaid, company_name)
                        
                        # Professional platform links
                        st.link_button(
                            "🚀 Edit in Draft1.ai",
                            export_data['draft1_url'],
                            help="AI-powered professional diagram creation",
                            use_container_width=True
                        )
                        
                        st.link_button(
                            "✨ Edit in Whimsical",
                            export_data['whimsical_url'],
                            help="Modern, collaborative diagram editing",
                            use_container_width=True
                        )
                    
                    # Lucidchart instructions
                    with st.expander("📐 Lucidchart Instructions"):
                        st.markdown(export_data['lucidchart_instructions'])
                        st.code("""
1. Copy the Mermaid code (download .mmd file)
2. Open Lucidchart
3. Insert → Diagram as Code → Mermaid
4. Paste the code and generate
5. Edit with professional styling
                        """)
            
            with col2:
                st.markdown("### 🎯 Generated Architecture Diagram")
                
                # Show different content based on what was generated
                if st.session_state.get('generated_mermaid') and st.session_state.get('generated_xml'):
                    st.info("✅ Both Mermaid and XML diagrams generated! Use the download buttons to get both formats.")
                
                # Display Mermaid diagram if available
                if st.session_state.get('generated_mermaid'):
                    st.markdown("#### 🧩 Mermaid Diagram")
                    mermaid_code = st.session_state.generated_mermaid
                    
                    # Display the Mermaid diagram
                    try:
                        stmd.st_mermaid(mermaid_code, height="500px")
                    except Exception as e:
                        st.error(f"Error displaying Mermaid diagram: {e}")
                        st.info("💡 The diagram code is still available for export")
                    
                    # Editable Mermaid code
                    st.markdown("#### 📝 Edit Mermaid Code")
                    with st.expander("Edit Mermaid Syntax", expanded=False):
                        edited_code = st.text_area(
                            "Mermaid Code:",
                            value=mermaid_code,
                            height=300,
                            help="Edit the Mermaid syntax directly. Changes will update the diagram."
                        )
                        
                        col_update, col_reset = st.columns(2)
                        
                        with col_update:
                            if st.button("🔄 Update Mermaid"):
                                st.session_state.generated_mermaid = edited_code
                                st.success("✅ Mermaid diagram updated!")
                                st.rerun()
                        
                        with col_reset:
                            if st.button("↩️ Reset Mermaid"):
                                # Would need to store original, for now just regenerate
                                st.info("💡 Use 'Regenerate' to get a fresh AI-generated diagram")
                    
                    # Copy to clipboard helper for Mermaid
                    st.markdown("#### 📋 Copy Mermaid Code")
                    st.code(mermaid_code, language="mermaid")
                    st.caption("💡 Select all and copy to use in other tools")
                
                # Display XML information if available
                if st.session_state.get('generated_xml'):
                    st.markdown("#### 📐 AI-Generated XML Diagram")
                    st.success("✅ Native draw.io XML format generated!")
                    st.info("💡 This diagram was generated directly as XML and is optimized for draw.io. Use the download buttons above to get the file and open it in draw.io or similar tools.")
                    
                    # Show XML preview (truncated)
                    xml_code = st.session_state.generated_xml
                    
                    with st.expander("Preview XML Code", expanded=False):
                        # Show first 1000 characters of XML
                        xml_preview = xml_code[:1000] + "..." if len(xml_code) > 1000 else xml_code
                        st.code(xml_preview, language="xml")
                        st.caption("💡 Complete XML available via download button")
                    
                    # Edit XML functionality
                    with st.expander("Edit XML Code", expanded=False):
                        edited_xml = st.text_area(
                            "XML Code:",
                            value=xml_code,
                            height=300,
                            help="Edit the XML code directly. This is advanced - ensure valid XML syntax."
                        )
                        
                        if st.button("🔄 Update XML"):
                            # Basic validation - check if it contains xml declaration
                            if '<?xml' in edited_xml and 'mxfile' in edited_xml:
                                st.session_state.generated_xml = edited_xml
                                st.success("✅ XML diagram updated!")
                                st.rerun()
                            else:
                                st.error("❌ Invalid XML format. Please ensure it's a valid draw.io XML file.")
                
                # Show architecture insights
                if st.session_state.get('generated_mermaid') or st.session_state.get('generated_xml'):
                    st.markdown("#### 🔍 Architecture Insights")
                    arch_type = st.session_state.get('architecture_type', '')
                    
                    if arch_type == "Current State":
                        st.info("**Current State Analysis:** This diagram shows your existing data architecture, highlighting current systems, processes, and potential bottlenecks identified from the discovery data.")
                    elif arch_type == "Future State (Snowflake-Optimized)":
                        st.success("**Future State Vision:** This diagram presents a Snowflake-optimized architecture designed to address current challenges with modern data cloud capabilities, Cortex AI, and Streamlit applications.")
                    else:
                        st.info("**Comparative Analysis:** This diagram shows both current and future state architectures, highlighting the transformation path from legacy systems to a modern Snowflake-powered data platform.")
                
                # If no diagrams generated yet
                if not st.session_state.get('generated_mermaid') and not st.session_state.get('generated_xml'):
                    st.info("👈 Select architecture type and diagram format, then click 'Generate Architecture' to create your diagrams.")

else:
    # Show setup message when no company context
    st.markdown("## 🚀 Demo Builder")
    st.markdown("**AI-powered Mermaid architecture diagrams with professional export options**")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 📋 What You Need")
        st.markdown("🏢 **Company Context** - Set up company information")
        st.markdown("📊 **Discovery Data** - Complete sales discovery questions")
        st.markdown("🧠 **AI Analysis** - Cortex Complete generates Mermaid diagrams")
    
    with col2:
        st.markdown("### 🎨 Professional Workflow")
        st.markdown("🤖 **AI Generates** - Mermaid syntax from discovery data")
        st.markdown("📐 **Export Options** - Lucidchart, Draw.io, Draft1.ai, Whimsical")
        st.markdown("✨ **Professional Polish** - Edit in industry-standard tools")
    
    # Quick start button
    if st.button("🏢 Get Started in Sales Activities", type="primary"):
        st.switch_page("pages/01_🏢_Sales_Activities.py")

# Footer
st.markdown("---")

# Readiness check removed for cleaner interface

st.markdown("**🚀 Demo Builder** | Generate comprehensive demo environments with AI") 