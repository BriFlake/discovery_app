CREATE OR REPLACE database discovery_app;
CREATE OR REPLACE schema discovery;
CREATE OR REPLACE warehouse discovery_wh;

USE database discovery_app;
USE schema discovery;
USE warehouse discovery_wh;

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