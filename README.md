# pyPass
Simple password manager with graphical UI made in Python

## Introduction
pyPass is a password manager inspired by Unix pass (https://www.passwordstore.org/), entirely made in Python. It was made as 
an University project and using it as a personal or professional password manager goes on total responsibility of the user. 
Any kind of feedback will be highly appreciated, feel free of using/modifying it with educational purposes if you want.

It introduces face recognition as a way to detect which user wants to login, and the requirement of a passphrase for
encryption purposes. All the submitted data is fully encrypted and stored on a sqlite3 binary file, so even when it is
possible to watch the content of the database via sqlite CLI, it is not possible to watch any meaningful data without
decrypting the content previously.

All the UI was made in Gtk3 using Glade. It was tested only on Linux but it should work on Windows/Mac with the proper library bindings installed.

## Dependencies
* Python 3.6.7 or higher (not tested on lower versions)
* Face Recognition - https://github.com/ageitgey/face_recognition
* OpenCV 4.1.0 for Python - https://opencv.org/
* PyGTK3 - https://pygobject.readthedocs.io/en/latest/
* Glade - https://glade.gnome.org/
* SQLite3 - https://sqlite.org/index.html

## Install
* Install the required dependencies
* Clone this repo
* Generate main.db database on /bin from .sql file on /doc
```
sqlite3 bin/main.db < doc/main_db.sql
```
* Run main.py script to start (you will need a webcam for face registration and recognition)
