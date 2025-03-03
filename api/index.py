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
import json
load_dotenv()

app = Flask(__name__)
# Combined CORS configuration
CORS(app)

# Add a specific OPTIONS handler - KEEP ONLY THIS ONE
@app.route('/', defaults={'path': ''}, methods=['OPTIONS'])
@app.route('/<path:path>', methods=['OPTIONS'])
def options_handler(path=''):
    response = jsonify({'status': 'ok'})
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,POST,PUT,DELETE,OPTIONS')
    return response

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
    logging.info("Register attempt received")
    connection = get_db_connection()
    if not connection:
        logging.error("Database connection failed during registration")
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
    logging.info("Login attempt received")
    connection = get_db_connection()
    if not connection:
        logging.error("Database connection failed during login")
        return jsonify({"message": "Error de conexión con la base de datos"}), 500

    cursor = connection.cursor()
    try:
        body = request.get_json()
        logging.info(f"Login request body: {body}")
        username = body.get("username")
        password = body.get("password")

        if not username or not password:
            logging.warning("Missing username or password")
            return jsonify({"message": "Debe ingresar usuario y contraseña"}), 400
       
        hashed_password = hash_password(password)  # Hashear la contraseña ingresada
        logging.info(f"Attempting login for user: {username}")

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
            
            # Ensure token is string, not bytes
            if isinstance(token, bytes):
                token = token.decode('utf-8')
            
            logging.info(f"Login successful for user: {username}")
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
            logging.warning(f"Invalid credentials for user: {username}")
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

        # Convertir UUID a strings
        activities_converted = [dict(activity, id=str(activity['id'])) for activity in activities]

        return jsonify({"activities": activities_converted}), 200
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

@app.route('/trips', methods=['POST'])
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

    cursor = connection.cursor(cursor_factory=RealDictCursor)
    try:  
        cursor.execute("SELECT * FROM resources")  
        resources = cursor.fetchall()  

        # Convertir UUID a strings
        resources_converted = [dict(resource, id=str(resource['id'])) for resource in resources]

        return jsonify({"resources": resources_converted}), 200  
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

@app.route('/reservations/user/<user_id>', methods=['GET'])
def get_reservations_by_user(user_id):
    connection = get_db_connection()
    if not connection:
        return jsonify({"message": "Error de conexión con la base de datos"}), 500

    cursor = connection.cursor()  # Using RealDictCursor from get_db_connection
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

@app.route('/reservations/<string:reservation_id>', methods=['DELETE'])
def delete_reservation(reservation_id):
    logging.info(f"Attempting to delete reservation with ID: {reservation_id}")
    connection = get_db_connection()
    if not connection:
        return jsonify({"message": "Error de conexión con la base de datos"}), 500
    
    cursor = connection.cursor()
    try:
        cursor.execute("DELETE FROM reservations WHERE id = %s RETURNING id", (reservation_id,))
        deleted = cursor.fetchone()
        
        if not deleted:
            logging.warning(f"Reservation not found: {reservation_id}")
            return jsonify({"message": "Reserva no encontrada"}), 404
            
        connection.commit()
        logging.info(f"Successfully deleted reservation: {reservation_id}")
        return jsonify({"message": "Reserva eliminada correctamente"}), 200
    
    except Exception as e:
        logging.error(f"Error deleting reservation: {str(e)}")
        return jsonify({"message": f"Error interno del servidor: {str(e)}"}), 500
    finally:
        cursor.close()
        connection.close()

# Alternative reservation deletion endpoint - by trip ID
@app.route('/reservations/trip/<string:trip_id>', methods=['DELETE'])
def delete_reservation_by_trip(trip_id):
    logging.info(f"Attempting to delete reservation with trip ID: {trip_id}")
    connection = get_db_connection()
    if not connection:
        return jsonify({"message": "Error de conexión con la base de datos"}), 500
    
    cursor = connection.cursor()
    try:
        # Try to find and delete by trip_id
        cursor.execute("DELETE FROM reservations WHERE trip_id = %s RETURNING id", (trip_id,))
        deleted = cursor.fetchone()
        
        if not deleted:
            logging.warning(f"No reservation found for trip: {trip_id}")
            return jsonify({"message": "Reserva no encontrada"}), 404
            
        connection.commit()
        logging.info(f"Successfully deleted reservation for trip: {trip_id}")
        return jsonify({"message": "Reserva eliminada correctamente"}), 200
    
    except Exception as e:
        logging.error(f"Error deleting reservation: {str(e)}")
        return jsonify({"message": f"Error interno del servidor: {str(e)}"}), 500
    finally:
        cursor.close()
        connection.close()

