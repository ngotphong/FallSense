import os
import cv2
import numpy as np
import sqlite3

def create_database(db_file):
    connection  = sqlite3.connect(db_file)
    cursor = connection.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users
                (id INTEGER PRIMARY KEY AUTOINCREMENT, id_save TEXT, path_input TEXT, path_save TEXT, is_fall TEXT, status TEXT, timestamp DATETIME DEFAULT (DATETIME(CURRENT_TIMESTAMP, 'localtime')))''')
    connection.commit()
    connection.close()

def insert_database(db_file, id_video, path_input, path_save, is_fall, status):
    connection  = sqlite3.connect(db_file)
    cursor = connection.cursor()
    data = "INSERT INTO users (id_save, path_input, path_save, is_fall, status) VALUES ( '{0}', '{1}', '{2}', '{3}', '{4}')".format(id_video, path_input, path_save, is_fall, status)
    cursor.execute(data)
    connection.commit()
    connection.close()

def update_database(db_file, id_video, is_fall, status ):
    connection  = sqlite3.connect(db_file)
    cursor = connection.cursor()
    cursor.execute("UPDATE users SET is_fall = ?, status = ? WHERE id_save = ?", (is_fall, status, id_video))
    connection.commit()
    connection.close()

def query_database(db_file, id_video):
    connection  = sqlite3.connect(db_file)
    cursor = connection.cursor()
    cursor.execute("SELECT * FROM users WHERE id_save = ?", (id_video,))
    result = cursor.fetchall()
    if len(result)<1:
        return False, "", "", ""
    stt, id,path_input, path_video, is_fall, status,timeline = result[0]
    return True, path_video, is_fall, status

def query_input_video_database(db_file):
    connection  = sqlite3.connect(db_file)
    cursor = connection.cursor()
    cursor.execute("SELECT id_save, path_input, path_save FROM users WHERE status = ?", ("Process",))
    results = cursor.fetchall()
    
    if len(results)<1:
        return False, [],[], []
    path_videos = []
    ids_save = []
    path_saves= []
    for res in results:
        id_save, video, path_save = res[0], res[1], res[2]
        path_videos.append(video)
        ids_save.append(id_save)
        path_saves.append(path_save)
    return True, path_videos, ids_save, path_saves