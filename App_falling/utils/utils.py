import os
import csv
import cv2
import numpy as np

def check_duplicate (csv_file, user, password, email):
    with open(csv_file, 'r') as file:
        csv_render = csv.reader(file)
        for row in csv_render:
            if row[0] == user:
                return 0
            if row[1] == password:
                return 1
            if row[2] == email:
                return 2
    return 3

def check_info (csv_file, user, password):
    with open(csv_file, 'r') as file:
        csv_render = csv.reader(file)
        for row in csv_render:
            if row[0] == user and row[1] == password:
                return True
    return False

def write_data_csv(csv_file, user, password, email):
    with open (csv_file, 'a', newline='') as file:
        csv_writer = csv.writer(file)
        csv_writer.writerow([user, password, email])
    