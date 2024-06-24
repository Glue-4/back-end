import os
from flask import Flask, jsonify, request
import mysql.connector
from mysql.connector import errorcode
from langchain_openai import OpenAI
from dotenv import load_dotenv


app = Flask(__name__)

# Konfigurasi MySQL
user = os.getenv("DB_USER")
password = os.getenv("DB_PASSWORD")
host = os.getenv("DB_HOST")
database = os.getenv("DB_NAME")

config = {
    'user': user, 
    'password': password,
    'host': host,
    'database': database,
    'raise_on_warnings': True
}

def get_table_fields(cursor, table_name):
    cursor.execute(f"DESCRIBE {table_name}")
    columns = cursor.fetchall()
    field_names = [column[0] for column in columns]
    return field_names

def get_database_schema(cursor):
    cursor.execute("SHOW TABLES")
    tables = cursor.fetchall()
    schema = {}
    for (table_name,) in tables:
        schema[table_name] = get_table_fields(cursor, table_name)
    return schema

# Setup OpenAI API key dari ENV

load_dotenv()
openai_api_key = os.getenv("OPENAI_API_KEY")
llm = OpenAI(api_key=openai_api_key)

# Route untuk endpoint '/'
@app.route('/')
def index():
    return jsonify({"message": "Selamat datang di API Backend Chat with MySQL (Kelompok Glue 4)"})

# Route untuk endpoint '/query'
@app.route('/query', methods=['POST'])
def query():
    try:
        # Ambil data JSON dari request
        data = request.json
        question = data['question']
        
        # Konek ke database
        cnx = mysql.connector.connect(**config)
        cursor = cnx.cursor()

        # Ngambil Skema Database
        schema = get_database_schema(cursor)

        # Bikin pertanyaan
        schema_str = '\n'.join(f"- {table}: {', '.join(fields)}" for table, fields in schema.items())
        prompt_query = f"""Berdasarkan skema database (lokergo_test) dibawah, tuliskan query SQL yang dapat menjawab pertanyaan user berikut, tulis query SQL tanpa penjelasan apapun:
        {schema_str}
        
        Pertanyaan user: {question}"""

        response_query = llm(prompt_query)

        sql_query = response_query.replace("?", "").replace("\\n", "\n").strip()

        print(sql_query)

        # Eksekusi query
        cursor.execute(sql_query)
        result = cursor.fetchall()

        print(result)

        cursor.close()
        cnx.close()

        prompt_jawaban = f"""Berdasarkan pertanyaan user dibawah dan berdasarkan data yang sudah di dapat dari database (lokergo_test), berikan kalimat jawaban yang sesuai:
        Pertanyaan user: {question}
        Hasil Query: {result}"""

        response_jawaban = llm(prompt_jawaban)
        return jsonify({"sql_query": sql_query, "result": result, "jawaban": response_jawaban})
    
    except mysql.connector.Error as err:
        if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
            return jsonify({"error": "Salah username atau password, cek lagi!"})
        elif err.errno == errorcode.ER_BAD_DB_ERROR:
            return jsonify({"error": "Databasenya ngga ada!"})
        else:
            return jsonify({"error": str(err)})
    except Exception as e:
        return jsonify({"error": str(e)})

if __name__ == '__main__':
    app.run(debug=True)
