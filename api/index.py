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
              body["biography"], body["email"], hashed_password 
              ))
        
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
        if not roles:
            return jsonify({"message": "No hay roles disponibles"}), 404
        return jsonify({"roles": roles}), 200
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
       
        hashed_password = hash_password(password)  # Hashear la contraseña ingresada
       
        cursor.execute("SELECT id, username, role_id, password FROM users WHERE username = %s", 
                       (username,))
        user = cursor.fetchone()
        
        if user and user["password"] == hashed_password:
            token = jwt.encode({
                "user_id": user["id"],
                "username": user["username"],
                "role_id": user["role_id"],
                "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=2)
            }, SECRET_KEY, algorithm="HS256")

            return jsonify({"message": "Login exitoso", "token": token}), 200
        else:
            return jsonify({"message": "Credenciales incorrectas"}), 401

    except Exception as e:
        logging.error(f"Error en el login: {e}")
        return jsonify({"message": "Error en el login"}), 500
    finally:
        cursor.close()
        connection.close()

@app.route('/activities', methods=['POST', 'GET'])
def create_activity():
    connection = get_db_connection()
    if not connection:
        return jsonify({"message": "Error de conexión con la base de datos"}), 500

    cursor = connection.cursor()
    try:
        # Si el método es POST, insertamos una nueva actividad
        if request.method == 'POST':
            body = request.get_json()

            # Inserción de la actividad en la tabla activities
            cursor.execute("""
                INSERT INTO activities (
                    category_id, location_id, name, description, duration, difficulty, 
                    min_participants, max_participants, is_available, 
                    is_public, cost, activity_image_url
                ) 
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (
                body["category_id"], body["location_id"], body["name"], body["description"], 
                body["duration"], body["difficulty"], body["min_participants"], body["max_participants"], 
                body["cancellation_policy"], body["is_available"], body["is_public"], 
                body["cost"], body["activity_image_url"]
            ))

            activity_id = cursor.fetchone()[0]  # Obtenemos el id de la actividad recién insertada

            # Ahora, relacionamos la actividad con un viaje (usando trip_id de la solicitud)
            cursor.execute("""
                INSERT INTO activity_trips (activity_id, trip_id)
                VALUES (%s, %s)
            """, (activity_id, body["trip_id"]))  # Se espera que body contenga el trip_id

            connection.commit()
            return jsonify({"message": "Actividad creada y asociada al viaje correctamente"}), 201

        # Si es GET, devuelve las actividades (o categorías de actividades según necesidad)
        elif request.method == 'GET':
            cursor.execute("SELECT * FROM activities")
            activities = cursor.fetchall()

            if not activities:
                return jsonify({"message": "No hay actividades disponibles"}), 404

            return jsonify({"activities": activities}), 200

    except Exception as e:
        logging.error(f"Error al crear o consultar la actividad: {e}")
        return jsonify({"message": "Error al crear o consultar la actividad"}), 500
    finally:
        cursor.close()
        connection.close()

@app.route('/activitycategory', methods=['GET'])  
def get_activity_categories():  
    """Obtiene todas las categorías de actividades"""  
    connection = get_db_connection()  
    if not connection:  
        return jsonify({"message": "Error de conexión con la base de datos"}), 500  

    cursor = connection.cursor(dictionary=True)  # Esto devuelve los resultados como diccionarios
    try:  
        cursor.execute("SELECT * FROM activity_categories")  
        activity_categories = cursor.fetchall()  

        if not activity_categories:  
            return jsonify({"message": "No hay categorías disponibles"}), 404  

        return jsonify({"categories": activity_categories}), 200  
    except Exception as e:  
        logging.error(f"Error al obtener categorías: {e}")  
        return jsonify({"message": "Error al obtener las categorías"}), 500  
    finally:  
        cursor.close()  
        connection.close()  

@app.route('/locations', methods=['GET'])
def get_locations():
    """Obtiene todas las localizaciones de actividades"""
    connection = get_db_connection()
    if not connection:
        return jsonify({"message": "Error de conexión con la base de datos", "status_code": 500}), 500

    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute("SELECT * FROM locations")
        locations = cursor.fetchall()

        if not locations:
            return jsonify({"message": "No hay localizaciones disponibles", "status_code": 404}), 404

        return jsonify({"locations": locations, "status_code": 200}), 200
    except mysql.connector.Error as e:
        logging.error(f"Error al obtener localizaciones: {e}")
        return jsonify({"message": "Error al obtener las localizaciones", "status_code": 500}), 500
    finally:
        cursor.close()
        if connection.is_connected():
            connection.close()

@app.route('/trips', methods=['POST'])
def create_trip():
    """Crea un nuevo viaje"""
    connection = get_db_connection()
    if not connection:
        return jsonify({"message": "Error de conexión con la base de datos"}), 500

    cursor = connection.cursor()
    try:
        body = request.get_json()

        cursor.execute("""
            INSERT INTO trips (
                trip_name, description, start_date, end_date, trip_status, 
                participants_number, estimated_weather_forecast, total_cost, trip_image_url
            ) 
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (body["trip_name"], body["description"], body["start_date"], body["end_date"], 
              body["trip_status"], body["participants_number"], body["estimated_weather_forecast"], 
              body["total_cost"], body["trip_image_url"]))

        connection.commit()
        return jsonify({"message": "Viaje creado correctamente"}), 201
    except Exception as e:
        logging.error(f"Error al crear el viaje: {e}")
        return jsonify({"message": "Error al crear el viaje"}), 500
    finally:
        cursor.close()
        connection.close()

import uuid

@app.route('/rangers', methods=['GET'])
def get_rangers():
    connection = get_db_connection()
    if not connection:
        return jsonify({"message": "Error de conexión con la base de datos"}), 500

    cursor = connection.cursor()
    try:
        ranger_role_id = uuid.UUID('8f285ee6-7ded-473d-8c57-5159a489e7e6')

        cursor.execute("""
            SELECT first_name, last_name, username 
            FROM users 
            WHERE role_id = %s::uuid
        """, (str(ranger_role_id),))

        rangers = cursor.fetchall()

        if not rangers:
            return jsonify({"message": "No hay rangers disponibles"}), 404

       
        formatted_rangers = [
            {"full_name": f"{r['first_name']} {r['last_name']} ({r['username']})"}
            for r in rangers
        ]

        return jsonify({"rangers": formatted_rangers}), 200

    except Exception as e:
        logging.error(f"Error al obtener rangers: {e}")
        return jsonify({"message": "Error al obtener los rangers"}), 500
    finally:
        cursor.close()
        connection.close()

if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True, port=5000)


  

