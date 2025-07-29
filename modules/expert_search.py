# Expert Search Module
# Expert finding logic, relevance scoring, and Salesforce opportunity analysis for Streamlit in Snowflake

import streamlit as st
import pandas as pd
import re
from datetime import datetime, timedelta
from modules.snowflake_utils import execute_query, get_salesforce_opportunities, get_freestyle_skills_data

@st.cache_data(ttl=300)
def search_freestyle_experts(search_terms):
    """Search for experts in Freestyle data based on skills and specialties"""
    if not search_terms:
        return {}
    
    try:
        # Normalize search terms
        search_terms_clean = re.sub(r'[^\w\s]', '', search_terms.lower())
        
        if len(search_terms_clean.strip()) < 2:
            return {}
        
        # Build flexible search query for Freestyle Summary
        query = """
        SELECT 
            NAME, 
            EMAIL,
            COLLEGE,
            EMPLOYERS,
            SELF_ASSESMENT_SKILL_400 as skills,
            SPECIALTIES,
            CASE 
                WHEN UPPER(SELF_ASSESMENT_SKILL_400) LIKE UPPER(?)
                     OR UPPER(SPECIALTIES) LIKE UPPER(?)
                     OR UPPER(NAME) LIKE UPPER(?) THEN 10
                WHEN UPPER(SELF_ASSESMENT_SKILL_400) LIKE UPPER(?)
                     OR UPPER(SPECIALTIES) LIKE UPPER(?)
                     OR UPPER(NAME) LIKE UPPER(?) THEN 8
                WHEN UPPER(SELF_ASSESMENT_SKILL_400) LIKE UPPER(?)
                     OR UPPER(SPECIALTIES) LIKE UPPER(?)
                     OR UPPER(NAME) LIKE UPPER(?) THEN 6
                ELSE 5
            END as relevance_score
        FROM SALES.SE_REPORTING.FREESTYLE_SUMMARY
        WHERE (UPPER(SELF_ASSESMENT_SKILL_400) LIKE UPPER(?)
               OR UPPER(SPECIALTIES) LIKE UPPER(?)
               OR UPPER(NAME) LIKE UPPER(?))
              AND NAME IS NOT NULL
              AND EMAIL IS NOT NULL
        ORDER BY relevance_score DESC, NAME ASC
        """
        
        # Create search patterns
        exact_pattern = f"%{search_terms_clean}%"
        params = [search_terms_clean] * 10  # For exact matches
        params.extend([search_terms_clean] * 2)  # For WHERE clause
        
        df = execute_query(query, params)
        
        if df.empty:
            return {}
        
        # Process results
        experts = {}
        for _, row in df.iterrows():
            expert_name = row['NAME']
            expert_email = row['EMAIL']
            relevance = row['relevance_score']
            
            # Parse skills safely
            skills = []
            if pd.notna(row['skills']) and row['skills']:
                skills_text = str(row['skills'])
                skills = [s.strip() for s in skills_text.split(',') if s.strip()]
            
            # Parse specialties safely  
            specialties = []
            if pd.notna(row['SPECIALTIES']) and row['SPECIALTIES']:
                specialties_text = str(row['SPECIALTIES'])
                specialties = [s.strip() for s in specialties_text.split(',') if s.strip()]
            
            experts[expert_email] = {
                'name': expert_name,
                'email': expert_email,
                'skills': skills,
                'specialties': specialties,
                'relevance_score': relevance,
                'college': row.get('COLLEGE', ''),
                'employers': row.get('EMPLOYERS', '')
            }
        
        return experts
        
    except Exception as e:
        st.error(f"Error searching experts: {e}")
        return {}

