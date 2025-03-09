import os
import uuid
import bcrypt
import logging
import datetime
from typing import Dict, Any, Optional

import jwt
import psycopg2
from psycopg2.extras import RealDictCursor, Json
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
from marshmallow import Schema, fields, validate, ValidationError

# Configuración inicial
load_dotenv()
app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": os.getenv("ALLOWED_ORIGINS", "*")}})

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuración JWT
app.config['JWT_SECRET_KEY'] = os.getenv("SECRET_KEY", "super_secreto_por_defecto")
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = datetime.timedelta(hours=2)

# Schemas de validación
class UserRegistrationSchema(Schema):
    username = fields.Str(required=True, validate=validate.Length(min=4))
    password = fields.Str(required=True, validate=validate.Length(min=8))
    email = fields.Email(required=True)
    first_name = fields.Str(required=True)
    last_name = fields.Str(required=True)

class LoginSchema(Schema):
    username = fields.Str(required=True)
    password = fields.Str(required=True)

# Helpers de base de datos
@contextmanager
def db_connection():
    conn = None
    try:
        conn = psycopg2.connect(
            dbname=os.getenv("DATABASE_NAME"),
            user=os.getenv("DATABASE_USER"),
            password=os.getenv("DATABASE_PASSWORD"),
            host=os.getenv("DATABASE_HOST"),
            port=os.getenv("DATABASE_PORT"),
            cursor_factory=RealDictCursor
        )
        yield conn
    except psycopg2.Error as e:
        logger.error(f"Database connection error: {str(e)}")
        raise
    finally:
        if conn:
            conn.close()

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode(), hashed_password.encode())

# Decoradores personalizados
def handle_errors(func):
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except ValidationError as e:
            return jsonify({"error": "Validation error", "details": e.messages}), 400
        except psycopg2.Error as e:
            logger.error(f"Database error: {str(e)}")
            return jsonify({"error": "Database error"}), 500
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            return jsonify({"error": "Internal server error"}), 500
    return wrapper

# Rutas de autenticación
@app.route('/register', methods=['POST'])
@handle_errors
def register():
    schema = UserRegistrationSchema()
    data = schema.load(request.get_json())
    
    with db_connection() as conn:
        with conn.cursor() as cursor:
            hashed_pw = hash_password(data['password'])
            cursor.execute("""
                INSERT INTO users (username, password, email, first_name, last_name)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id, username, email
            """, (data['username'], hashed_pw, data['email'], data['first_name'], data['last_name']))
            
            user = cursor.fetchone()
            conn.commit()
            return jsonify({"message": "User created", "user": user}), 201

@app.route('/login', methods=['POST'])
@handle_errors
def login():
    schema = LoginSchema()
    data = schema.load(request.get_json())
    
    with db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT id, username, password, role_id 
                FROM users 
                WHERE username = %s
            """, (data['username'],))
            
            user = cursor.fetchone()
            if not user or not verify_password(data['password'], user['password']):
                return jsonify({"error": "Invalid credentials"}), 401
            
            token = jwt.encode({
                'sub': user['id'],
                'username': user['username'],
                'role': user['role_id'],
                'exp': datetime.datetime.utcnow() + app.config['JWT_ACCESS_TOKEN_EXPIRES']
            }, app.config['JWT_SECRET_KEY'], algorithm='HS256')
            
            return jsonify({
                "access_token": token,
                "user": {
                    "id": user['id'],
                    "username": user['username'],
                    "role": user['role_id']
                }
            }), 200

# Rutas de perfil de usuario
@app.route('/api/user-profile/<username>', methods=['GET', 'PUT'])
@handle_errors
def user_profile(username: str):
    if request.method == 'GET':
        with db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT id, username, email, first_name, last_name, 
                           profile_picture_url, biography_extend
                    FROM users 
                    WHERE username = %s
                """, (username,))
                
                user = cursor.fetchone()
                if not user:
                    return jsonify({"error": "User not found"}), 404
                
                return jsonify({
                    "id": str(user['id']),
                    "username": user['username'],
                    "email": user['email'],
                    "firstName": user['first_name'],
                    "lastName": user['last_name'],
                    "profilePicture": user['profile_picture_url'],
                    "bio": user['biography_extend']
                }), 200

    elif request.method == 'PUT':
        data = request.get_json()
        with db_connection() as conn:
            with conn.cursor() as cursor:
                update_fields = []
                update_values = []
                
                if 'email' in data:
                    update_fields.append("email = %s")
                    update_values.append(data['email'])
                
                if 'firstName' in data:
                    update_fields.append("first_name = %s")
                    update_values.append(data['firstName'])
                
                if 'lastName' in data:
                    update_fields.append("last_name = %s")
                    update_values.append(data['lastName'])
                
                if update_fields:
                    query = f"""
                        UPDATE users 
                        SET {', '.join(update_fields)}
                        WHERE username = %s
                        RETURNING *
                    """
                    update_values.append(username)
                    cursor.execute(query, update_values)
                    updated_user = cursor.fetchone()
                    conn.commit()
                    
                    return jsonify({
                        "message": "Profile updated",
                        "user": {
                            "username": updated_user['username'],
                            "email": updated_user['email']
                        }
                    }), 200
                return jsonify({"message": "No changes detected"}), 200

# Rutas de actividades
@app.route('/activities', methods=['GET', 'POST'])
@handle_errors
def activities():
    if request.method == 'GET':
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        
        with db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) FROM activities")
                total = cursor.fetchone()['count']
                
                cursor.execute("""
                    SELECT id, name, description, difficulty, cost
                    FROM activities
                    ORDER BY created_at DESC
                    LIMIT %s OFFSET %s
                """, (per_page, (page-1)*per_page))
                
                activities = [dict(act, id=str(act['id'])) for act in cursor.fetchall()]
                return jsonify({
                    "data": activities,
                    "pagination": {
                        "total": total,
                        "page": page,
                        "per_page": per_page
                    }
                }), 200

    elif request.method == 'POST':
        data = request.get_json()
        with db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO activities (name, description, difficulty, cost)
                    VALUES (%s, %s, %s, %s)
                    RETURNING id, name
                """, (data['name'], data.get('description'), data.get('difficulty', 'medium'), data.get('cost', 0)))
                
                new_activity = cursor.fetchone()
                conn.commit()
                return jsonify({
                    "message": "Activity created",
                    "activity": new_activity
                }), 201

# Manejo de errores global
@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Resource not found"}), 404

@app.errorhandler(405)
def method_not_allowed(error):
    return jsonify({"error": "Method not allowed"}), 405

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=os.getenv("DEBUG", "false").lower() == "true")