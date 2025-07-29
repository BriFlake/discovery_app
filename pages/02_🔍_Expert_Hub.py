# Expert Hub - Find internal experts using Freestyle skills and Salesforce data
# Search Freestyle Summary table and display SE Directory with modal details

import streamlit as st
import pandas as pd
import re
from modules.snowflake_utils import execute_query
from modules.ui_components import render_navigation_sidebar

# Page configuration
st.set_page_config(
    page_title="Expert Hub - Sales Discovery",
    page_icon="🔍",
    layout="wide"
)

# Mark app as fully loaded for database queries
from modules.snowflake_utils import mark_app_loaded
mark_app_loaded()

# Render sidebar navigation
render_navigation_sidebar()

# Main header
st.title("🔍 Expert Hub")
st.markdown("**Find internal experts using Freestyle skills and Salesforce opportunity data**")

# Custom CSS for skill tags
st.markdown("""
<style>
.skill-tag {
    display: inline-block;
    background-color: #e3f2fd;
    color: #1976d2;
    padding: 2px 8px;
    margin: 2px;
    border-radius: 12px;
    font-size: 12px;
    font-weight: 500;
}
.high-skill-tag {
    display: inline-block;
    background-color: #e8f5e8;
    color: #388e3c;
    padding: 2px 8px;
    margin: 2px;
    border-radius: 12px;
    font-size: 12px;
    font-weight: 600;
}
.cert-tag {
    display: inline-block;
    background-color: #fff3e0;
    color: #f57c00;
    padding: 2px 8px;
    margin: 2px;
    border-radius: 12px;
    font-size: 12px;
    font-weight: 500;
}
</style>
""", unsafe_allow_html=True)

def search_freestyle_experts(search_terms):
    """Search the Freestyle Summary table for experts"""
    try:
        # Clean and prepare search terms
        search_terms_clean = search_terms.strip().lower()
        
        # Search query for Freestyle Summary table
        # Search query for Freestyle Summary table - handle ARRAY columns properly
        query = """
        SELECT 
            USER_ID,
            NAME,
            EMAIL,
            COLLEGE,
            EMPLOYERS,
            SELF_ASSESMENT_SKILL_400,
            SPECIALTIES,
            CERT_EXTERNAL,
            CERT_INTERNAL,
            -- Calculate relevance score based on search terms
            CASE 
                WHEN LOWER(ARRAY_TO_STRING(SELF_ASSESMENT_SKILL_400, ',')) ILIKE '%' || ? || '%' THEN 100
                WHEN LOWER(ARRAY_TO_STRING(SPECIALTIES, ',')) ILIKE '%' || ? || '%' THEN 80
                WHEN LOWER(ARRAY_TO_STRING(CERT_EXTERNAL, ',')) ILIKE '%' || ? || '%' THEN 60
                WHEN LOWER(ARRAY_TO_STRING(CERT_INTERNAL, ',')) ILIKE '%' || ? || '%' THEN 55
                WHEN LOWER(NAME) ILIKE '%' || ? || '%' THEN 40
                ELSE 20
            END as RELEVANCE_SCORE
        FROM SALES.SE_REPORTING.FREESTYLE_SUMMARY
        WHERE 
            LOWER(ARRAY_TO_STRING(SELF_ASSESMENT_SKILL_400, ',')) ILIKE '%' || ? || '%'
            OR LOWER(ARRAY_TO_STRING(SPECIALTIES, ',')) ILIKE '%' || ? || '%'
            OR LOWER(ARRAY_TO_STRING(CERT_EXTERNAL, ',')) ILIKE '%' || ? || '%'
            OR LOWER(ARRAY_TO_STRING(CERT_INTERNAL, ',')) ILIKE '%' || ? || '%'
            OR LOWER(NAME) ILIKE '%' || ? || '%'
        ORDER BY RELEVANCE_SCORE DESC, NAME
        """
        
        # Execute search with parameters
        result_df = execute_query(query, params=[search_terms_clean] * 10)
        return result_df
        
    except Exception as e:
        st.error(f"Error searching experts: {e}")
        return pd.DataFrame()

