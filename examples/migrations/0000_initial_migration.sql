-- CREATE TABLE users
CREATE TABLE users (
	id INTEGER NOT NULL, 
	username VARCHAR(50) NOT NULL, 
	email VARCHAR(100) NOT NULL, 
	is_active BOOLEAN, 
	created_at DATETIME, 
	PRIMARY KEY (id), 
	UNIQUE (username), 
	UNIQUE (email)
);

-- CREATE TABLE posts
CREATE TABLE posts (
	id INTEGER NOT NULL, 
	title VARCHAR(200) NOT NULL, 
	content VARCHAR, 
	author_id INTEGER, 
	published BOOLEAN, 
	created_at DATETIME, 
	PRIMARY KEY (id)
);
