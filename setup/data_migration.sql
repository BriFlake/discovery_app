-- DATA MIGRATION SCRIPT
-- Transforms existing JSON blob sessions into normalized relational structure
-- Run AFTER creating the normalized schema

-- Step 1: Backup existing data (safety first!)
CREATE OR REPLACE TABLE discovery_sessions_backup AS
SELECT * FROM snowpublic.streamlit.discovery_sessions;

-- Step 2: Migrate core session data
INSERT INTO discovery_sessions (
    session_id, session_name, user_email, company_name, company_website,
    competitor, contact_name, contact_title, created_at, updated_at, status
)
SELECT 
    SESSION_ID,
    SESSION_NAME,
    USER_EMAIL,
    COMPANY_NAME,
    COMPANY_WEBSITE,
    COMPETITOR,
    CONTACT_NAME,
    CONTACT_TITLE,
    CREATED_AT,
    UPDATED_AT,
    COALESCE(STATUS, 'active')
FROM snowpublic.streamlit.discovery_sessions
WHERE SESSION_ID IS NOT NULL;

-- Step 3: Extract and normalize questions from JSON
WITH parsed_questions AS (
    SELECT 
        old.SESSION_ID,
        CASE 
            -- Handle list format
            WHEN ARRAY_SIZE(old.DISCOVERY_QUESTIONS) > 0 THEN
                SELECT ARRAY_AGG(
                    OBJECT_CONSTRUCT(
                        'question_id', CONCAT(old.SESSION_ID, '-q-', ROW_NUMBER() OVER (ORDER BY f.seq)),
                        'category', COALESCE(f.value:category::STRING, 'Technical'),
                        'question_text', f.value:text::STRING,
                        'explanation', f.value:explanation::STRING,
                        'importance', COALESCE(f.value:importance::STRING, 'medium'),
                        'order', ROW_NUMBER() OVER (ORDER BY f.seq)
                    )
                )
                FROM TABLE(FLATTEN(old.DISCOVERY_QUESTIONS)) f
                WHERE f.value:text IS NOT NULL
            -- Handle object format (category -> questions)
            ELSE
                SELECT ARRAY_AGG(
                    OBJECT_CONSTRUCT(
                        'question_id', CONCAT(old.SESSION_ID, '-q-', 
                            REPLACE(cat.key, ' ', '') || '-' || ROW_NUMBER() OVER (PARTITION BY cat.key ORDER BY q.seq)),
                        'category', cat.key,
                        'question_text', q.value:text::STRING,
                        'explanation', q.value:explanation::STRING,
                        'importance', COALESCE(q.value:importance::STRING, 'medium'),
                        'order', ROW_NUMBER() OVER (ORDER BY cat.seq, q.seq)
                    )
                )
                FROM TABLE(FLATTEN(old.DISCOVERY_QUESTIONS)) cat,
                     TABLE(FLATTEN(cat.value)) q
                WHERE q.value:text IS NOT NULL
        END as questions_array
    FROM snowpublic.streamlit.discovery_sessions old
    WHERE old.DISCOVERY_QUESTIONS IS NOT NULL
)
INSERT INTO discovery_questions (
    question_id, session_id, category, question_text, 
    explanation, importance, question_order
)
SELECT 
    q.value:question_id::STRING,
    pq.SESSION_ID,
    q.value:category::STRING,
    q.value:question_text::STRING,
    q.value:explanation::STRING,
    q.value:importance::STRING,
    q.value:order::INTEGER
FROM parsed_questions pq,
     TABLE(FLATTEN(pq.questions_array)) q
WHERE q.value:question_text IS NOT NULL;

-- Step 4: Extract and normalize answers
WITH parsed_answers AS (
    SELECT 
        old.SESSION_ID,
        CASE 
            -- Handle list format
            WHEN ARRAY_SIZE(old.DISCOVERY_QUESTIONS) > 0 THEN
                SELECT ARRAY_AGG(
                    OBJECT_CONSTRUCT(
                        'answer_id', CONCAT(old.SESSION_ID, '-a-', ROW_NUMBER() OVER (ORDER BY f.seq)),
                        'question_id', CONCAT(old.SESSION_ID, '-q-', ROW_NUMBER() OVER (ORDER BY f.seq)),
                        'answer_text', f.value:answer::STRING
                    )
                )
                FROM TABLE(FLATTEN(old.DISCOVERY_QUESTIONS)) f
                WHERE f.value:answer IS NOT NULL AND TRIM(f.value:answer::STRING) != ''
            -- Handle object format
            ELSE
                SELECT ARRAY_AGG(
                    OBJECT_CONSTRUCT(
                        'answer_id', CONCAT(old.SESSION_ID, '-a-', 
                            REPLACE(cat.key, ' ', '') || '-' || ROW_NUMBER() OVER (PARTITION BY cat.key ORDER BY q.seq)),
                        'question_id', CONCAT(old.SESSION_ID, '-q-', 
                            REPLACE(cat.key, ' ', '') || '-' || ROW_NUMBER() OVER (PARTITION BY cat.key ORDER BY q.seq)),
                        'answer_text', q.value:answer::STRING
                    )
                )
                FROM TABLE(FLATTEN(old.DISCOVERY_QUESTIONS)) cat,
                     TABLE(FLATTEN(cat.value)) q
                WHERE q.value:answer IS NOT NULL AND TRIM(q.value:answer::STRING) != ''
        END as answers_array
    FROM snowpublic.streamlit.discovery_sessions old
    WHERE old.DISCOVERY_QUESTIONS IS NOT NULL
)
INSERT INTO discovery_answers (
    answer_id, question_id, session_id, answer_text, confidence_level
)
SELECT 
    a.value:answer_id::STRING,
    a.value:question_id::STRING,
    pa.SESSION_ID,
    a.value:answer_text::STRING,
    3 -- Default confidence level
