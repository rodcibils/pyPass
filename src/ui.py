import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk
import face_recognition
import cv2
import numpy as np
import os.path
from db import DBManager
import datetime
import string
import random

# ======== User Interface ========

# helper class for UI management
class UIManager:
	# starts the program
	def startUI():
		builder = Gtk.Builder()
		builder.add_from_file("../bin/ui.glade")
		window = MenuWindow(builder)
		window.showWindow()
		Gtk.main()


# ======== Parent Classes ========

class StandardWindow:
	def __init__(self, window, parent):
		self.window = window
		self.parent = parent

	def showWindow(self):
		self.window.show_all()

	def hideWindow(self):
		self.window.hide()


class ListWindow(StandardWindow):
	def __init__(self, window, parent, tree, liststore, searchEntry):
		super().__init__(window, parent)
		self.tree = tree
		self.liststore = liststore
		self.searchEntry = searchEntry

		self.clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)

		if self.searchEntry:
			self.searchEntry.connect("changed", self.onSearch)

	def setFilterAndSortedModel(self):
		self.modelFilter = self.liststore.filter_new()
		self.modelFilter.set_visible_func(self.filterFunc, data=None)
		self.modelSorted = Gtk.TreeModelSort(self.modelFilter)
		self.tree.set_model(self.modelSorted)

	def filterFunc(self, model, treeiter, data):
		currentSearch = self.searchEntry.get_text()
		if not currentSearch:
			return True
		return currentSearch in model[treeiter][1]

	def initializeTree(self, columns, invisible):
		renderer = Gtk.CellRendererText()
		for i in range(0, len(columns)):
			listCol = Gtk.TreeViewColumn(columns[i], renderer, text=i)
			listCol.set_sort_column_id(i)
			if invisible and columns[i] in invisible:
				listCol.set_visible(False)
			self.tree.append_column(listCol)

	def onSearch(self, widget):
		self.modelFilter.refilter()

	def fillList(self, elements):
		for element in elements:
			self.liststore.append(list(element))

	def addToList(self, toAdd):
		self.liststore.append(toAdd)

	def onClose(self, widget, *args):
		self.liststore.clear()
		if self.searchEntry:
			self.searchEntry.set_text("")
		super().hideWindow()
		return True

	def onClipboard(self, index):
		select = self.tree.get_selection()
		model, treeiter = select.get_selected()
		if treeiter is not None:
			element = model[treeiter][index]
			self.clipboard.set_text(element, -1)


# ======== Common Classes ========

class MenuWindow(StandardWindow):
	def __init__(self, builder):
		window = builder.get_object("window_menu")
		super().__init__(window, None)

		self.loginButton = builder.get_object("btn_menu_face")
		self.registerButton = builder.get_object("btn_menu_new_user")

		self.window.connect("delete-event", Gtk.main_quit)
		self.loginButton.connect("clicked", self.onLoginClicked)
		self.registerButton.connect("clicked", self.onRegisterClicked)

		self.registerWindow = RegisterWindow(builder, self)
		self.passWindow = PassphraseWindow(builder, self)
		self.mainWindow = MainWindow(builder, self)

	def onLoginClicked(self, button):
		recognizer = FaceRecognizer()
		self.window.hide()
		id_user, name = recognizer.recognizeUser()
		self.window.show_all()
		if name is not None:
			self.window.hide()
			self.passWindow.showWindow(id_user, name)

	def onRegisterClicked(self, button):
		self.window.hide()
		self.registerWindow.showWindow()

	def successfulLogin(self):
		self.mainWindow.showWindow()


class MainWindow(StandardWindow):
	def __init__(self, builder, parent):
		window = builder.get_object("window_main")
		super().__init__(window, parent)

		self.notesButton = builder.get_object("menu_main_notes")
		self.webButton = builder.get_object("menu_main_web")
		self.bookButton = builder.get_object("menu_main_book")
		self.bankButton = builder.get_object("menu_main_bank")
		self.logsButton = builder.get_object("menu_main_logs")
		self.logoutButton = builder.get_object("menu_main_logout")

		self.window.connect("delete-event", self.onClose)
		self.notesButton.connect("activate", self.showNotes)
		self.webButton.connect("activate", self.showWeb)
		self.bookButton.connect("activate", self.showBook)
		self.bankButton.connect("activate", self.showBank)
		self.logsButton.connect("activate", self.showLogs)
		self.logoutButton.connect("activate", self.onLogout)

		self.genPassWindow = PassGenerateWindow(builder)
		self.genPinWindow = PinGenerateWindow(builder)
		self.notesWindow = NotesListWindow(builder, self)
		self.webWindow = WebAccountsListWindow(builder, self, self.genPassWindow)
		self.bankWindow = BankAccountsListWindow(builder, self, self.genPassWindow, self.genPinWindow)
		self.bookWindow = BookListWindow(builder, self)
		self.logsWindow = LogListWindow(builder, self)

	def onLogout(self, widget):
		dbManager = DBManager()
		dbManager.logout()
		self.window.hide()
		self.parent.showWindow()

	def onClose(self, widget, *args):
		dbManager = DBManager()
		dbManager.logout()
		self.hideWindow()
		self.parent.showWindow()
		return True

	def showWeb(self, widget):
		self.webWindow.showWindow()

	def showNotes(self, widget):
		self.notesWindow.showWindow()

	def showBank(self, widget):
		self.bankWindow.showWindow()

	def showBook(self, widget):
		self.bookWindow.showWindow()

	def showLogs(self, widget):
		self.logsWindow.showWindow()


class NotesListWindow(ListWindow):
	def __init__(self, builder, parent):
		searchEntry = builder.get_object("txt_notes_list_search")
		tree = builder.get_object("tree_notes_list")
		liststore = builder.get_object("list_notes")
		window = builder.get_object("window_notes_list")
		super().__init__(window, parent, tree, liststore, searchEntry)
		
		self.addButton = builder.get_object("btn_notes_list_add")
		self.editButton = builder.get_object("btn_notes_list_edit")
		self.deleteButton = builder.get_object("btn_notes_list_delete")

		self.setFilterAndSortedModel()

		self.window.connect("delete-event", self.onClose)
		self.addButton.connect("clicked", self.onAdd)
		self.editButton.connect("clicked", self.onEdit)
		self.deleteButton.connect("clicked", self.onDelete)

		self.addWindow = NotesAddWindow(builder, self)
		self.editWindow = NotesEditWindow(builder, self)

		columns = ["ID", "Title", "Content", "Date"]
		self.initializeTree(columns, None)

	def showWindow(self):
		self.fillList()
		super().showWindow()

	def fillList(self):
		dbManager = DBManager()
		dbManager.connect()
		notes = dbManager.getAllNotes()
		dbManager.close()
		super().fillList(notes)

	def updateList(self):
		self.liststore.clear()
		self.fillList()

	def onAdd(self, widget):
		self.addWindow.showWindow()

	def onEdit(self, widget):
		select = self.tree.get_selection()
		model, treeiter = select.get_selected()
		if treeiter is not None:
			self.editWindow.showWindow(model, treeiter)

	def onDelete(self, widget):
		select = self.tree.get_selection()
		model, treeiter = select.get_selected()
		if treeiter is not None:
			result = UIUtils.showDesitionMessage(self.window, "Delete private note", \
				"Are you sure about deleting this private note?")
			if result == Gtk.ResponseType.YES:
				dbManager = DBManager()
				id_note = model[treeiter][0]
				dbManager.connect()
				dbManager.deleteNote(id_note)
				dbManager.close()
				self.updateList()


class NotesAddWindow(StandardWindow):
	def __init__(self, builder, parent):
		window = builder.get_object("window_notes_add")
		super().__init__(window, parent)

		self.titleEntry = builder.get_object("txt_notes_add_title")
		self.contentEntry = builder.get_object("txt_notes_add_content")
		self.okButton = builder.get_object("btn_notes_add_ok")
		self.cancelButton = builder.get_object("btn_notes_add_cancel")

		self.window.connect("delete-event", self.onClose)
		self.okButton.connect("clicked", self.onAccept)
		self.cancelButton.connect("clicked", self.onCancel)

	def onClose(self, widget, *args):
		self.titleEntry.set_text("")
		self.contentEntry.get_buffer().set_text("")
		self.hideWindow()
		return True

	def onCancel(self, widget):
		self.titleEntry.set_text("")
		self.contentEntry.get_buffer().set_text("")
		self.hideWindow()

	def onAccept(self, widget):
		title = self.titleEntry.get_text()
		contentBuffer = self.contentEntry.get_buffer()
		start, end = contentBuffer.get_bounds()
		content = contentBuffer.get_text(start, end, True)

		if self.validateFields(title, content):
			dbManager = DBManager()
			dbManager.connect()
			timestamp = datetime.datetime.now()
			timestamp = timestamp.strftime("%Y-%m-%d %H:%M:%S")
			id_note = dbManager.saveNote(title, content, timestamp)
			dbManager.close()
			UIUtils.showInfoMessage(self.window, "Private note saved", \
				"Private note succesfully saved")
			self.titleEntry.set_text("")
			self.contentEntry.get_buffer().set_text("")
			self.window.hide()
			note = [id_note, title, content, timestamp]
			self.parent.addToList(note)

	def validateFields(self, title, content):
		if not title or not content:
			UIUtils.showErrorMessage(self.window, "Error", \
				"All fields required")
			return False
		return True


