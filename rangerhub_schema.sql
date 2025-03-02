
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";


CREATE TABLE user_roles (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    role_name VARCHAR(25) NOT NULL UNIQUE,
    description VARCHAR(50) NOT NULL
);


CREATE TABLE users (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    username VARCHAR(100) NOT NULL UNIQUE,
    first_name varchar(50) NOT NULL,
    last_name varchar(50) NOT NULL,
    nationality varchar(50) NOT NULL,
    rut varchar(25) UNIQUE,
    passport_number varchar(25) UNIQUE,
     role_id uuid NOT NULL REFERENCES user_roles(id) on DELETE CASCADE,
    biography text,
    email varchar(100) NOT NULL UNIQUE,
    availability_start_date date,
    availability_end_date date,
    user_status VARCHAR(50) NOT NULL DEFAULT 'activo',
    profile_picture_url varchar(255) UNIQUE,
    profile_visibility BOOLEAN NOT NULL DEFAULT TRUE   
    phone_number varchar(25) UNIQUE
);


CREATE TABLE trips (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    start_date timestamptz NOT NULL,
    end_date timestamptz NOT NULL,
    participants_number integer NOT NULL,
    trip_status VARCHAR(50) NOT NULL DEFAULT 'pendiente',
    estimated_weather_forecast text,
    description text ,
    created_at TIMESTAMP with time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP with time zone,
    total_cost numeric(10,2),
    trip_image_url varchar(255)
    trip_name varchar(50) UNIQUE
    lead_ranger UUID REFERENCES users(id)
);


CREATE TABLE payment (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    user_id uuid NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    trip_id uuid NOT NULL REFERENCES trips(id) ON DELETE NO ACTION,
    payment_amount numeric(10,2),
    payment_method VARCHAR(50),
    payment_date date,
    payment_voucher_url varchar(255) UNIQUE,
    payment_status VARCHAR(50)
);


CREATE TABLE reservations (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    trip_id uuid NOT NULL REFERENCES trips(id) ON DELETE CASCADE,
    user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    status VARCHAR(50) NOT NULL DEFAULT 'pendiente'
);


CREATE TABLE locations (
   id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
   place_name varchar(255) NOT NULL UNIQUE,
   place_type VARCHAR(50) NOT NULL,
   country varchar(100) NOT NULL,
   province varchar(100) NOT NULL,
   nearest_city varchar(100) NOT NULL,
   coordinates point NOT NULL,
   location_image_url varchar(255)
);

CREATE TABLE activity_categories (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE,
    description TEXT
);

CREATE TABLE activities (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    category_id UUID REFERENCES activity_categories(id) ON DELETE SET NULL,
    location_id uuid NOT NULL REFERENCES locations(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL UNIQUE,
    description varchar(255) NOT NULL,
    duration numeric(5,2) NOT NULL,
    difficulty varchar(20) NOT NULL,
    min_participants integer NOT NULL,
    max_participants integer NOT NULL,
    cancellation_policy text,
    is_available boolean NOT NULL DEFAULT TRUE,
    is_public boolean NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP with time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP with time zone,
    cost numeric(10,2) NOT NULL,
    activity_image_url varchar(255) UNIQUE
);


CREATE TABLE activity_trips (
   id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
   activity_id uuid NOT NULL REFERENCES activities(id) ON DELETE CASCADE,
   trip_id uuid NOT NULL REFERENCES trips(id) ON DELETE CASCADE
);



CREATE TABLE resources (
   id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
   name varchar(100) NOT NULL UNIQUE,
   description jsonb NOT NULL,
   cost numeric(10,2) NOT NULL
);


CREATE TABLE trip_resources (
   id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
   resource_id uuid NOT NULL REFERENCES resources(id),
   trip_id uuid NOT NULL REFERENCES trips(id)
);


CREATE TABLE certifications (
   id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
   issued_by varchar(100) NOT NULL,
   issued_date date NOT NULL,
   valid_until date NOT NULL,
   certification_number varchar(50),
   document_url varchar(255),
   created_at date NOT NULL DEFAULT CURRENT_DATE,
   title VARCHAR(100),
   UNIQUE (title, certification_number, valid_until)
);

CREATE TABLE ranger_certifications (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    certification_id uuid NOT NULL REFERENCES certifications(id),
    user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE(certification_id, user_id)
);

CREATE TABLE ranger_activities (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    activity_id uuid NOT NULL REFERENCES activities(id),
    user_id uuid NOT NULL REFERENCES users(id),
    UNIQUE(activity_id, user_id)
);

