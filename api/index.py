import os
import uuid
import hashlib
import datetime
import logging
import json

import jwt
import psycopg2
from psycopg2.extras import RealDictCursor, Json

from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

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



app.route('/')
def home():
    return 'Hello, World!'

@app.route('/about')
def about():
    return 'About'

# Ruta GET actualizada para especialidades

@app.route('/api/user-profile/<string:username>', methods=['GET'])
def get_user_profile(username):
    connection = get_db_connection()
    if not connection:
        return jsonify({"error": "Database connection failed"}), 500

    try:
        cursor = connection.cursor(cursor_factory=RealDictCursor)
        
        # Manejar el caso del usuario actual basado en la sesión
        if username == "current":
            # Obtener el username del usuario actual desde la sesión
            from flask import session
            if 'username' not in session:
                return jsonify({"error": "Authentication required"}), 401
            username = session.get('username')
        
        # Consulta optimizada para obtener todos los campos necesarios
        cursor.execute("""
            SELECT 
                username,
                first_name,
                last_name,
                email,
                nationality,
                country,
                region_state,
                profile_picture_url,
                biography_extend,
                languages
            FROM users 
            WHERE username = %s
        """, (username,))
        
        user = cursor.fetchone()
        
        if not user:
            return jsonify({"error": "Usuario no encontrado"}), 404
        
        # Extraer datos del JSON biography_extend si existe
        postcode = ""
        bio_languages = []
        specialities = []
        
        if user['biography_extend']:
    bio_extend = user['biography_extend']
    print("Contenido de biography_extend:", bio_extend)
    # Manejar tanto string como diccionario
    if isinstance(bio_extend, str):
        import json
        try:
            bio_extend = json.loads(bio_extend)
            if isinstance(bio_extend, dict):
                postcode = bio_extend.get('postcode', "")
                if 'languages' in bio_extend and isinstance(bio_extend['languages'], list):
                    bio_languages = bio_extend['languages']
                if 'specialties' in bio_extend and isinstance(bio_extend['specialties'], list):  # Asegúrate de usar 'specialties'
                    specialities = bio_extend['specialties']
        except Exception as e:
            print("Error al parsear biography_extend:", e)
    elif isinstance(bio_extend, dict):
        postcode = bio_extend.get('postcode', "")
        if 'languages' in bio_extend and isinstance(bio_extend['languages'], list):
            bio_languages = bio_extend['languages']
        if 'specialties' in bio_extend and isinstance(bio_extend['specialties'], list):  # Asegúrate de usar 'specialties'
            specialities = bio_extend['specialties']

# Asegúrate de que las especialidades se estén incluyendo en la respuesta
formatted_user = {
    "username": user['username'],
    "firstName": user['first_name'],
    "lastName": user['last_name'],
    "displayName": f"{user['first_name']} {user['last_name']}",
    "email": user['email'],
    "nationality": user['nationality'] or "",
    "country": user['country'] or "",
    "region": user['region_state'] or "",
    "postcode": postcode,
    "profilePicture": user['profile_picture_url'],
    "languages": languages,
    "specialities": specialities  # Asegúrate de que esto esté presente
}
print("Respuesta formateada:", formatted_user)
return jsonify(formatted_user), 200
   except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Error en get_user_profile: {str(e)}\n{error_details}")
        return jsonify({"error": "Error interno al obtener perfil de usuario", "details": str(e)}), 500
    finally:
        if 'cursor' in locals(): cursor.close()
        if connection: connection.close()
        
# Nueva ruta para verificar la disponibilidad del email
@app.route('/api/check-email-availability', methods=['POST'])
def check_email_availability():
    connection = get_db_connection()
    if not connection:
        return jsonify({"error": "Database connection failed"}), 500
    
    try:
        data = request.json
        if not data or 'email' not in data:
            return jsonify({"error": "Email no proporcionado"}), 400
            
        email = data['email']
        current_username = data.get('currentUsername')  # Para excluir al usuario actual
        
        cursor = connection.cursor()
        
        # Si tenemos un username actual, excluirlo de la búsqueda
        if current_username:
            cursor.execute("SELECT COUNT(*) FROM users WHERE email = %s AND username != %s", (email, current_username))
        else:
            cursor.execute("SELECT COUNT(*) FROM users WHERE email = %s", (email,))
            
        count = cursor.fetchone()[0]
        
        return jsonify({
            "available": count == 0,
            "message": "Email disponible" if count == 0 else "Este email ya está registrado"
        }), 200
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Error en check_email_availability: {str(e)}\n{error_details}")
        return jsonify({"error": "Error al verificar disponibilidad del email", "details": str(e)}), 500
    finally:
        if 'cursor' in locals(): cursor.close()
        if connection: connection.close()

# Nueva ruta para subir foto de perfil
@app.route('/api/upload-profile-picture', methods=['POST'])
def upload_profile_picture():
    connection = get_db_connection()
    if not connection:
        return jsonify({"error": "Database connection failed"}), 500
    
    try:
        # Verificar si hay un archivo en la solicitud
        if 'file' not in request.files:
            return jsonify({"error": "No se envió ningún archivo"}), 400
            
        file = request.files['file']
        
        # Si el usuario no seleccionó un archivo
        if file.filename == '':
            return jsonify({"error": "No se seleccionó ningún archivo"}), 400
            
        # Obtener el username del usuario actual
        from flask import session
        if 'username' not in session:
            return jsonify({"error": "Authentication required"}), 401
            
        username = session.get('username')
        
        # Verificar extensiones permitidas
        allowed_extensions = {'png', 'jpg', 'jpeg', 'gif'}
        if '.' not in file.filename or file.filename.rsplit('.', 1)[1].lower() not in allowed_extensions:
            return jsonify({"error": "Formato de archivo no permitido"}), 400
            
        # Generar nombre único para el archivo
        import uuid
        import os
        filename = f"{uuid.uuid4()}.{file.filename.rsplit('.', 1)[1].lower()}"
        
        # Ruta donde se guardarán las imágenes (ajustar según tu configuración)
        upload_folder = os.path.join('static', 'uploads', 'profile_pictures')
        os.makedirs(upload_folder, exist_ok=True)
        
        # Guardar el archivo
        file_path = os.path.join(upload_folder, filename)
        file.save(file_path)
        
        # URL pública de la imagen
        public_url = f"/static/uploads/profile_pictures/{filename}"
        
        # Actualizar la base de datos con la nueva URL
        cursor = connection.cursor()
        cursor.execute("UPDATE users SET profile_picture_url = %s WHERE username = %s", (public_url, username))
        connection.commit()
        
        return jsonify({
            "message": "Imagen de perfil actualizada correctamente",
            "profilePictureUrl": public_url
        }), 200
        
    except Exception as e:
        if connection:
            connection.rollback()
        import traceback
        error_details = traceback.format_exc()
        print(f"Error en upload_profile_picture: {str(e)}\n{error_details}")
        return jsonify({"error": "Error al subir la imagen de perfil", "details": str(e)}), 500
    finally:
        if 'cursor' in locals(): cursor.close()
        if connection: connection.close()
        
      
@app.route('/api/certifications', methods=['GET'])
def get_certifications():
    connection = get_db_connection()
    if not connection:
        return jsonify({"error": "Database connection failed"}), 500

    try:
        cursor = connection.cursor(cursor_factory=RealDictCursor)
        
        # Obtener todas las certificaciones disponibles
        cursor.execute("""
            SELECT 
                id,
                title,
                description,
                certification_entity,
                created_at
            FROM certifications
            ORDER BY title ASC
        """)
        
        certifications = cursor.fetchall()
        
        # Formatear IDs para JSON
        for cert in certifications:
            cert['id'] = str(cert['id'])
            cert['created_at'] = cert['created_at'].isoformat() if cert['created_at'] else None
        
        return jsonify({"certifications": certifications}), 200

    except Exception as e:
        logging.error(f"Error en /api/certifications: {str(e)}")
        return jsonify({"error": "Error interno al obtener certificaciones"}), 500
    finally:
        if 'cursor' in locals(): cursor.close()
        if connection: connection.close()
        
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