class NotesEditWindow(StandardWindow):
	def __init__(self, builder, parent):
		window = builder.get_object("window_notes_edit")
		super().__init__(window, parent)

		self.titleEntry = builder.get_object("txt_notes_edit_title")
		self.contentEntry = builder.get_object("txt_notes_edit_content")
		self.okButton = builder.get_object("btn_notes_edit_ok")
		self.cancelButton = builder.get_object("btn_notes_edit_cancel")

		self.window.connect("delete-event", self.onClose)
		self.okButton.connect("clicked", self.onAccept)
		self.cancelButton.connect("clicked", self.onCancel)

	def onClose(self, widget, *args):
		self.titleEntry.set_text("")
		self.contentEntry.get_buffer().set_text("")
		self.hideWindow()
		return True

	def showWindow(self, model, treeiter):
		self.model = model
		self.treeiter = treeiter
		self.titleEntry.set_text(model[treeiter][1])
		self.contentEntry.get_buffer().set_text(model[treeiter][2])
		super().showWindow()

	def onDelete(self, widget, *args):
		self.titleEntry.set_text("")
		self.contentEntry.get_buffer().set_text("")
		self.hideWindow()
		return True

	def onAccept(self, widget):
		title = self.titleEntry.get_text()
		contentBuffer = self.contentEntry.get_buffer()
		start, end = contentBuffer.get_bounds()
		content = contentBuffer.get_text(start, end, True)

		if self.validateFields(title, content):
			dbManager = DBManager()
			dbManager.connect()
			timestamp = datetime.datetime.now()
			timestamp = timestamp.strftime("%Y-%m-%d %H:%M:%S")
			id_note = self.model[self.treeiter][0]
			dbManager.updateNote(id_note, title, content, timestamp)
			dbManager.close()
			UIUtils.showInfoMessage(self.window, "Private note updated", \
				"Private note succesfully updated")
			self.titleEntry.set_text("")
			self.contentEntry.get_buffer().set_text("")
			self.hideWindow()
			self.parent.updateList()

	def validateFields(self, title, content):
		if not title or not content:
			UIUtils.showErrorMessage(self.window, "Error", "All fields required")
			return False

		return True

	def onCancel(self, widget):
		self.titleEntry.set_text("")
		self.contentEntry.get_buffer().set_text("")
		self.hideWindow()


class WebAccountsListWindow(ListWindow):
	def __init__(self, builder, parent, genPassWindow):
		window = builder.get_object("window_web_list")
		searchEntry = builder.get_object("txt_web_list_search")
		tree = builder.get_object("tree_web_list")
		liststore = builder.get_object("list_web")
		super().__init__(window, parent, tree, liststore, searchEntry)
		
		self.addButton = builder.get_object("btn_web_list_add")
		self.editButton = builder.get_object("btn_web_list_edit")
		self.deleteButton = builder.get_object("btn_web_list_delete")
		self.clipboardButton = builder.get_object("btn_web_list_clip")

		self.setFilterAndSortedModel()

		self.window.connect("delete-event", self.onClose)
		self.addButton.connect("clicked", self.onAdd)
		self.editButton.connect("clicked", self.onEdit)
		self.deleteButton.connect("clicked", self.onDelete)
		self.clipboardButton.connect("clicked", self.onClipboard)

		self.generatePassWindow = genPassWindow
		self.addWindow = WebAccountsAddWindow(builder, self, self.generatePassWindow)
		self.editWindow = WebAccountsEditWindow(builder, self, self.generatePassWindow)

		columns = ["ID", "Website", "Username", "EMail", "Password"]
		invisible = ["Password"]
		self.initializeTree(columns, invisible)

	def onClipboard(self, widget):
		super().onClipboard(4)

	def showWindow(self):
		self.fillList()
		super().showWindow()

	def fillList(self):
		dbManager = DBManager()
		dbManager.connect()
		webAccounts = dbManager.getAllWebAccounts()
		dbManager.close()
		super().fillList(webAccounts)

	def updateList(self):
		self.liststore.clear()
		self.fillList()

	def onSearch(self, widget):
		self.modelFilter.refilter()

	def onAdd(self, widget):
		self.addWindow.showWindow()

	def onEdit(self, widget):
		select = self.tree.get_selection()
		model, treeiter = select.get_selected()
		if treeiter is not None:
			self.editWindow.showWindow(model, treeiter)

	def onDelete(self, widget):
		select = self.tree.get_selection()
		model, treeiter = select.get_selected()
		if treeiter is not None:
			result = UIUtils.showDesitionMessage(self.window, "Web account deleted", \
				"Are you sure about deleting this Web Account?")
			if result == Gtk.ResponseType.YES:
				dbManager = DBManager()
				id_web = model[treeiter][0]
				dbManager.connect()
				dbManager.deleteWebAccount(id_web)
				dbManager.close()
				self.updateList()


class WebAccountsAddWindow(StandardWindow):
	def __init__(self, builder, parent, generatePassWindow):
		self.generatePassWindow = generatePassWindow
		
		window = builder.get_object("window_web_add")
		super().__init__(window, parent)

		self.userEntry = builder.get_object("txt_web_add_username")
		self.emailEntry = builder.get_object("txt_web_add_email")
		self.passwordEntry = builder.get_object("txt_web_add_password")
		self.websiteEntry = builder.get_object("txt_web_add_website")
		self.randomButton = builder.get_object("btn_web_add_random")
		self.showButton = builder.get_object("btn_web_add_show")
		self.cancelButton = builder.get_object("btn_web_add_cancel")
		self.okButton = builder.get_object("btn_web_add_ok")

		self.window.connect("delete-event", self.onClose)
		self.okButton.connect("clicked", self.onAccept)
		self.cancelButton.connect("clicked", self.onCancel)
		self.randomButton.connect("clicked", self.onRandom)
		self.showButton.connect("clicked", self.onShow)

	def onRandom(self, widget):
		self.generatePassWindow.showWindow(self)

	def onShow(self, widget):
		flag = self.passwordEntry.get_visibility()
		self.passwordEntry.set_visibility(not flag)

	def setPassword(self, password):
		self.passwordEntry.set_text(password)

	def onClose(self, widget, *args):
		self.userEntry.set_text("")
		self.emailEntry.set_text("")
		self.passwordEntry.set_text("")
		self.websiteEntry.set_text("")
		self.passwordEntry.set_visibility(False)
		self.hideWindow()
		return True

	def onCancel(self, widget):
		self.userEntry.set_text("")
		self.emailEntry.set_text("")
		self.passwordEntry.set_text("")
		self.websiteEntry.set_text("")
		self.passwordEntry.set_visibility(False)
		self.hideWindow()

	def onAccept(self, widget):
		user = self.userEntry.get_text()
		email = self.emailEntry.get_text()
		password = self.passwordEntry.get_text()
		website = self.websiteEntry.get_text()
		if self.validateFields(user, email, password, website):
			dbManager = DBManager()
			dbManager.connect()
			id_web = dbManager.saveWebAccount(user, email, password, website)
			dbManager.close()
			UIUtils.showInfoMessage(self.window, "Web account saved", \
				"Web account succesfully saved")
			self.userEntry.set_text("")
			self.emailEntry.set_text("")
			self.passwordEntry.set_text("")
			self.websiteEntry.set_text("")
			self.passwordEntry.set_visibility(False)
			self.hideWindow()
			webAccount = [id_web, website, user, email, password]
			self.parent.addToList(webAccount)

	def validateFields(self, user, email, password, website):
		if not user or not email or not password or not website:
			UIUtils.showErrorMessage(self.window, "Error", \
				"All fields required")
			return False

		return True	


class WebAccountsEditWindow(StandardWindow):
	def __init__(self, builder, parent, generatePassWindow):
		self.generatePassWindow = generatePassWindow
		
		window = builder.get_object("window_web_edit")
		super().__init__(window, parent)

		self.userEntry = builder.get_object("txt_web_edit_username")
		self.emailEntry = builder.get_object("txt_web_edit_email")
		self.passwordEntry = builder.get_object("txt_web_edit_password")
		self.websiteEntry = builder.get_object("txt_web_edit_website")
		self.randomButton = builder.get_object("btn_web_edit_random")
		self.showButton = builder.get_object("btn_web_edit_show")
		self.cancelButton = builder.get_object("btn_web_edit_cancel")
		self.okButton = builder.get_object("btn_web_edit_ok")

		self.window.connect("delete-event", self.onClose)
		self.okButton.connect("clicked", self.onAccept)
		self.cancelButton.connect("clicked", self.onCancel)
		self.randomButton.connect("clicked", self.onRandom)
		self.showButton.connect("clicked", self.onShow)

	def showWindow(self, model, treeiter):
		self.model = model
		self.treeiter = treeiter
		self.userEntry.set_text(model[treeiter][2])
		self.emailEntry.set_text(model[treeiter][3])
		self.passwordEntry.set_text(model[treeiter][4])
		self.websiteEntry.set_text(model[treeiter][1])
		super().showWindow()

	def onRandom(self, widget):
		self.generatePassWindow.showWindow(self)

	def onShow(self, widget):
		flag = self.passwordEntry.get_visibility()
		self.passwordEntry.set_visibility(not flag)

	def setPassword(self, password):
		self.passwordEntry.set_text(password)

	def onClose(self, widget, *args):
		self.userEntry.set_text("")
		self.emailEntry.set_text("")
		self.passwordEntry.set_text("")
		self.websiteEntry.set_text("")
		self.passwordEntry.set_visibility(False)
		self.hideWindow()
		return True

	def onCancel(self, widget):
		self.userEntry.set_text("")
		self.emailEntry.set_text("")
		self.passwordEntry.set_text("")
		self.websiteEntry.set_text("")
		self.passwordEntry.set_visibility(False)
		self.hideWindow()

	def onAccept(self, widget):
		user = self.userEntry.get_text()
		email = self.emailEntry.get_text()
		website = self.websiteEntry.get_text()
		password = self.passwordEntry.get_text()
		if self.validateFields(user, email, password, website):
			id_web = self.model[self.treeiter][0]
			dbManager = DBManager()
			dbManager.connect()
			dbManager.updateWebAccount(id_web, user, email, website, password)
			dbManager.close()
			UIUtils.showInfoMessage(self.window, "Web Account updated", \
				"Web Account succesfully updated")
			self.userEntry.set_text("")
			self.emailEntry.set_text("")
			self.passwordEntry.set_text("")
			self.websiteEntry.set_text("")
			self.passwordEntry.set_visibility(False)
			self.hideWindow()
			self.parent.updateList()

	def validateFields(self, user, email, password, website):
		if not user or not email or not password or not website:
			UIUtils.showErrorMessage(self.window, "Error", "All fields required")
			return False

		return True


