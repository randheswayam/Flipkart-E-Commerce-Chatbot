from groq import Groq
import os
import re
import sqlite3
import pandas as pd
from pathlib import Path
from dotenv import load_dotenv
from pandas import DataFrame


load_dotenv()

GROQ_MODEL = os.getenv('GROQ_MODEL')

db_path = Path(__file__).parent / "db.sqlite"

client_sql = Groq()

sql_prompt = """You are an expert in understanding the database schema and generating SQL queries for a natural language question asked
pertaining to the data you have. The schema is provided in the schema tags. 
<schema> 
table: product 

fields: 
product_link - string (hyperlink to product)	
title - string (name of the product)	
brand - string (brand of the product)	
price - integer (price of the product in Indian Rupees)	
discount - float (discount on the product. 10 percent discount is represented as 0.1, 20 percent as 0.2, and such.)	
avg_rating - float (average rating of the product. Range 0-5, 5 is the highest.)	
total_ratings - integer (total number of ratings for the product)

</schema>
Make sure whenever you try to search for the brand name, the name can be in any case. 
So, make sure to use %LIKE% to find the brand in condition. Never use "ILIKE". 
Create a single SQL query for the question provided. 
The query should have all the fields in SELECT clause (i.e. SELECT *)

Just the SQL query is needed, nothing more. Always provide the SQL in between the <SQL></SQL> tags."""

def generate_sql_query(question):
    chat_completion = client_sql.chat.completions.create(
        messages=[
            {
                "role": "system",
                "content": sql_prompt,
            },
            {
                "role": "user",
                "content": question,
            }
        ],
        model=os.environ['GROQ_MODEL'],
        temperature=0.2,
        max_tokens=1024
    )

    response = chat_completion.choices[0].message.content
    print(response)   
    return response 

def run_query(query):
    if query.strip().upper().startswith('SELECT'):
        with sqlite3.connect(db_path) as conn:
            df = pd.read_sql_query(query,conn)
            return df 

if __name__ == "__main__":
    question = "All NIKE shoes in price range 5000 to 10000"
    sql_query = generate_sql_query(question)
    print(sql_query)
    # query = "SELECT * from product where brand LIKE'%nike%'"
    # df = run_query(query)
    # pass 
