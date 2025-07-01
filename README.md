# Discovery App

This Streamlit app is built to speed up account research and discovery preparation. The repo has two files:
+ A basic SQL file to create a database, schema, table, and virtual warehouse.
+ Python to power a Streamlit app.

# How to setup?

Inside of your Snowflake demo account, import the SQL file as a Worksheet. Run the SQL to create the database, schema, table, and virtual warehouse.

Create a Streamlit app and replace the code with the Python file.

# Sample Workflow

Let's say you have a discovery call coming up with a Data Scientist at Berlin Packaging and you don't know where to start. Grab the URL of the company website and paste it into the app. Enter their industry which in this case is Packaging and Distribution. Select the title of the person you're meeting with. Select the primary competitor and click "Generate Summary and Questions."

![image](https://github.com/user-attachments/assets/bbe37625-507e-4180-8a2f-eb620fe0ce12)

The app use Cortex to call the LLM of your choice--in this case Claude 3.5 Sonnet--to generate 10 technical questions, 10 business questions, and 10 questions to position Snowflake against the primary competitor.

As you prepare for your discovery, you can favorite or delete questions. When conducting discovery, you can enter your answers in the app then export to CSV, save to the Snowflake table created in the SQL worksheet, or copy the formatted text to paste in Google Docs or another editor. 

Additionally, the "Snowflake Solution Chatter" tab allows you to enter ad hoc questions to help find Snowflake-centric responses or do further research.