FROM parsed_answers pa,
     TABLE(FLATTEN(pa.answers_array)) a
WHERE a.value:answer_text IS NOT NULL;

-- Step 5: Migrate strategic content
-- Business Cases
INSERT INTO session_content (content_id, session_id, content_type, content_text)
SELECT 
    CONCAT(SESSION_ID, '-content-business_case'),
    SESSION_ID,
    'business_case',
    BUSINESS_CASE
FROM snowpublic.streamlit.discovery_sessions
WHERE BUSINESS_CASE IS NOT NULL AND TRIM(BUSINESS_CASE) != '';

-- Competitive Strategy
INSERT INTO session_content (content_id, session_id, content_type, content_text)
SELECT 
    CONCAT(SESSION_ID, '-content-competitive_strategy'),
    SESSION_ID,
    'competitive_strategy',
    COMPETITOR_STRATEGY
FROM snowpublic.streamlit.discovery_sessions
WHERE COMPETITOR_STRATEGY IS NOT NULL AND TRIM(COMPETITOR_STRATEGY) != '';

-- Value Hypothesis
INSERT INTO session_content (content_id, session_id, content_type, content_text)
SELECT 
    CONCAT(SESSION_ID, '-content-value_hypothesis'),
    SESSION_ID,
    'value_hypothesis',
    VALUE_HYPOTHESIS
FROM snowpublic.streamlit.discovery_sessions
WHERE VALUE_HYPOTHESIS IS NOT NULL AND TRIM(VALUE_HYPOTHESIS) != '';

-- Roadmap Data (complex JSON)
INSERT INTO session_content (content_id, session_id, content_type, content_data)
SELECT 
    CONCAT(SESSION_ID, '-content-roadmap'),
    SESSION_ID,
    'roadmap',
    ROADMAP_DATA
FROM snowpublic.streamlit.discovery_sessions
WHERE ROADMAP_DATA IS NOT NULL;

-- Outreach Emails (complex JSON)
INSERT INTO session_content (content_id, session_id, content_type, content_data)
SELECT 
    CONCAT(SESSION_ID, '-content-outreach_emails'),
    SESSION_ID,
    'outreach_emails',
    OUTREACH_EMAILS
FROM snowpublic.streamlit.discovery_sessions
WHERE OUTREACH_EMAILS IS NOT NULL;

-- LinkedIn Messages (complex JSON)
INSERT INTO session_content (content_id, session_id, content_type, content_data)
SELECT 
    CONCAT(SESSION_ID, '-content-linkedin_messages'),
    SESSION_ID,
    'linkedin_messages',
    LINKEDIN_MESSAGES
FROM snowpublic.streamlit.discovery_sessions
WHERE LINKEDIN_MESSAGES IS NOT NULL;

-- Step 6: Migrate people research
WITH people_data AS (
    SELECT 
        old.SESSION_ID,
        f.value:name::STRING as contact_name,
        f.value:title::STRING as contact_title,
        f.value:linkedin::STRING as contact_linkedin,
        f.value:background::STRING as background_notes,
        ROW_NUMBER() OVER (PARTITION BY old.SESSION_ID ORDER BY f.seq) as contact_num
    FROM snowpublic.streamlit.discovery_sessions old,
         TABLE(FLATTEN(old.PEOPLE_RESEARCH)) f
    WHERE old.PEOPLE_RESEARCH IS NOT NULL
    AND f.value:name IS NOT NULL
)
INSERT INTO session_contacts (
    contact_id, session_id, contact_name, contact_title, 
    contact_linkedin, background_notes, contact_type
)
SELECT 
    CONCAT(SESSION_ID, '-contact-', contact_num),
    SESSION_ID,
    contact_name,
    contact_title,
    contact_linkedin,
    background_notes,
    CASE WHEN contact_num = 1 THEN 'primary' ELSE 'stakeholder' END
FROM people_data;

-- Step 7: Validation queries
SELECT 'Migration Summary:' as step;

SELECT 
    'Sessions migrated' as metric,
    COUNT(*) as count
FROM discovery_sessions;

SELECT 
    'Questions migrated' as metric,
    COUNT(*) as count
FROM discovery_questions;

SELECT 
    'Answers migrated' as metric,
    COUNT(*) as count
FROM discovery_answers;

SELECT 
    'Content items migrated' as metric,
    COUNT(*) as count
FROM session_content;

SELECT 
    'Contacts migrated' as metric,
    COUNT(*) as count
FROM session_contacts;

-- Step 8: Performance test the new schema
SELECT 
    'Progress calculation test' as test,
    COUNT(*) as sessions_with_progress
FROM session_progress
WHERE completion_percentage > 0;

-- Step 9: Show sample migrated data
SELECT 
    s.session_name,
    s.company_name,
    sp.total_questions,
    sp.answered_questions,
    sp.completion_percentage,
    sp.available_content
FROM session_progress sp
JOIN discovery_sessions s ON sp.session_id = s.session_id
LIMIT 5;

SELECT 'Migration completed successfully!' as status; 