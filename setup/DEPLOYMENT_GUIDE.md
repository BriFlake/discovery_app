# Snowflake Sales Discovery Assistant - Deployment Guide

## 🚀 Deploy to Streamlit in Snowflake

This guide walks you through deploying the Sales Discovery Assistant to Streamlit in Snowflake.

## Prerequisites

### 1. Snowflake Account Requirements
- Snowflake account with Streamlit enabled
- `ACCOUNTADMIN` or appropriate role with:
  - CREATE DATABASE privileges
  - CREATE SCHEMA privileges  
  - USAGE on SNOWFLAKE.CORTEX functions
  - CREATE STREAMLIT privileges

### 2. Required Snowflake Features
- **Cortex AI Functions** - For LLM/AI functionality
- **Streamlit in Snowflake** - For the web application
- **Standard SQL** - For data storage and retrieval

### 3. Optional Integrations
- **Fivetran Salesforce Data** - For Salesforce account lookup
- **SE Reporting Data** - For expert search functionality

## Step-by-Step Deployment

### Step 1: Set Up Snowflake Objects

1. **Run the setup SQL script**:
   ```sql
   -- Copy and run the contents of snowflake_setup.sql in your Snowflake worksheet
   ```

2. **Verify setup**:
   ```sql
   USE DATABASE SALES_DISCOVERY;
   USE SCHEMA DISCOVERY_APP;
   DESCRIBE TABLE SALES_DISCOVERY_ANSWERS;
   ```

### Step 2: Prepare Application Files

1. **Ensure all files are ready**:
   ```
   discovery_app/
   ├── app.py                          # Main entry point
   ├── requirements.txt                # Dependencies
   ├── shared/
   │   ├── __init__.py
   │   └── state_manager.py
   ├── modules/
   │   ├── __init__.py
   │   ├── snowflake_utils.py
   │   ├── llm_functions.py
   │   ├── expert_search.py
   │   ├── sales_functions.py
   │   ├── session_management.py
   │   ├── ui_components.py
   │   └── data_visualization.py
   └── pages/
       ├── 01_🏢_Sales_Activities.py
       ├── 02_🔍_Expert_Hub.py
       └── 03_🚀_Demo_Builder.py
   ```

### Step 3: Deploy to Streamlit in Snowflake

#### Option A: Using Snowsight UI (Recommended)

1. **Access Snowsight**:
   - Log into your Snowflake account
   - Navigate to Snowsight (the modern UI)

2. **Create Streamlit App**:
   - Go to **Streamlit** section in the left navigation
   - Click **+ Streamlit App**
   - Choose **Create from scratch**

3. **Configure App**:
   - **App Name**: `Sales Discovery Assistant`
   - **Database**: `SALES_DISCOVERY`
   - **Schema**: `DISCOVERY_APP`
   - **Warehouse**: `DISCOVERY_WH` (or your preferred warehouse)

4. **Upload Files**:
   - Upload all files maintaining the directory structure
   - Ensure `app.py` is in the root directory
   - Upload `requirements.txt`

#### Option B: Using SQL Commands

```sql
-- Create Streamlit app
CREATE STREAMLIT SALES_DISCOVERY_ASSISTANT
  ROOT_LOCATION = '@SALES_DISCOVERY.DISCOVERY_APP.APP_STAGE'
  MAIN_FILE = 'app.py'
  QUERY_WAREHOUSE = 'DISCOVERY_WH';

-- Create stage for files (if not exists)
CREATE STAGE IF NOT EXISTS APP_STAGE;

-- Upload files to stage (use SnowSQL or Snowsight file upload)
PUT file://app.py @APP_STAGE/;
PUT file://requirements.txt @APP_STAGE/;
-- (Upload all other files maintaining directory structure)
```

### Step 4: Configure Permissions

1. **Grant Streamlit permissions**:
   ```sql
   -- Grant usage on the Streamlit app
   GRANT USAGE ON STREAMLIT SALES_DISCOVERY_ASSISTANT TO ROLE SYSADMIN;
   
   -- Grant necessary database permissions
   GRANT USAGE ON DATABASE SALES_DISCOVERY TO ROLE SYSADMIN;
   GRANT USAGE ON SCHEMA SALES_DISCOVERY.DISCOVERY_APP TO ROLE SYSADMIN;
   GRANT ALL ON TABLE SALES_DISCOVERY.DISCOVERY_APP.SALES_DISCOVERY_ANSWERS TO ROLE SYSADMIN;
   ```