# Ruta PUT actualizada para especialidades

@app.route('/api/user-profile/<string:username>', methods=['PUT'])
def update_user_profile(username):
    connection = get_db_connection()
    if not connection:
        return jsonify({"error": "Database connection failed"}), 500

    try:
        # Obtener datos del request
        data = request.json
        if not data:
            return jsonify({"error": "No se proporcionaron datos"}), 400
        
        cursor = connection.cursor(cursor_factory=RealDictCursor)
        
        # Manejar el caso del usuario actual basado en la sesión
        if username == "current":
            # Obtener el username del usuario actual desde la sesión
            from flask import session
            if 'username' not in session:
                return jsonify({"error": "Authentication required"}), 401
            username = session.get('username')
        
        # Verificar que el usuario existe y obtener sus datos actuales
        cursor.execute("SELECT username, biography_extend FROM users WHERE username = %s", (username,))
        user = cursor.fetchone()
        
        if not user:
            return jsonify({"error": "Usuario no encontrado"}), 404
        
        # Preparar campos para actualizar
        update_fields = []
        update_values = []
        
        # Verificar y añadir los campos a actualizar
        if 'displayName' in data:
            # Dividir el displayName en first_name y last_name
            names = data['displayName'].split(' ', 1)
            first_name = names[0]
            last_name = names[1] if len(names) > 1 else ""
            
            update_fields.append("first_name = %s")
            update_values.append(first_name)
            
            update_fields.append("last_name = %s")
            update_values.append(last_name)
        
        if 'email' in data:
            update_fields.append("email = %s")
            update_values.append(data['email'])
        
        # Actualizar nacionalidad si se proporciona
        if 'nationality' in data:
            update_fields.append("nationality = %s")
            update_values.append(data['nationality'])
        
        # Actualizar país de residencia
        if 'country' in data:
            update_fields.append("country = %s")
            update_values.append(data['country'])
        
        # Actualizar región en region_state
        if 'region' in data:
            update_fields.append("region_state = %s")
            update_values.append(data['region'])
        
        # Actualizar idiomas si se proporcionan
        if 'languages' in data and isinstance(data['languages'], list):
            # Guardar los idiomas en el campo languages (array de PostgreSQL)
            update_fields.append("languages = %s")
            from psycopg2.extensions import AsIs
            update_values.append(AsIs("ARRAY[" + ",".join([f"'{lang}'" for lang in data['languages']]) + "]"))
        
        # Preparar datos para biography_extend (para código postal, idiomas y especialidades)
        update_biography_extend = False
        bio_extend = {}
        
        # Si ya existe biography_extend, cargarlo
        if user['biography_extend']:
            if isinstance(user['biography_extend'], str):
                import json
                try:
                    bio_extend = json.loads(user['biography_extend'])
                except:
                    bio_extend = {}
            elif isinstance(user['biography_extend'], dict):
                bio_extend = user['biography_extend']
        
        # Añadir/actualizar el código postal
        if 'postcode' in data and data['postcode']:
            bio_extend['postcode'] = data['postcode']
            update_biography_extend = True
        
        # Añadir/actualizar los idiomas en biography_extend también
        if 'languages' in data and isinstance(data['languages'], list):
            bio_extend['languages'] = data['languages']
            update_biography_extend = True
        
        # Añadir/actualizar las especialidades en biography_extend
        if 'specialities' in data and isinstance(data['specialities'], list):
            bio_extend['specialities'] = data['specialities']
            update_biography_extend = True
        
        # Añadir a los campos a actualizar si hubo cambios en biography_extend
        if update_biography_extend:
            update_fields.append("biography_extend = %s")
            from psycopg2.extras import Json
            update_values.append(Json(bio_extend))
        
        # Añadir username al final de los valores para la cláusula WHERE
        update_values.append(username)
        
        # Construir y ejecutar la consulta solo si hay campos a actualizar
        if update_fields:
            query = f"UPDATE users SET {', '.join(update_fields)} WHERE username = %s RETURNING username"
            cursor.execute(query, update_values)
            connection.commit()
            
            # Imprimir información de depuración
            print(f"Usuario actualizado: {username}")
            print(f"Campos actualizados: {update_fields}")
            
            return jsonify({"message": "Perfil actualizado correctamente"}), 200
        else:
            return jsonify({"message": "No hay cambios para aplicar"}), 200

    except Exception as e:
        if connection:
            connection.rollback()
        import traceback
        error_details = traceback.format_exc()
        print(f"Error en update_user_profile: {str(e)}\n{error_details}")
        return jsonify({"error": "Error interno al actualizar perfil de usuario", "details": str(e)}), 500
    finally:
        if 'cursor' in locals(): cursor.close()
        if connection: connection.close()

@app.route('/roles')
def get_roles():
    """Obtiene todos los roles de usuario"""
    connection = get_db_connection()
    if not connection:
        return jsonify({"message": "Error de conexión con la base de datos"}), 500

    cursor = connection.cursor()
    try:
        cursor.execute("SELECT * FROM user_roles where role_name != 'Admin'")
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
        
@app.route('/activities/<activity_id>', methods=['PUT'])
def update_activity(activity_id):
    connection = get_db_connection()
    if not connection:
        return jsonify({"message": "Error de conexión con la base de datos"}), 500

    cursor = connection.cursor()
    try:
        if request.method == 'PUT':
            body = request.get_json()
            if not body:
                return jsonify({"message": "No se proporcionaron datos"}), 400

            # Validar tipos de datos
            try:
                duration = float(body.get("duration", 0))
                min_participants = int(body.get("min_participants", 0))
                max_participants = int(body.get("max_participants", 0))
                cost = float(body.get("cost", 0))
            except (ValueError, TypeError) as e:
                return jsonify({"message": f"Error en los tipos de datos: {str(e)}"}), 400

            # Actualización de la actividad en la tabla activities
            cursor.execute("""
                UPDATE activities SET
                    category_id = COALESCE(%s, category_id),
                    location_id = COALESCE(%s, location_id),
                    name = COALESCE(%s, name),
                    description = COALESCE(%s, description),
                    duration = COALESCE(%s, duration),
                    difficulty = COALESCE(%s, difficulty),
                    min_participants = COALESCE(%s, min_participants),
                    max_participants = COALESCE(%s, max_participants),
                    is_available = COALESCE(%s, is_available),
                    is_public = COALESCE(%s, is_public),
                    cost = COALESCE(%s, cost),
                    activity_image_url = COALESCE(%s, activity_image_url)
                WHERE id = %s
                RETURNING *
            """, (
                body.get("category_id"), body.get("location_id"), body.get("name"), 
                body.get("description"), duration if "duration" in body else None, 
                body.get("difficulty"), 
                min_participants if "min_participants" in body else None, 
                max_participants if "max_participants" in body else None, 
                body.get("is_available"), 
                body.get("is_public"), 
                cost if "cost" in body else None, 
                body.get("activity_image_url"),
                activity_id
            ))

            updated_activity = cursor.fetchone()
            
            if not updated_activity:
                return jsonify({"message": "Actividad no encontrada"}), 404
                
            connection.commit()
            
            # Convertir el resultado a un diccionario
            if isinstance(updated_activity, dict):
                # Ya es un diccionario, solo convertir UUID a string si es necesario
                if 'id' in updated_activity and updated_activity['id']:
                    updated_activity['id'] = str(updated_activity['id'])
            else:
                # Convertir a diccionario utilizando nombres de columnas
                columns = [desc[0] for desc in cursor.description]
                updated_activity = dict(zip(columns, updated_activity))
                if 'id' in updated_activity and updated_activity['id']:
                    updated_activity['id'] = str(updated_activity['id'])

            return jsonify({
                "message": "Actividad actualizada correctamente",
                "activity": updated_activity
            }), 200
    
    except psycopg2.IntegrityError as e:
        logging.error(f"Error al actualizar la actividad: {e}")
        return jsonify({"message": "Error al actualizar la actividad: posible violación de restricción"}), 400
    
    except Exception as e:
        logging.error(f"Error al actualizar la actividad: {e}")
        return jsonify({"message": f"Error al actualizar la actividad: {str(e)}"}), 500
    finally:
        cursor.close()
        connection.close()

