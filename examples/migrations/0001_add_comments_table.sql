-- CREATE TABLE comments
CREATE TABLE comments (
	id INTEGER NOT NULL, 
	content VARCHAR NOT NULL, 
	post_id INTEGER, 
	author_id INTEGER, 
	created_at DATETIME, 
	PRIMARY KEY (id)
);
