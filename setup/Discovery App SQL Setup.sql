CREATE OR REPLACE database discovery_app;
CREATE OR REPLACE schema discovery;
CREATE OR REPLACE warehouse discovery_wh;

USE database discovery_app;
USE schema discovery;
USE warehouse discovery_wh;

//Create table to save answers from app
CREATE OR REPLACE TABLE SALES_DISCOVERY_ANSWERS (
    id STRING,
    company_name STRING,
    company_website STRING,
    question_category STRING,
    question TEXT,
    answer TEXT,
    saved_at TIMESTAMP_NTZ,
    favorite BOOLEAN
);

//Create table to save answers from beta/WIP app
CREATE OR REPLACE TABLE SALES_DISCOVERY_ANSWERS_BETA (
    id STRING,
    company_name STRING,
    company_website STRING,
    question_category STRING,
    question TEXT,
    answer TEXT,
    saved_at TIMESTAMP_NTZ,
    favorite BOOLEAN
);

//Create table to save session state
CREATE OR REPLACE TABLE SALES_DISCOVERY_SESSIONS (
    session_id VARCHAR PRIMARY KEY,
    session_name VARCHAR,
    created_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    session_state VARIANT,
    saved_by_user VARCHAR
);

//Truncate test data
truncate table sales_discovery_sessions;

//View discovery sessions
select *
from sales_discovery_sessions;