# More specific endpoint - by trip and user ID
@app.route('/reservations/trip/<string:trip_id>/user/<string:user_id>', methods=['DELETE'])
def delete_reservation_by_trip_user(trip_id, user_id):
    logging.info(f"Attempting to delete reservation with trip ID: {trip_id} and user ID: {user_id}")
    connection = get_db_connection()
    if not connection:
        return jsonify({"message": "Error de conexión con la base de datos"}), 500
        cursor = connection.cursor()
    try:
        # Try to find and delete by both trip_id and user_id
        cursor.execute(
            "DELETE FROM reservations WHERE trip_id = %s AND user_id = %s RETURNING id", 
            (trip_id, user_id)
        )
        
        deleted = cursor.fetchone()
        
        if not deleted:
            logging.warning(f"No reservation found for trip: {trip_id} and user: {user_id}")
            return jsonify({"message": "Reserva no encontrada"}), 404
            
        connection.commit()
        logging.info(f"Successfully deleted reservation for trip: {trip_id} and user: {user_id}")
        return jsonify({"message": "Reserva eliminada correctamente"}), 200
    
    except Exception as e:
        logging.error(f"Error deleting reservation: {str(e)}")
        return jsonify({"message": f"Error interno del servidor: {str(e)}"}), 500
    finally:
        cursor.close()
        connection.close()
    

    
@app.route('/reservations/trip/<trip_id>/explorers', methods=['GET'])
def get_explorers_by_trip(trip_id):
    """Obtiene la lista de exploradores registrados en un viaje específico"""
    connection = get_db_connection()
    if not connection:
        logging.error("No se pudo conectar a la base de datos")
        return jsonify({"error": "No se pudo conectar a la base de datos"}), 500

    try:
       
        with connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
         
            
            query = """
                SELECT 
                    users.id, 
                    CONCAT(users.first_name, ' ', users.last_name) AS name, 
                    users.email, 
                    users.phone_number AS phone, 
                    reservations.status
                FROM reservations
                JOIN users ON reservations.user_id = users.id
                WHERE reservations.trip_id = %s;
            """
            cursor.execute(query, (trip_id,))
            explorers_data = cursor.fetchall()
            
            # Convertir a lista de diccionarios planos para asegurar serialización JSON correcta
            explorers = []
            for explorer in explorers_data:
                # Si ya es un diccionario (con RealDictCursor/DictCursor)
                if hasattr(explorer, 'items'):
                    explorer_dict = dict(explorer)
                else:
                    # Si es una tupla (con cursor estándar)
                    explorer_dict = {
                        "id": explorer[0],
                        "name": explorer[1],
                        "email": explorer[2],
                        "phone": explorer[3],
                        "status": explorer[4]
                    }
                
                # Convertir UUID a string si es necesario
                if isinstance(explorer_dict.get('id'), (uuid.UUID)):
                    explorer_dict['id'] = str(explorer_dict['id'])
                
                explorers.append(explorer_dict)

            # Agregar log para depuración
            logging.info(f"Datos de exploradores obtenidos: {explorers}")
            
            return jsonify({"explorers": explorers}), 200

    except Exception as e:
        logging.error(f"Error en la consulta SQL: {str(e)}")
        return jsonify({"error": "Error interno del servidor", "details": str(e)}), 500

    finally:
        connection.close()

