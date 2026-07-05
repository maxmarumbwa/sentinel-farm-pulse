-- Delete ALL existing records
TRUNCATE TABLE fields_admin_admin1 RESTART IDENTITY CASCADE;

-- Insert all provinces
INSERT INTO fields_admin_admin1 (name, pcode) VALUES
    ('Bulawayo', 'ZW10'),
    ('Harare', 'ZW19'),
    ('Manicaland', 'ZW11'),
    ('Mashonaland Central', 'ZW12'),
    ('Mashonaland East', 'ZW13'),
    ('Mashonaland West', 'ZW14'),
    ('Masvingo', 'ZW18'),
    ('Matabeleland North', 'ZW15'),
    ('Matabeleland South', 'ZW16'),
    ('Midlands', 'ZW17');