@st.cache_data(ttl=300)
def search_salesforce_experts(search_terms):
    """Search for experts based on Salesforce opportunity data"""
    if not search_terms:
        return {}
    
    try:
        # Convert search terms to list if string
        if isinstance(search_terms, str):
            terms = [term.strip() for term in search_terms.split(',')]
        else:
            terms = search_terms
        
        # Get opportunities that match search criteria
        opportunities_df = pd.DataFrame()
        
        for term in terms:
            if len(term.strip()) >= 2:
                # Search in opportunity descriptions, account names, industries
                query = """
                SELECT 
                    o.ID as opportunity_id,
                    o.NAME as opportunity_name,
                    o.ACCOUNT_ID,
                    a.NAME as account_name,
                    o.AMOUNT,
                    o.STAGE_NAME as stage,
                    o.CLOSE_DATE,
                    o.DESCRIPTION,
                    a.INDUSTRY,
                    a.WEBSITE,
                    o.OWNER_ID,
                    u.NAME as owner_name,
                    u.EMAIL as owner_email
                FROM FIVETRAN.SALESFORCE.OPPORTUNITY o
                LEFT JOIN FIVETRAN.SALESFORCE.ACCOUNT a ON o.ACCOUNT_ID = a.ID
                LEFT JOIN FIVETRAN.SALESFORCE.USER u ON o.OWNER_ID = u.ID
                WHERE o.IS_DELETED = FALSE
                AND (UPPER(o.NAME) LIKE UPPER(?) OR
                     UPPER(o.DESCRIPTION) LIKE UPPER(?) OR
                     UPPER(a.NAME) LIKE UPPER(?) OR
                     UPPER(a.INDUSTRY) LIKE UPPER(?))
                ORDER BY o.CLOSE_DATE DESC
                LIMIT 200
                """
                
                term_pattern = f"%{term.strip()}%"
                df = execute_query(query, [term_pattern, term_pattern, term_pattern, term_pattern])
                opportunities_df = pd.concat([opportunities_df, df], ignore_index=True)
        
        # Remove duplicates
        opportunities_df = opportunities_df.drop_duplicates(subset=['opportunity_id'])
        
        # Group by owner to create expert profiles
        experts = {}
        for _, row in opportunities_df.iterrows():
            if pd.isna(row['owner_email']) or not row['owner_email']:
                continue
                
            expert_id = row['owner_email']
            
            if expert_id not in experts:
                experts[expert_id] = {
                    'name': row['owner_name'] or 'Unknown',
                    'email': row['owner_email'],
                    'skills': {'specialties': [], 'high_proficiency': []},
                    'opportunities': [],
                    'industries': set(),
                    'relevance_score': 0
                }
            
            # Add opportunity
            experts[expert_id]['opportunities'].append({
                'id': row['opportunity_id'],
                'name': row['opportunity_name'],
                'account': row['account_name'],
                'amount': row['AMOUNT'] or 0,
                'stage': row['stage'],
                'close_date': row['CLOSE_DATE'],
                'industry': row['INDUSTRY']
            })
            
            # Add industry
            if row['INDUSTRY']:
                experts[expert_id]['industries'].add(row['INDUSTRY'])
        
        # Calculate relevance scores based on opportunities
        for expert_id, expert in experts.items():
            expert['relevance_score'] = min(100, len(expert['opportunities']) * 10 + len(expert['industries']) * 5)
            expert['industries'] = list(expert['industries'])
        
        return experts
        
    except Exception as e:
        st.error(f"Error searching Salesforce experts: {e}")
        return {}

def calculate_skill_relevance(row, search_terms):
    """Calculate relevance score based on skill matches"""
    try:
        total_score = 0
        max_score = len(search_terms) * 100  # Maximum possible score
        
        # Convert arrays to strings for searching
        skill_text = ""
        
        # High-value skills (higher weight)
        if row.get('SELF_ASSESMENT_SKILL_400'):
            skill_text += " " + str(row['SELF_ASSESMENT_SKILL_400']).upper()
        if row.get('MGR_SCORE_SKILL_400'):
            skill_text += " " + str(row['MGR_SCORE_SKILL_400']).upper()
        
        # Medium-value skills
        if row.get('SELF_ASSESMENT_SKILL_300'):
            skill_text += " " + str(row['SELF_ASSESMENT_SKILL_300']).upper()
        if row.get('MGR_SCORE_SKILL_300'):
            skill_text += " " + str(row['MGR_SCORE_SKILL_300']).upper()
        
        # Specialties (highest weight)
        if row.get('SPECIALTIES'):
            skill_text += " " + str(row['SPECIALTIES']).upper() * 2  # Double weight
        
        # Certifications
        if row.get('CERT_EXTERNAL'):
            skill_text += " " + str(row['CERT_EXTERNAL']).upper()
        if row.get('CERT_INTERNAL'):
            skill_text += " " + str(row['CERT_INTERNAL']).upper()
        
        # Calculate matches
        for term in search_terms:
            if term.upper() in skill_text:
                total_score += 100
        
        # Normalize to percentage
        relevance = min(100, int((total_score / max_score) * 100)) if max_score > 0 else 0
        return max(relevance, 20)  # Minimum 20% for any match
        
    except Exception:
        return 50  # Default relevance