@app.route('/resources', methods=['POST'])
def create_resource():
    """Crea un nuevo recurso"""
    logging.info("Attempting to create a new resource")
    connection = get_db_connection()
    if not connection:
        return jsonify({"message": "Error de conexión con la base de datos"}), 500
    
    cursor = connection.cursor()
    try:
       
        body = request.get_json()
        if not body:
            return jsonify({"message": "No se proporcionaron datos"}), 400
            
        
        required_fields = ['name', 'description', 'cost']
        for field in required_fields:
            if field not in body:
                return jsonify({"message": f"Campo requerido faltante: {field}"}), 400
                
      
        try:
            cost = float(body.get("cost"))
        except (ValueError, TypeError):
            return jsonify({"message": "El costo debe ser un valor numérico"}), 400
            
     
        cursor.execute("SELECT 1 FROM resources WHERE name = %s", (body.get("name"),))
        if cursor.fetchone():
            return jsonify({"message": "Ya existe un recurso con ese nombre"}), 409
            
      
        description = body.get("description")
        if isinstance(description, dict) or isinstance(description, list):
            # Already in the right format - psycopg2 will handle JSON serialization
            description_json = description
        else:
            # Try to parse the string as JSON
            try:
                description_json = json.loads(description) if isinstance(description, str) else description
            except json.JSONDecodeError:
                return jsonify({"message": "El campo description debe ser un JSON válido"}), 400
                
        # Insert the new resource
        cursor.execute("""
            INSERT INTO resources (name, description, cost)
            VALUES (%s, %s, %s)
            RETURNING id, name
        """, (
            body.get("name"),
            psycopg2.extras.Json(description_json),  # Properly handle JSONB
            cost
        ))
        
        created = cursor.fetchone()
        connection.commit()
        
        logging.info(f"Successfully created resource: {created['name']}")
        return jsonify({
            "message": "Recurso creado correctamente",
            "resource": {
                "id": str(created["id"]),
                "name": created["name"]
            }
        }), 201
        
    except psycopg2.IntegrityError as e:
        logging.error(f"Integrity error: {str(e)}")
        connection.rollback()
        return jsonify({"message": "Error de integridad en la base de datos"}), 400
        
    except Exception as e:
        logging.error(f"Error creating resource: {str(e)}")
        connection.rollback()
        return jsonify({"message": f"Error interno del servidor: {str(e)}"}), 500
    finally:
        cursor.close()
        connection.close()


@app.route('/resources/<string:resource_id>', methods=['DELETE'])
def delete_resource(resource_id):
    """Elimina un recurso por su ID"""
    logging.info(f"Attempting to delete resource with ID: {resource_id}")
    connection = get_db_connection()
    if not connection:
        return jsonify({"message": "Error de conexión con la base de datos"}), 500
    
    cursor = connection.cursor()
    try:
        # Validate UUID format
        try:
            resource_uuid = uuid.UUID(resource_id)
        except ValueError:
            return jsonify({"message": "Formato de UUID inválido"}), 400
            
        # Check if resource exists
        cursor.execute("SELECT 1 FROM resources WHERE id = %s", (str(resource_uuid),))
        if not cursor.fetchone():
            return jsonify({"message": "Recurso no encontrado"}), 404
        
        # Check if resource is referenced in trip_resources and get trip names
        cursor.execute("""
            SELECT t.trip_name, t.id
            FROM trip_resources tr
            JOIN trips t ON tr.trip_id = t.id
            WHERE tr.resource_id = %s
        """, (str(resource_uuid),))
        
        trips = cursor.fetchall()
        
        if trips:
            # Create a list of trip names
            trip_names = [trip['trip_name'] for trip in trips]
            
            # Format the trip names for display
            if len(trip_names) == 1:
                trip_list = f'"{trip_names[0]}"'
            elif len(trip_names) == 2:
                trip_list = f'"{trip_names[0]}" y "{trip_names[1]}"'
            else:
                trip_list = ", ".join([f'"{name}"' for name in trip_names[:-1]]) + f' y "{trip_names[-1]}"'
            
            # Return detailed error message
            return jsonify({
                "message": f"No se puede eliminar este recurso porque está siendo utilizado por el/los viaje(s): {trip_list}. Debe eliminar estas referencias primero.",
                "references": len(trips),
                "trips": [{"id": str(trip["id"]), "name": trip["trip_name"]} for trip in trips]
            }), 409
        
        # If no references, delete the resource
        cursor.execute("DELETE FROM resources WHERE id = %s RETURNING id, name", (str(resource_uuid),))
        deleted = cursor.fetchone()
        
        if not deleted:
            return jsonify({"message": "No se pudo eliminar el recurso"}), 500
            
        # Commit changes
        connection.commit()
        
        logging.info(f"Successfully deleted resource: {resource_id}")
        return jsonify({
            "message": f"Recurso '{deleted['name']}' eliminado correctamente", 
            "id": str(deleted["id"])
        }), 200
        
    except Exception as e:
        # Rollback in case of error
        connection.rollback()
        logging.error(f"Error deleting resource: {str(e)}")
        return jsonify({"message": f"Error interno del servidor: {str(e)}"}), 500
    finally:
        cursor.close()
        connection.close()
        
            