# También necesitarás una ruta GET individual para obtener una sola actividad
@app.route('/activities/<activity_id>', methods=['GET'])
def get_activity(activity_id):
    connection = get_db_connection()
    if not connection:
        return jsonify({"message": "Error de conexión con la base de datos"}), 500

    cursor = connection.cursor(cursor_factory=RealDictCursor)
    try:
        cursor.execute("SELECT * FROM activities WHERE id = %s", (activity_id,))
        activity = cursor.fetchone()

        if not activity:
            return jsonify({"message": "Actividad no encontrada"}), 404

        # Convertir UUID a string
        activity['id'] = str(activity['id'])

        return jsonify({"activity": activity}), 200
    except Exception as e:
        logging.error(f"Error al obtener la actividad: {e}")
        return jsonify({"message": f"Error interno del servidor: {str(e)}"}), 500
    finally:
        cursor.close()
        connection.close()


# Ya tienes la ruta DELETE, pero si no la tuvieras, aquí está cómo podría ser
@app.route('/activities/<activity_id>', methods=['DELETE'])
def delete_activity(activity_id):
    connection = get_db_connection()
    if not connection:
        return jsonify({"message": "Error de conexión con la base de datos"}), 500

    cursor = connection.cursor()
    try:
        cursor.execute("DELETE FROM activities WHERE id = %s RETURNING id", (activity_id,))
        deleted = cursor.fetchone()
        
        if not deleted:
            return jsonify({"message": "Actividad no encontrada"}), 404
            
        connection.commit()
        return jsonify({"message": "Actividad eliminada correctamente"}), 200
    
    except Exception as e:
        logging.error(f"Error al eliminar la actividad: {e}")
        return jsonify({"message": f"Error al eliminar la actividad: {str(e)}"}), 500
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

@app.route('/trips/<trip_id>/activities', methods=['GET'])
def get_trip_activities(trip_id):
    connection = get_db_connection()
    if not connection:
        return jsonify({"message": "Error de conexión con la base de datos"}), 500

    cursor = connection.cursor(cursor_factory=RealDictCursor)
    try:
        # Consulta para obtener actividades asociadas a un viaje específico
        cursor.execute("""
            SELECT a.*, lo.* 
           FROM activities a
           JOIN activity_trips at ON a.id = at.activity_id
           join locations lo on a.location_id = lo.id
           WHERE at.trip_id = %s
        """, (trip_id,))
         
        
        activities = cursor.fetchall()

        # Convertir UUID a strings
        activities_converted = [dict(activity, id=str(activity['id'])) for activity in activities]

        return jsonify({"activities": activities_converted}), 200
    except Exception as e:
        logging.error(f"Error al obtener actividades del viaje: {e}")
        return jsonify({"message": "Error interno del servidor"}), 500
    finally:
        cursor.close()
        connection.close()

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
        