class PassGenerateWindow(StandardWindow):
	def __init__(self, builder):
		window = builder.get_object("window_pass")
		super().__init__(window, None)

		self.passLength = builder.get_object("adj_pass")
		self.specialCharCheck = builder.get_object("check_pass_special_char")
		self.numbersCheck = builder.get_object("check_pass_number")
		self.mayusCheck = builder.get_object("check_pass_mayus")
		self.generatedPass = builder.get_object("lbl_pass_generated_content")
		self.okButton = builder.get_object("btn_pass_ok")
		self.cancelButton = builder.get_object("btn_pass_cancel")
		self.generateButton = builder.get_object("btn_pass_generate")

		self.passLength.set_value(10)

		self.window.connect("delete-event", self.onClose)
		self.okButton.connect("clicked", self.onAccept)
		self.cancelButton.connect("clicked", self.onCancel)
		self.generateButton.connect("clicked", self.onGenerate)

	def showWindow(self, parent):
		self.parent = parent
		self.window.set_transient_for(parent.window)
		super().showWindow()

	def onClose(self, widget, *args):
		self.passLength.set_value(10)
		self.specialCharCheck.set_active(False)
		self.numbersCheck.set_active(False)
		self.mayusCheck.set_active(False)
		self.generatedPass.set_text("")
		self.hideWindow()
		return True

	def onGenerate(self, widget):
		length = int(self.passLength.get_value())
		includeMayus = self.mayusCheck.get_active()
		includeNumbers = self.numbersCheck.get_active()
		includeSpecialChars = self.specialCharCheck.get_active()

		flag = string.ascii_lowercase
		if includeMayus:
			flag = flag + string.ascii_uppercase
		if includeNumbers:
			flag = flag + string.digits
		if includeSpecialChars:
			flag = flag + string.punctuation

		generated = ''.join(random.SystemRandom().choice(flag) for _ in range(length))
		self.generatedPass.set_text(generated)

	def onCancel(self, widget):
		self.passLength.set_value(10)
		self.specialCharCheck.set_active(False)
		self.numbersCheck.set_active(False)
		self.mayusCheck.set_active(False)
		self.generatedPass.set_text("")
		self.hideWindow()

	def onAccept(self, widget):
		password = self.generatedPass.get_text()
		if not password:
			UIUtils.showErrorMessage(self.window, "Error", \
				"You have not generated any password")
			return
		else:
			self.parent.setPassword(password)
			self.passLength.set_value(10)
			self.specialCharCheck.set_active(False)
			self.numbersCheck.set_active(False)
			self.mayusCheck.set_active(False)
			self.generatedPass.set_text("")
			self.hideWindow()


class PinGenerateWindow(StandardWindow):
	def __init__(self, builder):
		window = builder.get_object("window_pin")
		super().__init__(window, None)

		self.passLength = builder.get_object("adj_pin")
		self.specialCharCheck = builder.get_object("check_pin_special_char")
		self.minusCheck = builder.get_object("check_pin_minus")
		self.mayusCheck = builder.get_object("check_pin_mayus")
		self.generatedPass = builder.get_object("lbl_pin_generated_content")
		self.okButton = builder.get_object("btn_pin_ok")
		self.cancelButton = builder.get_object("btn_pin_cancel")
		self.generateButton = builder.get_object("btn_pin_generate")

		self.passLength.set_value(10)

		self.window.connect("delete-event", self.onClose)
		self.okButton.connect("clicked", self.onAccept)
		self.cancelButton.connect("clicked", self.onCancel)
		self.generateButton.connect("clicked", self.onGenerate)

	def showWindow(self, parent):
		self.parent = parent
		self.window.set_transient_for(parent.window)
		super().showWindow()

	def onClose(self, widget, *args):
		self.passLength.set_value(10)
		self.specialCharCheck.set_active(False)
		self.minusCheck.set_active(False)
		self.mayusCheck.set_active(False)
		self.generatedPass.set_text("")
		self.hideWindow()
		return True

	def onGenerate(self, widget):
		length = int(self.passLength.get_value())
		includeMayus = self.mayusCheck.get_active()
		includeMinus = self.minusCheck.get_active()
		includeSpecialChars = self.specialCharCheck.get_active()

		flag = string.digits
		if includeMayus:
			flag = flag + string.ascii_uppercase
		if includeMinus:
			flag = flag + string.ascii_lowercase
		if includeSpecialChars:
			flag = flag + string.punctuation

		generated = ''.join(random.SystemRandom().choice(flag) for _ in range(length))
		self.generatedPass.set_text(generated)

	def onCancel(self, widget):
		self.passLength.set_value(10)
		self.specialCharCheck.set_active(False)
		self.minusCheck.set_active(False)
		self.mayusCheck.set_active(False)
		self.generatedPass.set_text("")
		self.hideWindow()

	def onAccept(self, widget):
		password = self.generatedPass.get_text()
		if not password:
			UIUtils.showErrorMessage(self.window, "Error", \
				"You have not generated any password")
			return
		else:
			self.parent.setPin(password)
			self.passLength.set_value(10)
			self.specialCharCheck.set_active(False)
			self.minusCheck.set_active(False)
			self.mayusCheck.set_active(False)
			self.generatedPass.set_text("")
			self.hideWindow()


class BankAccountsListWindow(ListWindow):
	def __init__(self, builder, parent, genPassWindow, genPinWindow):
		window = builder.get_object("window_bank_list")
		searchEntry = builder.get_object("txt_bank_list_search")
		tree = builder.get_object("tree_bank_list")
		liststore = builder.get_object("list_bank")
		super().__init__(window, parent, tree, liststore, searchEntry)

		self.addButton = builder.get_object("btn_bank_list_add")
		self.editButton = builder.get_object("btn_bank_list_edit")
		self.deleteButton = builder.get_object("btn_bank_list_delete")
		self.showCardsButton = builder.get_object("btn_bank_list_cards")
		self.passClipboard = builder.get_object("btn_bank_list_pass_clip")
		self.pinClipboard = builder.get_object("btn_bank_list_pin_clip")

		self.setFilterAndSortedModel()

		self.window.connect("delete-event", self.onClose)
		self.searchEntry.connect("changed", self.onSearch)
		self.addButton.connect("clicked", self.onAdd)
		self.editButton.connect("clicked", self.onEdit)
		self.deleteButton.connect("clicked", self.onDelete)
		self.passClipboard.connect("clicked", self.onPassClip)
		self.pinClipboard.connect("clicked", self.onPinClip)
		self.showCardsButton.connect("clicked", self.onShowCards)

		self.addWindow = BankAccountsAddWindow(builder, self, genPassWindow, genPinWindow)
		self.editWindow = BankAccountsEditWindow(builder, self, genPassWindow, genPinWindow)
		self.cardsListWindow = BankCardsListWindow(builder, self)

		columns = ["ID", "Bank", "Detail", "Username", "Password", "PIN", "Account number", "Alias"]
		invisible = ["Password", "PIN", "CBU", "Account number"]
		self.initializeTree(columns, invisible)

	def onShowCards(self, widget):
		select = self.tree.get_selection()
		model, treeiter = select.get_selected()
		if treeiter is not None:
			id_bank = model[treeiter][0]
			self.cardsListWindow.showWindow(id_bank)

	def onPassClip(self, widget):
		super().onClipboard(4)

	def onPinClip(self, widget):
		super().onClipboard(5)

	def showWindow(self):
		self.fillList()
		super().showWindow()

	def fillList(self):
		dbManager = DBManager()
		dbManager.connect()
		bankAccounts = dbManager.getAllBankAccounts()
		dbManager.close()
		super().fillList(bankAccounts)

	def updateList(self):
		self.liststore.clear()
		self.fillList()

	def onAdd(self, widget):
		self.addWindow.showWindow()

	def onEdit(self, widget):
		select = self.tree.get_selection()
		model, treeiter = select.get_selected()
		if treeiter is not None:
			self.editWindow.showWindow(model, treeiter)

	def onDelete(self, widget):
		select = self.tree.get_selection()
		model, treeiter = select.get_selected()
		if treeiter is not None:
			result = UIUtils.showDesitionMessage(self.window, "Delete bank account", \
				"Are you sure about deleting this bank account?")
			if result == Gtk.ResponseType.YES:
				dbManager = DBManager()
				id_bank = model[treeiter][0]
				dbManager.connect()
				dbManager.deleteBankAccount(id_bank)
				dbManager.close()
				self.updateList()


