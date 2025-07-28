# Snowflake Utilities Module
# Database connections and basic data functions for Streamlit in Snowflake

import streamlit as st
import pandas as pd
import time

# Try to import Snowpark - only available in Streamlit in Snowflake
try:
    from snowflake.snowpark.context import get_active_session
    SNOWPARK_AVAILABLE = True
except ImportError:
    SNOWPARK_AVAILABLE = False

# Global flag to prevent queries during startup
_APP_FULLY_LOADED = False

# Singleton connection to prevent concurrent queries
_GLOBAL_CONNECTION = None
_CONNECTION_LOCK = False

def mark_app_loaded():
    """Mark the app as fully loaded - call this after page config"""
    global _APP_FULLY_LOADED
    _APP_FULLY_LOADED = True

def get_connection():
    """Get Snowflake connection - optimized for Streamlit in Snowflake environment"""
    global _GLOBAL_CONNECTION, _CONNECTION_LOCK
    
    try:
        if _GLOBAL_CONNECTION is None:
            if SNOWPARK_AVAILABLE:
                # In SiS environment, reuse the active session aggressively
                session = get_active_session()
                _GLOBAL_CONNECTION = {'type': 'snowpark', 'session': session}
            else:
                # Fallback for local development (should not be used in production)
                conn = st.connection("snowflake", ttl=3600)
                _GLOBAL_CONNECTION = {'type': 'streamlit', 'connection': conn}
                
        return _GLOBAL_CONNECTION
        
    except Exception as e:
        st.error(f"Failed to connect to Snowflake: {e}")
        st.error("Make sure you're running in Streamlit in Snowflake environment")
        st.stop()

def execute_query(query, params=None, max_retries=3):
    """Execute query optimized for Streamlit in Snowflake environment"""
    
    # Prevent queries until app is fully loaded
    if not _APP_FULLY_LOADED:
        return pd.DataFrame()
    
    for attempt in range(max_retries):
        try:
            conn_info = get_connection()
            
            if conn_info['type'] == 'snowpark':
                # Preferred path for SiS environment
                session = conn_info['session']
                if params:
                    result = session.sql(query, params).to_pandas()
                else:
                    result = session.sql(query).to_pandas()
            else:
                # Fallback for local development
                conn = conn_info['connection']
                if params:
                    result = conn.query(query, params=params, ttl=0)
                else:
                    result = conn.query(query, ttl=0)
            
            return result
            
        except Exception as e:
            error_msg = str(e).lower()
            
            if "concurrent queries" in error_msg or "exceeded" in error_msg or "limit" in error_msg:
                if attempt < max_retries - 1:
                    # Shorter wait for SiS environment
                    wait_time = 1 + attempt  # 1, 2, 3 seconds
                    import time
                    time.sleep(wait_time)
                    
                    # Reset connection for retry in SiS
                    global _GLOBAL_CONNECTION
                    _GLOBAL_CONNECTION = None
                    continue
                else:
                    st.error("🚫 Database temporarily busy. Please try again.")
                    return pd.DataFrame()
            else:
                st.error(f"Query execution failed: {e}")
                return pd.DataFrame()
    return pd.DataFrame()

def execute_expert_query(query):
    """Execute query using the appropriate connection method - legacy function"""
    return execute_query(query)

# Salesforce Data Access Functions (using Fivetran tables in Snowflake)

def get_salesforce_opportunities(account_name=None, limit=100):
    """Get Salesforce opportunities from Fivetran tables"""
    try:
        base_query = """
        SELECT 
            o.ID as opportunity_id,
            o.NAME as opportunity_name,
            o.ACCOUNT_ID,
            a.NAME as account_name,
            o.AMOUNT,
            o.STAGE_NAME as stage,
            o.CLOSE_DATE,
            o.PROBABILITY,
            o.TYPE as opportunity_type,
            o.LEAD_SOURCE,
            o.DESCRIPTION,
            a.INDUSTRY,
            a.WEBSITE,
            a.BILLING_CITY,
            a.BILLING_STATE,
            a.BILLING_COUNTRY
        FROM FIVETRAN.SALESFORCE.OPPORTUNITY o
        LEFT JOIN FIVETRAN.SALESFORCE.ACCOUNT a ON o.ACCOUNT_ID = a.ID
        WHERE o.IS_DELETED = FALSE
        """
        
        if account_name:
            base_query += " AND UPPER(a.NAME) LIKE UPPER(?)"
            params = [f"%{account_name}%"]
        else:
            params = None
            
        base_query += f" ORDER BY o.CLOSE_DATE DESC LIMIT {limit}"
        
        return execute_query(base_query, params)
    except Exception as e:
        st.error(f"Error querying Salesforce opportunities: {e}")
        return pd.DataFrame()

