-- Habilitar la extensión UUID
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Tabla de roles de usuario (debe ir ANTES de users ya que users la referencia)
CREATE TABLE user_roles (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    role_name VARCHAR(10) NOT NULL UNIQUE,
    description varchar(50) NOT NULL
);

-- Tabla de usuarios
CREATE TABLE users (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    username VARCHAR(10) NOT NULL UNIQUE,
    first_name varchar(20) NOT NULL,
    last_name varchar(20) NOT NULL,
    nationality varchar(20) NOT NULL,
    rut varchar(11),
    passport_number varchar(20),
    role_id uuid NOT NULL REFERENCES user_roles(id),
    profession varchar(50),
    biography text,
    email varchar(100) NOT NULL,
    availability_start_date date,
    availability_end_date date
);

-- Tabla de viajes
CREATE TABLE trips (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    start_date timestamptz NOT NULL,
    end_date timestamptz NOT NULL,
    participants_number integer NOT NULL,
    status varchar(25) DEFAULT 'pending' NOT NULL, 
    estimated_weather_forecast text,
    description text NOT NULL,
    created_at timestamptz NOT NULL,
    updated_at timestamptz,
    total_cost numeric(10,2)
);

-- Tabla de pagos
CREATE TABLE payment (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    user_id uuid NOT NULL,
    trip_id uuid NOT NULL,
    payment_amount numeric(10,2),
    payment_method VARCHAR(50),
    payment_date date,
    payment_bill_url VARCHAR(255),
    payment_voucher_url varchar(255),
    payment_status VARCHAR(50)
);

-- Tabla de reservas
CREATE TABLE reservations (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    trip_id uuid NOT NULL REFERENCES trips(id),
    user_id uuid NOT NULL REFERENCES users(id),
    status varchar(255) DEFAULT 'reserved' NOT NULL
);

-- Tabla de ubicaciones
CREATE TABLE locations (
   id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
   place_name varchar(30) NOT NULL UNIQUE,
   place_type VARCHAR(15) NOT NULL,
   country varchar(50) NOT NULL,
   province varchar(50) NOT NULL,
   nearest_city varchar(50) NOT NULL,
   coordinates point NOT NULL
);

-- Tabla de actividades
CREATE TABLE activities (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    location_id uuid NOT NULL REFERENCES locations(id),
    name VARCHAR(20) NOT NULL UNIQUE,
    description varchar(50) NOT NULL,
    duration numeric(5,2) NOT NULL,
    difficulty char(1) NOT NULL,
    min_participants integer NOT NULL,
    max_participants integer NOT NULL,
    cancellation_policy text NOT NULL,
    is_available boolean NOT NULL DEFAULT TRUE,
    is_public boolean NOT NULL DEFAULT TRUE,
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL,
    cost numeric(10,2) NOT NULL
);

-- Tabla puente para actividades y viajes
CREATE TABLE activity_trips (
   id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
   activity_id uuid NOT NULL REFERENCES activities(id),
   trip_id uuid NOT NULL REFERENCES trips(id)
);

-- Tabla de recursos
CREATE TABLE resources (
   id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
   name varchar(100) NOT NULL UNIQUE,
   description jsonb NOT NULL,
   cost numeric(10,2) NOT NULL
);

-- Tabla puente para recursos y viajes
CREATE TABLE trip_resources (
   id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
   resource_id uuid NOT NULL REFERENCES resources(id),
   trip_id uuid NOT NULL REFERENCES trips(id)
);

-- Tabla de certificaciones
CREATE TABLE certifications (
   id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
   issued_by varchar(100) NOT NULL,
   issued_date date NOT NULL,
   valid_until date NOT NULL,
   certification_number varchar(50),
   document_url varchar(255),
   created_at date NOT NULL,
   title VARCHAR(100) UNIQUE
);

-- Tabla puente para certificaciones y rangers (usuarios)
CREATE TABLE ranger_certifications (
   id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
   certification_id uuid NOT NULL REFERENCES certifications(id),
   user_id uuid NOT NULL REFERENCES users(id)
);

-- Constraints adicionales
ALTER TABLE users
    ADD CONSTRAINT fk_user_role
    FOREIGN KEY (role_id)
    REFERENCES user_roles(id)
    ON DELETE CASCADE;

ALTER TABLE payment
    ADD CONSTRAINT fk_user_payment
    FOREIGN KEY (user_id)
    REFERENCES users(id)
    ON DELETE RESTRICT;

ALTER TABLE payment
    ADD CONSTRAINT fk_trip_payment
    FOREIGN KEY (trip_id)
    REFERENCES trips(id)
    ON DELETE NO ACTION;
