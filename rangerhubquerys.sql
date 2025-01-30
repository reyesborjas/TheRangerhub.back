INSERT INTO user_roles (role_name, description) VALUES 
('admin', 'Sysadmin'),
('Ranger', 'Guide and Instructor'),
('Explorer','Common user and trip participant');

INSERT INTO USERS (username, first_name, last_name, nationality, rut, passport_number, role_id, profession, email, availability_start_date, availability_end_date) VALUES
('jarb86', 'José','Reyes','Venezolana','26769151-7','A123456789',(select id from user_roles where role_name='Ranger'),
'Ingeniero','reyesborjas@gmail.com','2025-01-01','2025-02-01')

select * from users

INSERT INTO locations (place_name, place_type, country, province, nearest_city, coordinates) VALUES
('Lago Rapel','Laguna', 'Chile', 'O''Higgins','Santa Cruz','51.0598, -73.0173')

SELECT * from locations