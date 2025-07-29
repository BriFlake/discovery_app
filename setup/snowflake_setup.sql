-- Snowflake Setup for Sales Discovery Assistant
-- Run this script to set up required database objects and permissions

-- 1. Create database and schema (adjust names as needed)
CREATE DATABASE IF NOT EXISTS SALES_DISCOVERY;
USE DATABASE SALES_DISCOVERY;
CREATE SCHEMA IF NOT EXISTS DISCOVERY_APP;
USE SCHEMA DISCOVERY_APP;

-- 2. Create table for storing discovery answers
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

-- 3. Grant necessary permissions for Cortex (AI/LLM functions)
-- Note: Cortex functions require specific privileges
-- SNOWFLAKE.CORTEX.COMPLETE requires USAGE on the database and schema

-- Grant usage on database and schema
GRANT USAGE ON DATABASE SALES_DISCOVERY TO ROLE SYSADMIN;
GRANT USAGE ON SCHEMA SALES_DISCOVERY.DISCOVERY_APP TO ROLE SYSADMIN;

-- Grant table permissions
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE SALES_DISCOVERY.DISCOVERY_APP.SALES_DISCOVERY_ANSWERS TO ROLE SYSADMIN;

-- 4. Verify Fivetran Salesforce data access (optional - only if using Salesforce integration)
-- Uncomment and adjust if you have Fivetran Salesforce data
/*
GRANT USAGE ON DATABASE FIVETRAN TO ROLE SYSADMIN;
GRANT USAGE ON SCHEMA FIVETRAN.SALESFORCE TO ROLE SYSADMIN;
GRANT SELECT ON ALL TABLES IN SCHEMA FIVETRAN.SALESFORCE TO ROLE SYSADMIN;
*/

-- 5. Verify SE Reporting data access (optional - only if using expert search)
-- Uncomment and adjust if you have SE reporting data
/*
GRANT USAGE ON DATABASE SALES TO ROLE SYSADMIN;
GRANT USAGE ON SCHEMA SALES.SE_REPORTING TO ROLE SYSADMIN;
GRANT SELECT ON ALL TABLES IN SCHEMA SALES.SE_REPORTING TO ROLE SYSADMIN;
*/

-- 6. Create a warehouse for the application (if needed)
CREATE WAREHOUSE IF NOT EXISTS DISCOVERY_WH 
WITH 
    WAREHOUSE_SIZE = 'SMALL'
    AUTO_SUSPEND = 300
    AUTO_RESUME = TRUE
    INITIALLY_SUSPENDED = TRUE;

GRANT USAGE ON WAREHOUSE DISCOVERY_WH TO ROLE SYSADMIN;

-- 7. Show current setup
SELECT 'Setup completed successfully! Database and table created.' AS STATUS;

-- Verify table creation
DESCRIBE TABLE SALES_DISCOVERY_ANSWERS;

-- Show sample data structure
SELECT 
    'session_example_123' AS SESSION_ID,
    'example.com' AS COMPANY_WEBSITE,
    'Technology' AS INDUSTRY,
    'Databricks' AS COMPETITOR,
    'Chief Data Officer' AS PERSONA,
    'Technical Discovery' AS CATEGORY,
    'uuid-example' AS QUESTION_ID,
    'What are your current data challenges?' AS QUESTION_TEXT,
    'We have data silos and need better analytics' AS ANSWER,
    FALSE AS IS_FAVORITE,
    CURRENT_TIMESTAMP() AS ANSWERED_DATE
LIMIT 0; -- Show structure only, no actual data 