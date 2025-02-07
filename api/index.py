from flask import Flask
import psycopg2
import os
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
from flask_cors import CORS 
from flask import request, jsonify

load_dotenv()
app = Flask(__name__)
CORS(app)

def get_db_connection():
    try:
        connection = psycopg2.connect(
            dbname=os.getenv("DATABASE_NAME"),
            user=os.getenv("DATABASE_USER"),
            password=os.getenv("DATABASE_PASSWORD"),
            host=os.getenv("DATABASE_HOST"),
            port=os.getenv("DATABASE_PORT"),
            cursor_factory=RealDictCursor
        )
        return connection
    except Exception as e:
        print(f"Error al conectar con la base de datos: {e}")
        return None

@app.route('/')
def home():
    return 'Hello, World!'

@app.route('/about')
def about():
    return 'About'

@app.route('/register', methods=['POST'])
def register():
    connection = get_db_connection()
    cursor = connection.cursor()
    try:
        body = request.get_json()
        cursor.execute("""
            INSERT INTO users (
            username, first_name, last_name, nationality, rut, passport_number, 
            role_id, biography, email, availability_start_date, 
            availability_end_date, user_status, profile_visibility
            ) 
            VALUES (
                %s, %s, %s, %s, %s, %s, 
                %s, %s, %s, %s, 
                %s, %s, %s
            )
            """, (body["username"], body["first_name"], body["last_name"], body["nationality"], 
                body["rut"], body["passport_number"], body["role_id"], 
                body["biography"], body["email"], body["availability_start_date"], 
                body["availability_end_date"], body["user_status"], body["profile_visibility"]))
        connection.commit()
        return jsonify({"message": "Usuario creado correctamente"}), 201
    except Exception as e:
        print(e)
        return jsonify({"message": "Error al crear usuario"}), 500
    finally:
        cursor.close()
        connection.close()

@app.route('/roles')
def get_roles():
    connection = get_db_connection()
    cursor = connection.cursor()
    try:
        cursor.execute("""SELECT * FROM user_roles""")
        roles = cursor.fetchall()
        return jsonify({"roles":  roles}), 201
    except Exception as e:
        print(e)
        return jsonify({"message": "Error al obtener los roles"}), 500
    finally:
        cursor.close()
        connection.close()

# Levantar back en local
# app.run(host='0.0.0.0', debug=True, port=5000)