CREATE TABLE users (
    id uuid NOT NULL PRIMARY KEY,
    username varchar(10) NOT NULL UNIQUE,
    first_name varchar(20) NOT NULL,
    last_name varchar(20) NOT NULL,
    nationality varchar(20) NOT NULL,
    rut varchar(11),
    passport_number varchar(20),
    role_id uuid NOT NULL,
    profession varchar(50),
    biography jsonb,
    email varchar(100) NOT NULL
);

CREATE TABLE user_roles (
    id uuid NOT NULL PRIMARY KEY,
    role_name char(1) NOT NULL UNIQUE,
    description varchar(50) NOT NULL
);

CREATE TABLE trips (
    id uuid NOT NULL PRIMARY KEY,
    start_date timestamptz NOT NULL,
    end_date timestamptz NOT NULL,
    participants_number integer NOT NULL,
    status status_type NOT NULL,
    estimated_weather_forecast text,
    description text NOT NULL,
    created_at timestamptz NOT NULL,
    updated_at timestamptz,
    total_cost numeric(10,2),
    payment_amount numeric(10,2),
    payment_method varchar(50),
    payment_date date,
    payment_bill_url varchar(255),
    payment_voucher_url varchar(255)
);

CREATE TABLE user_trips (
    id uuid NOT NULL PRIMARY KEY,
    trip_id uuid NOT NULL REFERENCES trips(id),
    user_id uuid NOT NULL REFERENCES users(id)
);

CREATE TABLE locations (
    id uuid NOT NULL PRIMARY KEY,
    place_name varchar(30) NOT NULL UNIQUE,
    place_type char(1) NOT NULL,
    country varchar(50) NOT NULL,
    state_or_province varchar(50) NOT NULL,
    nearest_city varchar(50) NOT NULL,
    coordinates point NOT NULL
);

CREATE TABLE activities (
    id uuid NOT NULL PRIMARY KEY,
    location_id uuid NOT NULL REFERENCES locations(id),
    name varchar(20) NOT NULL UNIQUE,
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

CREATE TABLE activity_trips (
    id uuid NOT NULL PRIMARY KEY,
    activity_id uuid NOT NULL REFERENCES activities(id),
    trip_id uuid NOT NULL REFERENCES trips(id)
);

CREATE TABLE resources (
    id uuid NOT NULL PRIMARY KEY,
    name varchar(100) NOT NULL UNIQUE,
    description jsonb NOT NULL,
    cost numeric(10,2) NOT NULL
);

CREATE TABLE trip_resources (
    id uuid NOT NULL PRIMARY KEY,
    resource_id uuid NOT NULL REFERENCES resources(id),
    trip_id uuid NOT NULL REFERENCES trips(id)
);

CREATE TABLE reservations (
    id uuid NOT NULL PRIMARY KEY,
    trip_id uuid NOT NULL REFERENCES trips(id),
    status status_type NOT NULL
);

CREATE TABLE user_reservations (
    id uuid NOT NULL PRIMARY KEY,
    reservation_id uuid NOT NULL REFERENCES reservations(id),
    user_id uuid NOT NULL REFERENCES users(id)
);

CREATE TABLE blog_posts (
    id uuid NOT NULL PRIMARY KEY,
    author_id uuid NOT NULL REFERENCES users(id),
    title varchar(20) NOT NULL UNIQUE,
    content text NOT NULL,
    summary varchar(50) NOT NULL,
    featured_img_url varchar(255),
    tags varchar(30)[] NOT NULL,
    status status_type NOT NULL DEFAULT 'pending',
    published_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL
);

CREATE TABLE ranger_availability (
    id uuid NOT NULL PRIMARY KEY,
    ranger_id uuid NOT NULL REFERENCES users(id),
    start_time date NOT NULL,
    end_date date NOT NULL,
    status status_type,
    UNIQUE (ranger_id, start_time, end_date)
);

CREATE TABLE certifications (
    id uuid NOT NULL PRIMARY KEY,
    issued_by varchar(100) NOT NULL,
    issued_date date NOT NULL,
    valid_until date NOT NULL,
    certification_number varchar(50),
    document_url varchar(255) NOT NULL,
    created_at date NOT NULL,
    title varchar(100) UNIQUE
);

CREATE TABLE ranger_certifications (
    id uuid NOT NULL PRIMARY KEY,
    certification_id uuid NOT NULL REFERENCES certifications(id),
    user_id uuid NOT NULL REFERENCES users(id)
);

ALTER TABLE users
    ADD CONSTRAINT fk_user_role
    FOREIGN KEY (role_id)
    REFERENCES user_roles(id)
    ON DELETE RESTRICT;
