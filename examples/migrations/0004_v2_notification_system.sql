-- CREATE TABLE notifications
CREATE TABLE notifications (
	id INTEGER NOT NULL, 
	user_id INTEGER, 
	message VARCHAR, 
	read BOOLEAN, 
	created_at DATETIME, 
	PRIMARY KEY (id)
);
