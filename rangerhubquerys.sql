-- Insertar roles de usuario
INSERT INTO user_roles (role_name, description) VALUES
('ranger', 'Guía especializado para actividades al aire libre'),
('explorer', 'Usuario que participa en las actividades'),
('admin', 'Administrador del sistema con acceso total');

-- Insertar usuarios
INSERT INTO users (username, first_name, last_name, nationality, rut, passport_number, role_id, biography, email, availability_start_date, availability_end_date, user_status, profile_visibility) VALUES
('juanrangero', 'Juan', 'Martínez', 'Chileno', '15789456-2', NULL, (SELECT id FROM user_roles WHERE role_name = 'ranger'), 'Guía especializado en montañismo con 5 años de experiencia', 'juan.martinez@email.com', '2025-01-01', '2025-12-31', 'activo', true),
('mariasanchez', 'María', 'Sánchez', 'Chilena', '16234567-8', NULL, (SELECT id FROM user_roles WHERE role_name = 'explorer'), 'Entusiasta de la naturaleza y las aventuras al aire libre', 'maria.sanchez@email.com', NULL, NULL, 'activo', true),
('carlosadmin', 'Carlos', 'Rodriguez', 'Chileno', '14567890-1', NULL, (SELECT id FROM user_roles WHERE role_name = 'admin'), 'Administrador principal del sistema', 'carlos.rodriguez@email.com', NULL, NULL, 'activo', true);

-- Insertar ubicaciones
INSERT INTO locations (place_name, place_type, country, province, nearest_city, coordinates, location_image_url) VALUES
('Volcán Villarrica', 'Volcán', 'Chile', 'Cautín', 'Pucón', point(-39.4198, -71.9347), 'villarrica.jpg'),
('Torres del Paine', 'Parque Nacional', 'Chile', 'Última Esperanza', 'Puerto Natales', point(-50.9423, -73.4068), 'torres-paine.jpg'),
('Valle Nevado', 'Centro de Ski', 'Chile', 'Santiago', 'Santiago', point(-33.3567, -70.2489), 'valle-nevado.jpg');
('Cajón del Maipo', 'Río Maipo', 'Chile', 'Santiago', 'Santiago', point(-33.8336, -70.1162), 'cajon-maipo.jpg');
('Pucón', 'Río Correntoso', 'Chile', 'Pucón', 'Villarica', point(-39.272255, -71.977631), 'pucon.jpg');
('Cajón del Maipo', 'Centro de Parapente', 'Chile', 'Santiago', 'Santiago', point(-33.8336, -70.1162), 'cajon-maipo-parapente.jpg');
('San Pedro', 'Centro Turístico', 'Chile', 'El Loa', 'Calama', point(-22.916667, -68.2), 'san-pedro.jpg');

-- Insertar categorías de actividades
INSERT INTO activity_categories (name, description) VALUES
('Montañismo', 'Actividades de ascenso en montañas y volcanes'),
('Trekking', 'Caminatas por senderos naturales'),
('Escalada', 'Actividades de escalada en roca y hielo');
('Rafting', 'Bajada en balsa por el río Maipo')
('Canyoning', 'Descender por cañones y ríos')
('Parapente', 'Vuelo en parapente')
('Sanboard', 'Deslizada sobre dunas,')

-- Insertar actividades
INSERT INTO activities (category_id, location_id, name, description, duration, difficulty, min_participants, max_participants, cancellation_policy, cost) VALUES
((SELECT id FROM activity_categories WHERE name = 'Montañismo'), (SELECT id FROM locations WHERE place_name = 'Volcán Villarrica'), 'Ascenso Villarrica', 'Ascenso guiado al volcán Villarrica', 8.5, 'difícil', 2, 8, 'Cancelación gratuita con 48 horas de anticipación', 150000.00),
((SELECT id FROM activity_categories WHERE name = 'Trekking'), (SELECT id FROM locations WHERE place_name = 'Torres del Paine'), 'Circuito W', 'Trekking por el famoso circuito W', 24.0, 'moderado', 4, 12, 'Cancelación gratuita con 72 horas de anticipación', 280000.00),
((SELECT id FROM activity_categories WHERE name = 'Escalada'), (SELECT id FROM locations WHERE place_name = 'Valle Nevado'), 'Escalada en Hielo', 'Curso básico de escalada en hielo', 6.0, 'intermedio', 2, 6, 'Cancelación gratuita con 24 horas de anticipación', 120000.00);
((SELECT id FROM activity_categories WHERE name = 'Rafting'), (SELECT id FROM locations WHERE place_name = 'Cajon del Maipo'), 'Rafting', 'Bajada en balsa por el río Maipo', 3, 'moderada', 4, 8, 'Cancelación gratuita con 48 horas de anticipación', 100.00);
((SELECT id FROM activity_categories WHERE name = 'Canyoning'), (SELECT id FROM locations WHERE place_name = 'Araucanía'), 'Canyoning', 'Descender por cañones y ríos', 6, 'difícil', 1, 8, 'Cancelación gratuita con 24 horas de anticipación', 150000.00);
((SELECT id FROM activity_categories WHERE name = 'Parapente'), (SELECT id FROM locations WHERE place_name = 'Cajon del Maipo'), 'Parapente', 'Vuelo en parapente', 6, 'fácil', 1, 8, 'Cancelación gratuita con 24 horas de anticipación', 65000.00);
((SELECT id FROM activity_categories WHERE name = 'Sandboard'), (SELECT id FROM locations WHERE place_name = 'San Pedro'), 'Sandboard', 'Deslizada sobre dunas', 4, 'fácil', 1, 20, 'Cancelación gratuita con 24 horas de anticipación', 50000.00);

