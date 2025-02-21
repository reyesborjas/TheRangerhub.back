from flask import Flask, request, jsonify
import psycopg2
import os
import hashlib
import jwt
import datetime
import logging
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
from flask_cors import CORS
import uuid

load_dotenv()

app = Flask(__name__)
CORS(app)

logging.basicConfig(level=logging.INFO)

SECRET_KEY = os.getenv("SECRET_KEY", "super_secreto_por_defecto")

def get_db_connection():
    """Conecta a la base de datos PostgreSQL"""
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
        logging.error(f"Error al conectar con la base de datos: {e}")
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
    """Registra un nuevo usuario"""
    connection = get_db_connection()
    if not connection:
        return jsonify({"message": "Error de conexión con la base de datos"}), 500

    cursor = connection.cursor()
    try:
        body = request.get_json()
        hashed_password = hash_password(body["password"])

        cursor.execute("""
            INSERT INTO users (
                username, first_name, last_name, nationality, rut, passport_number, 
                role_id, biography, email, password
            ) 
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (body["username"], body["first_name"], body["last_name"], body["nationality"], 
              body["rut"], body["passport_number"], body["role_id"], 
              body["biography"], body["email"], hashed_password))
        
        connection.commit()
        return jsonify({"message": "Usuario creado correctamente"}), 201
    except Exception as e:
        logging.error(f"Error en el registro: {e}")
        return jsonify({"message": "Error al crear usuario"}), 500
    finally:
        cursor.close()
        connection.close()

@app.route('/roles')
def get_roles():
    """Obtiene todos los roles de usuario"""
    connection = get_db_connection()
    if not connection:
        return jsonify({"message": "Error de conexión con la base de datos"}), 500

    cursor = connection.cursor()
    try:
        cursor.execute("SELECT * FROM user_roles")
        roles = cursor.fetchall()
        return jsonify({"roles": roles if roles else []}), 200
    except Exception as e:
        logging.error(f"Error al obtener roles: {e}")
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
            return jsonify({"message": "Debe ingresar usuario y contraseña"}), 400
       
        hashed_password = hash_password(password)
       
        cursor.execute("SELECT id, username, role_id, password FROM users WHERE username = %s", (username,))
        user = cursor.fetchone()
        
        if user and user["password"] == hashed_password:
            token = jwt.encode({
                "user_id": user["id"],
                "username": user["username"],
                "role_id": user["role_id"],
                "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=2)
            }, SECRET_KEY, algorithm="HS256")

            return jsonify({"message": "Login exitoso", "token": token}), 200
        return jsonify({"message": "Credenciales incorrectas"}), 401

    except Exception as e:
        logging.error(f"Error en el login: {e}")
        return jsonify({"message": "Error en el login"}), 500
    finally:
        cursor.close()
        connection.close()

@app.route('/trips', methods=['GET'])
def get_trips():  
    connection = get_db_connection()  
    if not connection:  
        return jsonify({"message": "Error de conexión con la base de datos"}), 500  

    cursor = connection.cursor()
    try:  
        cursor.execute("SELECT * FROM trips")  
        trips = cursor.fetchall()  

        return jsonify({"trips": trips if trips else []}), 200  
    except Exception as e:  
        logging.error(f"Error al obtener los viajes: {e}")  
        return jsonify({"message": "Error al obtener los viajes"}), 500  
    finally:  
        cursor.close()
        connection.close()

@app.route('/resources', methods=['GET'])
def get_resources():
    """Obtiene todos los recursos"""
    connection = get_db_connection()
    if not connection:
        return jsonify({"message": "Error de conexión con la base de datos"}), 500

    cursor = connection.cursor()
    try:
        cursor.execute("SELECT * FROM resources")
        resources = cursor.fetchall()

        return jsonify({"resources": resources if resources else []}), 200
    except Exception as e:
        logging.error(f"Error al obtener los recursos: {e}")
        return jsonify({"message": "Error al obtener los recursos"}), 500
    finally:
        cursor.close()
        connection.close()

@app.route('/rangers', methods=['GET'])
def get_rangers():
    connection = get_db_connection()
    if not connection:
        return jsonify({"message": "Error de conexión con la base de datos"}), 500

    cursor = connection.cursor()
    try:
        ranger_role_id = "8f285ee6-7ded-473d-8c57-5159a489e7e6"

        cursor.execute("""
            SELECT first_name, last_name, username 
            FROM users 
            WHERE role_id = %s
        """, (ranger_role_id,))

        rangers = cursor.fetchall()

        formatted_rangers = [
            {"full_name": f"{r['first_name']} {r['last_name']} ({r['username']})"}
            for r in rangers
        ]

        return jsonify({"rangers": formatted_rangers if formatted_rangers else []}), 200

    except Exception as e:
        logging.error(f"Error al obtener rangers: {e}")
        return jsonify({"message": "Error al obtener los rangers"}), 500
    finally:
        cursor.close()
        connection.close()

if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True, port=5000)