class BankAccountsAddWindow(StandardWindow):
	def __init__(self, builder, parent, passWindow, pinWindow):
		self.passWindow = passWindow
		self.pinWindow = pinWindow
		
		window = builder.get_object("window_bank_add")
		super().__init__(window, parent)

		self.nameEntry = builder.get_object("txt_bank_add_name")
		self.userEntry = builder.get_object("txt_bank_add_user")
		self.passEntry = builder.get_object("txt_bank_add_pass")
		self.pinEntry = builder.get_object("txt_bank_add_pin")
		self.cbuEntry = builder.get_object("txt_bank_add_cbu")
		self.aliasEntry = builder.get_object("txt_bank_add_alias")
		self.detailEntry = builder.get_object("txt_bank_add_detail")
		self.generatePassButton = builder.get_object("btn_bank_add_generate_pass")
		self.generatePinButton = builder.get_object("btn_bank_add_generate_pin")
		self.showPassButton = builder.get_object("btn_bank_add_show_pass")
		self.showPinButton = builder.get_object("btn_bank_add_show_pin")
		self.okButton = builder.get_object("btn_bank_add_ok")
		self.cancelButton = builder.get_object("btn_bank_add_cancel")

		self.window.connect("delete-event", self.onClose)
		self.okButton.connect("clicked", self.onAccept)
		self.cancelButton.connect("clicked", self.onCancel)
		self.generatePassButton.connect("clicked", self.onGeneratePass)
		self.generatePinButton.connect("clicked", self.onGeneratePin)
		self.showPassButton.connect("clicked", self.onShowPass)
		self.showPinButton.connect("clicked", self.onShowPin)

	def setPassword(self, password):
		self.passEntry.set_text(password)

	def setPin(self, pin):
		self.pinEntry.set_text(pin)

	def onShowPass(self, widget):
		flag = self.passEntry.get_visibility()
		self.passEntry.set_visibility(not flag)

	def onGeneratePass(self, widget):
		self.passWindow.showWindow(self)

	def onGeneratePin(self, widget):
		self.pinWindow.showWindow(self)

	def onShowPin(self, widget):
		flag = self.pinEntry.get_visibility()
		self.pinEntry.set_visibility(not flag)

	def onClose(self, widget, *args):
		self.nameEntry.set_text("")
		self.userEntry.set_text("")
		self.passEntry.set_text("")
		self.pinEntry.set_text("")
		self.cbuEntry.set_text("")
		self.aliasEntry.set_text("")
		self.detailEntry.get_buffer().set_text("")
		self.passEntry.set_visibility(False)
		self.pinEntry.set_visibility(False)
		self.hideWindow()
		return True

	def onCancel(self, widget):
		self.nameEntry.set_text("")
		self.userEntry.set_text("")
		self.passEntry.set_text("")
		self.pinEntry.set_text("")
		self.cbuEntry.set_text("")
		self.aliasEntry.set_text("")
		self.detailEntry.get_buffer().set_text("")
		self.passEntry.set_visibility(False)
		self.pinEntry.set_visibility(False)
		self.hideWindow()

	def onAccept(self, widget):
		name = self.nameEntry.get_text()
		user = self.userEntry.get_text()
		password = self.passEntry.get_text()
		pin = self.pinEntry.get_text()
		cbu = self.cbuEntry.get_text()
		alias = self.aliasEntry.get_text()
		detailBuffer = self.detailEntry.get_buffer()
		start, end = detailBuffer.get_bounds()
		detail = detailBuffer.get_text(start, end, True)

		if self.validateFields(name):
			dbManager = DBManager()
			dbManager.connect()
			id_bank = dbManager.saveBankAccount(name, detail, user, password, pin, cbu, alias)
			dbManager.close()
			UIUtils.showInfoMessage(self.window, "Bank account saved", \
				"Bank account succesfully saved")
			self.nameEntry.set_text("")
			self.userEntry.set_text("")
			self.passEntry.set_text("")
			self.pinEntry.set_text("")
			self.cbuEntry.set_text("")
			self.aliasEntry.set_text("")
			self.detailEntry.get_buffer().set_text("")
			self.passEntry.set_visibility(False)
			self.pinEntry.set_visibility(False)
			self.hideWindow()
			bankAccount = [id_bank, name, detail, user, password, pin, cbu, alias]
			self.parent.addToList(bankAccount)

	def validateFields(self, name):
		if not name:
			UIUtils.showErrorMessage(self.window, "Error", \
				"Bank name is a required field")
			return False
		return True


class BankAccountsEditWindow(StandardWindow):
	def __init__(self, builder, parent, passWindow, pinWindow):
		self.passWindow = passWindow
		self.pinWindow = pinWindow
		
		window = builder.get_object("window_bank_edit")
		super().__init__(window, parent)

		self.nameEntry = builder.get_object("txt_bank_edit_name")
		self.userEntry = builder.get_object("txt_bank_edit_user")
		self.passEntry = builder.get_object("txt_bank_edit_pass")
		self.pinEntry = builder.get_object("txt_bank_edit_pin")
		self.cbuEntry = builder.get_object("txt_bank_edit_cbu")
		self.aliasEntry = builder.get_object("txt_bank_edit_alias")
		self.detailEntry = builder.get_object("txt_bank_edit_detail")
		self.generatePassButton = builder.get_object("btn_bank_edit_generate_pass")
		self.generatePinButton = builder.get_object("btn_bank_edit_generate_pin")
		self.showPassButton = builder.get_object("btn_bank_edit_show_pass")
		self.showPinButton = builder.get_object("btn_bank_edit_show_pin")
		self.okButton = builder.get_object("btn_bank_edit_ok")
		self.cancelButton = builder.get_object("btn_bank_edit_cancel")

		self.window.connect("delete-event", self.onClose)
		self.okButton.connect("clicked", self.onAccept)
		self.cancelButton.connect("clicked", self.onCancel)
		self.generatePassButton.connect("clicked", self.onGeneratePass)
		self.generatePinButton.connect("clicked", self.onGeneratePin)
		self.showPassButton.connect("clicked", self.onShowPass)
		self.showPinButton.connect("clicked", self.onShowPin)

	def onShowPass(self, widget):
		flag = self.passEntry.get_visibility()
		self.passEntry.set_visibility(not flag)

	def onShowPin(self, widget):
		flag = self.pinEntry.get_visibility()
		self.pinEntry.set_visibility(not flag)

	def onGeneratePass(self, widget):
		self.passWindow.showWindow(self)

	def onGeneratePin(self, widget):
		self.pinWindow.showWindow(self)

	def setPassword(self, password):
		self.passEntry.set_text(password)

	def setPin(self, pin):
		self.pinEntry.set_text(pin)

	def showWindow(self, model, treeiter):
		self.model = model
		self.treeiter = treeiter
		self.nameEntry.set_text(model[treeiter][1])
		self.userEntry.set_text(model[treeiter][3])
		self.passEntry.set_text(model[treeiter][4])
		self.pinEntry.set_text(model[treeiter][5])
		self.cbuEntry.set_text(model[treeiter][6])
		self.aliasEntry.set_text(model[treeiter][7])
		self.detailEntry.get_buffer().set_text(model[treeiter][2])
		super().showWindow()

	def onClose(self, widget, *args):
		self.nameEntry.set_text("")
		self.userEntry.set_text("")
		self.passEntry.set_text("")
		self.pinEntry.set_text("")
		self.cbuEntry.set_text("")
		self.aliasEntry.set_text("")
		self.detailEntry.get_buffer().set_text("")
		self.passEntry.set_visibility(False)
		self.pinEntry.set_visibility(False)
		self.hideWindow()
		return True

	def onCancel(self, widget):
		self.nameEntry.set_text("")
		self.userEntry.set_text("")
		self.passEntry.set_text("")
		self.pinEntry.set_text("")
		self.cbuEntry.set_text("")
		self.aliasEntry.set_text("")
		self.detailEntry.get_buffer().set_text("")
		self.passEntry.set_visibility(False)
		self.pinEntry.set_visibility(False)
		self.hideWindow()

	def onAccept(self, widget):
		name = self.nameEntry.get_text()
		user = self.userEntry.get_text()
		password = self.passEntry.get_text()
		pin = self.pinEntry.get_text()
		cbu = self.cbuEntry.get_text()
		alias = self.aliasEntry.get_text()
		detailBuffer = self.detailEntry.get_buffer()
		start, end = detailBuffer.get_bounds()
		detail = detailBuffer.get_text(start, end, True)

		if self.validateFields(name):
			id_bank = self.model[self.treeiter][0]
			dbManager = DBManager()
			dbManager.connect()
			dbManager.updateBankAccount(id_bank, name, detail, user, password, pin, cbu, alias)
			dbManager.close()
			UIUtils.showInfoMessage(self.window, "Bank account saved", \
				"Bank account succesfully saved")
			self.nameEntry.set_text("")
			self.userEntry.set_text("")
			self.passEntry.set_text("")
			self.pinEntry.set_text("")
			self.cbuEntry.set_text("")
			self.aliasEntry.set_text("")
			self.detailEntry.get_buffer().set_text("")
			self.passEntry.set_visibility(False)
			self.pinEntry.set_visibility(False)
			self.hideWindow()
			self.parent.updateList()

	def validateFields(self, name):
		if not name:
			UIUtils.showErrorMessage(self.window, "Error", \
				"Bank name is a required field")
			return False
		return True


