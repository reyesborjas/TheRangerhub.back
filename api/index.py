from flask import Flask, request, jsonify
import psycopg2
import os
import hashlib
import jwt
import datetime
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
from flask_cors import CORS

load_dotenv()
app = Flask(__name__)
CORS(app)

SECRET_KEY = "tu_secreto_super_seguro"

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

def hash_password(password):
    """Hashea la contraseña con SHA-256"""
    return hashlib.sha256(password.encode()).hexdigest()

@app.route('/')
def home():
    return 'Hello, World!'

@app.route('/about')
def about():
    return 'About'

@app.route('/register', methods=['POST'])
def register():
    connection = get_db_connection()
    if not connection:
        return jsonify({"message": "Error de conexión con la base de datos"}), 500

    cursor = connection.cursor()
    try:
        body = request.get_json()

        # Hashear la contraseña antes de insertarla en la BD
        hashed_password = hash_password(body["password"])

        cursor.execute("""
            INSERT INTO users (
            username, first_name, last_name, nationality, rut, passport_number, 
            role_id, biography, email, password, availability_start_date, 
            availability_end_date, user_status, profile_visibility
            ) 
            VALUES (
                %s, %s, %s, %s, %s, %s, 
                %s, %s, %s, %s, %s, 
                %s, %s, %s
            )
            """, (body["username"], body["first_name"], body["last_name"], body["nationality"], 
                body["rut"], body["passport_number"], body["role_id"], 
                body["biography"], body["email"], hashed_password, 
                body["availability_start_date"], body["availability_end_date"], 
                body["user_status"], body["profile_visibility"]))
        
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
    if not connection:
        return jsonify({"message": "Error de conexión con la base de datos"}), 500

    cursor = connection.cursor()
    try:
        cursor.execute("SELECT * FROM user_roles")
        roles = cursor.fetchall()
        return jsonify({"roles": roles}), 200  # Código 200 (OK) en lugar de 201
    except Exception as e:
        print(e)
        return jsonify({"message": "Error al obtener los roles"}), 500
    finally:
        cursor.close()
        connection.close()

@app.route('/login', methods=['POST'])
def login():
    connection = get_db_connection()
    if not connection:
        return jsonify({"message": "Error de conexión con la base de datos"}), 500

    cursor = connection.cursor()
    try:
        body = request.get_json()
        username = body.get("username")
        password = body.get("password")

        if not username or not password:
            return jsonify({"message": "Faltan datos"}), 400

        # Hashear la contraseña antes de compararla con la BD
        hashed_password = hash_password(password)

        cursor.execute("SELECT id, username, role_id FROM users WHERE username = %s AND password = %s", (username, hashed_password))
        user = cursor.fetchone()

        if user:
            token = jwt.encode({
                "user_id": user["id"],
                "username": user["username"],
                "role_id": user["role_id"],
                "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=2)  # Expira en 2 horas
            }, SECRET_KEY, algorithm="HS256")

            return jsonify({"message": "Login exitoso", "token": token}), 200
        else:
            return jsonify({"message": "Credenciales incorrectas"}), 401

    except Exception as e:
        print(e)
        return jsonify({"message": "Error en el login"}), 500
    finally:
        cursor.close()
        connection.close()

# Levantar back en local
# app.run(host='0.0.0.0', debug=True, port=5000)