# Endpoint para obtener las ubicaciones de un viaje específico
@app.route('/trips/<uuid:trip_id>/locations', methods=['GET'])
def get_trip_locations(trip_id):
    connection = get_db_connection()
    try:
        cursor = connection.cursor()
        
        # Consulta para obtener todas las ubicaciones asociadas a las actividades de un viaje
        cursor.execute("""
            SELECT l.id, l.place_name, l.coordinates
            FROM locations l
            JOIN activities a ON l.id = a.location_id
            JOIN activity_trips at ON a.id = at.activity_id
            WHERE at.trip_id = %s::uuid
        """, (str(trip_id),))
        
        locations = cursor.fetchall()
        return jsonify({"locations": locations}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()
        connection.close()

# Endpoint para obtener el próximo viaje según el rol del usuario
@app.route('/next-trip/<uuid:user_id>/<string:role>', methods=['GET'])
def get_next_trip(user_id, role):
    connection = get_db_connection()
    try:
        cursor = connection.cursor()
        
        if role.lower() == 'ranger':
            # Para rangers, buscar en trips donde lead_ranger coincide con user_id
            cursor.execute("""
                SELECT id, trip_name, start_date, trip_status
                FROM trips 
                WHERE lead_ranger = %s::uuid
                AND start_date >= CURRENT_DATE
                ORDER BY start_date ASC
                LIMIT 1
            """, (str(user_id),))
        else:
            # Para explorers, buscar en reservations y unir con trips
            cursor.execute("""
                SELECT t.id, t.trip_name, t.start_date, t.trip_status
                FROM trips t
                JOIN reservations r ON t.id = r.trip_id
                WHERE r.user_id = %s::uuid
                AND t.start_date >= CURRENT_DATE
                ORDER BY t.start_date ASC
                LIMIT 1
            """, (str(user_id),))
        
        trip = cursor.fetchone()
        
        if trip:
            return jsonify({"trip": trip}), 200
        else:
            return jsonify({"message": "No upcoming trips found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()
        connection.close()

@app.route('/trips', methods=['POST'])
def create_or_update_trip():
    connection = get_db_connection()
    if not connection:
        return jsonify({"message": "Error de conexión con la base de datos"}), 500

    cursor = connection.cursor()
    try:
        # Obtener datos del cuerpo de la solicitud
        # Acepta tanto JSON como form-data
        if request.is_json:
            body = request.get_json()
        else:
            body = request.form.to_dict()
        
        # Verificar si estamos actualizando un viaje existente
        trip_id = body.get('id')
        
        # Validar campos requeridos
        required_fields = ['trip_name', 'lead_ranger', 'start_date', 'end_date']
        for field in required_fields:
            if field not in body:
                return jsonify({"message": f"Campo requerido faltante: {field}"}), 400

        if trip_id:
            # ACTUALIZAR VIAJE EXISTENTE
            cursor.execute("""
                UPDATE trips SET
                    trip_name = %s,
                    start_date = %s,
                    end_date = %s,
                    max_participants_number = %s,
                    trip_status = %s,
                    estimated_weather_forecast = %s,
                    description = %s,
                    total_cost = %s,
                    trip_image_url = %s,
                    lead_ranger = %s
                WHERE id = %s
                RETURNING id
            """, (
                body.get("trip_name"),
                body.get("start_date"),
                body.get("end_date"),
                body.get("max_participants_number", 0),
                body.get("trip_status", "pending"),
                body.get("estimated_weather_forecast", ""),
                body.get("description", ""),
                body.get("total_cost", 0),
                body.get("trip_image_url", ""),
                body.get("lead_ranger"),
                trip_id
            ))
            
            result = cursor.fetchone()
            if not result:
                return jsonify({"message": f"No se encontró un viaje con ID {trip_id}"}), 404
                
            connection.commit()
            
            return jsonify({
                "message": "Viaje actualizado exitosamente",
                "id": str(trip_id)
            }), 200
        else:
            # CREAR NUEVO VIAJE
            cursor.execute("""
                INSERT INTO trips (
                    trip_name, start_date, end_date, max_participants_number,
                    trip_status, estimated_weather_forecast, description,
                    total_cost, trip_image_url, lead_ranger
                ) 
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (
                body.get("trip_name"),
                body.get("start_date"),
                body.get("end_date"),
                body.get("max_participants_number", 0),
                body.get("trip_status", "pending"),
                body.get("estimated_weather_forecast", ""),
                body.get("description", ""),
                body.get("total_cost", 0),
                body.get("trip_image_url", ""),
                body.get("lead_ranger")
            ))

            trip_row = cursor.fetchone()
            new_trip_id = trip_row["id"]
            connection.commit()
            
            return jsonify({
                "message": "Viaje creado exitosamente",
                "id": str(new_trip_id)
            }), 201

    except Exception as e:
        logging.error(f"Error en operación de viaje: {str(e)}")
        return jsonify({"message": f"Error interno del servidor: {str(e)}"}), 500
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

        # 2. Query mejorada con más información
        cursor.execute("""
            SELECT 
                u.id, 
                u.first_name, 
                u.last_name, 
                u.username,
                u.email,
                u.phone_number,
                u.nationality,
                u.biography,
                u.profile_picture_url,
                u.availability_start_date,
                u.availability_end_date,
                u.user_status,
                u.biography_extend,
                u.calification,
                COUNT(rc.id) as trips
            FROM users u
            LEFT JOIN ranger_califications rc ON u.id = rc.user_id
            WHERE u.role_id = %s
            GROUP BY u.id
        """, (role['id'],))

        rangers = cursor.fetchall()
        formatted_rangers = []
        
        for r in rangers:
            # Verificar disponibilidad
            is_available = r['user_status'] == 'activo'
            
            # Extraer datos de JSONB
            specialties = []
            languages = []
            title = "Guía Profesional"
            
            if r['biography_extend']:
                bio_extend = r['biography_extend']
                if isinstance(bio_extend, dict):
                    specialties = bio_extend.get('specialties', [])
                    languages = bio_extend.get('languages', [])
                    title = bio_extend.get('title', "Guía Profesional")
            
            ranger_info = {
                "id": str(r['id']),
                "name": f"{r['first_name']} {r['last_name']}",
                "username": r['username'],
                "title": title,
                "photo": r['profile_picture_url'] or "https://randomuser.me/api/portraits/men/32.jpg",
                "email": r['email'],
                "phone": r['phone_number'] or "No disponible",
                "location": r['nationality'] or "Chile",
                "isAvailable": is_available,
                "bio": r['biography'] or "Guía profesional con experiencia en rutas de montaña y senderismo.",
                "rating": float(r['calification']) if r['calification'] else 4.5,
                "trips": r['trips'] or 0,
                "specialties": specialties,
                "languages": languages,
                "certifications": ["Certificado Profesional"]  # Dato estático temporal
            }
            
            formatted_rangers.append(ranger_info)
        
        return jsonify({"rangers": formatted_rangers}), 200

    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        logging.error(f"Error en /rangers: {str(e)}\n{error_details}")
        return jsonify({"error": "Error interno al obtener rangers", "details": str(e)}), 500
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
    
    # Corrección: Mueve esta línea fuera del bloque condicional
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
        connection.rollback()  # Añade rollback en caso de error
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

@app.route('/activity-trips/<trip_id>/<activity_id>', methods=['DELETE'])
def delete_activity_trip(trip_id, activity_id):
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Imprimir valores para depuración
        print(f"Intentando eliminar relación entre viaje {trip_id} y actividad {activity_id}")
        
        # Validar UUIDs
        try:
            uuid_trip = uuid.UUID(trip_id)
            uuid_activity = uuid.UUID(activity_id)
            print(f"UUIDs válidos: {uuid_trip} y {uuid_activity}")
        except ValueError:
            return jsonify({"message": "IDs inválidos"}), 400
        
        # Verificar si existe la relación
        cur.execute(
            "SELECT id FROM activity_trips WHERE trip_id = %s AND activity_id = %s",
            (trip_id, activity_id)
        )
        existing = cur.fetchone()
        print(f"¿Existe la relación antes de eliminar? {existing is not None}")
        
        # Ejecutar la consulta de eliminación
        cur.execute(
            "DELETE FROM activity_trips WHERE trip_id = %s AND activity_id = %s RETURNING id",
            (trip_id, activity_id)
        )
        
        deleted_row = cur.fetchone()
        print(f"Resultado de la eliminación: {deleted_row}")
        
        # Forzar commit explícitamente
        conn.commit()
        
        # Verificar después de la eliminación
        cur.execute(
            "SELECT id FROM activity_trips WHERE trip_id = %s AND activity_id = %s",
            (trip_id, activity_id)
        )
        check_after = cur.fetchone()
        print(f"¿Existe la relación después de eliminar? {check_after is not None}")
        
        cur.close()
        conn.close()
        
        if deleted_row:
            return jsonify({"message": "Actividad eliminada del viaje exitosamente"}), 200
        else:
            return jsonify({"message": "No se encontró la relación entre esa actividad y ese viaje"}), 404
            
    except Exception as e:
        # Si hay excepciones, asegurarnos de cerrar las conexiones
        if 'cur' in locals() and cur is not None:
            cur.close()
        if 'conn' in locals() and conn is not None:
            conn.close()
        print(f"Error al eliminar: {str(e)}")
        return jsonify({"message": f"Error al eliminar la actividad: {str(e)}"}), 500

@app.route('/payments', methods=['POST'])
def create_payment():
    try:
        # Obtener datos del request
        data = request.get_json()
        
        # Validar datos de entrada
        user_id = data.get('user_id')
        trip_id = data.get('trip_id')
        payment_amount = data.get('payment_amount')
        payment_method = data.get('payment_method')
        payment_voucher_url = data.get('payment_voucher_url', None)  # Opcional
        
        # Validaciones básicas
        if not all([user_id, trip_id, payment_amount, payment_method]):
            return jsonify({"error": "Datos de pago incompletos"}), 400
        
        # Establecer conexión a la base de datos
        connection = get_db_connection()
        cursor = connection.cursor()
        
        # Insertar pago con estado pendiente por defecto
        cursor.execute("""
            INSERT INTO payments (
                user_id, 
                trip_id, 
                payment_amount, 
                payment_method, 
                payment_date, 
                payment_voucher_url,
                payment_status
            ) VALUES (%s, %s, %s, %s, CURRENT_DATE, %s, 'pending')
            RETURNING id
        """, (
            user_id, 
            trip_id, 
            payment_amount, 
            payment_method,
            payment_voucher_url
        ))
        
        # Obtener el ID del pago insertado
        payment_id = cursor.fetchone()[0]
        
        # Commit de la transacción
        connection.commit()
        
        return jsonify({
            "message": "Pago iniciado correctamente", 
            "payment_id": payment_id
        }), 201
    
    except Exception as e:
        # Manejo de errores
        logging.error(f"Error creating payment: {str(e)}")
        return jsonify({"error": "Error al procesar el pago"}), 500
    finally:
        # Cerrar cursor y conexión
        if 'cursor' in locals():
            cursor.close()
        if 'connection' in locals():
            connection.close()

@app.route('/trips/action', methods=['POST'])
def trip_action():
    """
    Endpoint para realizar acciones sobre viajes (eliminar/verificar) usando POST en lugar de DELETE
    """
    logging.info("Trip action endpoint called")
    
    # Verificar la autenticación y el rol del usuario
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({"message": "No se proporcionó token de autenticación"}), 401
        
    token = auth_header.split(' ')[1]
    try:
        # Decodificar el token JWT
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        user_role = payload.get('role_name')
        
        # Verificar si el usuario es un Ranger
        if user_role != 'Ranger':
            return jsonify({"message": "No tienes permisos para esta acción. Rol requerido: Ranger"}), 403
    except jwt.ExpiredSignatureError:
        return jsonify({"message": "Token expirado"}), 401
    except jwt.InvalidTokenError:
        return jsonify({"message": "Token inválido"}), 401
    
    # Obtener datos del cuerpo de la solicitud
    body = request.get_json()
    if not body:
        return jsonify({"message": "No se proporcionaron datos"}), 400
        
    action = body.get('action')
    trip_id = body.get('trip_id')
    
    if not action or not trip_id:
        return jsonify({"message": "Faltan parámetros: action y trip_id son requeridos"}), 400
        
    # Validar ID del viaje
    try:
        trip_uuid = uuid.UUID(trip_id)
    except ValueError:
        return jsonify({"message": "Formato de ID de viaje inválido"}), 400
        
    # Obtener conexión a la base de datos
    connection = get_db_connection()
    if not connection:
        return jsonify({"message": "Error de conexión con la base de datos"}), 500
        
    cursor = connection.cursor()
    
    try:
        # Verificar si el viaje existe
        cursor.execute("SELECT id, trip_name FROM trips WHERE id = %s", (str(trip_uuid),))
        trip = cursor.fetchone()
        if not trip:
            return jsonify({"message": "Viaje no encontrado"}), 404
            
        # ACCIÓN: VERIFICAR RESERVACIONES
        if action.lower() == 'check':
            # Verificar si el viaje tiene reservaciones
            cursor.execute("SELECT COUNT(*) as count FROM reservations WHERE trip_id = %s", (str(trip_uuid),))
            result = cursor.fetchone()
            reservation_count = result["count"] if "count" in result else 0
            has_reservations = reservation_count > 0
            
            return jsonify({
                "trip_id": trip_id,
                "hasReservations": has_reservations,
                "reservationCount": reservation_count
            }), 200
            
        # ACCIÓN: ELIMINAR VIAJE
        elif action.lower() == 'delete':
            # Verificar si el viaje tiene reservaciones
            cursor.execute("SELECT id FROM reservations WHERE trip_id = %s LIMIT 1", (str(trip_uuid),))
            has_reservations = cursor.fetchone() is not None
            
            if has_reservations:
                return jsonify({
                    "message": "No se puede eliminar el viaje porque tiene reservaciones existentes"
                }), 400
                
            # Si no tiene reservaciones, proceder con la eliminación
            # Paso 1: Eliminar las actividades asociadas al viaje
            cursor.execute("DELETE FROM activity_trips WHERE trip_id = %s", (str(trip_uuid),))
            activity_count = cursor.rowcount
            logging.info(f"Deleted {activity_count} activities associated with trip {trip_id}")
            
            # Paso 2: Eliminar recursos asociados al viaje (si existen)
            try:
                cursor.execute("DELETE FROM trip_resources WHERE trip_id = %s", (str(trip_uuid),))
                resource_count = cursor.rowcount
                logging.info(f"Deleted {resource_count} resources associated with trip {trip_id}")
            except Exception as e:
                logging.warning(f"Error deleting trip_resources: {str(e)}")
                # Continuamos con la eliminación del viaje incluso si hay error con los recursos
            
            # Paso 3: Eliminar el viaje
            cursor.execute("DELETE FROM trips WHERE id = %s", (str(trip_uuid),))
            
            if cursor.rowcount == 0:
                # Si llegamos aquí, es extraño porque verificamos que existía antes
                connection.rollback()
                return jsonify({"message": "Error al eliminar el viaje"}), 500
                
            # Confirmar todos los cambios en la base de datos
            connection.commit()
            
            trip_name = trip["trip_name"] if "trip_name" in trip else "Desconocido"
            return jsonify({
                "message": f"Viaje '{trip_name}' eliminado exitosamente",
                "activities_removed": activity_count
            }), 200
        
        else:
            return jsonify({"message": f"Acción no reconocida: {action}"}), 400
            
    except Exception as e:
        connection.rollback()
        logging.error(f"Error in trip action: {str(e)}")
        return jsonify({"message": f"Error al procesar la acción: {str(e)}"}), 500
    finally:
        cursor.close()
        connection.close()
    """
    Endpoint para eliminar un viaje si no tiene reservaciones existentes.
    También elimina todas las actividades asociadas al viaje de la tabla activity_trips.
    Solo usuarios con rol Ranger pueden acceder a esta funcionalidad.
    """
    logging.info(f"Attempting to delete trip with ID: {trip_id}")
    
    # Verificar la autenticación y el rol del usuario
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({"message": "No se proporcionó token de autenticación"}), 401
        
    token = auth_header.split(' ')[1]
    try:
        # Decodificar el token JWT
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        user_role = payload.get('role_name')
        
        # Verificar si el usuario es un Ranger
        if user_role != 'Ranger':
            return jsonify({"message": "No tienes permisos para eliminar viajes. Rol requerido: Ranger"}), 403
    except jwt.ExpiredSignatureError:
        return jsonify({"message": "Token expirado"}), 401
    except jwt.InvalidTokenError:
        return jsonify({"message": "Token inválido"}), 401
    
    # Obtener conexión a la base de datos
    connection = get_db_connection()
    if not connection:
        return jsonify({"message": "Error de conexión con la base de datos"}), 500
        
    cursor = connection.cursor()
    
    try:
        # Validar ID del viaje
        try:
            trip_uuid = uuid.UUID(trip_id)
        except ValueError:
            return jsonify({"message": "Formato de ID de viaje inválido"}), 400
            
        # Verificar si el viaje existe
        cursor.execute("SELECT id, trip_name FROM trips WHERE id = %s", (str(trip_uuid),))
        trip = cursor.fetchone()
        if not trip:
            return jsonify({"message": "Viaje no encontrado"}), 404
            
        # Verificar si el viaje tiene reservaciones
        cursor.execute("SELECT id FROM reservations WHERE trip_id = %s LIMIT 1", (str(trip_uuid),))
        has_reservations = cursor.fetchone() is not None
        
        if has_reservations:
            return jsonify({
                "message": "No se puede eliminar el viaje porque tiene reservaciones existentes"
            }), 400
            
        # Si no tiene reservaciones, proceder con la eliminación
        # Paso 1: Eliminar las actividades asociadas al viaje
        cursor.execute("DELETE FROM activity_trips WHERE trip_id = %s", (str(trip_uuid),))
        activity_count = cursor.rowcount
        logging.info(f"Deleted {activity_count} activities associated with trip {trip_id}")
        
        # Paso 2: Eliminar recursos asociados al viaje (si existen)
        try:
            cursor.execute("DELETE FROM trip_resources WHERE trip_id = %s", (str(trip_uuid),))
            resource_count = cursor.rowcount
            logging.info(f"Deleted {resource_count} resources associated with trip {trip_id}")
        except Exception as e:
            logging.warning(f"Error deleting trip_resources: {str(e)}")
            # Continuamos con la eliminación del viaje incluso si hay error con los recursos
        
        # Paso 3: Eliminar el viaje
        cursor.execute("DELETE FROM trips WHERE id = %s", (str(trip_uuid),))
        
        if cursor.rowcount == 0:
            # Si llegamos aquí, es extraño porque verificamos que existía antes
            connection.rollback()
            return jsonify({"message": "Error al eliminar el viaje"}), 500
            
        # Confirmar todos los cambios en la base de datos
        connection.commit()
        
        trip_name = trip["trip_name"] if "trip_name" in trip else "Desconocido"
        return jsonify({
            "message": f"Viaje '{trip_name}' eliminado exitosamente",
            "activities_removed": activity_count
        }), 200
        
    except Exception as e:
        connection.rollback()
        logging.error(f"Error deleting trip: {str(e)}")
        return jsonify({"message": f"Error al eliminar el viaje: {str(e)}"}), 500
    finally:
        cursor.close()
        connection.close()

@app.route('/trips/<trip_id>/check', methods=['GET'])
def check_trip_reservations(trip_id):
    """
    Endpoint para verificar si un viaje tiene reservaciones.
    Solo usuarios con rol Ranger pueden acceder a esta funcionalidad.
    """
    logging.info(f"Checking reservations for trip ID: {trip_id}")
    
    # Verificar la autenticación y el rol del usuario
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({"message": "No se proporcionó token de autenticación"}), 401
        
    token = auth_header.split(' ')[1]
    try:
        # Decodificar el token JWT
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        user_role = payload.get('role_name')
        
        # Verificar si el usuario es un Ranger
        if user_role != 'Ranger':
            return jsonify({"message": "No tienes permisos para verificar este viaje. Rol requerido: Ranger"}), 403
    except jwt.ExpiredSignatureError:
        return jsonify({"message": "Token expirado"}), 401
    except jwt.InvalidTokenError:
        return jsonify({"message": "Token inválido"}), 401
    
    # Obtener conexión a la base de datos
    connection = get_db_connection()
    if not connection:
        return jsonify({"message": "Error de conexión con la base de datos"}), 500
        
    cursor = connection.cursor()
    
    try:
        # Validar ID del viaje
        try:
            trip_uuid = uuid.UUID(trip_id)
        except ValueError:
            return jsonify({"message": "Formato de ID de viaje inválido"}), 400
            
        # Verificar si el viaje existe
        cursor.execute("SELECT id, trip_name FROM trips WHERE id = %s", (str(trip_uuid),))
        trip = cursor.fetchone()
        if not trip:
            return jsonify({"message": "Viaje no encontrado"}), 404
            
        # Verificar si el viaje tiene reservaciones
        cursor.execute("SELECT COUNT(*) as count FROM reservations WHERE trip_id = %s", (str(trip_uuid),))
        result = cursor.fetchone()
        reservation_count = result["count"] if "count" in result else 0
        has_reservations = reservation_count > 0
        
        # Obtener información sobre las reservaciones si existen
        reservations_info = []
        if has_reservations:
            cursor.execute("""
                SELECT r.id, r.status, u.first_name, u.last_name, u.email
                FROM reservations r
                JOIN users u ON r.user_id = u.id
                WHERE r.trip_id = %s
            """, (str(trip_uuid),))
            
            reservations = cursor.fetchall()
            for reservation in reservations:
                reservations_info.append({
                    "id": str(reservation["id"]),
                    "status": reservation["status"],
                    "user": f"{reservation['first_name']} {reservation['last_name']}",
                    "email": reservation["email"]
                })
        
        return jsonify({
            "trip_id": trip_id,
            "trip_name": trip["trip_name"],
            "hasReservations": has_reservations,
            "reservationCount": reservation_count,
            "reservations": reservations_info
        }), 200
        
    except Exception as e:
        logging.error(f"Error checking trip reservations: {str(e)}")
        return jsonify({"message": f"Error al verificar las reservaciones: {str(e)}"}), 500
    finally:
        cursor.close()
        connection.close()
        
@app.route('/trips/<trip_id>', methods=['PUT'])
def edit_trip(trip_id):
    """
    Endpoint para editar un viaje si no tiene reservaciones existentes.
    Solo usuarios con rol Ranger pueden acceder a esta funcionalidad.
    """
    logging.info(f"Attempting to edit trip with ID: {trip_id}")
    
    # Verificar la autenticación y el rol del usuario
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({"message": "No se proporcionó token de autenticación"}), 401
        
    token = auth_header.split(' ')[1]
    try:
        # Decodificar el token JWT
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        user_role = payload.get('role_name')
        
        # Verificar si el usuario es un Ranger
        if user_role != 'Ranger':
            return jsonify({"message": "No tienes permisos para editar viajes. Rol requerido: Ranger"}), 403
    except jwt.ExpiredSignatureError:
        return jsonify({"message": "Token expirado"}), 401
    except jwt.InvalidTokenError:
        return jsonify({"message": "Token inválido"}), 401
    
    # Obtener conexión a la base de datos
    connection = get_db_connection()
    if not connection:
        return jsonify({"message": "Error de conexión con la base de datos"}), 500
        
    cursor = connection.cursor()
    
    try:
        # Validar ID del viaje
        try:
            trip_uuid = uuid.UUID(trip_id)
        except ValueError:
            return jsonify({"message": "Formato de ID de viaje inválido"}), 400
            
        # Verificar si el viaje existe
        cursor.execute("SELECT * FROM trips WHERE id = %s", (str(trip_uuid),))
        trip = cursor.fetchone()
        if not trip:
            return jsonify({"message": "Viaje no encontrado"}), 404
            
        # Verificar si el viaje tiene reservaciones
        cursor.execute("SELECT id FROM reservations WHERE trip_id = %s LIMIT 1", (str(trip_uuid),))
        has_reservations = cursor.fetchone() is not None
        
        if has_reservations:
            return jsonify({
                "message": "No se puede editar el viaje porque tiene reservaciones existentes"
            }), 400
            
        # Si no tiene reservaciones, proceder con la edición
        body = request.get_json()
        if not body:
            return jsonify({"message": "No se proporcionaron datos para actualizar"}), 400
            
        # Construir la consulta SQL dinámicamente con los campos proporcionados
        update_fields = []
        update_values = []
        
        # Campos permitidos para actualizar
        allowed_fields = [
            'trip_name', 'start_date', 'end_date', 'max_participants_number',
            'trip_status', 'estimated_weather_forecast', 'description',
            'total_cost', 'trip_image_url', 'lead_ranger'
        ]
        
        for field in allowed_fields:
            if field in body:
                update_fields.append(f"{field} = %s")
                update_values.append(body[field])
        
        if not update_fields:
            return jsonify({"message": "No se proporcionaron campos válidos para actualizar"}), 400
            
        # Agregar el ID del viaje como último parámetro
        update_values.append(str(trip_uuid))
        
        # Construir y ejecutar la consulta de actualización
        update_query = f"""
            UPDATE trips 
            SET {', '.join(update_fields)}
            WHERE id = %s
            RETURNING id, trip_name
        """
        
        cursor.execute(update_query, update_values)
        updated_trip = cursor.fetchone()
        
        if not updated_trip:
            connection.rollback()
            return jsonify({"message": "Error al actualizar el viaje"}), 500
            
        # Confirmar todos los cambios en la base de datos
        connection.commit()
        
        return jsonify({
            "message": f"Viaje '{updated_trip['trip_name']}' actualizado exitosamente",
            "id": str(updated_trip["id"])
        }), 200
        
    except Exception as e:
        connection.rollback()
        logging.error(f"Error updating trip: {str(e)}")
        return jsonify({"message": f"Error al actualizar el viaje: {str(e)}"}), 500
    finally:
        cursor.close()
        connection.close()

@app.route('/rangers/<string:ranger_id>', methods=['GET'])
def get_ranger_details(ranger_id):
    connection = get_db_connection()
    if not connection:
        return jsonify({"error": "Database connection failed"}), 500

    try:
        cursor = connection.cursor(cursor_factory=RealDictCursor)
        
        # Obtener detalles del ranger por ID
        cursor.execute("""
            SELECT 
                u.id, 
                u.first_name, 
                u.last_name, 
                u.username,
                u.email,
                u.phone_number,
                u.nationality,
                u.biography,
                u.profile_picture_url,
                u.availability_start_date,
                u.availability_end_date,
                u.user_status,
                u.biography_extend,
                u.calification
            FROM users u
            WHERE u.id = %s
        """, (ranger_id,))
        
        ranger = cursor.fetchone()
        
        if not ranger:
            return jsonify({"error": "Ranger no encontrado"}), 404
        
        # Extraer datos del campo JSONB biography_extend
        specialties = []
        languages = []
        
        if ranger['biography_extend']:
            bio_extend = ranger['biography_extend']
            specialties = bio_extend.get('specialties', [])
            languages = bio_extend.get('languages', [])
        
        # Formatear la respuesta
        formatted_ranger = {
            "id": str(ranger['id']),
            "name": f"{ranger['first_name']} {ranger['last_name']}",
            "username": ranger['username'],
            "title": ranger['biography_extend'].get('title', "Guía Profesional") if ranger['biography_extend'] else "Guía Profesional",
            "photo": ranger['profile_picture_url'] or "https://via.placeholder.com/150?text=Ranger",
            "email": ranger['email'],
            "phone": ranger['phone_number'] or "+56 9 xxxx xxxx",
            "location": ranger['nationality'] or "Chile",
            "isAvailable": ranger['user_status'] == 'activo',
            "bio": ranger['biography'] or "Guía profesional con experiencia",
            "rating": float(ranger['calification']) if ranger['calification'] else 0.0,
            "trips": 0,  # Esto debería ser calculado
            "specialties": specialties,
            "languages": languages,
            "certifications": []  # Podrías cargar esto aquí o en una petición separada
        }
        
        return jsonify(formatted_ranger), 200

    except Exception as e:
        logging.error(f"Error en /rangers/{ranger_id}: {str(e)}")
        return jsonify({"error": "Error interno al obtener detalles del ranger"}), 500
    finally:
        if 'cursor' in locals(): cursor.close()
        if connection: connection.close()
        
# 1. Ruta para obtener las certificaciones de un ranger específico
@app.route('/rangers/<string:ranger_id>/certifications', methods=['GET'])
def get_ranger_certifications(ranger_id):
    connection = get_db_connection()
    if not connection:
        return jsonify({"error": "Database connection failed"}), 500

    try:
        cursor = connection.cursor(cursor_factory=RealDictCursor)
        
        # Verificar que el ranger existe y tiene rol de ranger
        cursor.execute("""
            SELECT u.id FROM users u
            JOIN user_roles ur ON u.role_id = ur.id
            WHERE u.id = %s AND ur.role_name = 'Ranger'
        """, (ranger_id,))
        
        if not cursor.fetchone():
            return jsonify({"error": "Ranger no encontrado"}), 404
        
        # Obtener certificaciones del ranger
        cursor.execute("""
            SELECT 
                c.id,
                c.title,
                c.issued_by,
                c.issued_date,
                c.valid_until,
                c.certification_number,
                c.document_url
            FROM certifications c
            JOIN ranger_certifications rc ON c.id = rc.certification_id
            WHERE rc.user_id = %s
            ORDER BY c.valid_until DESC
        """, (ranger_id,))
        
        certifications = cursor.fetchall()
        
        # Formatear fechas para JSON
        for cert in certifications:
            cert['issued_date'] = cert['issued_date'].isoformat() if cert['issued_date'] else None
            cert['valid_until'] = cert['valid_until'].isoformat() if cert['valid_until'] else None
            cert['id'] = str(cert['id'])
        
        return jsonify({"certifications": certifications}), 200

    except Exception as e:
        logging.error(f"Error en /rangers/{ranger_id}/certifications: {str(e)}")
        return jsonify({"error": "Error interno al obtener certificaciones"}), 500
    finally:
        if 'cursor' in locals(): cursor.close()
        if connection: connection.close()

# 2. Ruta para actualizar la disponibilidad de un ranger
@app.route('/rangers/<string:ranger_id>/availability', methods=['PUT'])
def update_ranger_availability(ranger_id):
    connection = get_db_connection()
    if not connection:
        return jsonify({"error": "Database connection failed"}), 500
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Datos no proporcionados"}), 400
        
        # Validar datos
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        
        cursor = connection.cursor()
        
        # Verificar que el ranger existe
        cursor.execute("SELECT id FROM users WHERE id = %s", (ranger_id,))
        if not cursor.fetchone():
            return jsonify({"error": "Ranger no encontrado"}), 404
        
        # Actualizar disponibilidad
        cursor.execute("""
            UPDATE users 
            SET 
                availability_start_date = %s,
                availability_end_date = %s
            WHERE id = %s
        """, (start_date, end_date, ranger_id))
        
        connection.commit()
        
        return jsonify({
            "message": "Disponibilidad actualizada correctamente",
            "availability": {
                "start_date": start_date,
                "end_date": end_date
            }
        }), 200
        
    except Exception as e:
        if connection:
            connection.rollback()
        logging.error(f"Error en update_ranger_availability: {str(e)}")
        return jsonify({"error": "Error al actualizar disponibilidad"}), 500
    finally:
        if 'cursor' in locals(): cursor.close()
        if connection: connection.close()

# 3. Ruta para actualizar el biography_extend de un ranger
@app.route('/rangers/<string:ranger_id>/profile', methods=['PUT'])
def update_ranger_profile(ranger_id):
    connection = get_db_connection()
    if not connection:
        return jsonify({"error": "Database connection failed"}), 500
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Datos no proporcionados"}), 400
        
        cursor = connection.cursor()
        
        # Verificar que el ranger existe
        cursor.execute("SELECT id, biography_extend FROM users WHERE id = %s", (ranger_id,))
        result = cursor.fetchone()
        
        if not result:
            return jsonify({"error": "Ranger no encontrado"}), 404
        
        # Obtener el biography_extend actual o inicializarlo si es None
        current_bio_extend = result[1] if result[1] else {}
        
        # Actualizar los campos proporcionados en biography_extend
        specialties = data.get('specialties')
        languages = data.get('languages')
        title = data.get('title')
        
        if specialties is not None:
            current_bio_extend['specialties'] = specialties
            
        if languages is not None:
            current_bio_extend['languages'] = languages
            
        if title is not None:
            current_bio_extend['title'] = title
        
        # Actualizar biography_extend en la base de datos
        cursor.execute("""
            UPDATE users 
            SET biography_extend = %s
            WHERE id = %s
        """, (Json(current_bio_extend), ranger_id))
        
        connection.commit()
        
        return jsonify({
            "message": "Perfil actualizado correctamente",
            "biography_extend": current_bio_extend
        }), 200
        
    except Exception as e:
        if connection:
            connection.rollback()
        logging.error(f"Error en update_ranger_profile: {str(e)}")
        return jsonify({"error": "Error al actualizar perfil"}), 500
    finally:
        if 'cursor' in locals(): cursor.close()
        if connection: connection.close()

# 4. Ruta para obtener los viajes de un ranger
@app.route('/rangers/<string:ranger_id>/trips', methods=['GET'])
def get_ranger_trips_list(ranger_id):
    connection = get_db_connection()
    if not connection:
        return jsonify({"error": "Database connection failed"}), 500
    
    try:
        cursor = connection.cursor(cursor_factory=RealDictCursor)
        
        # Verificar que el ranger existe
        cursor.execute("SELECT id FROM users WHERE id = %s", (ranger_id,))
        if not cursor.fetchone():
            return jsonify({"error": "Ranger no encontrado"}), 404
        
        # Obtener viajes del ranger
        # Suponiendo que hay una relación entre trips y rangers
        cursor.execute("""
            SELECT 
                t.id,
                t.trip_name,
                t.start_date,
                t.end_date,
                t.status,
                AVG(rc.calification) as avg_rating,
                COUNT(rc.id) as review_count
            FROM trips t
            LEFT JOIN ranger_califications rc ON t.id = rc.trip_id
            WHERE t.ranger_id = %s
            GROUP BY t.id
            ORDER BY t.start_date DESC
        """, (ranger_id,))
        
        trips = cursor.fetchall()
        
        # Formatear fechas para JSON y convertir UUID a string
        for trip in trips:
            trip['start_date'] = trip['start_date'].isoformat() if trip['start_date'] else None
            trip['end_date'] = trip['end_date'].isoformat() if trip['end_date'] else None
            trip['id'] = str(trip['id'])
            trip['avg_rating'] = float(trip['avg_rating']) if trip['avg_rating'] else 0.0
        
        return jsonify({"trips": trips}), 200
        
    except Exception as e:
        logging.error(f"Error en get_ranger_trips: {str(e)}")
        return jsonify({"error": "Error al obtener viajes"}), 500
    finally:
        if 'cursor' in locals(): cursor.close()
        if connection: connection.close()

# 5. Ruta para añadir certificación a un ranger
@app.route('/rangers/<string:ranger_id>/certifications', methods=['POST'])
def add_ranger_certification(ranger_id):
    connection = get_db_connection()
    if not connection:
        return jsonify({"error": "Database connection failed"}), 500
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Datos no proporcionados"}), 400
        
        # Validar datos mínimos necesarios
        required_fields = ['title', 'issued_by', 'issued_date', 'valid_until']
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"Campo requerido: {field}"}), 400
        
        cursor = connection.cursor(cursor_factory=RealDictCursor)
        
        # Verificar que el ranger existe
        cursor.execute("SELECT id FROM users WHERE id = %s", (ranger_id,))
        if not cursor.fetchone():
            return jsonify({"error": "Ranger no encontrado"}), 404
        
        # Primero insertamos la certificación
        cursor.execute("""
            INSERT INTO certifications (
                title, 
                issued_by, 
                issued_date, 
                valid_until, 
                certification_number, 
                document_url
            ) VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            data['title'],
            data['issued_by'],
            data['issued_date'],
            data['valid_until'],
            data.get('certification_number'),
            data.get('document_url')
        ))
        
        certification_id = cursor.fetchone()['id']
        
        # Luego vinculamos la certificación con el ranger
        cursor.execute("""
            INSERT INTO ranger_certifications (
                certification_id,
                user_id
            ) VALUES (%s, %s)
            RETURNING id
        """, (certification_id, ranger_id))
        
        connection.commit()
        
        return jsonify({
            "message": "Certificación añadida correctamente",
            "certification_id": str(certification_id)
        }), 201
        
    except Exception as e:
        if connection:
            connection.rollback()
        logging.error(f"Error en add_ranger_certification: {str(e)}")
        return jsonify({"error": "Error al añadir certificación"}), 500
    finally:
        if 'cursor' in locals(): cursor.close()
        if connection: connection.close()

# 6. Ruta para actualizar la calificación de un ranger
@app.route('/rangers/<string:ranger_id>/rating', methods=['PUT'])
def update_ranger_rating(ranger_id):
    connection = get_db_connection()
    if not connection:
        return jsonify({"error": "Database connection failed"}), 500
    
    try:
        data = request.get_json()
        if not data or 'rating' not in data:
            return jsonify({"error": "Calificación no proporcionada"}), 400
        
        rating = data['rating']
        # Validar que la calificación esté en el rango correcto
        if not isinstance(rating, (int, float)) or rating < 0 or rating > 5:
            return jsonify({"error": "La calificación debe ser un número entre 0 y 5"}), 400
        
        cursor = connection.cursor()
        
        # Verificar que el ranger existe
        cursor.execute("SELECT id FROM users WHERE id = %s", (ranger_id,))
        if not cursor.fetchone():
            return jsonify({"error": "Ranger no encontrado"}), 404
        
        # Actualizar calificación
        cursor.execute("""
            UPDATE users 
            SET calification = %s
            WHERE id = %s
        """, (rating, ranger_id))
        
        connection.commit()
        
        return jsonify({
            "message": "Calificación actualizada correctamente",
            "rating": rating
        }), 200
        
    except Exception as e:
        if connection:
            connection.rollback()
        logging.error(f"Error en update_ranger_rating: {str(e)}")
        return jsonify({"error": "Error al actualizar calificación"}), 500
    finally:
        if 'cursor' in locals(): cursor.close()
        if connection: connection.close()

# 7. Ruta para actualizar la calificación de un ranger por un viaje específico
@app.route('/rangers/<string:ranger_id>/trips/<string:trip_id>/rating', methods=['POST'])
def rate_ranger_trip(ranger_id, trip_id):
    connection = get_db_connection()
    if not connection:
        return jsonify({"error": "Database connection failed"}), 500
    
    try:
        data = request.get_json()
        if not data or 'rating' not in data:
            return jsonify({"error": "Calificación no proporcionada"}), 400
        
        rating = data['rating']
        # Validar que la calificación esté en el rango correcto
        if not isinstance(rating, (int, float)) or rating < 0 or rating > 5:
            return jsonify({"error": "La calificación debe ser un número entre 0 y 5"}), 400
        
        # Obtener el ID del usuario que califica (del token JWT)
        # user_id = get_jwt_identity()  # Ejemplo si usas Flask-JWT-Extended
        user_id = data.get('user_id')  # Por ahora lo tomamos del cuerpo de la petición
        
        if not user_id:
            return jsonify({"error": "Se requiere ID de usuario"}), 400
        
        cursor = connection.cursor()
        
        # Verificar que el ranger y el viaje existen
        cursor.execute("""
            SELECT u.id AS ranger_id, t.id AS trip_id
            FROM users u, trips t
            WHERE u.id = %s AND t.id = %s
        """, (ranger_id, trip_id))
        
        if not cursor.fetchone():
            return jsonify({"error": "Ranger o viaje no encontrado"}), 404
        
        # Verificar si ya existe una calificación para este usuario, ranger y viaje
        cursor.execute("""
            SELECT id FROM ranger_califications
            WHERE user_id = %s AND trip_id = %s
        """, (user_id, trip_id))
        
        existing_rating = cursor.fetchone()
        
        if existing_rating:
            # Actualizar calificación existente
            cursor.execute("""
                UPDATE ranger_califications
                SET calification = %s
                WHERE user_id = %s AND trip_id = %s
            """, (rating, user_id, trip_id))
            message = "Calificación actualizada correctamente"
        else:
            # Crear nueva calificación
            cursor.execute("""
                INSERT INTO ranger_califications (user_id, trip_id, calification)
                VALUES (%s, %s, %s)
            """, (user_id, trip_id, rating))
            message = "Calificación registrada correctamente"
        
        # Actualizar el promedio de calificación del ranger
        cursor.execute("""
            UPDATE users
            SET calification = (
                SELECT AVG(calification)
                FROM ranger_califications
                WHERE trip_id IN (SELECT id FROM trips WHERE ranger_id = %s)
            )
            WHERE id = %s
        """, (ranger_id, ranger_id))
        
        connection.commit()
        
        return jsonify({
            "message": message,
            "rating": rating
        }), 200
        
    except Exception as e:
        if connection:
            connection.rollback()
        logging.error(f"Error en rate_ranger_trip: {str(e)}")
        return jsonify({"error": "Error al registrar calificación"}), 500
    finally:
        if 'cursor' in locals(): cursor.close()
        if connection: connection.close()
@app.route('/api/guide-certifications/<string:guide_id>', methods=['GET'])
def fetch_guide_certifications(guide_id):
    connection = get_db_connection()
    if not connection:
        return jsonify({"error": "Database connection failed"}), 500

    try:
        cursor = connection.cursor(cursor_factory=RealDictCursor)
        
        # Verificar que el ranger/guía existe
        cursor.execute("SELECT id FROM users WHERE id = %s", (guide_id,))
        if not cursor.fetchone():
            return jsonify({"error": "Guía no encontrado"}), 404
        
        # Obtener certificaciones del guía
        cursor.execute("""
            SELECT 
                c.id,
                c.title,
                c.issued_by,
                c.issued_date,
                c.valid_until,
                c.certification_number,
                c.document_url
            FROM certifications c
            JOIN ranger_certifications rc ON c.id = rc.certification_id
            WHERE rc.user_id = %s
            ORDER BY c.valid_until DESC
        """, (guide_id,))
        
        certifications = cursor.fetchall()
        
        # Formatear fechas para JSON
        formatted_certifications = []
        for cert in certifications:
            formatted_cert = dict(cert)
            if formatted_cert['issued_date']:
                formatted_cert['issued_date'] = formatted_cert['issued_date'].isoformat()
            if formatted_cert['valid_until']:
                formatted_cert['valid_until'] = formatted_cert['valid_until'].isoformat()
            formatted_cert['id'] = str(formatted_cert['id'])
            formatted_certifications.append(formatted_cert)
        
        return jsonify({"certifications": formatted_certifications}), 200

    except Exception as e:
        # Manejo de errores
        import traceback
        error_details = traceback.format_exc()
        print(f"Error en fetch_guide_certifications: {str(e)}\n{error_details}")
        return jsonify({"error": "Error interno al obtener certificaciones"}), 500
    finally:
        if 'cursor' in locals(): cursor.close()
        if connection: connection.close()
                
if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True, port=5000)