def get_expert_opportunities(expert_email):
    """Get opportunities where expert is Lead Sales Engineer"""
    try:
        query = """
        SELECT 
            o.NAME as OPPORTUNITY_NAME,
            a.NAME as ACCOUNT_NAME,
            a.INDUSTRY,
            o.STAGE_NAME,
            o.CLOSE_DATE,
            o.AMOUNT,
            o.PRIMARY_COMPETITOR_C
        FROM FIVETRAN.SALESFORCE.OPPORTUNITY o
        JOIN FIVETRAN.SALESFORCE.ACCOUNT a ON o.ACCOUNT_ID = a.ID
        JOIN FIVETRAN.SALESFORCE.USER u ON o.LEAD_SALES_ENGINEER_C = u.ID
        WHERE LOWER(u.EMAIL) = LOWER(?)
        ORDER BY o.CLOSE_DATE DESC
        LIMIT 20
        """
        
        return execute_query(query, params=[expert_email])
        
    except Exception as e:
        st.error(f"Error getting opportunities: {e}")
        return pd.DataFrame()
def extract_skills_from_row(row):
    """Extract and parse skills from a Freestyle row with proper JSON parsing"""
    import json
    
    skills = {
        'high_skills': [],
        'specialties': [],
        'certifications': []
    }
    
    # Parse high proficiency skills (JSON array)
    if pd.notna(row['SELF_ASSESMENT_SKILL_400']):
        try:
            high_skills_data = row['SELF_ASSESMENT_SKILL_400']
            if isinstance(high_skills_data, str):
                # Try to parse as JSON
                skills_list = json.loads(high_skills_data)
            else:
                # If it's already a list/array
                skills_list = high_skills_data
            
            if isinstance(skills_list, list):
                skills['high_skills'] = [str(skill).strip() for skill in skills_list if skill]
        except (json.JSONDecodeError, TypeError):
            # Fallback to old method if JSON parsing fails
            high_skills_str = str(row['SELF_ASSESMENT_SKILL_400'])
            skills['high_skills'] = [s.strip().strip('"\'[]') for s in high_skills_str.split(',') if s.strip()]
    
    # Parse specialties (JSON array)
    if pd.notna(row['SPECIALTIES']):
        try:
            specialties_data = row['SPECIALTIES']
            if isinstance(specialties_data, str):
                specialties_list = json.loads(specialties_data)
            else:
                specialties_list = specialties_data
            
            if isinstance(specialties_list, list):
                skills['specialties'] = [str(spec).strip() for spec in specialties_list if spec]
        except (json.JSONDecodeError, TypeError):
            # Fallback to old method
            specialties_str = str(row['SPECIALTIES'])
            skills['specialties'] = [s.strip().strip('"\'[]') for s in specialties_str.split(',') if s.strip()]
    
    # Parse certifications (combine external and internal JSON arrays)
    certifications = []
    
    # External certifications
    if pd.notna(row['CERT_EXTERNAL']):
        try:
            cert_data = row['CERT_EXTERNAL']
            if isinstance(cert_data, str):
                cert_list = json.loads(cert_data)
            else:
                cert_list = cert_data
            
            if isinstance(cert_list, list):
                certifications.extend([str(cert).strip() for cert in cert_list if cert])
        except (json.JSONDecodeError, TypeError):
            # Fallback
            ext_certs_str = str(row['CERT_EXTERNAL'])
            certifications.extend([s.strip().strip('"\'[]') for s in ext_certs_str.split(',') if s.strip()])
    
    # Internal certifications
    if pd.notna(row['CERT_INTERNAL']):
        try:
            cert_data = row['CERT_INTERNAL']
            if isinstance(cert_data, str):
                cert_list = json.loads(cert_data)
            else:
                cert_list = cert_data
            
            if isinstance(cert_list, list):
                certifications.extend([str(cert).strip() for cert in cert_list if cert])
        except (json.JSONDecodeError, TypeError):
            # Fallback
            int_certs_str = str(row['CERT_INTERNAL'])
            certifications.extend([s.strip().strip('"\'[]') for s in int_certs_str.split(',') if s.strip()])
    
    skills['certifications'] = certifications
    
    return skills