-- Insertar viajes
INSERT INTO trips (start_date, end_date, participants_number, trip_status, description, total_cost) VALUES
('2025-03-15 08:00:00-03', '2025-03-15 18:00:00-03', 6, 'confirmado', 'Ascenso al Volcán Villarrica', 900000.00),
('2025-04-01 07:00:00-03', '2025-04-05 19:00:00-03', 8, 'pendiente', 'Trekking Circuito W en Torres del Paine', 2240000.00),
('2025-02-20 09:00:00-03', '2025-02-20 16:00:00-03', 4, 'confirmado', 'Curso de escalada en hielo en Valle Nevado', 480000.00);

-- Insertar reservaciones
INSERT INTO reservations (trip_id, user_id, status) VALUES
((SELECT id FROM trips WHERE description LIKE '%Villarrica%'), (SELECT id FROM users WHERE username = 'mariasanchez'), 'confirmado'),
((SELECT id FROM trips WHERE description LIKE '%Torres del Paine%'), (SELECT id FROM users WHERE username = 'mariasanchez'), 'pendiente'),
((SELECT id FROM trips WHERE description LIKE '%Valle Nevado%'), (SELECT id FROM users WHERE username = 'mariasanchez'), 'confirmado');

-- Insertar pagos
INSERT INTO payment (user_id, trip_id, payment_amount, payment_method, payment_date, payment_status) VALUES
((SELECT id FROM users WHERE username = 'mariasanchez'), (SELECT id FROM trips WHERE description LIKE '%Villarrica%'), 150000.00, 'tarjeta_credito', '2025-02-15', 'completado'),
((SELECT id FROM users WHERE username = 'mariasanchez'), (SELECT id FROM trips WHERE description LIKE '%Torres del Paine%'), 280000.00, 'transferencia', '2025-03-01', 'pendiente'),
((SELECT id FROM users WHERE username = 'mariasanchez'), (SELECT id FROM trips WHERE description LIKE '%Valle Nevado%'), 120000.00, 'tarjeta_debito', '2025-01-20', 'completado');

-- Insertar recursos
INSERT INTO resources (name, description, cost) VALUES
('Piolet', '{"tipo": "equipo_técnico", "marca": "Black Diamond", "estado": "nuevo"}', 75000.00),
('Carpa 4 estaciones', '{"tipo": "equipo_camping", "marca": "The North Face", "capacidad": "2 personas"}', 250000.00),
('Crampones', '{"tipo": "equipo_escalada", "marca": "Petzl", "talla": "universal"}', 85000.00);
('Remo', '{"tipo": "equipo_técnico", "marca": "Xped", "talla": "universal"}', 40000.00);
('Casco', '{"tipo": "equipo_técnico", "marca": "Xped", "talla": "universal"}', 50000.00);
('Tabla', '{"tipo": "equipo_técnico", "marca": "Adventure", "talla": "universal"}', 120000.00);
('Salvavidas', '{"tipo": "equipo_técnico", "marca": "Decathlon", "talla": "universal"}', 80000.00);



-- Insertar recursos para viajes
INSERT INTO trip_resources (resource_id, trip_id) VALUES
((SELECT id FROM resources WHERE name = 'Piolet'), (SELECT id FROM trips WHERE description LIKE '%Villarrica%')),
((SELECT id FROM resources WHERE name = 'Carpa 4 estaciones'), (SELECT id FROM trips WHERE description LIKE '%Torres del Paine%')),
((SELECT id FROM resources WHERE name = 'Crampones'), (SELECT id FROM trips WHERE description LIKE '%Valle Nevado%'));
((SELECT id FROM resources WHERE name = 'Remo'), (SELECT id FROM trips WHERE description LIKE '%Cajón del Maipo%'));
((SELECT id FROM resources WHERE name = 'Casco'), (SELECT id FROM trips WHERE description LIKE '%Pucón%'));

-- Insertar actividades para viajes
INSERT INTO activity_trips (activity_id, trip_id) VALUES
((SELECT id FROM activities WHERE name = 'Ascenso Villarrica'), (SELECT id FROM trips WHERE description LIKE '%Villarrica%')),
((SELECT id FROM activities WHERE name = 'Circuito W'), (SELECT id FROM trips WHERE description LIKE '%Torres del Paine%')),
((SELECT id FROM activities WHERE name = 'Escalada en Hielo'), (SELECT id FROM trips WHERE description LIKE '%Valle Nevado%'));
((SELECT id FROM activities WHERE name = 'Rafting') ,(SELECT id FROM trips WHERE description LIKE '%Cajón del Maipo%'));
((SELECT id FROM activities WHERE name = 'Canyoning') ,(SELECT id FROM trips WHERE description LIKE '%Pucón%'));

-- Insertar certificaciones
INSERT INTO certifications (issued_by, issued_date, valid_until, certification_number, title) VALUES
('NOLS Wilderness Medicine', '2024-01-01', '2026-01-01', 'WFR-2024-001', 'Wilderness First Responder'),
('UIAGM', '2024-01-15', '2029-01-15', 'UIAGM-2024-123', 'Guía de Alta Montaña'),
('ACGM', '2024-02-01', '2026-02-01', 'ACGM-2024-456', 'Guía de Escalada');

-- Insertar certificaciones de rangers
INSERT INTO ranger_certifications (certification_id, user_id) VALUES
((SELECT id FROM certifications WHERE certification_number = 'WFR-2024-001'), (SELECT id FROM users WHERE username = 'juanrangero')),
((SELECT id FROM certifications WHERE certification_number = 'UIAGM-2024-123'), (SELECT id FROM users WHERE username = 'juanrangero')),
((SELECT id FROM certifications WHERE certification_number = 'ACGM-2024-456'), (SELECT id FROM users WHERE username = 'juanrangero'));