@app.route('/resources/<string:resource_id>', methods=['PUT'])
def update_resource(resource_id):
    """Actualiza un recurso por su ID"""
    logging.info(f"Attempting to update resource with ID: {resource_id}")
    connection = get_db_connection()
    if not connection:
        return jsonify({"message": "Error de conexión con la base de datos"}), 500
    
    cursor = connection.cursor()
    try:
        # Validate UUID format
        try:
            resource_uuid = uuid.UUID(resource_id)
        except ValueError:
            return jsonify({"message": "Formato de UUID inválido"}), 400
        
        # Get request body
        body = request.get_json()
        if not body:
            return jsonify({"message": "No se proporcionaron datos para actualizar"}), 400
            
        # Check required fields
        required_fields = ['name', 'description', 'cost']
        for field in required_fields:
            if field not in body:
                return jsonify({"message": f"Campo requerido faltante: {field}"}), 400
                
        # Validate cost is numeric
        try:
            cost = float(body.get("cost"))
        except (ValueError, TypeError):
            return jsonify({"message": "El costo debe ser un valor numérico"}), 400
            
        # Check if resource exists
        cursor.execute("SELECT 1 FROM resources WHERE id = %s", (str(resource_uuid),))
        if not cursor.fetchone():
            return jsonify({"message": "Recurso no encontrado"}), 404
            
        # Check for name uniqueness (if changing name)
        cursor.execute("""
            SELECT 1 FROM resources 
            WHERE name = %s AND id != %s
        """, (body.get("name"), str(resource_uuid)))
        
        if cursor.fetchone():
            return jsonify({"message": "Ya existe un recurso con ese nombre"}), 409
            
        # Serialize description as JSON if it's not already
        description = body.get("description")
        if isinstance(description, dict) or isinstance(description, list):
            # Already in the right format - psycopg2 will handle JSON serialization
            description_json = description
        else:
            # Try to parse the string as JSON
            try:
                description_json = json.loads(description) if isinstance(description, str) else description
            except json.JSONDecodeError:
                return jsonify({"message": "El campo description debe ser un JSON válido"}), 400
                
        # Update the resource
        cursor.execute("""
            UPDATE resources 
            SET name = %s, description = %s, cost = %s
            WHERE id = %s
            RETURNING id, name
        """, (
            body.get("name"),
            psycopg2.extras.Json(description_json),  # Properly handle JSONB
            cost,
            str(resource_uuid)
        ))
        
        updated = cursor.fetchone()
        connection.commit()
        
        logging.info(f"Successfully updated resource: {resource_id}")
        return jsonify({
            "message": "Recurso actualizado correctamente",
            "resource": {
                "id": str(updated["id"]),
                "name": updated["name"]
            }
        }), 200
        
    except psycopg2.IntegrityError as e:
        logging.error(f"Integrity error: {str(e)}")
        connection.rollback()
        return jsonify({"message": "Error de integridad en la base de datos"}), 400
        
    except Exception as e:
        logging.error(f"Error updating resource: {str(e)}")
        connection.rollback()
        return jsonify({"message": f"Error interno del servidor: {str(e)}"}), 500
    finally:
        cursor.close()
        connection.close()

