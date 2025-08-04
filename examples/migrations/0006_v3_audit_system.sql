-- CREATE TABLE audit_logs
CREATE TABLE audit_logs (
	id INTEGER NOT NULL, 
	table_name VARCHAR, 
	action VARCHAR, 
	timestamp DATETIME, 
	PRIMARY KEY (id)
);