@st.dialog("Sales Engineer Profile", width="large")
def show_expert_modal(expert_row, opportunities_df):
    """Display expert details in an enhanced modal dialog"""
    expert_name = expert_row['NAME'] if pd.notna(expert_row['NAME']) else "Unknown Expert"
    expert_email = expert_row['EMAIL'] if pd.notna(expert_row['EMAIL']) else "No email"
    # Parse college from JSON array properly
    expert_college = "Not specified"
    if pd.notna(expert_row['COLLEGE']) and expert_row['COLLEGE']:
        try:
            import json
            college_data = expert_row['COLLEGE']
            if isinstance(college_data, str):
                college_list = json.loads(college_data)
            else:
                college_list = college_data
            
            if isinstance(college_list, list) and college_list:
                # Take the first college if multiple
                expert_college = str(college_list[0]).strip()
        except (json.JSONDecodeError, TypeError, IndexError):
            # Fallback to string parsing
            college_str = str(expert_row['COLLEGE'])
            expert_college = college_str.strip('[]').replace('"', '').replace("'", "").split(',')[0].strip()
    
    # Extract skills with improved JSON parsing
    skills = extract_skills_from_row(expert_row)
    
    # Header with gradient background
    st.markdown("""
    <div style='background: linear-gradient(90deg, #1e3c72 0%, #2a5298 100%); 
                padding: 20px; border-radius: 10px; margin-bottom: 20px;'>
        <h2 style='color: white; margin: 0; text-align: center;'>
            👤 """ + expert_name + """
        </h2>
    </div>
    """, unsafe_allow_html=True)
    
    # Contact and background info in cards
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        <div style='background: #f8f9fa; padding: 15px; border-radius: 8px; border-left: 4px solid #007bff;'>
            <h4 style='margin-top: 0; color: #007bff;'>📞 Contact Information</h4>
            <p><strong>Email:</strong> """ + expert_email + """</p>
            <p><strong>Education:</strong> """ + expert_college + """</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        # Show past employers if available
        employers_display = "No employers specified"
        
        # Debug: Show raw employers data (uncomment to debug)
        # if 'EMPLOYERS' in expert_row:
        #     st.write(f"DEBUG - Raw EMPLOYERS data: {repr(expert_row['EMPLOYERS'])}")
        #     st.write(f"DEBUG - Type: {type(expert_row['EMPLOYERS'])}")
        
        if pd.notna(expert_row.get('EMPLOYERS')) and expert_row.get('EMPLOYERS'):
            try:
                import json
                employers_data = expert_row['EMPLOYERS']
                
                # Handle different data formats
                if isinstance(employers_data, str):
                    # Try to parse as JSON first
                    try:
                        employers_list = json.loads(employers_data)
                    except json.JSONDecodeError:
                        # If not JSON, check if it's a single quoted value or comma-separated
                        if employers_data.startswith('"') and employers_data.endswith('"') and employers_data.count('"') == 2:
                            # Single quoted value
                            employers_list = [employers_data.strip('"')]
                        elif ',' in employers_data:
                            # Comma-separated values
                            employers_list = [emp.strip() for emp in employers_data.split(',') if emp.strip()]
                        else:
                            # Single unquoted value
                            employers_list = [employers_data.strip()]
                elif isinstance(employers_data, list):
                    employers_list = employers_data
                else:
                    # Convert to string and treat as single value
                    employers_list = [str(employers_data)]
                
                # Clean and format the employers list
                if employers_list and len(employers_list) > 0:
                    # Filter out empty strings and clean up formatting
                    clean_employers = []
                    for emp in employers_list:
                        emp_str = str(emp).strip().strip('[]').strip('"').strip("'").strip()
                        if emp_str and emp_str.lower() not in ['null', 'none', 'nan', '']:
                            clean_employers.append(emp_str)
                    
                    if clean_employers:
                        if len(clean_employers) <= 3:
                            employers_display = ", ".join(clean_employers)
                        else:
                            employers_display = ", ".join(clean_employers[:3]) + f" +{len(clean_employers) - 3} more"
                    
            except Exception as e:
                # Fallback: try to extract any meaningful text
                try:
                    employers_str = str(expert_row['EMPLOYERS'])
                    if employers_str and employers_str.lower() not in ['nan', 'none', 'null', '']:
                        # Clean up common JSON artifacts
                        cleaned = employers_str.strip('[]').replace('"', '').replace("'", "").replace('\\', '')
                        if cleaned and len(cleaned) > 2:
                            employers_display = cleaned[:100] + ("..." if len(cleaned) > 100 else "")
                except:
                    pass
        
        # Alternative: Check if there might be a differently named column
        alternative_columns = ['PREVIOUS_EMPLOYERS', 'PAST_EMPLOYERS', 'EMPLOYER_HISTORY', 'COMPANY_HISTORY']
        for alt_col in alternative_columns:
            if alt_col in expert_row and pd.notna(expert_row.get(alt_col)) and expert_row.get(alt_col):
                try:
                    alt_data = str(expert_row[alt_col])
                    if alt_data and alt_data.lower() not in ['nan', 'none', 'null', '']:
                        employers_display = f"From {alt_col}: {alt_data[:100]}"
                        break
                except:
                    pass
        
        st.markdown("""
        <div style='background: #f8f9fa; padding: 15px; border-radius: 8px; border-left: 4px solid #28a745;'>
            <h4 style='margin-top: 0; color: #28a745;'>💼 Professional Background</h4>
            <p><strong>Past Employers:</strong> """ + employers_display + """</p>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Skills overview with metrics
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("🎯 High Skills", len(skills['high_skills']))
    with col2:
        st.metric("🚀 Specialties", len(skills['specialties']))
    with col3:
        st.metric("🏅 Certifications", len(skills['certifications']))
    
    st.markdown("---")    # Skills sections with enhanced styling
    if skills['high_skills']:
        st.markdown("### 🎯 High Proficiency Skills")
        
        # Create skill pills with data sanitization
        skills_html = "<div style='margin-bottom: 15px;'>"
        for skill in skills['high_skills'][:20]:  # Show more skills
            # Sanitize the skill text
            clean_skill = str(skill).strip().replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')
            if clean_skill:  # Only add if not empty
                skills_html += f"""<span style='display: inline-block; background: linear-gradient(45deg, #667eea 0%, #764ba2 100%); color: white; padding: 6px 12px; margin: 3px; border-radius: 20px; font-size: 13px; font-weight: 500; box-shadow: 0 2px 4px rgba(0,0,0,0.1);'>{clean_skill}</span>"""
        skills_html += "</div>"
        st.markdown(skills_html, unsafe_allow_html=True)
    
    if skills['specialties']:
        st.markdown("### 🚀 Specialties")
        
        spec_html = "<div style='margin-bottom: 15px;'>"
        for spec in skills['specialties'][:15]:
            # Sanitize the specialty text
            clean_spec = str(spec).strip().replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')
            if clean_spec:  # Only add if not empty
                spec_html += f"""<span style='display: inline-block; background: linear-gradient(45deg, #f093fb 0%, #f5576c 100%); color: white; padding: 6px 12px; margin: 3px; border-radius: 20px; font-size: 13px; font-weight: 500; box-shadow: 0 2px 4px rgba(0,0,0,0.1);'>{clean_spec}</span>"""
        spec_html += "</div>"
        st.markdown(spec_html, unsafe_allow_html=True)
    
    if skills['certifications']:
        st.markdown("### 🏅 Certifications")
        
        cert_html = "<div style='margin-bottom: 15px;'>"
        for cert in skills['certifications'][:12]:
            # Sanitize the certification text
            clean_cert = str(cert).strip().replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')
            if clean_cert:  # Only add if not empty
                cert_html += f"""<span style='display: inline-block; background: linear-gradient(45deg, #ffecd2 0%, #fcb69f 100%); color: #8b5a2b; padding: 6px 12px; margin: 3px; border-radius: 20px; font-size: 13px; font-weight: 500; box-shadow: 0 2px 4px rgba(0,0,0,0.1);'>{clean_cert}</span>"""
        cert_html += "</div>"
        st.markdown(cert_html, unsafe_allow_html=True)

def get_context_opportunities(expert_email, competitor=None):
    """Get opportunities based on search context"""
    try:
        if competitor:
            # If searching by competitor, find opportunities against that competitor
            query = """
            SELECT 
                o.NAME as OPPORTUNITY_NAME,
                a.NAME as ACCOUNT_NAME,
                a.INDUSTRY,
                o.STAGE_NAME,
                o.CLOSE_DATE,
                o.AMOUNT,
                o.PRIMARY_COMPETITOR_C
            FROM FIVETRAN.SALESFORCE.OPPORTUNITY o
            JOIN FIVETRAN.SALESFORCE.ACCOUNT a ON o.ACCOUNT_ID = a.ID
            JOIN FIVETRAN.SALESFORCE.USER u ON o.LEAD_SALES_ENGINEER_C = u.ID
            WHERE LOWER(u.EMAIL) = LOWER(?)
                AND UPPER(o.PRIMARY_COMPETITOR_C) ILIKE '%' || UPPER(?) || '%'
                AND o.NAME IS NOT NULL
            ORDER BY o.CLOSE_DATE DESC
            LIMIT 5
            """
            return execute_query(query, params=[expert_email, competitor])
        else:
            # Default: get 5 most recent opportunities as Lead SE
            query = """
            SELECT 
                o.NAME as OPPORTUNITY_NAME,
                a.NAME as ACCOUNT_NAME,
                a.INDUSTRY,
                o.STAGE_NAME,
                o.CLOSE_DATE,
                o.AMOUNT,
                o.PRIMARY_COMPETITOR_C
            FROM FIVETRAN.SALESFORCE.OPPORTUNITY o
            JOIN FIVETRAN.SALESFORCE.ACCOUNT a ON o.ACCOUNT_ID = a.ID
            JOIN FIVETRAN.SALESFORCE.USER u ON o.LEAD_SALES_ENGINEER_C = u.ID
            WHERE LOWER(u.EMAIL) = LOWER(?)
                AND o.NAME IS NOT NULL
            ORDER BY o.CLOSE_DATE DESC
            LIMIT 5
            """
            return execute_query(query, params=[expert_email])
    except Exception as e:
        return pd.DataFrame()

# Main content tabs
tab1, tab2 = st.tabs(["Expert Search", "👥 SE Directory"])

with tab1:
    # Search interface
    st.markdown("**Enter skills, technologies, or expertise areas:**")
    col1, col2 = st.columns([3, 1])
    
    # Check if a suggestion was clicked
    selected_suggestion = None
    for key in st.session_state.keys():
        if key.startswith("suggest_clicked_") and st.session_state[key]:
            selected_suggestion = st.session_state[key]
            # Clear the flag
            st.session_state[key] = None
            break
    
    with col1:
        # Use the selected suggestion as default value if available
        default_value = selected_suggestion if selected_suggestion else ""
        search_value = st.text_input(
            "Search input",
            value=default_value,
            placeholder="e.g., Python, Machine Learning, AWS, Healthcare",
            key="freestyle_search",
            label_visibility="collapsed"
        )
    
    with col2:
        search_button = st.button("🔍 Search Experts", type="primary", use_container_width=True)
    
    # Quick search buttons - minimalist design
    st.caption("🎯 Quick search:")
    suggestion_cols = st.columns(5)
    suggestions = ["Databricks", "Microsoft", "AWS", "Oracle", "Salesforce"]
    
    for i, suggestion in enumerate(suggestions):
        with suggestion_cols[i % 5]:
            if st.button(f"{suggestion}", key=f"suggest_{i}", use_container_width=True):
                # Set a flag that will be picked up on next run
                st.session_state[f"suggest_clicked_{i}"] = suggestion
                st.rerun()    
    # Set default search parameters
    min_relevance = 10  # Lower threshold for broader results
    
    # Search execution
    if (search_button and search_value) or selected_suggestion:
        with st.spinner("Searching Freestyle Summary for experts..."):
            experts_df = search_freestyle_experts(selected_suggestion or search_value)            
            if not experts_df.empty:
                # Filter by relevance and sort by relevance score descending
                display_df = experts_df[experts_df['RELEVANCE_SCORE'] >= min_relevance].sort_values('RELEVANCE_SCORE', ascending=False)
                
                st.success(f"Found {len(display_df)} experts matching '{selected_suggestion or search_value}'")
                
                # Display results
                for idx, expert in display_df.iterrows():
                    with st.expander(f"⭐ {expert['NAME']} - Relevance: {expert['RELEVANCE_SCORE']}", expanded=False):
                        # Basic info
                        st.write(f"**📧 Email:** {expert['EMAIL']}")
                        
                        # Parse and display college properly
                        if pd.notna(expert['COLLEGE']) and expert['COLLEGE']:
                            college_display = "Not specified"
                            try:
                                import json
                                college_data = expert['COLLEGE']
                                if isinstance(college_data, str):
                                    college_list = json.loads(college_data)
                                else:
                                    college_list = college_data
                                
                                if isinstance(college_list, list) and college_list:
                                    college_display = str(college_list[0]).strip()
                            except (json.JSONDecodeError, TypeError, IndexError):
                                # Fallback to string parsing
                                college_str = str(expert['COLLEGE'])
                                college_display = college_str.strip('[]').replace('"', '').replace("'", "").split(',')[0].strip()
                            
                            if college_display != "Not specified":
                                st.write(f"**🎓 College:** {college_display}")
                        
                        # Skills preview
                        skills = extract_skills_from_row(expert)
                        if skills['high_skills']:
                            st.write("**🎯 Top Skills:**")
                            skills_preview = ', '.join(skills['high_skills'][:5])
                            if len(skills['high_skills']) > 5:
                                skills_preview += f" (+{len(skills['high_skills'])-5} more)"
                            st.caption(skills_preview)
            else:
                st.info("No experts found. Try different search terms.")
    

with tab2:
    st.header("Sales Engineer Directory")
    st.markdown("Browse all sales engineers with detailed profiles and opportunity history")
    
    # Get all SEs from Freestyle Summary
    with st.spinner("Loading sales engineer directory..."):
        try:
            all_ses_query = """
            SELECT 
                USER_ID,
                NAME,
                EMAIL,
                COLLEGE,
                EMPLOYERS,
                SELF_ASSESMENT_SKILL_400,
                SPECIALTIES,
                CERT_EXTERNAL,
                CERT_INTERNAL
            FROM SALES.SE_REPORTING.FREESTYLE_SUMMARY
            WHERE NAME IS NOT NULL
            ORDER BY NAME
            """
            
            all_ses_df = execute_query(all_ses_query)
            if not all_ses_df.empty:
                # Store SE data in session state for modal access
                if 'directory_data' not in st.session_state:
                    st.session_state.directory_data = all_ses_df
                
                # Prepare display data with proper college parsing
                display_data = []
                colleges_set = set()
                for _, se_row in all_ses_df.iterrows():
                    se_name = se_row['NAME'] if pd.notna(se_row['NAME']) else "Unknown"
                    se_email = se_row['EMAIL'] if pd.notna(se_row['EMAIL']) else "No email"
                    
                    # Parse college from JSON array
                    se_college = "Not specified"
                    if pd.notna(se_row['COLLEGE']) and se_row['COLLEGE']:
                        try:
                            import json
                            college_data = se_row['COLLEGE']
                            if isinstance(college_data, str):
                                college_list = json.loads(college_data)
                            else:
                                college_list = college_data
                            
                            if isinstance(college_list, list) and college_list:
                                # Take the first college if multiple
                                se_college = str(college_list[0]).strip()
                        except (json.JSONDecodeError, TypeError, IndexError):
                            # Fallback to string parsing
                            college_str = str(se_row['COLLEGE'])
                            se_college = college_str.strip('[]').replace('"', '').replace("'", "").split(',')[0].strip()
                    
                    colleges_set.add(se_college)
                    
                    # Count skills
                    skills = extract_skills_from_row(se_row)
                    total_skills = len(skills['high_skills']) + len(skills['specialties']) + len(skills['certifications'])
                    
                    display_data.append({
                        'Name': se_name,
                        'Email': se_email,
                        'College': se_college,
                        'Total Skills': total_skills,
                        'USER_ID': se_row['USER_ID']  # Hidden for selection
                    })
                
                # Create filters
                col1, col2 = st.columns(2)
                
                with col1:
                    # Search filter
                    search_term = st.text_input(
                        "🔍 Search by name, email, or college:",
                        placeholder="Type to filter results...",
                        key="se_directory_search"
                    )
                
                with col2:
                    # College filter
                    sorted_colleges = sorted([c for c in colleges_set if c and c != "Not specified"]) + ["Not specified"]
                    selected_college = st.selectbox(
                        "🎓 Filter by college:",
                        ["All Colleges"] + sorted_colleges,
                        key="se_directory_college_filter"
                    )
                
                # Apply filters
                filtered_data = display_data.copy()
                
                # Apply search filter
                if search_term:
                    search_lower = search_term.lower()
                    filtered_data = [
                        row for row in filtered_data 
                        if search_lower in row['Name'].lower() 
                        or search_lower in row['Email'].lower() 
                        or search_lower in row['College'].lower()
                    ]
                
                # Apply college filter
                if selected_college != "All Colleges":
                    filtered_data = [row for row in filtered_data if row['College'] == selected_college]
                
                # Create and display table
                if filtered_data:
                    table_df = pd.DataFrame(filtered_data)
                    
                    # Show filter results
                    total_count = len(display_data)
                    filtered_count = len(filtered_data)
                    
                    if filtered_count != total_count:
                        st.subheader(f"👥 Sales Engineers ({filtered_count} of {total_count} total)")
                    else:
                        st.subheader(f"👥 Sales Engineers ({total_count} total)")
                    
                    st.markdown("*Click on any row to view detailed profile instantly*")
                    
                    # Display table with proper event handling
                    event = st.dataframe(
                        table_df.drop('USER_ID', axis=1),  # Hide the USER_ID column
                        use_container_width=True,
                        height=500,
                        hide_index=True,
                        on_select="rerun",  # Use rerun for proper event handling
                        selection_mode="single-row"
                    )
                    
                    # Handle row selection with instant modal
                    if hasattr(event, 'selection') and event.selection and hasattr(event.selection, 'rows') and event.selection.rows:
                        selected_row_idx = event.selection.rows[0]
                        selected_user_id = filtered_data[selected_row_idx]['USER_ID']
                        
                        # Show modal immediately - no waiting for DB calls
                        if 'last_selected_user' not in st.session_state or st.session_state.last_selected_user != selected_user_id:
                            st.session_state.last_selected_user = selected_user_id
                            
                            # Find the selected expert's data from cached results
                            selected_expert_data = st.session_state.directory_data[st.session_state.directory_data['USER_ID'] == selected_user_id]
                            if not selected_expert_data.empty:
                                expert_row = selected_expert_data.iloc[0]
                                
                                # Show modal immediately with expert details (no opportunities needed)
                                show_expert_modal(expert_row, pd.DataFrame())
                else:
                    if search_term or selected_college != "All Colleges":
                        st.info("No sales engineers match your current filters. Try adjusting your search terms or college selection.")
                    else:
                        st.info("No sales engineers found in the directory")
            else:
                st.error("Could not load sales engineer directory")                
        except Exception as e:
            st.error(f"Error loading directory: {e}")

# Footer
st.markdown("---")
st.markdown("**🔍 Expert Hub** | Find and connect with internal experts") 