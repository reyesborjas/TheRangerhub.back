# Esta es la API funcional
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

        cursor.execute(
            """SELECT users.id, users.username, users.role_id, user_roles.role_name, users.password FROM users 
               inner join 
               user_roles
               on users.role_id = user_roles.id WHERE users.username = %s     
            """
        ,(username,))
       
        user = cursor.fetchone()
        
        if user and user["password"] == hashed_password:
            token = jwt.encode({
                "user_id": user["id"],
                "username": user["username"],
                "role_id": user["role_id"],
                'role_name': user['role_name'],
                "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=2)
            }, SECRET_KEY, algorithm="HS256")

            return jsonify({
                "message": "Login exitoso", 
                "token": token,
                "username": user["username"],
                "user": {
                    "id": user["id"],
                    "username": user["username"],
                    "role_id": user["role_id"],
                    "role_name": user['role_name'],
                }
            }), 200
        else:
            return jsonify({"message": "Credenciales incorrectas"}), 401

    except Exception as e:
        logging.error(f"Error en el login: {e}")
        return jsonify({"message": "Error en el login"}), 500
    finally:
        cursor.close()
        connection.close()

@app.route('/activities', methods=['POST'])
def create_activity():
    connection = get_db_connection()
    if not connection:
        return jsonify({"message": "Error de conexión con la base de datos"}), 500

    cursor = connection.cursor()
    try:
        if request.method == 'POST':
            body = request.get_json()
            if not body:
                return jsonify({"message": "No se proporcionaron datos"}), 400

            # Validar tipos de datos
            try:
                duration = float(body.get("duration"))
                min_participants = int(body.get("min_participants"))
                max_participants = int(body.get("max_participants"))
                cost = float(body.get("cost"))
            except (ValueError, TypeError) as e:
                return jsonify({"message": f"Error en los tipos de datos: {str(e)}"}), 400

            # Inserción de la actividad en la tabla activities
            cursor.execute("""
                INSERT INTO activities (
                    category_id, location_id, name, description, duration, difficulty, 
                    min_participants, max_participants, is_available, 
                    is_public, cost, activity_image_url
                ) 
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (
                body.get("category_id"), body.get("location_id"), body.get("name"), 
                body.get("description"), duration, body.get("difficulty"), 
                min_participants, max_participants, body.get("is_available", True), 
                body.get("is_public", True), cost, body.get("activity_image_url")
            ))

            activity_id = cursor.fetchone()["id"]  # Obtenemos el id de la actividad recién insertada
            connection.commit()

            return jsonify({
                "message": "Actividad creada correctamente",
                "activity_id": activity_id
            }), 201
    
    except psycopg2.IntegrityError as e:
        logging.error(f"Error al crear la actividad: {e}")
        return jsonify({"message": "Error al crear la actividad"}), 400
    
    except Exception as e:
        logging.error(f"Error al crear la actividad: {e}")
        return jsonify({"message": "Error al crear la actividad"}), 500
    finally:
        cursor.close()
        connection.close()
            
@app.route('/activities', methods=['GET'])
def get_all_activities():
    connection = get_db_connection()
    if not connection:
        return jsonify({"message": "Error de conexión con la base de datos"}), 500

    cursor = connection.cursor(cursor_factory=RealDictCursor)
    try:
        cursor.execute("SELECT * FROM activities")
        activities = cursor.fetchall()

        if not activities:
            return jsonify({"message": "No hay actividades disponibles"}), 404

        return jsonify({"activities": activities}), 200
    except Exception as e:
        logging.error(f"Error al obtener actividades: {e}")
        return jsonify({"message": "Error interno del servidor"}), 500
    finally:
        cursor.close()
        connection.close()
            
@app.route('/activity-trips', methods=['POST'])
def associate_activity_trip():
    try:
        body = request.get_json()
        
        # Validar presencia de campos
        if 'activity_id' not in body or 'trip_id' not in body:
            return jsonify({"message": "Faltan campos requeridos: activity_id o trip_id"}), 400
        
        # Validar formato UUID
        try:
            activity_id = uuid.UUID(body["activity_id"])
            trip_id = uuid.UUID(body["trip_id"])
        except ValueError:
            return jsonify({"message": "Formato de UUID inválido"}), 400
        
        # Obtener conexión
        connection = get_db_connection()
        if not connection:
            return jsonify({"message": "Error de conexión con la base de datos"}), 500
            
        cursor = connection.cursor()
        
        try:
            # Verificar existencia de los IDs en sus tablas
            cursor.execute("SELECT 1 FROM activities WHERE id = %s", (str(activity_id),))
            if not cursor.fetchone():
                return jsonify({"message": "La actividad no existe"}), 404
                
            cursor.execute("SELECT 1 FROM trips WHERE id = %s", (str(trip_id),))
            if not cursor.fetchone():
                return jsonify({"message": "El viaje no existe"}), 404
            
            # Verificar relación existente
            cursor.execute("""
                SELECT 1 FROM activity_trips 
                WHERE activity_id = %s AND trip_id = %s
            """, (str(activity_id), str(trip_id)))
            
            if cursor.fetchone():
                return jsonify({"message": "La relación ya existe"}), 409
                
            # Insertar nueva relación
            cursor.execute("""
                INSERT INTO activity_trips (activity_id, trip_id)
                VALUES (%s, %s)
            """, (str(activity_id), str(trip_id)))
            
            connection.commit()
            return jsonify({"message": "Relación creada exitosamente"}), 201
            
        except psycopg2.IntegrityError as e:
            logging.error(f"Error de integridad: {str(e)}")
            return jsonify({"message": "Error en relaciones de base de datos"}), 400
            
        except Exception as e:
            logging.error(f"Error interno: {str(e)}")
            return jsonify({"message": "Error del servidor"}), 500
            
        finally:
            cursor.close()
            connection.close()
            
    except Exception as e:
        logging.error(f"Error general: {str(e)}")
        return jsonify({"message": "Error procesando la solicitud"}), 500

@app.route('/activitycategory', methods=['GET'])  
def get_activity_categories():  
    """Obtiene todas las categorías de actividades"""  
    connection = get_db_connection()  
    if not connection:  
        return jsonify({"message": "Error de conexión con la base de datos"}), 500  

    cursor = connection.cursor()
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
    connection = get_db_connection()
    if not connection:
        return jsonify({"message": "Error de conexión"}), 500

    cursor = connection.cursor(cursor_factory=psycopg2.extras.DictCursor)
    try:
        # Parámetros de búsqueda y filtrado
        search_query = request.args.get('search', '').lower()
        country = request.args.get('country', '').lower()
        province = request.args.get('province', '').lower()
        place_name = request.args.get('place_name', '').lower()
        
        # Parámetros de paginación
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 10))
        offset = (page - 1) * per_page
        
        # Parámetros de ordenamiento
        sort_by = request.args.get('sort_by', 'id')
        order = request.args.get('order', 'asc').upper()
        if order not in ['ASC', 'DESC']:
            order = 'ASC'

        # Construcción dinámica de la consulta
        base_query = "SELECT * FROM locations"
        conditions = []
        params = []
        
        # Filtros
        if search_query:
            search_pattern = f"%{search_query}%"
            conditions.append(
                "(LOWER(place_name) LIKE %s OR "
                "LOWER(country) LIKE %s OR "
                "LOWER(province) LIKE %s)"
            )
            params.extend([search_pattern]*3)
        
        if country:
            conditions.append("LOWER(country) = %s")
            params.append(country)
            
        if province:
            conditions.append("LOWER(province) = %s")
            params.append(province)
            
        if place_name:
            conditions.append("LOWER(place_name) LIKE %s")
            params.append(f"%{place_name}%")

        # Ensamblar consulta
        if conditions:
            base_query += " WHERE " + " AND ".join(conditions)
            
        # Ordenamiento
        base_query += f" ORDER BY {sort_by} {order}"
        
        # Paginación
        base_query += " LIMIT %s OFFSET %s"
        params.extend([per_page, offset])

        # Ejecutar consulta
        cursor.execute(base_query, params)
        locations = cursor.fetchall()
        
        # Obtener total para paginación
        count_query = "SELECT COUNT(*) FROM locations"
        if conditions:
            count_query += " WHERE " + " AND ".join(conditions)
        cursor.execute(count_query, params[:-2])  # Excluir LIMIT y OFFSET
        total = cursor.fetchone()[0]

        return jsonify({
            "locations": [dict(row) for row in locations],
            "pagination": {
                "total": total,
                "page": page,
                "per_page": per_page,
                "total_pages": (total + per_page - 1) // per_page
            }
        }), 200

    except Exception as e:
        logging.error(f"Error: {str(e)}")
        return jsonify({"message": "Error al obtener localizaciones"}), 500
    finally:
        cursor.close()
        connection.close()

@app.route('/trips', methods=['POST','PUT'])
def create_trip():
    connection = get_db_connection()
    if not connection:
        return jsonify({"message": "Error de conexión con la base de datos"}), 500

    cursor = connection.cursor()
    try:
        body = request.get_json()
        
        # Validar campos requeridos
        required_fields = ['trip_name', 'lead_ranger', 'start_date', 'end_date']
        for field in required_fields:
            if field not in body:
                return jsonify({"message": f"Campo requerido faltante: {field}"}), 400

        # Insertar con todos los campos correctos
        cursor.execute("""
            INSERT INTO trips (
                trip_name, start_date, end_date, participants_number,
                trip_status, estimated_weather_forecast, description,
                total_cost, trip_image_url, lead_ranger
            ) 
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            body.get("trip_name"),
            body.get("start_date"),
            body.get("end_date"),
            body.get("participants_number", 0),
            body.get("trip_status", "pending"),
            body.get("estimated_weather_forecast", ""),
            body.get("description", ""),
            body.get("total_cost", 0),
            body.get("trip_image_url", ""),
            body["lead_ranger"]  
        ))

        trip_row = cursor.fetchone()
        trip_id = trip_row["id"]
        connection.commit()
        
        return jsonify({
            "message": "Viaje creado exitosamente",
            "id": str(trip_id)
        }), 201

    except Exception as e:
        logging.error(f"Error en creación de viaje: {str(e)}")
        return jsonify({"message": "Error interno del servidor"}), 500
    finally:
        cursor.close()
        connection.close()
        
