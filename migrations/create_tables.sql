CREATE DATABASE jibas_db;
CREATE USER jibas_user WITH PASSWORD 'secure_pass';
GRANT ALL PRIVILEGES ON DATABASE jibas_db TO jibas_user;

CREATE INDEX idx_challenges_user_status ON auth_challenges(user_id, status);
CREATE INDEX idx_challenges_expires ON auth_challenges(expires_at);
CREATE INDEX idx_audit_user_time ON audit_logs(user_id, created_at DESC);