2. **For Cortex AI functions**:
   ```sql
   -- Cortex functions are available to all users by default
   -- No additional permissions needed for SNOWFLAKE.CORTEX.COMPLETE
   ```

### Step 5: Configure Optional Integrations

#### Salesforce Integration (Optional)
If you have Fivetran Salesforce data:

```sql
-- Grant access to Salesforce data
GRANT USAGE ON DATABASE FIVETRAN TO ROLE SYSADMIN;
GRANT USAGE ON SCHEMA FIVETRAN.SALESFORCE TO ROLE SYSADMIN;
GRANT SELECT ON ALL TABLES IN SCHEMA FIVETRAN.SALESFORCE TO ROLE SYSADMIN;
```

#### Expert Search Integration (Optional)
If you have SE reporting data:

```sql
-- Grant access to SE reporting data
GRANT USAGE ON DATABASE SALES TO ROLE SYSADMIN;
GRANT USAGE ON SCHEMA SALES.SE_REPORTING TO ROLE SYSADMIN;
GRANT SELECT ON ALL TABLES IN SCHEMA SALES.SE_REPORTING TO ROLE SYSADMIN;
```

### Step 6: Test and Launch

1. **Open the Streamlit app**:
   - In Snowsight, go to Streamlit section
   - Find your "Sales Discovery Assistant" app
   - Click to open

2. **Test basic functionality**:
   - Verify the welcome page loads
   - Try setting up a company manually
   - Test AI question generation
   - Check data saving functionality

3. **Test integrations** (if configured):
   - Try Salesforce account search
   - Test expert search functionality

## Configuration Options

### Database Configuration

Update table names or schema if needed in `modules/snowflake_utils.py`:

```python
# Change table name if different
table_name = "YOUR_TABLE_NAME"

# Update database/schema references if different
```

### AI Model Configuration

The app uses Claude 3.5 Sonnet by default. Available models:
- `claude-3-5-sonnet` (recommended)
- `claude-3-haiku` (faster, less detailed)
- `llama3-70b`
- `mixtral-8x7b`
- `mistral-large`

### Feature Toggles

Disable features you don't need by modifying the pages:

```python
# In pages, comment out features you don't want:
# - Salesforce integration
# - Expert search
# - Specific AI functions
```

## Troubleshooting

### Common Issues

1. **"Failed to connect to Snowflake"**:
   - Ensure you're running in Streamlit in Snowflake
   - Check database and schema permissions

2. **"Table not found" errors**:
   - Run the setup SQL script
   - Verify table permissions
   - Check you're using the correct database/schema

3. **Cortex AI errors**:
   - Verify your Snowflake account has Cortex enabled
   - Check if you have usage permissions
   - Try a different AI model

4. **Salesforce/Expert search not working**:
   - These are optional features
   - Check if the required data sources exist
   - Verify permissions on external databases

### Performance Optimization

1. **Warehouse sizing**:
   - Start with SMALL warehouse
   - Scale up for better performance if needed

2. **Query optimization**:
   - Expert search queries are cached for 5 minutes
   - Salesforce queries are cached for 5 minutes
   - Session data is cached for 1 minute

3. **Memory management**:
   - App uses session state efficiently
   - Large datasets are paginated
   - Charts are rendered on-demand

## Security Considerations

1. **Data Privacy**:
   - All data stays within your Snowflake account
   - No external API calls except for AI functions
   - Session data is stored securely in Snowflake

2. **Access Control**:
   - Use Snowflake's role-based access control
   - Limit database permissions appropriately
   - Consider row-level security if needed

3. **AI/LLM Usage**:
   - All AI processing happens within Snowflake Cortex
   - No data leaves your Snowflake environment
   - Consider data classification for sensitive content

## Support and Maintenance

### Regular Maintenance
- Monitor warehouse usage and costs
- Review and clean up old session data
- Update dependencies as needed

### Monitoring
- Check Streamlit app logs in Snowsight
- Monitor query performance
- Track AI function usage and costs

### Updates
- Update individual modules as needed
- Test changes in development environment first
- Use version control for production deployments

## Next Steps

After successful deployment:

1. **Train your team** on using the three main modules
2. **Customize** industry-specific templates and prompts
3. **Integrate** with your existing Salesforce and expert data
4. **Expand** functionality based on user feedback
5. **Monitor** usage and optimize performance

## Need Help?

- Check Snowflake documentation for Streamlit in Snowflake
- Review Cortex AI function documentation
- Consult with your Snowflake account team for advanced configurations 