@app.route('/rangers', methods=['GET'])
def get_rangers():
    connection = get_db_connection()
    if not connection:
        return jsonify({"error": "Database connection failed"}), 500

    try:
        cursor = connection.cursor(cursor_factory=RealDictCursor)
        
        # 1. Obtener ID del rol Ranger
        cursor.execute("SELECT id FROM user_roles WHERE role_name = 'Ranger'")
        role = cursor.fetchone()
        
        if not role or 'id' not in role:
            return jsonify({"error": "Rol Ranger no configurado"}), 404

        # 2. Query corregida
        cursor.execute("""
            SELECT id, first_name, last_name, username 
            FROM users 
            WHERE role_id = %s
            AND user_status = 'activo'  -- Filtro adicional
        """, (role['id'],))

        # 3. Formatear respuesta
        rangers = cursor.fetchall()
        return jsonify({
            "rangers": [
                {
                    "id": str(r['id']),
                    "full_name": f"{r['first_name']} {r['last_name']}",
                    "username": r['username']
                } for r in rangers
            ]
        }), 200

    except Exception as e:
        logging.error(f"Error en /rangers: {str(e)}")
        return jsonify({"error": "Error interno al obtener rangers"}), 500
    finally:
        if 'cursor' in locals(): cursor.close()
        if connection: connection.close()
        
