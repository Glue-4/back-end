from flask import Flask, jsonify, request
import mysql.connector
from mysql.connector import errorcode
from langchain_openai import OpenAI
import json

app = Flask(__name__)

# Konfigurasi koneksi MySQL
config = {
    'user': 'root',      # Ganti dengan username MySQL Anda
    'password': '',      # Ganti dengan password MySQL Anda
    'host': 'localhost',
    'database': 'lokergo_test',  # Ganti dengan nama database Anda
    'raise_on_warnings': True
}

def get_table_fields(cursor, table_name):
    cursor.execute(f"DESCRIBE {table_name}")
    columns = cursor.fetchall()
    field_names = [column[0] for column in columns]  # Hanya mengambil nama field
    return field_names

def get_database_schema(cursor):
    cursor.execute("SHOW TABLES")
    tables = cursor.fetchall()
    schema = {}
    for (table_name,) in tables:
        schema[table_name] = get_table_fields(cursor, table_name)
    return schema

# Setup OpenAI API key
openai_api_key = ''
llm = OpenAI(api_key=openai_api_key)

# Route untuk endpoint '/'
# @app.route('/')
# def index():
#     try:
#         cnx = mysql.connector.connect(**config)
#         cursor = cnx.cursor()

#         schema = get_database_schema(cursor)

#         cursor.close()
#         cnx.close()

#         return jsonify(schema)
    
#     except mysql.connector.Error as err:
#         if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
#             return jsonify({"error": "Salah username atau password, cek lagi!"})
#         elif err.errno == errorcode.ER_BAD_DB_ERROR:
#             return jsonify({"error": "Databasenya ngga ada!"})
#         else:
#             return jsonify({"error": str(err)})
#     except Exception as e:
#         return jsonify({"error": str(e)})

# Route untuk endpoint '/query'
@app.route('/query', methods=['POST'])
def query():
    try:
        # Ambil data JSON dari request
        data = request.json
        question = data['question']
        
        # Koneksi ke database
        cnx = mysql.connector.connect(**config)
        cursor = cnx.cursor()

        # Dapatkan skema database
        schema = get_database_schema(cursor)

        # Generate prompt untuk pertanyaan SQL menggunakan OpenAI GPT-3
        schema_str = '\n'.join(f"- {table}: {', '.join(fields)}" for table, fields in schema.items())
        prompt = f"""Berdasarkan skema database (lokergo_test) dibawah, tuliskan query SQL yang dapat menjawab pertanyaan user berikut, tulis query SQL tanpa penjelasan apapun:
        {schema_str}
        
        Pertanyaan user: {question}"""

        response = llm(prompt)

        sql_query = response.replace("?", "").replace("\\n", "\n").strip()

        print(sql_query)

        # Eksekusi query
        cursor.execute(sql_query)
        result = cursor.fetchall()


        print(result)

        cursor.close()
        cnx.close()


        return jsonify({"sql_query": sql_query, "result": result})
    
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