def get_salesforce_accounts(search_term=None, limit=100):
    """Get Salesforce accounts from Fivetran tables"""
    try:
        base_query = """
        SELECT 
            ID as account_id,
            NAME as account_name,
            WEBSITE,
            INDUSTRY,
            TYPE as account_type,
            BILLING_CITY,
            BILLING_STATE,
            BILLING_COUNTRY,
            ANNUAL_REVENUE,
            NUMBER_OF_EMPLOYEES
        FROM FIVETRAN.SALESFORCE.ACCOUNT
        WHERE IS_DELETED = FALSE
        """
        
        if search_term:
            base_query += " AND (UPPER(NAME) LIKE UPPER(?) OR UPPER(WEBSITE) LIKE UPPER(?))"
            params = [f"%{search_term}%", f"%{search_term}%"]
        else:
            params = None
            
        base_query += f" ORDER BY NAME LIMIT {limit}"
        
        return execute_query(base_query, params)
    except Exception as e:
        st.error(f"Error querying Salesforce accounts: {e}")
        return pd.DataFrame()

def search_salesforce_accounts_live(search_term, limit=20):
    """Enhanced search for Salesforce accounts with comprehensive fields"""
    if not search_term or len(search_term) < 2:
        return pd.DataFrame()
    
    try:
        query = """
        SELECT 
            ID as ACCOUNT_ID,
            NAME as ACCOUNT_NAME,
            WEBSITE,
            INDUSTRY,
            BILLING_CITY,
            TYPE,
            NUMBER_OF_EMPLOYEES
        FROM FIVETRAN.SALESFORCE.ACCOUNT
        WHERE IS_DELETED = FALSE
        AND UPPER(NAME) LIKE UPPER(?)
        ORDER BY NAME ASC
        LIMIT ?
        """
        params = [f"%{search_term}%", limit]
        return execute_query(query, params)
    except Exception as e:
        st.error(f"Error in live search: {e}")
        return pd.DataFrame()

def get_salesforce_account_by_id(account_id):
    """Get a specific Salesforce account by its ID"""
    if not account_id:
        return pd.DataFrame()
    
    try:
        query = """
        SELECT 
            ID as account_id,
            NAME as account_name,
            WEBSITE,
            INDUSTRY,
            TYPE as account_type,
            BILLING_CITY,
            BILLING_STATE,
            BILLING_COUNTRY,
            ANNUAL_REVENUE,
            NUMBER_OF_EMPLOYEES,
            DESCRIPTION
        FROM FIVETRAN.SALESFORCE.ACCOUNT
        WHERE ID = ? AND IS_DELETED = FALSE
        """
        
        return execute_query(query, [account_id])
    except Exception as e:
        st.error(f"Error querying Salesforce account: {e}")
        return pd.DataFrame()

def search_accounts_by_domain(domain):
    """Search for Salesforce accounts by website domain"""
    if not domain:
        return pd.DataFrame()
    
    try:
        # Clean the domain (remove http/https, www)
        clean_domain = domain.replace('http://', '').replace('https://', '').replace('www.', '')
        
        query = """
        SELECT 
            ID as account_id,
            NAME as account_name,
            WEBSITE,
            INDUSTRY,
            TYPE as account_type,
            BILLING_CITY,
            BILLING_STATE,
            BILLING_COUNTRY,
            ANNUAL_REVENUE,
            NUMBER_OF_EMPLOYEES
        FROM FIVETRAN.SALESFORCE.ACCOUNT
        WHERE UPPER(WEBSITE) LIKE UPPER(?) 
        AND IS_DELETED = FALSE
        ORDER BY NAME
        LIMIT 50
        """
        
        return execute_query(query, [f"%{clean_domain}%"])
    except Exception as e:
        st.error(f"Error searching accounts by domain: {e}")
        return pd.DataFrame()

# Sales Engineer and Expert Data Access

def get_freestyle_skills_data():
    """Get freestyle skills data from Snowflake tables"""
    try:
        query = """
        SELECT 
            EMPLOYEE_ID,
            USER_ID,
            NAME,
            EMAIL,
            COLLEGE,
            SELF_ASSESMENT_SKILL_300,
            SELF_ASSESMENT_SKILL_400,
            MGR_SCORE_SKILL_300,
            MGR_SCORE_SKILL_400,
            SPECIALTIES,
            CERT_EXTERNAL,
            CERT_INTERNAL,
            EMPLOYERS
        FROM SALES.SE_REPORTING.FREESTYLE_SUMMARY 
        WHERE NAME IS NOT NULL
        AND TRIM(NAME) != ''
        ORDER BY NAME
        """
        
        return execute_query(query)
    except Exception as e:
        st.error(f"Error querying freestyle skills data: {e}")
        return pd.DataFrame()