def extract_freestyle_skills(row):
    """Extract skills from Freestyle data row"""
    skills = {
        'high_proficiency': [],
        'medium_proficiency': [],
        'specialties': [],
        'certifications': []
    }
    
    try:
        # High proficiency skills
        if row.get('SELF_ASSESMENT_SKILL_400'):
            skills['high_proficiency'].extend(parse_skill_array(row['SELF_ASSESMENT_SKILL_400']))
        if row.get('MGR_SCORE_SKILL_400'):
            skills['high_proficiency'].extend(parse_skill_array(row['MGR_SCORE_SKILL_400']))
        
        # Medium proficiency skills
        if row.get('SELF_ASSESMENT_SKILL_300'):
            skills['medium_proficiency'].extend(parse_skill_array(row['SELF_ASSESMENT_SKILL_300']))
        if row.get('MGR_SCORE_SKILL_300'):
            skills['medium_proficiency'].extend(parse_skill_array(row['MGR_SCORE_SKILL_300']))
        
        # Specialties
        if row.get('SPECIALTIES'):
            skills['specialties'].extend(parse_skill_array(row['SPECIALTIES']))
        
        # Certifications
        certs = []
        if row.get('CERT_EXTERNAL'):
            certs.extend(parse_skill_array(row['CERT_EXTERNAL']))
        if row.get('CERT_INTERNAL'):
            certs.extend(parse_skill_array(row['CERT_INTERNAL']))
        skills['certifications'] = certs
        
        # Remove duplicates and clean up
        for key in skills:
            skills[key] = list(set([s.strip() for s in skills[key] if s.strip()]))
        
    except Exception as e:
        st.warning(f"Error parsing skills: {e}")
    
    return skills

def parse_skill_array(skill_data):
    """Parse skill array data from Snowflake"""
    if not skill_data:
        return []
    
    try:
        # Handle different data types
        if isinstance(skill_data, list):
            return skill_data
        elif isinstance(skill_data, str):
            # Remove array brackets and split by comma
            cleaned = skill_data.strip('[]"\'')
            if ',' in cleaned:
                return [s.strip().strip('"\'') for s in cleaned.split(',')]
            else:
                return [cleaned] if cleaned else []
        else:
            return [str(skill_data)]
    except Exception:
        return []

@st.cache_data(ttl=600)
def get_all_sales_engineers():
    """Get all Sales Engineers with their information"""
    try:
        return get_freestyle_skills_data()
    except Exception as e:
        st.error(f"Error querying Sales Engineer data: {str(e)}")
        return pd.DataFrame()

def extract_se_skills(row):
    """Extract skills for SE Directory display"""
    skills = {
        'high_skills': [],
        'medium_skills': [],
        'specialties': [],
        'certifications': []
    }
    
    try:
        # Extract high proficiency skills
        if row.get('SELF_ASSESMENT_SKILL_400'):
            skills['high_skills'] = parse_skill_array(row['SELF_ASSESMENT_SKILL_400'])
        
        # Extract medium proficiency skills  
        if row.get('SELF_ASSESMENT_SKILL_300'):
            skills['medium_skills'] = parse_skill_array(row['SELF_ASSESMENT_SKILL_300'])
        
        # Extract specialties
        if row.get('SPECIALTIES'):
            skills['specialties'] = parse_skill_array(row['SPECIALTIES'])
        
        # Extract certifications
        certs = []
        if row.get('CERT_EXTERNAL'):
            certs.extend(parse_skill_array(row['CERT_EXTERNAL']))
        if row.get('CERT_INTERNAL'):
            certs.extend(parse_skill_array(row['CERT_INTERNAL']))
        skills['certifications'] = certs
        
    except Exception as e:
        st.warning(f"Error extracting SE skills: {e}")
    
    return skills

def find_experts_for_company(company_website, search_terms):
    """Find experts relevant to a specific company and technologies"""
    if not search_terms:
        return {}
    
    try:
        # Combine freestyle and Salesforce expert searches
        freestyle_experts = search_freestyle_experts(search_terms)
        salesforce_experts = search_salesforce_experts(search_terms)
        
        # Merge experts from both sources
        all_experts = freestyle_experts.copy()
        
        for expert_id, expert_data in salesforce_experts.items():
            if expert_id in all_experts:
                # Merge data from both sources
                all_experts[expert_id]['opportunities'].extend(expert_data.get('opportunities', []))
                all_experts[expert_id]['industries'].update(expert_data.get('industries', []))
                # Use higher relevance score
                all_experts[expert_id]['relevance_score'] = max(
                    all_experts[expert_id]['relevance_score'],
                    expert_data.get('relevance_score', 0)
                )
            else:
                all_experts[expert_id] = expert_data
        
        # Sort by relevance score
        sorted_experts = dict(sorted(all_experts.items(), 
                                   key=lambda x: x[1].get('relevance_score', 0), 
                                   reverse=True))
        
        return sorted_experts
        
    except Exception as e:
        st.error(f"Error finding experts for company: {e}")
        return {}