@app.route('/trips-resources', methods=['POST'])
def create_trip_resource_association():
    """Crea una asociación entre un viaje y un recurso"""
    logging.info("Attempting to create a trip-resource association")
    connection = get_db_connection()
    if not connection:
        return jsonify({"message": "Error de conexión con la base de datos"}), 500
    
    cursor = connection.cursor()
    try:
        # Get request body
        body = request.get_json()
        if not body:
            return jsonify({"message": "No se proporcionaron datos"}), 400
        
        # Check required fields
        required_fields = ['trip_id', 'resource_id']
        for field in required_fields:
            if field not in body:
                return jsonify({"message": f"Campo requerido faltante: {field}"}), 400
        
        # Validate UUID formats
        try:
            trip_id = uuid.UUID(body["trip_id"])
            resource_id = uuid.UUID(body["resource_id"])
        except ValueError:
            return jsonify({"message": "Formato de UUID inválido"}), 400
            
        # Check if trip exists
        cursor.execute("SELECT 1 FROM trips WHERE id = %s", (str(trip_id),))
        if not cursor.fetchone():
            return jsonify({"message": "El viaje especificado no existe"}), 404
            
        # Check if resource exists
        cursor.execute("SELECT 1 FROM resources WHERE id = %s", (str(resource_id),))
        if not cursor.fetchone():
            return jsonify({"message": "El recurso especificado no existe"}), 404
        
        # Check if association already exists
        cursor.execute("""
            SELECT 1 FROM trip_resources 
            WHERE trip_id = %s AND resource_id = %s
        """, (str(trip_id), str(resource_id)))
        
        if cursor.fetchone():
            return jsonify({"message": "Esta asociación ya existe"}), 409
            
        # Create the association
        cursor.execute("""
            INSERT INTO trip_resources (trip_id, resource_id)
            VALUES (%s, %s)
            RETURNING id
        """, (
            str(trip_id),
            str(resource_id)
        ))
        
        association_id = cursor.fetchone()["id"]
        connection.commit()
        
        logging.info(f"Successfully created trip-resource association with ID: {association_id}")
        return jsonify({
            "message": "Asociación entre viaje y recurso creada correctamente",
            "id": str(association_id)
        }), 201
        
    except psycopg2.IntegrityError as e:
        logging.error(f"Integrity error: {str(e)}")
        connection.rollback()
        return jsonify({"message": "Error de integridad en la base de datos"}), 400
        
    except Exception as e:
        logging.error(f"Error creating trip-resource association: {str(e)}")
        connection.rollback()
        return jsonify({"message": f"Error interno del servidor: {str(e)}"}), 500
    finally:
        cursor.close()
        connection.close()
        
@app.route('/trips/<string:trip_id>/resources', methods=['GET'])
def get_trip_resources(trip_id):
    """Obtiene todos los recursos asociados a un viaje específico"""
    logging.info(f"Fetching resources for trip ID: {trip_id}")
    connection = get_db_connection()
    if not connection:
        return jsonify({"message": "Error de conexión con la base de datos"}), 500
    
    cursor = connection.cursor()
    try:
        # Validate UUID format
        try:
            trip_uuid = uuid.UUID(trip_id)
        except ValueError:
            return jsonify({"message": "Formato de UUID inválido"}), 400
            
        # First check if trip exists
        cursor.execute("SELECT trip_name FROM trips WHERE id = %s", (str(trip_uuid),))
        trip = cursor.fetchone()
        if not trip:
            return jsonify({"message": "El viaje no existe"}), 404
            
        # Query trip resources with resource details
        cursor.execute("""
            SELECT r.id, r.name, r.description, r.cost, tr.id as association_id
            FROM trip_resources tr
            JOIN resources r ON tr.resource_id = r.id
            WHERE tr.trip_id = %s
        """, (str(trip_uuid),))
        
        resources = cursor.fetchall()
        
        return jsonify({
            "trip_id": trip_id,
            "trip_name": trip["trip_name"],
            "resources": resources
        }), 200
        
    except Exception as e:
        logging.error(f"Error getting trip resources: {str(e)}")
        return jsonify({"message": f"Error interno del servidor: {str(e)}"}), 500
    finally:
        cursor.close()
        connection.close()

if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True, port=5000)