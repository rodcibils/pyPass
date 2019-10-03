import sqlite3
import io
import numpy as np
from aes import AESCipher
import datetime
import string

class DBSingleton(object):
	_instances = {}
	currentUser = -1
	currentPassphrase = ""
	def __new__(class_, *args, **kwargs):
		if class_ not in class_._instances:
			class_._instances[class_] = super(DBSingleton, class_).__new__(class_, *args, **kwargs)
		return class_._instances[class_]

	def __init__(self):
		self.conn = None
		self.isConnected = False
		sqlite3.register_adapter(np.ndarray, self.adapt_array)
		sqlite3.register_converter("BLOB", self.convert_array)

	def setUser(self, id_user, username, passphrase):
		aes = AESCipher(passphrase)
		username = aes.decrypt(username)
		if username:
			self.currentUser = id_user
			self.currentPassphrase = passphrase
			self.registerLog("Login")
		return username

	def logout(self):
		self.registerLog("Logout")
		self.currentUser = -1
		self.currentPassphrase = ""

	def adapt_array(self, arr):
		out = io.BytesIO()
		np.save(out, arr)
		out.seek(0)
		return sqlite3.Binary(out.read())

	def convert_array(self, text):
		out = io.BytesIO(text)
		out.seek(0)
		return np.load(out)

	def connect(self):
		if not self.isConnected:
			self.conn = sqlite3.connect("../bin/main.db", detect_types=sqlite3.PARSE_DECLTYPES)
			self.isConnected = True

	def close(self):
		if self.isConnected:
			self.conn.close()
			self.isConnected = False

	def registerUser(self, usr, pwd, enc):
		aes = AESCipher(pwd)
		usr = aes.encrypt(usr)
		c = self.conn.cursor()
		c.execute("INSERT INTO users(username, encoding) VALUES (?,?)", (usr,enc))
		self.conn.commit()
		c.close()

	def getKnownUsers(self):
		known_ids = []
		known_names = []
		known_encodings = []
		c = self.conn.cursor()
		c.execute("SELECT * FROM users")
		
		for row in c:
			known_ids.append(row[0])
			known_names.append(row[1])
			known_encodings.append(row[2])

		c.close()
		return known_ids, known_names, known_encodings

	def saveNote(self, title, content, timestamp):
		aes = AESCipher(self.currentPassphrase)
		title = aes.encrypt(title)
		content = aes.encrypt(content)
		timestamp = aes.encrypt(timestamp)
		c = self.conn.cursor()
		c.execute("INSERT INTO notes(title, content, note_timestamp, id_user) VALUES (?,?,?,?)", \
			(title,content,timestamp,self.currentUser))
		id_note = c.lastrowid
		self.conn.commit()
		c.close()
		self.registerLog("Private note succesfully saved")
		return id_note

	def updateNote(self, id_note, title, content, timestamp):
		aes = AESCipher(self.currentPassphrase)
		title = aes.encrypt(title)
		content = aes.encrypt(content)
		timestamp = aes.encrypt(timestamp)
		c = self.conn.cursor()
		c.execute("UPDATE notes SET title=?, content=?, note_timestamp=? WHERE id_note=?", \
			(title,content,timestamp,id_note))
		self.conn.commit()
		c.close()
		self.registerLog("Private note succesfully updated")

	def getAllNotes(self):
		c = self.conn.cursor()
		c.execute("SELECT id_note, title, content, note_timestamp FROM notes WHERE id_user=?", \
			(self.currentUser,))
		notes = []
		for row in c:
			aes = AESCipher(self.currentPassphrase)
			note = [row[0], aes.decrypt(row[1]), aes.decrypt(row[2]), aes.decrypt(row[3])]
			notes.append(note)
		c.close()
		self.registerLog("Private notes successfully retrieved from database")
		return notes

	def deleteNote(self, id_note):
		c = self.conn.cursor()
		c.execute("DELETE FROM notes WHERE id_note=?", (id_note,))
		self.conn.commit()
		c.close()
		self.registerLog("Private note succesfully deleted")

	def getAllWebAccounts(self):
		c = self.conn.cursor()
		c.execute("SELECT id_account, website, username, email, password FROM web_account WHERE id_user=?", \
			(self.currentUser,))
		accounts = []
		for row in c:
			aes = AESCipher(self.currentPassphrase)
			account = [row[0], aes.decrypt(row[1]), aes.decrypt(row[2]), aes.decrypt(row[3]),\
				aes.decrypt(row[4])]
			accounts.append(account)
		c.close()
		self.registerLog("Web accounts succesfully retrieved from database")
		return accounts

	def saveWebAccount(self, user, email, password, website):
		aes = AESCipher(self.currentPassphrase)
		user = aes.encrypt(user)
		email = aes.encrypt(email)
		password = aes.encrypt(password)
		website = aes.encrypt(website)
		c = self.conn.cursor()
		c.execute("INSERT INTO web_account(username, email, password, website, id_user) VALUES (?,?,?,?,?)", \
			(user, email, password, website, self.currentUser))
		id_web = c.lastrowid
		self.conn.commit()
		c.close()
		self.registerLog("Web account succesfully saved")
		return id_web

	def updateWebAccount(self, id_web, user, email, website, password):
		aes = AESCipher(self.currentPassphrase)
		user = aes.encrypt(user)
		email = aes.encrypt(email)
		password = aes.encrypt(password)
		website = aes.encrypt(website)
		c = self.conn.cursor()
		c.execute("UPDATE web_account SET username=?, email=?, password=?, website=? WHERE id_account=?", \
			(user, email, password, website, id_web))
		self.conn.commit()
		c.close()
		self.registerLog("Web account succesfully updated")

	def deleteWebAccount(self, id_web):
		c = self.conn.cursor()
		c.execute("DELETE FROM web_account WHERE id_account=?", (id_web,))
		self.conn.commit()
		c.close()
		self.registerLog("Web account succesfully deleted")

	def getAllBankAccounts(self):
		c = self.conn.cursor()
		c.execute("SELECT id_account, bank_name, detail, username, password, pin, cbu, alias FROM bank_account WHERE id_user=?", \
			(self.currentUser,))
		accounts = []
		for row in c:
			aes = AESCipher(self.currentPassphrase)
			account = [row[0], aes.decrypt(row[1]), aes.decrypt(row[2]), \
				aes.decrypt(row[3]), aes.decrypt(row[4]), aes.decrypt(row[5]), aes.decrypt(row[6]), \
				aes.decrypt(row[7])]
			accounts.append(account)
		c.close()
		self.registerLog("Bank accounts succesfully retrieved from database")
		return accounts

	def saveBankAccount(self, name, detail, user, password, pin, cbu, alias):
		aes = AESCipher(self.currentPassphrase)
		name = aes.encrypt(name)
		detail = aes.encrypt(detail)
		user = aes.encrypt(user)
		password = aes.encrypt(password)
		pin = aes.encrypt(pin)
		cbu = aes.encrypt(cbu)
		alias = aes.encrypt(alias)
		c = self.conn.cursor()
		c.execute("INSERT INTO bank_account(bank_name, detail, username, password, pin, cbu, alias, id_user) VALUES (?,?,?,?,?,?,?,?)", \
			(name, detail, user, password, pin, cbu, alias, self.currentUser))
		id_bank = c.lastrowid
		self.conn.commit()
		c.close()
		self.registerLog("Bank account succesfully saved")
		return id_bank

	def updateBankAccount(self, id_bank, name, detail, user, password, pin, cbu, alias):
		aes = AESCipher(self.currentPassphrase)
		name = aes.encrypt(name)
		detail = aes.encrypt(detail)
		user = aes.encrypt(user)
		password = aes.encrypt(password)
		pin = aes.encrypt(pin)
		cbu = aes.encrypt(cbu)
		alias = aes.encrypt(alias)
		c = self.conn.cursor()
		c.execute("UPDATE bank_account SET bank_name=?, detail=?, username=?, password=?, pin=?, cbu=?, alias=? WHERE id_account=?", \
			(name, detail, user, password, pin, cbu, alias, id_bank))
		self.conn.commit()
		c.close()
		self.registerLog("Bank account succesfully updated")

	def deleteBankAccount(self, id_bank):
		c = self.conn.cursor()
		c.execute("DELETE FROM bank_card WHERE id_account=?", (id_bank,))
		c.execute("DELETE FROM bank_account WHERE id_account=?", (id_bank,))
		self.conn.commit()
		c.close()
		self.registerLog("Bank account succesfully deleted")

	def getAllBankCards(self, id_bank):
		c = self.conn.cursor()
		c.execute("SELECT id_card, entity, type, detail, card_number, security_code FROM bank_card WHERE id_account=?", \
			(id_bank,))
		cards = []
		for row in c:
			aes = AESCipher(self.currentPassphrase)
			card = [row[0], aes.decrypt(row[1]), aes.decrypt(row[2]), aes.decrypt(row[3]), \
				aes.decrypt(row[4]), aes.decrypt(row[5])]
			cards.append(card)
		c.close()
		self.registerLog("Bank cards succesfully retrieved from database")
		return cards

	def saveBankCard(self, entity, card_type, card_number, code, detail, id_bank):
		aes = AESCipher(self.currentPassphrase)
		entity = aes.encrypt(entity)
		card_type = aes.encrypt(card_type)
		card_number = aes.encrypt(card_number)
		code = aes.encrypt(code)
		detail = aes.encrypt(detail)
		c = self.conn.cursor()
		c.execute("INSERT INTO bank_card(entity, type, card_number, security_code, detail, id_account) VALUES (?,?,?,?,?,?)", \
			(entity, card_type, card_number, code, detail, id_bank))
		id_card = c.lastrowid
		self.conn.commit()
		c.close()
		self.registerLog("Bank card succesfully saved")
		return id_card

	def updateBankCard(self, id_card, entity, card_type, card_number, code, detail):
		aes = AESCipher(self.currentPassphrase)
		entity = aes.encrypt(entity)
		card_type = aes.encrypt(card_type)
		card_number = aes.encrypt(card_number)
		code = aes.encrypt(code)
		detail = aes.encrypt(detail)
		c = self.conn.cursor()
		c.execute("UPDATE bank_card SET entity=?, type=?, card_number=?, security_code=?, detail=? WHERE id_card=?",\
			(entity, card_type, card_number, code, detail, id_card))
		self.conn.commit()
		c.close()
		self.registerLog("Bank card succesfully updated")

	def deleteBankCard(self, id_card):
		c = self.conn.cursor()
		c.execute("DELETE FROM bank_card WHERE id_card=?", (id_card,))
		self.conn.commit()
		c.close()
		self.registerLog("Bank card succesfully deleted")

	def getAllBooks(self):
		c = self.conn.cursor()
		c.execute("SELECT id_book, title, detail FROM contact_book WHERE id_user=?", (self.currentUser,))
		agendas = []
		for row in c:
			aes = AESCipher(self.currentPassphrase)
			agenda = [row[0], aes.decrypt(row[1]), aes.decrypt(row[2])]
			agendas.append(agenda)
		c.close()
		self.registerLog("Contact books succesfully retrieved from database")
		return agendas

	def saveBook(self, title, detail):
		aes = AESCipher(self.currentPassphrase)
		title = aes.encrypt(title)
		detail = aes.encrypt(detail)
		c = self.conn.cursor()
		c.execute("INSERT INTO contact_book(title, detail, id_user) VALUES (?,?,?)", \
			(title, detail, self.currentUser))
		id_agenda = c.lastrowid
		self.conn.commit()
		c.close()
		self.registerLog("Contact book succesfully saved")
		return id_agenda

	def updateBook(self, id_book, title, detail):
		aes = AESCipher(self.currentPassphrase)
		title = aes.encrypt(title)
		detail = aes.encrypt(detail)
		c = self.conn.cursor()
		c.execute("UPDATE contact_book SET title=?, detail=? WHERE id_book=?", (title, detail, id_book))
		self.conn.commit()
		c.close()
		self.registerLog("Contact book succesfully updated")

	def deleteBook(self, id_book):
		c = self.conn.cursor()
		c.execute("DELETE FROM contact WHERE id_book=?", (id_book,))
		c.execute("DELETE FROM contact_book WHERE id_book=?", (id_book,))
		self.conn.commit()
		c.close()
		self.registerLog("Contact book succesfully deleted")

	def registerLog(self, event_detail):
		self.connect()
		timestamp = datetime.datetime.now()
		timestamp = timestamp.strftime("%Y-%m-%d %H:%M:%S")
		aes = AESCipher(self.currentPassphrase)
		timestamp = aes.encrypt(timestamp)
		event_detail = aes.encrypt(event_detail)
		c = self.conn.cursor()
		c.execute("INSERT INTO logs(event_timestamp, event_user, event_detail) VALUES (?,?,?)", \
			(timestamp, self.currentUser, event_detail))
		self.conn.commit()
		c.close()
		self.close()

	def getAllLogs(self):
		c = self.conn.cursor()
		c.execute("SELECT id_log, event_timestamp, event_detail FROM logs WHERE event_user=?", \
			(self.currentUser,))
		logs = []
		for row in c:
			aes = AESCipher(self.currentPassphrase)
			log = [row[0], aes.decrypt(row[1]), aes.decrypt(row[2])]
			logs.append(log)
		c.close()
		return logs

	def getAllContacts(self, id_book):
		c = self.conn.cursor()
		c.execute("SELECT id_contact, full_name, address, email, phone_one, phone_two, webpage, detail FROM contact WHERE id_book=?", \
			(id_book,))
		contacts = []
		for row in c:
			aes = AESCipher(self.currentPassphrase)
			contact = [row[0], aes.decrypt(row[1]), aes.decrypt(row[2]), aes.decrypt(row[3]), aes.decrypt(row[4]), \
				aes.decrypt(row[5]), aes.decrypt(row[6]), aes.decrypt(row[7])]
			contacts.append(contact)
		c.close()
		self.registerLog("Contacts from contact book succesfully retrieved from database")
		return contacts

	def deleteContact(self, id_contact):
		c = self.conn.cursor()
		c.execute("DELETE FROM contact WHERE id_contact=?", (id_contact,))
		self.conn.commit()
		c.close()
		self.registerLog("Contact succesfully deleted")

	def saveContact(self, name, address, email, phoneOne, phoneTwo, webPage, detail, id_book):
		aes = AESCipher(self.currentPassphrase)
		name = aes.encrypt(name)
		address = aes.encrypt(address)
		email = aes.encrypt(email)
		phoneOne = aes.encrypt(phoneOne)
		phoneTwo = aes.encrypt(phoneTwo)
		webPage = aes.encrypt(webPage)
		detail = aes.encrypt(detail)
		c = self.conn.cursor()
		c.execute("INSERT INTO contact(full_name, address, email, phone_one, phone_two, webpage, detail, id_book) VALUES (?,?,?,?,?,?,?,?)", \
			(name, address, email, phoneOne, phoneTwo, webPage, detail, id_book))
		id_contact = c.lastrowid
		self.conn.commit()
		c.close()
		self.registerLog("Contact succesfully saved")
		return id_contact

	def updateContact(self, id_contact, name, address, email, phoneOne, phoneTwo, webPage, detail):
		aes = AESCipher(self.currentPassphrase)
		name = aes.encrypt(name)
		address = aes.encrypt(address)
		email = aes.encrypt(email)
		phoneOne = aes.encrypt(phoneOne)
		phoneTwo = aes.encrypt(phoneTwo)
		webPage = aes.encrypt(webPage)
		detail = aes.encrypt(detail)
		c = self.conn.cursor()
		c.execute("UPDATE contact SET full_name=?, address=?, email=?, phone_one=?, phone_two=?,webpage=?,detail=? WHERE id_contact=?",\
			(name, address, email, phoneOne, phoneTwo, webPage, detail, id_contact))
		self.conn.commit()
		c.close()
		self.registerLog("Contact succesfully updated")

class DBManager(DBSingleton):
	pass