@st.cache_data(ttl=300)
def get_top_industries():
    """Get top industries from Salesforce account data"""
    try:
        query = """
        SELECT 
            INDUSTRY,
            COUNT(*) as account_count
        FROM FIVETRAN.SALESFORCE.ACCOUNT
        WHERE INDUSTRY IS NOT NULL
        AND IS_DELETED = FALSE
        GROUP BY INDUSTRY
        ORDER BY account_count DESC
        LIMIT 20
        """
        
        return execute_query(query)
    except Exception as e:
        st.error(f"Error getting top industries: {e}")
        return pd.DataFrame()

def get_expert_opportunities(expert_email, limit=10):
    """Get recent opportunities for a specific expert"""
    if not expert_email:
        return pd.DataFrame()
    
    try:
        query = """
        SELECT 
            o.ID as opportunity_id,
            o.NAME as opportunity_name,
            o.ACCOUNT_ID,
            a.NAME as account_name,
            o.AMOUNT,
            o.STAGE_NAME as stage,
            o.CLOSE_DATE,
            o.DESCRIPTION,
            a.INDUSTRY,
            a.WEBSITE
        FROM FIVETRAN.SALESFORCE.OPPORTUNITY o
        LEFT JOIN FIVETRAN.SALESFORCE.ACCOUNT a ON o.ACCOUNT_ID = a.ID
        LEFT JOIN FIVETRAN.SALESFORCE.USER u ON o.OWNER_ID = u.ID
        WHERE u.EMAIL = ?
        AND o.IS_DELETED = FALSE
        ORDER BY o.CLOSE_DATE DESC
        LIMIT ?
        """
        
        return execute_query(query, [expert_email, limit])
    except Exception as e:
        st.error(f"Error getting expert opportunities: {e}")
        return pd.DataFrame()

def search_competitive_experience(competitor_name):
    """Search for experts with competitive experience"""
    if not competitor_name:
        return {}
    
    try:
        # Search opportunities with competitor mentions
        query = """
        SELECT 
            o.ID as opportunity_id,
            o.NAME as opportunity_name,
            o.ACCOUNT_ID,
            a.NAME as account_name,
            o.AMOUNT,
            o.STAGE_NAME as stage,
            o.CLOSE_DATE,
            o.DESCRIPTION,
            a.INDUSTRY,
            u.NAME as owner_name,
            u.EMAIL as owner_email
        FROM FIVETRAN.SALESFORCE.OPPORTUNITY o
        LEFT JOIN FIVETRAN.SALESFORCE.ACCOUNT a ON o.ACCOUNT_ID = a.ID
        LEFT JOIN FIVETRAN.SALESFORCE.USER u ON o.OWNER_ID = u.ID
        WHERE o.IS_DELETED = FALSE
        AND (UPPER(o.DESCRIPTION) LIKE UPPER(?) OR 
             UPPER(o.NAME) LIKE UPPER(?))
        AND u.EMAIL IS NOT NULL
        ORDER BY o.CLOSE_DATE DESC
        LIMIT 100
        """
        
        competitor_pattern = f"%{competitor_name}%"
        df = execute_query(query, [competitor_pattern, competitor_pattern])
        
        # Group by expert
        experts = {}
        for _, row in df.iterrows():
            expert_id = row['owner_email']
            
            if expert_id not in experts:
                experts[expert_id] = {
                    'name': row['owner_name'],
                    'email': row['owner_email'],
                    'competitive_opportunities': [],
                    'relevance_score': 0
                }
            
            experts[expert_id]['competitive_opportunities'].append({
                'opportunity_name': row['opportunity_name'],
                'account_name': row['account_name'],
                'stage': row['stage'],
                'amount': row['AMOUNT'] or 0,
                'close_date': row['CLOSE_DATE'],
                'industry': row['INDUSTRY']
            })
        
        # Calculate relevance scores
        for expert_id, expert in experts.items():
            expert['relevance_score'] = min(100, len(expert['competitive_opportunities']) * 20)
        
        return experts
        
    except Exception as e:
        st.error(f"Error searching competitive experience: {e}")
        return {} 