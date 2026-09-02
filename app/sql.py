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
For product categories or attributes mentioned by the user, use case-insensitive
LOWER(column) LIKE '%value%' conditions. For words such as "shoes", "women's",
or "running", search the title with separate LIKE conditions when appropriate.
Convert shorthand such as 10k or 5K to 10000 or 5000 before comparing price. 
Create a single SQL query for the question provided. 
The query should have all the fields in SELECT clause (i.e. SELECT *)

Just the SQL query is needed, nothing more. Always provide the SQL in between the <SQL></SQL> tags."""


comprehension_prompt = """You are an expert in understanding the context of the question and replying based on the data pertaining to the question provided. You will be provided with Question: and Data:. The data will be in the form of an array or a dataframe or dict. Reply based on only the data provided as Data for answering the question asked as Question. Do not write anything like 'Based on the data' or any other technical words. Just a plain simple natural language response.
The Data would always be in context to the question asked. For example is the question is “What is the average rating?” and data is “4.3”, then answer should be “The average rating for the product is 4.3”. So make sure the response is curated with the question and data. Make sure to note the column names to have some context, if needed, for your response.
Think carefully internally, but return only the final user-facing answer. Never return a <think> block, analysis, or planning text.
There can also be cases where you are given an entire dataframe in the Data: field. Always remember that the data field contains the answer of the question asked. All you need to do is to always reply in the following format when asked about a product: 
Produt title, price in indian rupees, discount, and rating, and then product link. Take care that all the products are listed in list format, one line after the other. Not as a paragraph.
For example:
1. Campus Women Running Shoes: Rs. 1104 (35 percent off), Rating: 4.4 <link>
2. Campus Women Running Shoes: Rs. 1104 (35 percent off), Rating: 4.4 <link>
3. Campus Women Running Shoes: Rs. 1104 (35 percent off), Rating: 4.4 <link>

"""


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
        max_tokens=4096
    )

    return chat_completion.choices[0].message.content



def run_query(query):
    if not query or not query.strip().upper().startswith('SELECT'):
        return None

    try:
        with sqlite3.connect(db_path) as conn:
            return pd.read_sql_query(query, conn)
    except (sqlite3.Error, ValueError):
        return None


def data_comprehension(question, context):
    chat_completion = client_sql.chat.completions.create(
        messages=[
            {
                "role": "system",
                "content": comprehension_prompt,
            },
            {
                "role": "user",
                "content": f"QUESTION: {question}. DATA: {context}",
            }
        ],
        model=os.environ['GROQ_MODEL'],
        temperature=0.2,
        max_tokens=2048
    )

    return remove_thinking(chat_completion.choices[0].message.content)


def remove_thinking(response):
    cleaned_response = re.sub(r"<think>.*?</think>", "", response, flags=re.IGNORECASE | re.DOTALL)
    if re.match(r"^\s*<think\b", cleaned_response, re.IGNORECASE):
        return ""
    return cleaned_response.strip()


def format_product_results(products):
    formatted_products = []
    for index, product in enumerate(products, start=1):
        title = product.get('title', 'Product')
        price = product.get('price', 'price unavailable')
        discount = product.get('discount')
        rating = product.get('avg_rating', 'not rated')
        link = product.get('product_link', '')
        discount_text = f", {discount * 100:.0f}% off" if isinstance(discount, (int, float)) else ""
        formatted_products.append(
            f"{index}. [{title}]({link}) - Rs. {price}{discount_text}, Rating: {rating}"
        )
    return "Here are the products I found:\n\n" + "\n".join(formatted_products)


def extract_sql_query(response):
    response = re.sub(r"<think>.*?</think>", "", response, flags=re.IGNORECASE | re.DOTALL)

    tagged_match = re.search(r"<SQL>\s*(.*?)\s*</SQL>", response, re.IGNORECASE | re.DOTALL)
    if tagged_match:
        return extract_statement(tagged_match.group(1))

    incomplete_tagged_match = re.search(r"<SQL>\s*(SELECT\b.*?)(?:\s*</SQL>|$)", response, re.IGNORECASE | re.DOTALL)
    if incomplete_tagged_match:
        return extract_statement(incomplete_tagged_match.group(1))

    fenced_match = re.search(r"```(?:sql)?\s*(.*?)\s*```", response, re.IGNORECASE | re.DOTALL)
    if fenced_match:
        return extract_statement(fenced_match.group(1))

    opening_fence = re.search(r"```(?:sql)?\s*", response, re.IGNORECASE)
    if opening_fence:
        return extract_statement(response[opening_fence.end():])

    without_fence = re.sub(r"```(?:sql)?", "", response, flags=re.IGNORECASE).strip()
    query_matches = list(re.finditer(r"\bSELECT\b", without_fence, re.IGNORECASE))
    for match in reversed(query_matches):
        query = extract_statement(without_fence[match.start():])
        if query and re.search(r"\bFROM\s+product\b", query, re.IGNORECASE):
            return query
    return extract_statement(without_fence[query_matches[-1].start():]) if query_matches else None


def extract_statement(text):
    statement = text.strip().strip('`').strip()
    if ';' in statement:
        statement = statement.split(';', 1)[0] + ';'
    else:
        lines = []
        for line in statement.splitlines():
            stripped_line = line.strip()
            if not stripped_line:
                break
            if lines and not re.match(
                r"^(from|where|and|or|order\s+by|group\s+by|having|limit|offset|join|left\s+join|right\s+join|inner\s+join|on|union)\b|^[,)]",
                stripped_line,
                re.IGNORECASE,
            ):
                break
            lines.append(line)
        statement = '\n'.join(lines).strip().strip('`').strip()
    return statement if statement.upper().startswith('SELECT') else None



def sql_chain(question):
    sql_query = extract_sql_query(generate_sql_query(question))

    if sql_query is None:
        return "Sorry, LLM is not able to generate a query for your question"

    print(sql_query)

    response = run_query(sql_query)
    if response is None:
        return "Sorry, there was a problem executing SQL query"
    if response.empty:
        return "I couldn't find any products matching that request. Try changing the brand, price, or category."

    context = response.to_dict(orient='records')

    answer = data_comprehension(question, context)
    return answer or format_product_results(context)


if __name__ == "__main__":
    # question = "All shoes with rating higher than 4.5 and total number of reviews greater than 500"
    # sql_query = generate_sql_query(question)
    # print(sql_query)
    question = "Show top 3 shoes in descending order of rating"
    # question = "Show me 3 running shoes for woman"
    # question = "sfsdfsddsfsf"
    answer = sql_chain(question)
    print(answer)