class BankCardsListWindow(ListWindow):
	def __init__(self, builder, parent):
		window = builder.get_object("window_bank_card_list")
		searchEntry = builder.get_object("txt_bank_card_list_search")
		tree = builder.get_object("tree_bank_card_list")
		liststore = builder.get_object("list_bank_card")
		super().__init__(window, parent, tree, liststore, searchEntry)

		self.addButton = builder.get_object("btn_bank_card_list_add")
		self.editButton = builder.get_object("btn_bank_card_list_edit")
		self.deleteButton = builder.get_object("btn_bank_card_list_delete")
		self.clipboardButton = builder.get_object("btn_bank_card_list_clipboard")

		self.setFilterAndSortedModel()

		self.window.connect("delete-event", self.onClose)
		self.searchEntry.connect("changed", self.onSearch)
		self.addButton.connect("clicked", self.onAdd)
		self.editButton.connect("clicked", self.onEdit)
		self.deleteButton.connect("clicked", self.onDelete)
		self.clipboardButton.connect("clicked", self.onClipboard)

		self.addWindow = BankCardsAddWindow(builder, self)
		self.editWindow = BankCardsEditWindow(builder, self)

		columns = ["ID", "Entity", "Type", "Description", "Number", "Security code"]
		invisible = ["Number", "Security code"]
		self.initializeTree(columns, invisible)

	def onClipboard(self, widget):
		super().onClipboard(5)

	def showWindow(self, id_bank):
		self.id_bank = id_bank
		self.fillList()
		super().showWindow()

	def fillList(self):
		dbManager = DBManager()
		dbManager.connect()
		bankCards = dbManager.getAllBankCards(self.id_bank)
		dbManager.close()
		super().fillList(bankCards)

	def updateList(self):
		self.liststore.clear()
		self.fillList()

	def onAdd(self, widget):
		self.addWindow.showWindow(self.id_bank)

	def onEdit(self, widget):
		select = self.tree.get_selection()
		model, treeiter = select.get_selected()
		if treeiter is not None:
			self.editWindow.showWindow(model, treeiter)

	def onDelete(self, widget):
		select = self.tree.get_selection()
		model, treeiter = select.get_selected()
		if treeiter is not None:
			result = UIUtils.showDesitionMessage(self.window, "Delete bank card", \
				"Are you sure about deleting this bank card?")
			if result == Gtk.ResponseType.YES:
				id_card = model[treeiter][0]
				dbManager = DBManager()
				dbManager.connect()
				dbManager.deleteBankCard(id_card)
				dbManager.close()
				self.updateList()


class BankCardsAddWindow(StandardWindow):
	def __init__(self, builder, parent):
		window = builder.get_object("window_bank_card_add")
		super().__init__(window, parent)
		
		self.entityCombo = builder.get_object("cmb_bank_card_add_entity")
		self.typeCombo = builder.get_object("cmb_bank_card_add_type")
		self.numberEntryOne = builder.get_object("txt_bank_card_add_number_one")
		self.numberEntryTwo = builder.get_object("txt_bank_card_add_number_two")
		self.numberEntryThree = builder.get_object("txt_bank_card_add_number_three")
		self.numberEntryFour = builder.get_object("txt_bank_card_add_number_four")
		self.codeEntry = builder.get_object("txt_bank_card_add_code")
		self.detailEntry = builder.get_object("txt_bank_card_add_detail")
		self.okButton = builder.get_object("btn_bank_card_add_ok")
		self.cancelButton = builder.get_object("btn_bank_card_add_cancel")
		self.showCodeButton = builder.get_object("btn_bank_card_add_show")

		self.window.connect("delete-event", self.onClose)
		self.okButton.connect("clicked", self.onAccept)
		self.cancelButton.connect("clicked", self.onCancel)
		self.showCodeButton.connect("clicked", self.onShow)
		self.numberEntryOne.connect("changed", self.onNextEntry)
		self.numberEntryTwo.connect("changed", self.onNextEntry)
		self.numberEntryThree.connect("changed", self.onNextEntry)
		self.numberEntryFour.connect("changed", self.onNextEntry)

	def onNextEntry(self, widget):
		length = len(widget.get_text())
		if length == 4:
			if widget is self.numberEntryOne:
				self.numberEntryTwo.grab_focus()
			elif widget is self.numberEntryTwo:
				self.numberEntryThree.grab_focus()
			else:
				self.numberEntryFour.grab_focus()
		
	def showWindow(self, id_bank):
		self.id_bank = id_bank
		super().showWindow()

	def onShow(self, widget):
		flag = self.codeEntry.get_visibility()
		self.codeEntry.set_visibility(not flag)

	def onClose(self, widget, *args):
		self.entityCombo.set_active(0)
		self.typeCombo.set_active(1)
		self.numberEntryOne.set_text("")
		self.numberEntryTwo.set_text("")
		self.numberEntryThree.set_text("")
		self.numberEntryFour.set_text("")
		self.codeEntry.set_text("")
		self.detailEntry.get_buffer().set_text("")
		self.hideWindow()
		return True

	def onCancel(self, widget):
		self.entityCombo.set_active(0)
		self.typeCombo.set_active(1)
		self.numberEntryOne.set_text("")
		self.numberEntryTwo.set_text("")
		self.numberEntryThree.set_text("")
		self.numberEntryFour.set_text("")
		self.codeEntry.set_text("")
		self.detailEntry.get_buffer().set_text("")
		self.hideWindow()

	def onAccept(self, widget):
		entity = self.entityCombo.get_active_id()
		cardType = self.typeCombo.get_active_id()
		number = self.numberEntryOne.get_text() + \
			self.numberEntryTwo.get_text() + \
			self.numberEntryThree.get_text() + \
			self.numberEntryFour.get_text()
		code = self.codeEntry.get_text()
		detailBuffer = self.detailEntry.get_buffer()
		start, end = detailBuffer.get_bounds()
		detail = detailBuffer.get_text(start, end, True)

		if self.validateFields(number, code):
			dbManager = DBManager()
			dbManager.connect()
			id_card = dbManager.saveBankCard(entity, cardType, number, code, detail, self.id_bank)
			dbManager.close()
			UIUtils.showInfoMessage(self.window, "Bank card saved", \
				"Bank card succesfully saved")
			self.entityCombo.set_active(0)
			self.typeCombo.set_active(1)
			self.numberEntryOne.set_text("")
			self.numberEntryTwo.set_text("")
			self.numberEntryThree.set_text("")
			self.numberEntryFour.set_text("")
			self.codeEntry.set_text("")
			self.detailEntry.get_buffer().set_text("")
			self.hideWindow()
			card = [id_card, entity, cardType, detail, number, code]
			self.parent.addToList(card)

	def validateFields(self, number, code):
		if not number or not code:
			UIUtils.showErrorMessage(self.window, "Error", \
				"The fields marked with * are required")
			return False
		if len(number) < 16:
			UIUtils.showErrorMessage(self.window, "Error", \
				"Bank card's number is incomplete")
			return False
		if len(code) < 3:
			UIUtils.showErrorMessage(self.window, "Error", \
				"Security Code is incomplete")
			return False
		return True