def search_experts_by_skills(skills_text, min_score=50):
    """Search for experts based on skills"""
    if not skills_text:
        return pd.DataFrame()
    
    try:
        # Split skills into individual terms
        skill_terms = [term.strip() for term in skills_text.split(',')]
        
        # Build search conditions
        search_conditions = []
        params = []
        
        for skill in skill_terms:
            search_conditions.append("""
            (UPPER(SELF_ASSESMENT_SKILL_300) LIKE UPPER(?) OR
             UPPER(SELF_ASSESMENT_SKILL_400) LIKE UPPER(?) OR
             UPPER(SPECIALTIES) LIKE UPPER(?))
            """)
            params.extend([f"%{skill}%", f"%{skill}%", f"%{skill}%"])
        
        where_clause = " OR ".join(search_conditions)
        
        query = f"""
        SELECT 
            EMPLOYEE_ID,
            NAME,
            EMAIL,
            SPECIALTIES,
            SELF_ASSESMENT_SKILL_300,
            SELF_ASSESMENT_SKILL_400,
            MGR_SCORE_SKILL_300,
            MGR_SCORE_SKILL_400,
            COLLEGE
        FROM SALES.SE_REPORTING.FREESTYLE_SUMMARY 
        WHERE NAME IS NOT NULL
        AND TRIM(NAME) != ''
        AND ({where_clause})
        ORDER BY NAME
        LIMIT 100
        """
        
        return execute_query(query, params)
    except Exception as e:
        st.error(f"Error searching experts by skills: {e}")
        return pd.DataFrame()

# Discovery Session Data Management

def save_session_data(session_id, session_data):
    """Save discovery session data to Snowflake"""
    try:
        # Convert session data to JSON string
        import json
        session_json = json.dumps(session_data)
        
        query = """
        MERGE INTO snowpublic.streamlit.sales_discovery_sessions s
        USING (SELECT ? as session_id, ? as session_state, CURRENT_TIMESTAMP as created_at) t
        ON s.SESSION_ID = t.session_id
        WHEN MATCHED THEN 
            UPDATE SET SESSION_STATE = PARSE_JSON(t.session_state), CREATED_AT = t.created_at
        WHEN NOT MATCHED THEN 
            INSERT (SESSION_ID, SESSION_STATE, CREATED_AT, SAVED_BY_USER) 
            VALUES (t.session_id, PARSE_JSON(t.session_state), t.created_at, USER())
        """
        
        execute_query(query, [session_id, session_json])
        return True
    except Exception as e:
        st.error(f"Error saving session data: {e}")
        return False

def load_session_data(session_id):
    """Load discovery session data from Snowflake"""
    try:
        query = """
        SELECT SESSION_STATE, CREATED_AT
        FROM snowpublic.streamlit.sales_discovery_sessions
        WHERE SESSION_ID = ?
        """
        
        result = execute_query(query, [session_id])
        if not result.empty:
            import json
            return json.loads(result.iloc[0]['SESSION_STATE'])
        return None
    except Exception as e:
        st.error(f"Error loading session data: {e}")
        return None

def get_all_sessions():
    """Get all discovery sessions"""
    try:
        query = """
        SELECT 
            SESSION_ID,
            SESSION_NAME,
            SAVED_BY_USER,
            CREATED_AT
        FROM snowpublic.streamlit.sales_discovery_sessions
        ORDER BY CREATED_AT DESC
        """
        
        return execute_query(query)
    except Exception as e:
        st.error(f"Error getting sessions: {e}")
        return pd.DataFrame()

# Utility Functions

def test_connection():
    """Test the Snowflake connection"""
    try:
        result = execute_query("SELECT CURRENT_VERSION() as version")
        if not result.empty:
            return True, f"Connected to Snowflake version: {result.iloc[0]['VERSION']}"
        return False, "No response from Snowflake"
    except Exception as e:
        return False, f"Connection failed: {e}"

@st.cache_data(ttl=3600)
def get_database_info():
    """Get information about available databases and schemas"""
    try:
        query = """
        SELECT 
            DATABASE_NAME,
            SCHEMA_NAME,
            TABLE_NAME,
            TABLE_TYPE
        FROM INFORMATION_SCHEMA.TABLES
        WHERE TABLE_SCHEMA IN ('SALESFORCE', 'SE_REPORTING', 'DISCOVERY')
        ORDER BY DATABASE_NAME, SCHEMA_NAME, TABLE_NAME
        """
        
        return execute_query(query)
    except Exception as e:
        st.error(f"Error getting database info: {e}")
        return pd.DataFrame()

def validate_table_access():
    """Validate access to key tables"""
    tables_to_check = [
        "FIVETRAN.SALESFORCE.ACCOUNT",
        "FIVETRAN.SALESFORCE.OPPORTUNITY", 
        "SALES.SE_REPORTING.FREESTYLE_SUMMARY"
    ]
    
    results = {}
    for table in tables_to_check:
        try:
            query = f"SELECT COUNT(*) as count FROM {table} LIMIT 1"
            result = execute_query(query)
            results[table] = result.iloc[0]['COUNT'] if not result.empty else 0
        except Exception as e:
            results[table] = f"Error: {e}"
    
    return results 
