# Snowflake Sales Discovery Assistant

A comprehensive multi-page Streamlit application for sales discovery, expert finding, and demo automation - designed to run natively in **Streamlit in Snowflake**.

## 🎯 Three Connected Modules

### 🏢 Sales Activities
Complete sales workflow including:
- **Company Research** - Salesforce integration and AI-powered analysis
- **Discovery Questions** - AI-generated questions with auto-population from notes
- **Value & Strategy** - Business case, competitive analysis, and roadmap generation
- **Outreach** - Email templates and LinkedIn messages
- **People Research** - Stakeholder analysis and conversation topics

### 🔍 Expert Hub
Find the right experts for your deals:
- **Freestyle Skills Search** - Search by any skills, technologies, or specialties
- **SE Directory** - Browse and filter all Sales Engineers
- **Competitive Experience** - Find experts with specific competitor experience
- **Expert Analytics** - Visual analysis and relevance scoring
- **Expert Context** - Context sharing for demo generation

### 🚀 Demo Builder
Generate comprehensive demo environments:
- **AI Demo Prompts** - Generate detailed prompts for Cursor AI
- **Data Architecture** - Visual planning and suggestions
- **Demo Templates** - Industry and use case specific templates
- **Integration** - Uses all discovery and expert context

## 🚀 Quick Start - Deploy to Snowflake

### Prerequisites
- Snowflake account with **Streamlit in Snowflake** enabled
- **Cortex AI** functions available
- `ACCOUNTADMIN` or role with appropriate privileges

### 1. Set Up Database Objects
```sql
-- Run this in a Snowflake worksheet
CREATE DATABASE IF NOT EXISTS SALES_DISCOVERY;
USE DATABASE SALES_DISCOVERY;
CREATE SCHEMA IF NOT EXISTS DISCOVERY_APP;
USE SCHEMA DISCOVERY_APP;

-- Create the main table
CREATE TABLE IF NOT EXISTS SALES_DISCOVERY_ANSWERS (
    SESSION_ID VARCHAR(100),
    COMPANY_WEBSITE VARCHAR(255),
    INDUSTRY VARCHAR(100),
    COMPETITOR VARCHAR(100),
    PERSONA VARCHAR(100),
    CATEGORY VARCHAR(100),
    QUESTION_ID VARCHAR(100),
    QUESTION_TEXT TEXT,
    ANSWER TEXT,
    IS_FAVORITE BOOLEAN DEFAULT FALSE,
    ANSWERED_DATE TIMESTAMP_LTZ DEFAULT CURRENT_TIMESTAMP(),
    PRIMARY KEY (SESSION_ID, QUESTION_ID)
);
```

### 2. Deploy to Streamlit in Snowflake

#### Option A: Snowsight UI (Recommended)
1. **Open Snowsight** in your Snowflake account
2. **Navigate to Streamlit** in the left sidebar
3. **Click "+ Streamlit App"**
4. **Choose "Create from scratch"**
5. **Configure**:
   - App Name: `Sales Discovery Assistant`
   - Database: `SALES_DISCOVERY`
   - Schema: `DISCOVERY_APP`
   - Warehouse: Your preferred warehouse
6. **Upload all files** maintaining the directory structure
7. **Start with `app.py`** as the main file

#### Option B: Upload Files Individually
1. Upload files in this order:
   ```
   app.py                              # Main entry point
   requirements.txt                    # Dependencies
   shared/__init__.py
   shared/state_manager.py
   modules/__init__.py
   modules/snowflake_utils.py
   modules/llm_functions.py
   modules/expert_search.py
   modules/sales_functions.py
   modules/session_management.py
   modules/ui_components.py
   modules/data_visualization.py
   pages/01_🏢_Sales_Activities.py
   pages/02_🔍_Expert_Hub.py
   pages/03_🚀_Demo_Builder.py
   ```

### 3. Configure Permissions
```sql
-- Grant basic permissions
GRANT USAGE ON DATABASE SALES_DISCOVERY TO ROLE SYSADMIN;
GRANT USAGE ON SCHEMA SALES_DISCOVERY.DISCOVERY_APP TO ROLE SYSADMIN;
GRANT ALL ON TABLE SALES_DISCOVERY.DISCOVERY_APP.SALES_DISCOVERY_ANSWERS TO ROLE SYSADMIN;
```

### 4. Launch and Test
1. **Open your Streamlit app** in Snowsight
2. **Test basic functionality**:
   - Navigate between the three main modules
   - Try setting up a company manually
   - Test AI question generation
   - Verify data saving works

## 🔧 Configuration

### Required Features
- ✅ **Streamlit in Snowflake** - The app runs natively in Snowflake
- ✅ **Cortex AI Functions** - For all AI/LLM functionality
- ✅ **Standard SQL** - For data storage and retrieval

### Optional Integrations
- 🔄 **Fivetran Salesforce Data** - Enables Salesforce account lookup and integration
- 🔄 **SE Reporting Data** - Enables expert search and skills analysis
- 🔄 **Custom Data Sources** - Easily extendable for your specific data

### AI Models Available
The app supports multiple Cortex AI models:
- `claude-3-5-sonnet` (default, recommended)
- `claude-3-haiku` (faster, good for simpler tasks)
- `llama3-70b` 
- `mixtral-8x7b`
- `mistral-large`

## 📊 Features