class BankCardsEditWindow(StandardWindow):
	def __init__(self, builder, parent):
		window = builder.get_object("window_bank_card_edit")
		super().__init__(window, parent)

		self.entityCombo = builder.get_object("cmb_bank_card_edit_entity")
		self.typeCombo = builder.get_object("cmb_bank_card_edit_type")
		self.numberEntryOne = builder.get_object("txt_bank_card_edit_number_one")
		self.numberEntryTwo = builder.get_object("txt_bank_card_edit_number_two")
		self.numberEntryThree = builder.get_object("txt_bank_card_edit_number_three")
		self.numberEntryFour = builder.get_object("txt_bank_card_edit_number_four")
		self.codeEntry = builder.get_object("txt_bank_card_edit_code")
		self.detailEntry = builder.get_object("txt_bank_card_edit_detail")
		self.okButton = builder.get_object("btn_bank_card_edit_ok")
		self.cancelButton = builder.get_object("btn_bank_card_edit_cancel")
		self.showCodeButton = builder.get_object("btn_bank_card_edit_show")

		self.window.connect("delete-event", self.onClose)
		self.okButton.connect("clicked", self.onAccept)
		self.cancelButton.connect("clicked", self.onCancel)
		self.showCodeButton.connect("clicked", self.onShow)
		self.numberEntryOne.connect("changed", self.onNextEntry)
		self.numberEntryTwo.connect("changed", self.onNextEntry)
		self.numberEntryThree.connect("changed", self.onNextEntry)
		self.numberEntryFour.connect("changed", self.onNextEntry)

	def onNextEntry(self, widget):
		length = len(widget.get_text())
		if length == 4:
			if widget is self.numberEntryOne:
				self.numberEntryTwo.grab_focus()
			elif widget is self.numberEntryTwo:
				self.numberEntryThree.grab_focus()
			else:
				self.numberEntryFour.grab_focus()
		
	def showWindow(self, model, treeiter):
		self.model = model
		self.treeiter = treeiter
		self.entityCombo.set_active_id(model[treeiter][1])
		self.typeCombo.set_active_id(model[treeiter][2])
		self.detailEntry.get_buffer().set_text(model[treeiter][3])
		self.numberEntryOne.set_text(model[treeiter][4][:4])
		self.numberEntryTwo.set_text(model[treeiter][4][4:8])
		self.numberEntryThree.set_text(model[treeiter][4][8:12])
		self.numberEntryFour.set_text(model[treeiter][4][12:16])
		self.codeEntry.set_text(model[treeiter][5])
		super().showWindow()

	def onShow(self, widget):
		flag = self.codeEntry.get_visibility()
		self.codeEntry.set_visibility(not flag)

	def onClose(self, widget, *args):
		self.entityCombo.set_active(0)
		self.typeCombo.set_active(1)
		self.numberEntryOne.set_text("")
		self.numberEntryTwo.set_text("")
		self.numberEntryThree.set_text("")
		self.numberEntryFour.set_text("")
		self.codeEntry.set_text("")
		self.detailEntry.get_buffer().set_text("")
		self.hideWindow()
		return True

	def onCancel(self, widget):
		self.entityCombo.set_active(0)
		self.typeCombo.set_active(1)
		self.numberEntryOne.set_text("")
		self.numberEntryTwo.set_text("")
		self.numberEntryThree.set_text("")
		self.numberEntryFour.set_text("")
		self.codeEntry.set_text("")
		self.detailEntry.get_buffer().set_text("")
		self.hideWindow()

	def onAccept(self, widget):
		entity = self.entityCombo.get_active_id()
		cardType = self.typeCombo.get_active_id()
		number = self.numberEntryOne.get_text() + \
			self.numberEntryTwo.get_text() + \
			self.numberEntryThree.get_text() + \
			self.numberEntryFour.get_text()
		code = self.codeEntry.get_text()
		detailBuffer = self.detailEntry.get_buffer()
		start, end = detailBuffer.get_bounds()
		detail = detailBuffer.get_text(start, end, True)

		if self.validateFields(number, code):
			id_card = self.model[self.treeiter][0]
			dbManager = DBManager()
			dbManager.connect()
			dbManager.updateBankCard(id_card, entity, cardType, number, code, detail)
			dbManager.close()
			UIUtils.showInfoMessage(self.window, "Bank card saved", \
				"Bank card succesfully saved")
			self.entityCombo.set_active(0)
			self.typeCombo.set_active(1)
			self.numberEntryOne.set_text("")
			self.numberEntryTwo.set_text("")
			self.numberEntryThree.set_text("")
			self.numberEntryFour.set_text("")
			self.codeEntry.set_text("")
			self.detailEntry.get_buffer().set_text("")
			self.hideWindow()
			self.parent.updateList()

	def validateFields(self, number, code):
		if not number or not code:
			UIUtils.showErrorMessage(self.window, "Error", \
				"The fields marked with * are required")
			return False
		if len(number) < 16:
			UIUtils.showErrorMessage(self.window, "Error", \
				"Bank card's number is incomplete")
			return False
		if len(code) < 3:
			UIUtils.showErrorMessage(self.window, "Error", \
				"Security Code is incomplete")
			return False
		return True


class BookListWindow(ListWindow):
	def __init__(self, builder, parent):
		window = builder.get_object("window_book_list")
		searchEntry = builder.get_object("txt_book_list_search")
		tree = builder.get_object("tree_book_list")
		liststore = builder.get_object("list_book")
		super().__init__(window, parent, tree, liststore, searchEntry)

		self.addButton = builder.get_object("btn_book_list_add")
		self.editButton = builder.get_object("btn_book_list_edit")
		self.deleteButton = builder.get_object("btn_book_list_delete")
		self.contactsButton = builder.get_object("btn_book_list_contacts")

		self.setFilterAndSortedModel()

		self.window.connect("delete-event", self.onClose)
		self.addButton.connect("clicked", self.onAdd)
		self.editButton.connect("clicked", self.onEdit)
		self.deleteButton.connect("clicked", self.onDelete)
		self.searchEntry.connect("changed", self.onSearch)
		self.contactsButton.connect("clicked", self.onShowContacts)


		self.addWindow = BookAddWindow(builder, self)
		self.editWindow = BookEditWindow(builder, self)
		self.contactsListWindow = ContactsListWindow(builder, self)

		columns = ["ID", "Title", "Detail"]
		self.initializeTree(columns, None)

	def onShowContacts(self, widget):
		select = self.tree.get_selection()
		model, treeiter = select.get_selected()
		if treeiter is not None:
			id_book = model[treeiter][0]
			self.contactsListWindow.showWindow(id_book)

	def showWindow(self):
		self.fillList()
		super().showWindow()

	def fillList(self):
		dbManager = DBManager()
		dbManager.connect()
		books = dbManager.getAllBooks()
		dbManager.close()
		super().fillList(books)

	def updateList(self):
		self.liststore.clear()
		self.fillList()

	def onAdd(self, widget):
		self.addWindow.showWindow()

	def onEdit(self, widget):
		select = self.tree.get_selection()
		model, treeiter = select.get_selected()
		if treeiter is not None:
			self.editWindow.showWindow(model, treeiter)

	def onDelete(self, widget):
		select = self.tree.get_selection()
		model, treeiter = select.get_selected()
		if treeiter is not None:
			result = UIUtils.showDesitionMessage(self.window, "Delete Contact Book", \
				"Are you sure about deleting this Contact Book?")
			if result == Gtk.ResponseType.YES:
				id_book = model[treeiter][0]
				dbManager = DBManager()
				dbManager.connect()
				dbManager.deleteBook(id_book)
				dbManager.close()
				self.updateList()


class BookAddWindow(StandardWindow):
	def __init__(self, builder, parent):
		window = builder.get_object("window_book_add")
		super().__init__(window, parent)
		
		self.titleEntry = builder.get_object("txt_book_add_title")
		self.detailEntry = builder.get_object("txt_book_add_detail")
		self.okButton = builder.get_object("btn_book_add_ok")
		self.cancelButton = builder.get_object("btn_book_add_cancel")

		self.window.connect("delete-event", self.onClose)
		self.okButton.connect("clicked", self.onAccept)
		self.cancelButton.connect("clicked", self.onCancel)

	def onClose(self, widget, *args):
		self.titleEntry.set_text("")
		self.detailEntry.get_buffer().set_text("")
		self.hideWindow()
		return True

	def onCancel(self, widget):
		self.titleEntry.set_text("")
		self.detailEntry.get_buffer().set_text("")
		self.hideWindow()

	def onAccept(self, widget):
		title = self.titleEntry.get_text()
		detailBuffer = self.detailEntry.get_buffer()
		start, end = detailBuffer.get_bounds()
		detail = detailBuffer.get_text(start, end, True)
		if self.validateFields(title):
			dbManager = DBManager()
			dbManager.connect()
			id_book = dbManager.saveBook(title, detail)
			dbManager.close()
			UIUtils.showInfoMessage(self.window, "Contact Book saved", \
				"Contact Book succesfully saved")
			self.titleEntry.set_text("")
			self.detailEntry.get_buffer().set_text("")
			self.hideWindow()
			book = [id_book, title, detail]
			self.parent.addToList(book)

	def validateFields(self, title):
		if not title:
			UIUtils.showErrorMessage(self.window, "Error", \
				"Contact Book's title is a required field")
			return False
		return True


class ContactsListWindow(ListWindow):
	def __init__(self, builder, parent):
		window = builder.get_object("window_contacts_list")
		searchEntry = builder.get_object("txt_contacts_list_search")
		tree = builder.get_object("tree_contacts_list")
		liststore = builder.get_object("list_contacts")
		super().__init__(window, parent, tree, liststore, searchEntry)

		self.addButton = builder.get_object("btn_contacts_list_add")
		self.editButton = builder.get_object("btn_contacts_list_edit")
		self.deleteButton = builder.get_object("btn_contacts_list_delete")

		self.window.connect("delete-event", self.onClose)
		self.searchEntry.connect("changed", self.onSearch)
		self.addButton.connect("clicked", self.onAdd)
		self.editButton.connect("clicked", self.onEdit)
		self.deleteButton.connect("clicked", self.onDelete)

		self.addWindow = ContactsAddWindow(builder, self)
		self.editWindow = ContactsEditWindow(builder, self)

		columns = ["ID", "Name", "Address", "Email", "Phone 1", "Phone 2", \
			"Website", "Detail"]
		self.initializeTree(columns, None)

	def showWindow(self, id_book):
		self.id_book = id_book
		self.fillList()
		super().showWindow()

	def fillList(self):
		dbManager = DBManager()
		dbManager.connect()
		bookContacts = dbManager.getAllContacts(self.id_book)
		dbManager.close()
		super().fillList(bookContacts)

	def updateList(self):
		self.liststore.clear()
		self.fillList()

	def onAdd(self, widget):
		self.addWindow.showWindow(self.id_book)

	def onEdit(self, widget):
		select = self.tree.get_selection()
		model, treeiter = select.get_selected()
		if treeiter is not None:
			self.editWindow.showWindow(model, treeiter)

	def onDelete(self, widget):
		select = self.tree.get_selection()
		model, treeiter = select.get_selected()
		if treeiter is not None:
			result = UIUtils.showDesitionMessage(self.window, "Contact deleted", \
				"Are you sure about deleting this contact?")
			if result == Gtk.ResponseType.YES:
				id_contact = model[treeiter][0]
				dbManager = DBManager()
				dbManager.connect()
				dbManager.deleteContact(id_contact)
				dbManager.close()
				self.updateList()	


