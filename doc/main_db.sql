PRAGMA foreign_keys=ON;

BEGIN TRANSACTION;

CREATE TABLE IF NOT EXISTS users(
	id_user INTEGER PRIMARY KEY,
	username TEXT UNIQUE,
	encoding BLOB
);

CREATE TABLE IF NOT EXISTS logs(
	id_log INTEGER PRIMARY KEY,
	event_timestamp TEXT,
	event_user INTEGER,
	event_detail TEXT,
	FOREIGN KEY(event_user) REFERENCES users(id_user)
);

CREATE TABLE IF NOT EXISTS notes(
	id_note INTEGER PRIMARY KEY,
	title TEXT,
	content TEXT,
	note_timestamp TEXT,
	id_user INTEGER,
	FOREIGN KEY(id_user) REFERENCES users(id_user)
);

CREATE TABLE IF NOT EXISTS web_account(
	id_account INTEGER PRIMARY KEY,
	username TEXT,
	email TEXT,
	password TEXT,
	website TEXT,
	id_user INTEGER,
	FOREIGN KEY(id_user) REFERENCES users(id_user)
);

CREATE TABLE IF NOT EXISTS contact_book(
	id_book INTEGER PRIMARY KEY,
	id_user INTEGER,
	title TEXT,
	detail TEXT,
	FOREIGN KEY(id_user) REFERENCES users(id_user)
);

CREATE TABLE IF NOT EXISTS contact(
	id_contact INTEGER PRIMARY KEY,
	id_book INTEGER,
	full_name TEXT,
	address TEXT,
	email TEXT,
	phone_one TEXT,
	phone_two TEXT,
	webpage TEXT,
	detail TEXT,
	FOREIGN KEY(id_book) REFERENCES agenda(id_book)
);

CREATE TABLE IF NOT EXISTS bank_account(
	id_account INTEGER PRIMARY KEY,
	id_user INTEGER,
	bank_name TEXT,
	username TEXT,
	password TEXT,
	pin TEXT,
	cbu TEXT,
	alias TEXT,
	detail TEXT,
	FOREIGN KEY(id_user) REFERENCES users(id_user)
);

CREATE TABLE IF NOT EXISTS bank_card(
	id_card INTEGER PRIMARY KEY,
	id_account INTEGER,
	entity TEXT,
	card_number TEXT,
	detail TEXT,
	type TEXT,
	security_code TEXT,
	FOREIGN KEY(id_account) REFERENCES bank_account(id_account)
);

COMMIT;