@app.route('/trips', methods=['GET'])  
def get_trips():
    connection = get_db_connection()  
    if not connection:  
        return jsonify({"message": "Error de conexión con la base de datos"}), 500  

    cursor = connection.cursor()
    try:  
        cursor.execute("SELECT * FROM trips")  
        trips = cursor.fetchall()  

        if not trips:  
            return jsonify({"message": "No hay viajes disponibles"}), 404  

        return jsonify({"trips": trips}), 200  
    except Exception as e:  
        logging.error(f"Error al obtener viajes: {e}")  
        return jsonify({"message": "Error al obtener los viajes"}), 500  
    finally:  
        cursor.close()
        connection.close()
        
@app.route('/resources', methods=['GET']) 
def get_resources():  
    connection = get_db_connection()  
    if not connection:  
        return jsonify({"message": "Error de conexión con la base de datos"}), 500  

    cursor = connection.cursor()
    try:  
        cursor.execute("SELECT * FROM resources")  
        resources = cursor.fetchall()  

        if not resources:  
            return jsonify({"message": "No hay recursos disponibles"}), 404  

        return jsonify({"resources": resources}), 200  
    except Exception as e:  
        logging.error(f"Error al obtener recursos: {e}")  
        return jsonify({"message": "Error al obtener los recursos"}), 500  
    finally:  
        cursor.close()
        connection.close()
        
@app.route('/reservations', methods=['POST'])
def create_reservation():
    connection = get_db_connection()
    if not connection:
        return jsonify({"message": "Error de conexión con la base de datos"}), 500

    cursor = connection.cursor()
    try:
        body = request.get_json()
        
        # Validar campos requeridos
        required_fields = ['trip_id', 'user_id','status']
        for field in required_fields:
            if field not in body:
                return jsonify({"message": f"Campo requerido faltante: {field}"}), 400

        # Insertar con todos los campos correctos
        cursor.execute("""
            INSERT INTO reservations (
                trip_id, user_id, status
            ) 
            VALUES (%s, %s, %s)
            RETURNING id
        """, (
            body.get("trip_id"),
            body.get("user_id"),
            body.get("status")
        ))

        reservation_row = cursor.fetchone()
        reservation_id = reservation_row["id"]
        connection.commit()
        
        return jsonify({
            "message": "Reserva creada exitosamente",
            "id": str(reservation_id)
        }), 201

    except Exception as e:
        logging.error(f"Error en creación de reserva: {str(e)}")
        return jsonify({"message": "Error interno del servidor"}), 500
    finally:
        cursor.close()
        connection.close()