### Core Capabilities
- **Multi-Page Architecture** - Clean separation of Sales, Expert, and Demo functionality
- **Cross-Module Integration** - Context flows seamlessly between modules
- **Persistent Sessions** - Save and load discovery sessions
- **AI-Powered Content** - Generate questions, strategies, emails, and demo prompts
- **Visual Analytics** - Charts and dashboards for expert analysis and discovery progress
- **Export Capabilities** - Download data, charts, and generated content

### Enterprise Ready
- **Snowflake Native** - Runs entirely within your Snowflake environment
- **Secure by Design** - All data stays within your Snowflake account
- **Scalable** - Leverages Snowflake's compute and storage
- **Role-Based Access** - Integrates with Snowflake's security model

## 📚 Usage Guide

### Getting Started Workflow
1. **Start in Sales Activities** - Set up your company and conduct discovery
2. **Move to Expert Hub** - Find relevant experts for your deal
3. **Finish in Demo Builder** - Generate comprehensive demo environments

### Sales Activities Workflow
1. **Company Setup** - Manual entry or Salesforce lookup
2. **Discovery Questions** - AI-generated, customizable by category
3. **Meeting Notes** - Auto-populate answers from notes
4. **Value Strategy** - Generate business case and roadmap
5. **Outreach** - Create emails and LinkedIn messages

### Expert Hub Workflow
1. **Skills Search** - Search for any skills, technologies, specialties
2. **Relevance Scoring** - AI-powered ranking of expert matches
3. **Industry Filtering** - Focus on specific industry experience
4. **Competitive Analysis** - Find experts with competitor experience
5. **Context Export** - Share expert context with demo generation

### Demo Builder Workflow
1. **Readiness Check** - Verify you have sufficient context
2. **Generate Prompt** - AI creates comprehensive Cursor AI prompts
3. **Architecture Planning** - Review suggested demo architectures
4. **Template Selection** - Choose from industry-specific templates
5. **Demo Creation** - Use generated prompts with Cursor AI

## 🔍 Optional Data Sources

### Salesforce Integration
If you have Fivetran Salesforce data, enable advanced features:
- Account lookup and auto-population
- Opportunity history and context
- Owner and stakeholder information

Grant access:
```sql
GRANT USAGE ON DATABASE FIVETRAN TO ROLE SYSADMIN;
GRANT USAGE ON SCHEMA FIVETRAN.SALESFORCE TO ROLE SYSADMIN;
GRANT SELECT ON ALL TABLES IN SCHEMA FIVETRAN.SALESFORCE TO ROLE SYSADMIN;
```

### Expert Search Integration
If you have SE reporting data, enable expert features:
- Skills and certifications analysis
- Competitive experience tracking
- Performance and opportunity history

Grant access:
```sql
GRANT USAGE ON DATABASE SALES TO ROLE SYSADMIN;
GRANT USAGE ON SCHEMA SALES.SE_REPORTING TO ROLE SYSADMIN;
GRANT SELECT ON ALL TABLES IN SCHEMA SALES.SE_REPORTING TO ROLE SYSADMIN;
```

## 🛠️ Troubleshooting

### Common Issues

**App won't start**:
- Verify you're running in Streamlit in Snowflake
- Check the `SALES_DISCOVERY_ANSWERS` table exists
- Ensure proper database permissions

**AI functions not working**:
- Confirm Cortex AI is enabled in your account
- Try switching to a different model in the sidebar
- Check for any Cortex usage limits

**Salesforce/Expert search not working**:
- These are optional features that require specific data sources
- Verify you have the required databases and permissions
- Features will gracefully disable if data isn't available

### Performance Tips
- Use appropriate warehouse sizing (start with SMALL)
- Enable auto-suspend to manage costs
- Queries are cached for optimal performance
- Charts render on-demand to save memory

## 📈 Next Steps

After deployment:

1. **Customize for your organization**:
   - Update industry templates
   - Modify AI prompts for your use cases
   - Add company-specific data sources

2. **Train your team**:
   - Sales reps on the discovery workflow
   - SEs on expert finding and demo generation
   - Managers on analytics and insights

3. **Integrate with your processes**:
   - Connect to your CRM systems
   - Link with your demo environments
   - Integrate with training materials

4. **Monitor and optimize**:
   - Track usage and performance
   - Gather user feedback
   - Optimize for your specific needs

## 📄 Documentation

- **[DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)** - Detailed deployment instructions
- **[snowflake_setup.sql](snowflake_setup.sql)** - Database setup script
- **[requirements.txt](requirements.txt)** - Python dependencies

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Streamlit in Snowflake                  │
├─────────────────────────────────────────────────────────────┤
│  app.py (Welcome & Navigation)                             │
├─────────────────┬─────────────────┬─────────────────────────┤
│  🏢 Sales        │  🔍 Expert       │  🚀 Demo Builder        │
│  Activities      │  Hub            │                         │
├─────────────────┼─────────────────┼─────────────────────────┤
│  shared/state_manager.py (Cross-page state)               │
├─────────────────────────────────────────────────────────────┤
│  modules/ (Business logic, AI, DB, UI, Visualization)     │
├─────────────────────────────────────────────────────────────┤
│  Snowflake Data Layer (Tables, AI, External Sources)      │
└─────────────────────────────────────────────────────────────┘
```

## 🤝 Contributing

This app is designed to be easily extensible:
- Add new pages by creating files in `pages/`
- Extend functionality by adding modules
- Customize AI prompts in `modules/llm_functions.py`
- Add new data visualizations in `modules/data_visualization.py`

---

**Built for Snowflake Sales Teams** | Powered by Streamlit in Snowflake & Cortex AI 