-- ==========================================
-- CIVICFLOW PRO - COMPLETE DATABASE SETUP (UPDATED)
-- Copyright (c) 2026
-- ==========================================

-- 1. FRESH START (Wipe old data to prevent conflicts)
DROP DATABASE IF EXISTS civicflow;
CREATE DATABASE civicflow;
USE civicflow;

-- ==========================================
-- 2. USERS TABLE (Citizens & Super Admins)
-- ==========================================
CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(150) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL, 
    phone VARCHAR(20),                -- Required for Twilio SMS
    role VARCHAR(20) DEFAULT 'citizen', -- 'citizen' or 'admin'
    address TEXT,                     -- Added address field for profile
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ==========================================
-- 3. COMPLAINTS TABLE (The Core Logic)
-- ==========================================
CREATE TABLE complaints (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    tracking_id VARCHAR(20) UNIQUE NOT NULL,
    
    -- AI & Routing Data
    department VARCHAR(100) NOT NULL,
    complaint TEXT NOT NULL,
    urgency VARCHAR(20) NOT NULL,      -- 'Medium', 'High', 'Critical'
    status VARCHAR(50) DEFAULT 'Registered',
    
    -- Media & Location
    image_path VARCHAR(255),
    latitude VARCHAR(50),              -- GPS Lat
    longitude VARCHAR(50),             -- GPS Long
    
    -- Hierarchy Tracking
    current_desk VARCHAR(50) DEFAULT 'Section Clerk',
    hierarchy_status VARCHAR(50) DEFAULT 'Pending Review',
    appeal_status VARCHAR(50) DEFAULT 'None', -- Added for Appeal logic
    
    -- Dates
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    target_date DATE,
    date_resolved DATE,
    
    -- Feedback
    feedback_comment TEXT,
    rating INT,

    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- ==========================================
-- 4. VOTING TABLE (For Duplicate Detection)
-- ==========================================
CREATE TABLE complaint_votes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    complaint_id INT NOT NULL,
    user_id INT NOT NULL,
    voter_name VARCHAR(100),
    voted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (complaint_id) REFERENCES complaints(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- ==========================================
-- 5. UPDATES TABLE (History Timeline)
-- ==========================================
CREATE TABLE complaint_updates (
    id INT AUTO_INCREMENT PRIMARY KEY,
    complaint_id INT NOT NULL,
    status VARCHAR(50) NOT NULL,
    remarks TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (complaint_id) REFERENCES complaints(id) ON DELETE CASCADE
);

-- ==========================================
-- 6. DEPARTMENT ADMINS (The 12 Official Logins)
-- ==========================================
CREATE TABLE department_admins (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100),
    email VARCHAR(150) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    department VARCHAR(100)
);
-- ==========================================
-- 7. LOGIN LOGS (New Audit Trail) 
-- ==========================================
CREATE TABLE login_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    email VARCHAR(150),
    role VARCHAR(50),
    ip_address VARCHAR(50),
    status VARCHAR(50),   -- <--- THIS IS THE NEW LINE YOU NEED
    login_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ==========================================
-- 8. SEED DATA: SUPER ADMIN
-- ==========================================
-- Fixed: Password set to 'admin123' (Plain text for testing)
INSERT INTO users (name, email, password, role) VALUES 
('System Administrator', 'admin@civicflow.com', 'admin123', 'super_admin'); 

-- ==========================================
-- 9. SEED DATA: DEPARTMENT OFFICERS
-- ==========================================
-- Fixed: All passwords set to 'admin123'
INSERT INTO department_admins (name, email, password, department) VALUES 
-- Infrastructure
('PWD Officer', 'pwd@admin.com', 'admin123', 'PWD (Roads)'),
('KSEB Officer', 'power@admin.com', 'admin123', 'KSEB'),
('Water Authority', 'water@admin.com', 'admin123', 'Water Authority'),

-- Safety & Health
('Police Control', 'police@admin.com', 'admin123', 'Police'),
('Health Inspector', 'health@admin.com', 'admin123', 'Health Dept'),
('Fire & Rescue', 'fire@admin.com', 'admin123', 'Fire Force'),

-- Governance
('Municipality Secretary', 'muni@admin.com', 'admin123', 'Municipality'),
('Revenue Officer', 'revenue@admin.com', 'admin123', 'Revenue Dept'),
('Education Officer', 'education@admin.com', 'admin123', 'Education Dept'),

-- Social Services
('Labor Officer', 'labor@admin.com', 'admin123', 'Labor Dept'),
('Civil Supplies', 'ration@admin.com', 'admin123', 'Civil Supplies'),
('Agriculture Officer', 'agri@admin.com', 'admin123', 'Agriculture');

-- ==========================================
-- 10. FINAL VERIFICATION
-- ==========================================
SELECT 'Database Built Successfully with Working Passwords!' AS 'Status';
SELECT * FROM department_admins;