class ContactsAddWindow(StandardWindow):
	def __init__(self, builder, parent):
		window = builder.get_object("window_contacts_add")
		super().__init__(window, parent)

		self.nameEntry = builder.get_object("txt_contacts_add_name")
		self.addressEntry = builder.get_object("txt_contacts_add_address")
		self.emailEntry = builder.get_object("txt_contacts_add_email")
		self.phoneOneEntry = builder.get_object("txt_contacts_add_phone_one")
		self.phoneTwoEntry = builder.get_object("txt_contacts_add_phone_two")
		self.webPageEntry = builder.get_object("txt_contacts_add_webpage")
		self.detailEntry = builder.get_object("txt_contacts_add_detail")
		self.okButton = builder.get_object("btn_contacts_add_ok")
		self.cancelButton = builder.get_object("btn_contacts_add_cancel")		

		self.window.connect("delete-event", self.onClose)
		self.okButton.connect("clicked", self.onAccept)
		self.cancelButton.connect("clicked", self.onCancel)
			
	def showWindow(self, id_book):
		self.id_book = id_book
		super().showWindow()

	def onClose(self, widget, *args):
		self.nameEntry.set_text("")
		self.addressEntry.set_text("")
		self.emailEntry.set_text("")
		self.phoneOneEntry.set_text("")
		self.phoneTwoEntry.set_text("")
		self.webPageEntry.set_text("")
		self.detailEntry.get_buffer().set_text("")		
		self.hideWindow()
		return True

	def onCancel(self, widget):
		self.nameEntry.set_text("")
		self.addressEntry.set_text("")
		self.emailEntry.set_text("")
		self.phoneOneEntry.set_text("")
		self.phoneTwoEntry.set_text("")
		self.webPageEntry.set_text("")
		self.detailEntry.get_buffer().set_text("")	
		self.hideWindow()

	def onAccept(self, widget):
		name = self.nameEntry.get_text()
		address = self.addressEntry.get_text()		
		email = self.emailEntry.get_text()
		phoneOne = self.phoneOneEntry.get_text()
		phoneTwo = self.phoneTwoEntry.get_text()
		webPage = self.webPageEntry.get_text()
		detailBuffer = self.detailEntry.get_buffer()
		start, end = detailBuffer.get_bounds()
		detail = detailBuffer.get_text(start, end, True)	

		if self.validateFields(name, address,email,phoneOne):
			dbManager = DBManager()
			dbManager.connect()
			id_contact = dbManager.saveContact(name, address, email, phoneOne, phoneTwo, webPage, detail, self.id_book)
			dbManager.close()
			UIUtils.showInfoMessage(self.window, "Contact saved", \
				"Contact succesfully saved")
			self.nameEntry.set_text("")
			self.addressEntry.set_text("")
			self.emailEntry.set_text("")
			self.phoneOneEntry.set_text("")
			self.phoneTwoEntry.set_text("")
			self.webPageEntry.set_text("")
			self.detailEntry.get_buffer().set_text("")
			self.hideWindow()
			contact = [id_contact, name, address, email, phoneOne, phoneTwo, webPage, detail]
			self.parent.addToList(contact)

	def validateFields(self, name, address,email,phoneOne):
		if not name or not address or not email or not phoneOne:
			UIUtils.showErrorMessage(self.window, "Error", "All fields required")
			return False
		return True


class ContactsEditWindow(StandardWindow):
	def __init__(self, builder, parent):
		window = builder.get_object("window_contacts_edit")
		super().__init__(window, parent)

		self.nameEntry = builder.get_object("txt_contacts_edit_name")
		self.addressEntry = builder.get_object("txt_contacts_edit_address")
		self.emailEntry = builder.get_object("txt_contacts_edit_email")
		self.phoneOneEntry = builder.get_object("txt_contacts_edit_phone_one")
		self.phoneTwoEntry = builder.get_object("txt_contacts_edit_phone_two")
		self.webPageEntry = builder.get_object("txt_contacts_edit_webpage")
		self.detailEntry = builder.get_object("txt_contacts_edit_detail")
		self.okButton = builder.get_object("btn_contacts_edit_ok")
		self.cancelButton = builder.get_object("btn_contacts_edit_cancel")		

		self.window.connect("delete-event", self.onClose)
		self.okButton.connect("clicked", self.onAccept)
		self.cancelButton.connect("clicked", self.onCancel)
			
	def showWindow(self, model, treeiter):
		self.model = model
		self.treeiter = treeiter
		self.nameEntry.set_text(model[treeiter][1])
		self.addressEntry.set_text(model[treeiter][2])
		self.emailEntry.set_text(model[treeiter][3])
		self.phoneOneEntry.set_text(model[treeiter][4])
		self.phoneTwoEntry.set_text(model[treeiter][5])
		self.webPageEntry.set_text(model[treeiter][6])
		self.detailEntry.get_buffer().set_text(model[treeiter][7])
		super().showWindow()

	def onClose(self, widget, *args):
		self.nameEntry.set_text("")
		self.addressEntry.set_text("")
		self.emailEntry.set_text("")
		self.phoneOneEntry.set_text("")
		self.phoneTwoEntry.set_text("")
		self.webPageEntry.set_text("")
		self.detailEntry.get_buffer().set_text("")	
		self.hideWindow()
		return True

	def onCancel(self, widget):
		self.nameEntry.set_text("")
		self.addressEntry.set_text("")
		self.emailEntry.set_text("")
		self.phoneOneEntry.set_text("")
		self.phoneTwoEntry.set_text("")
		self.webPageEntry.set_text("")
		self.detailEntry.get_buffer().set_text("")	
		self.hideWindow()

	def onAccept(self, widget):
		name = self.nameEntry.get_text()
		address = self.addressEntry.get_text()		
		email = self.emailEntry.get_text()
		phoneOne = self.phoneOneEntry.get_text()
		phoneTwo = self.phoneTwoEntry.get_text()
		webPage = self.webPageEntry.get_text()
		detailBuffer = self.detailEntry.get_buffer()
		start, end = detailBuffer.get_bounds()
		detail = detailBuffer.get_text(start, end, True)	

		if self.validateFields(name, address, email, phoneOne):
			id_contact = self.model[self.treeiter][0]
			dbManager = DBManager()
			dbManager.connect()
			dbManager.updateContact(id_contact, name, address, email, phoneOne, phoneTwo, webPage, detail)
			dbManager.close()
			UIUtils.showInfoMessage(self.window, "Contact updated", \
				"Contact succesfully updated")
			self.nameEntry.set_text("")
			self.addressEntry.set_text("")
			self.emailEntry.set_text("")
			self.phoneOneEntry.set_text("")
			self.phoneTwoEntry.set_text("")
			self.webPageEntry.set_text("")
			self.detailEntry.get_buffer().set_text("")
			self.hideWindow()
			self.parent.updateList()

	def validateFields(self, name, address, email, phoneOne):
		if not name or not address or not email or not phoneOne:
			UIUtils.showErrorMessage(self.window, "Error", "All fields required")
			return False

		return True


class BookEditWindow(StandardWindow):
	def __init__(self, builder, parent):
		window = builder.get_object("window_book_edit")
		super().__init__(window, parent)

		self.titleEntry = builder.get_object("txt_book_edit_title")
		self.detailEntry = builder.get_object("txt_book_edit_detail")
		self.okButton = builder.get_object("btn_book_edit_ok")
		self.cancelButton = builder.get_object("btn_book_edit_cancel")

		self.window.connect("delete-event", self.onClose)
		self.okButton.connect("clicked", self.onAccept)
		self.cancelButton.connect("clicked", self.onCancel)

	def showWindow(self, model, treeiter):
		self.model = model
		self.treeiter = treeiter
		self.titleEntry.set_text(model[treeiter][1])
		self.detailEntry.get_buffer().set_text(model[treeiter][2])
		super().showWindow()

	def onClose(self, widget, *args):
		self.titleEntry.set_text("")
		self.detailEntry.get_buffer().set_text("")
		self.hideWindow()
		return True

	def onCancel(self, widget):
		self.titleEntry.set_text("")
		self.detailEntry.get_buffer().set_text("")
		self.hideWindow()

	def onAccept(self, widget):
		title = self.titleEntry.get_text()
		detailBuffer = self.detailEntry.get_buffer()
		start, end = detailBuffer.get_bounds()
		detail = detailBuffer.get_text(start, end, True)
		if self.validateFields(title):
			id_book = self.model[self.treeiter][0]
			dbManager = DBManager()
			dbManager.connect()
			dbManager.updateBook(id_book, title, detail)
			dbManager.close()
			UIUtils.showInfoMessage(self.window, "Contact book updated", \
				"Contact Book succesfully updated")
			self.titleEntry.set_text("")
			self.detailEntry.get_buffer().set_text("")
			self.hideWindow()
			self.parent.updateList()

	def validateFields(self, title):
		if not title:
			UIUtils.showErrorMessage(self.window, "Error", \
				"Book's title is a required field")
			return False
		return True


class LogListWindow(ListWindow):
	def __init__(self, builder, parent):
		window = builder.get_object("window_log")
		tree = builder.get_object("tree_log")
		liststore = builder.get_object("list_log")
		super().__init__(window, parent, tree, liststore, None)

		self.window.connect("delete-event", self.onClose)

		columns = ["ID", "Date", "Event"]
		self.initializeTree(columns, None)

	def showWindow(self):
		self.fillList()
		self.window.show_all()

	def fillList(self):
		dbManager = DBManager()
		dbManager.connect()
		logs = dbManager.getAllLogs()
		dbManager.close()
		super().fillList(logs)