@app.route('/reservations/<string:reservation_id>', methods=['DELETE'])
def delete_reservation(reservation_id):
    connection = get_db_connection()
    if not connection:
        return jsonify({"message": "Error de conexión con la base de datos"}), 500
    cursor = connection.cursor()
    try:
        cursor.execute("DELETE FROM reservations WHERE id = %s", (reservation_id,))
        if cursor.rowcount == 0: 
            return jsonify({"message": "Reserva no encontrada"}), 404
        connection.commit()
        return jsonify({"message": "Reserva eliminada correctamente"}), 200
    except Exception as e:
        logging.error(f"Error al eliminar la reserva: {str(e)}")
        return jsonify({"message": "Error interno del servidor"}), 500
    finally:
        cursor.close()
        connection.close()

        
# Endpoint para Rangers
@app.route('/trips/ranger/<uuid:user_id>', methods=['GET'])
def get_ranger_trips(user_id):
    connection = get_db_connection()
    try:
        cursor = connection.cursor()
        cursor.execute("""
            SELECT * FROM trips 
            WHERE lead_ranger = %s::uuid
        """, (str(user_id),))
        trips = cursor.fetchall()
        return jsonify({"trips": trips}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()
        connection.close()

# Endpoint para Explorers
@app.route('/trips/explorer/<uuid:user_id>', methods=['GET'])
def get_explorer_trips(user_id):
    connection = get_db_connection()
    try:
        cursor = connection.cursor()
        
        # Paso 1: Obtener reservas del usuario
        cursor.execute("""
            SELECT trip_id FROM reservations 
            WHERE user_id = %s::uuid
        """, (str(user_id),))
        reservations = cursor.fetchall()
        trip_ids = [str(r['trip_id']) for r in reservations]

        # Paso 2: Obtener viajes relacionados
        if trip_ids:
            cursor.execute("""
                SELECT * FROM trips 
                WHERE id::text = ANY(%s)
            """, (trip_ids,))
            trips = cursor.fetchall()
        else:
            trips = []

        return jsonify({"trips": trips}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()
        connection.close()

@app.route('/reservations/explorer/<uuid:user_id>', methods=['GET'])
def get_reservations_explorer(user_id):

    connection = get_db_connection()
    if not connection:
        return jsonify({"message": "Error de conexión con la base de datos"}), 500

    cursor = connection.cursor()
    try:
        cursor.execute(""" 
            SELECT * FROM reservations inner join
            trips 
            on reservations.trip_id = trips.id
            where reservations.user_id = %s
        """, (str(user_id),))
        trips = cursor.fetchall()

        if not trips:
            return jsonify({"message": "No hay reservas disponibles"}), 404

        return jsonify({"trips": trips}), 200
    except Exception as e:
        logging.error(f"Error al obtener reservas: {e}")
        return jsonify({"message": "Error al obtener las reservas"}), 500
    finally:
        cursor.close()
        connection.close()

@app.route('/reservations/ranger/<uuid:user_id>', methods=['GET'])
def get_reservations_ranger(user_id):
    connection = get_db_connection()
    if not connection:
        return jsonify({"message": "Error de conexión con la base de datos"}), 500

    cursor = connection.cursor()
    try:
        cursor.execute(""" 
           select * from trips where trips.lead_ranger = %s
        """, (str(user_id),))
        trips = cursor.fetchall()

        if not trips:
            return jsonify({"message": "No hay reservas disponibles"}), 404

        return jsonify({"trips": trips}), 200
    except Exception as e:
        logging.error(f"Error al obtener reservas: {e}")
        return jsonify({"message": "Error al obtener las reservas"}), 500
    finally:
        cursor.close()
        connection.close()      

import uuid  # Importar módulo para trabajar con UUIDs

@app.route('/reservations/user/<user_id>', methods=['GET'])
def get_reservations_by_user(user_id):
    connection = get_db_connection()
    if not connection:
        return jsonify({"message": "Error de conexión con la base de datos"}), 500

    cursor = connection.cursor(dictionary=True)  # Habilita la conversión de filas a diccionarios
    try:
        # Convertir el user_id a UUID (manejar error si el formato es incorrecto)
        try:
            user_uuid = uuid.UUID(user_id)
        except ValueError:
            return jsonify({"message": "Formato de UUID inválido"}), 400

        # Consulta SQL con UUID
        cursor.execute("SELECT * FROM reservations WHERE user_id = %s", (str(user_uuid),))
        reservations = cursor.fetchall()

        if not reservations:
            return jsonify({"message": "No se encontraron reservas para este usuario"}), 404

        return jsonify({"reservations": reservations}), 200

    except Exception as e:
        logging.error(f"Error al obtener reservas: {str(e)}")
        return jsonify({"message": "Error interno del servidor"}), 500
    finally:
        cursor.close()
        connection.close()



if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True, port=5000)