class PassphraseWindow:
	def __init__(self, builder, parent):
		self.parent = parent
		self.window = builder.get_object("window_passphrase")
		self.okButton = builder.get_object("btn_passphrase_ok")
		self.cancelButton = builder.get_object("btn_passphrase_cancel")
		self.txtPass = builder.get_object("txt_passphrase_pass")

		self.window.connect("delete-event", self.onClose)
		self.cancelButton.connect("clicked", self.onCancel)
		self.okButton.connect("clicked", self.onAccept)

	def showWindow(self, userid, username):
		self.id_user = userid
		self.username = username
		self.window.show_all()

	def onClose(self, widget, *args):
		self.txtPass.set_text("")
		self.window.hide()
		self.parent.showWindow()
		return True

	def onCancel(self, button):
		self.txtPass.set_text("")
		self.window.hide()
		self.parent.showWindow()

	def onAccept(self, button):
		passphrase = self.txtPass.get_text()
		if not passphrase:
			UIUtils.showErrorMessage(self.window, "Error", \
				"Passphrase is a required field")
			return
		else:
			dbManager = DBManager()
			if dbManager.setUser(self.id_user, self.username, passphrase):
				self.parent.successfulLogin()
				self.txtPass.set_text("")
				self.window.hide()
			else:
				UIUtils.showErrorMessage(self.window, "Error", \
					"Wrong passphrase submitted, please retry")


class RegisterWindow:
	def __init__(self, builder, parent):
		self.parent = parent
		self.window = builder.get_object("window_register")
		self.okButton = builder.get_object("btn_register_ok")
		self.cancelButton = builder.get_object("btn_register_cancel")
		self.txtUsername = builder.get_object("txt_register_username")
		self.txtPassOne = builder.get_object("txt_register_passphrase_one")
		self.txtPassTwo = builder.get_object("txt_register_passphrase_two")
		self.imageButton = builder.get_object("btn_register_image")
		self.lblImage = builder.get_object("lbl_register_image_status")
		self.imageState = False
		self.imageEncoding = None

		self.window.connect("delete-event", self.onClose)
		self.cancelButton.connect("clicked", self.onCancel)
		self.okButton.connect("clicked", self.onAccept)
		self.imageButton.connect("clicked", self.onImage)

	def showWindow(self):
		self.window.show_all()

	def onImage(self, button):
		recognizer = FaceRecognizer()
		self.imageEncoding = recognizer.getEncoding()
		if self.imageEncoding is not None:
			self.imageState = True
			self.lblImage.set_text("Face succesfully loaded")
		else:
			self.imageState = False
			self.lblImage.set_text("No face loaded")

	def onClose(self, widget, *args):
		self.txtUsername.set_text("")
		self.txtPassOne.set_text("")
		self.txtPassTwo.set_text("")
		self.imageState = False
		self.lblImage.set_text("No face loaded")
		self.imageEncoding = None
		self.window.hide()
		self.parent.showWindow()
		return True

	def onCancel(self, button):
		self.txtUsername.set_text("")
		self.txtPassOne.set_text("")
		self.txtPassTwo.set_text("")
		self.imageState = False
		self.lblImage.set_text("No face loaded")
		self.imageEncoding = None
		self.window.hide()
		self.parent.showWindow()

	def onAccept(self, button):
		username = self.txtUsername.get_text()
		passone = self.txtPassOne.get_text()
		passtwo = self.txtPassTwo.get_text()

		if self.validateFields(username, passone, passtwo, self.imageState, self.window):
			dbManager = DBManager()
			dbManager.connect()
			dbManager.registerUser(username, passone, self.imageEncoding)
			UIUtils.showInfoMessage(self.window, "User registered", \
				"User succesfully registered")
			self.txtUsername.set_text("")
			self.txtPassOne.set_text("")
			self.txtPassTwo.set_text("")
			self.imageState = False
			self.lblImage.set_text("No face loaded")
			self.imageEncoding = None
			self.window.hide()
			self.parent.showWindow()
				
			dbManager.close()

	
	def validateFields(self, usr, pwd_one, pwd_two, state, parent):
		if not usr or not pwd_one or not pwd_two:
			UIUtils.showErrorMessage(parent, "Error", "All fields required")
			return False
		if pwd_one != pwd_two:
			UIUtils.showErrorMessage(parent, "Error", "Both passphrases do not match")
			return False
		if len(pwd_one) < 8:
			UIUtils.showErrorMessage(parent, "Error", \
				"Passphrase must have at least 8 characters")
			return False
		if not state:
			UIUtils.showErrorMessage(parent, "Error", "Face picture required")
			return False
		return True


class UIUtils(object):
	@staticmethod
	def showInfoMessage(parent, title, message):
		dialog = Gtk.MessageDialog(parent, 0, Gtk.MessageType.INFO, Gtk.ButtonsType.OK, title)
		dialog.format_secondary_text(message)
		dialog.run()
		dialog.destroy()

	@staticmethod
	def showErrorMessage(parent, title, message):
		dialog = Gtk.MessageDialog(parent, 0, Gtk.MessageType.ERROR, Gtk.ButtonsType.OK, title)
		dialog.format_secondary_text(message)
		dialog.run()
		dialog.destroy()

	@staticmethod
	def showDesitionMessage(parent, title, message):
		dialog = Gtk.MessageDialog(parent, 0, Gtk.MessageType.QUESTION, Gtk.ButtonsType.YES_NO, title)
		dialog.format_secondary_text(message)
		response = dialog.run()
		dialog.destroy()
		return response

# ======== Face Recognition ========

class FaceRecognizer:
	def getEncoding(self):
		video_capture = cv2.VideoCapture(0)
		face_locations = []
		face_encodings = []
		face_names = []
		process_this_frame = True
		cur_encoding = None

		while True:
			ret, frame = video_capture.read()
			small_frame = cv2.resize(frame, (0,0), fx=0.25, fy=0.25)
			rgb_small_frame = small_frame[:,:,::-1]

			font = cv2.FONT_HERSHEY_DUPLEX

			if process_this_frame:
				face_locations = face_recognition.face_locations(rgb_small_frame)
				face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locations)
				name = "Press \"W\""
				face_names.append(name)
				for face_encoding in face_encodings:
					cur_encoding = face_encoding

			process_this_frame = not process_this_frame

			for (top, right, bottom, left), name in zip(face_locations, face_names):
				top *= 4
				right *= 4
				bottom *= 4
				left *= 4

				cv2.rectangle(frame, (left, top), (right, bottom), (0, 0, 255), 2)
				cv2.rectangle(frame, (left, bottom - 35), (right, bottom), (0, 0, 255), cv2.FILLED)
				cv2.putText(frame, name, (left + 6, bottom - 6), font, 1.0, (255, 255, 255), 1)

			cv2.putText(frame, "Press \"q\" to quit", (10,30), font, 0.8, (0,255,0), 1)
			cv2.imshow('Face capture', frame)
			if cv2.waitKey(33) == ord('q'):
			    break
			elif cv2.waitKey(33) == ord('w'):
				video_capture.release()
				cv2.destroyAllWindows()
				return cur_encoding

		video_capture.release()
		cv2.destroyAllWindows()
		return None

	def recognizeUser(self):
		video_capture = cv2.VideoCapture(0)

		dbManager = DBManager()
		dbManager.connect()
		known_ids, known_face_names, known_face_encodings = dbManager.getKnownUsers()
		dbManager.close()

		face_locations = []
		face_encodings = []
		face_names = []
		process_this_frame = True

		while True:
			ret, frame = video_capture.read()
			small_frame = cv2.resize(frame, (0,0), fx=0.25, fy=0.25)
			rgb_small_frame = small_frame[:,:,::-1]

			font = cv2.FONT_HERSHEY_DUPLEX

			if process_this_frame:
				face_locations = face_recognition.face_locations(rgb_small_frame)
				face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locations)
				face_names = []
				for face_encoding in face_encodings:
					name = "Unknown"
					if(len(known_face_names) > 0):
						matches = face_recognition.compare_faces(known_face_encodings, face_encoding)
						face_distances = face_recognition.face_distance(known_face_encodings, face_encoding)
						best_match_index = np.argmin(face_distances)
						if matches[best_match_index]:
							name = known_face_names[best_match_index]
							id_user = known_ids[best_match_index]
							video_capture.release()
							cv2.destroyAllWindows()
							return id_user, name

					face_names.append(name)

			process_this_frame = not process_this_frame

			for (top, right, bottom, left), name in zip(face_locations, face_names):
				top *= 4
				right *= 4
				bottom *= 4
				left *= 4

				cv2.rectangle(frame, (left, top), (right, bottom), (0, 0, 255), 2)
				cv2.rectangle(frame, (left, bottom - 35), (right, bottom), (0, 0, 255), cv2.FILLED)
				cv2.putText(frame, name, (left + 6, bottom - 6), font, 1.0, (255, 255, 255), 1)

			cv2.putText(frame, "Press \"q\" to quit", (10,30), font, 0.8, (0,255,0), 1)
			cv2.imshow('Facial login', frame)
			if cv2.waitKey(1) & 0xFF == ord('q'):
			    break

		video_capture.release()
		cv2.destroyAllWindows()
		return None, None