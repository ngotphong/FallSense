# coding=utf-8
import os
import json, time
import threading
import cv2
import numpy as np
from PIL import Image
from PyQt5 import QtGui
from PyQt5.QtWidgets import QLabel, QSizePolicy
from qt_thread_updater import get_updater
from src import config as co
from src.Fall_detection import FallDetector

class Main:
    def __init__(self, MainGUI):
        self.MainGUI = MainGUI
        self.camera = None
        self.cam_availible = False
        self.start_camera = True
        self.fall_detect = FallDetector('weights/fall_detection_person.pt', 'cpu')
        
    # basically turning an opencv image into a QPixmap object for the GUI display    
    def img_cv_2_qt(self, img_cv):
        # extracts the image dimesion from the passed in opencv image
        height, width, channel = img_cv.shape
        # calculates the number of bytes per line in the image
        bytes_per_line = channel * width
        # converts the opencv image to a QImage object
        img_qt = QtGui.QImage(img_cv, width, height, bytes_per_line, QtGui.QImage.Format_RGB888).rgbSwapped()
        # converts the QImage object to a QPixmap object
        cam_availibleurn QtGui.QPixmap.fromImage(img_qt)
    
    # start the video capture device 
    def init_devices(self, url_camera):
        self.camera = cv2.VideoCapture(url_camera) 
        # check if camera/video is reading and reads the first frame from the source   
        self.cam_availible, frame = self.camera.read()
        if not self.cam_availible:
            self.start_camera = False
            self.MainGUI.MessageBox_signal.emit("Error: Camera not found", "error")
        else:
            self.start_camera = True

    # camera detection function 
    def auto_camera(self):
        url_camera = co.CAMERA_DEVICE
        self.init_devices(url_camera)
        while self.cam_availible and self.start_camera:
            try:
                cam_availible, frame = self.camera.read()
                self.cam_availible = cam_availible
                if self.cam_availible and self.start_camera:
                    img_result, is_fall = self.fall_detect.inference(frame)
                    get_updater().call_latest(self.MainGUI.label_Image.setPixmap, self.img_cv_2_qt(img_result))
                    if is_fall:
                        image_view = img_result.copy()
                        cv2.putText(image_view, 'Person Falling down', (20, 200), 0, 1, [0, 0, 255], thickness=2, lineType=cv2.LINE_AA)
                        get_updater().call_latest(self.MainGUI.label_View.setPixmap, self.img_cv_2_qt(image_view))
                        get_updater().call_latest(self.MainGUI.text_resutl.setText, "Fall")
                        get_updater().call_latest(self.MainGUI.text_resutl.setStyleSheet,"background-color: rgb(255, 0, 0);")
                    else:
                        get_updater().call_latest(self.MainGUI.text_resutl.setText, "OK")
                        get_updater().call_latest(self.MainGUI.text_resutl.setStyleSheet,"background-color: rgb(0, 255, 0);")
                else:
                    break
            except Exception as e:
                print("Bug: ", e)
        self.close_camera()
    
    # video detection function 
    def auto_video(self, path_video):
        url_camera = path_video
        self.init_devices(url_camera)
        while self.cam_availible and self.start_camera:
            try:
                cam_availible, frame = self.camera.read()
                self.cam_availible = cam_availible
                if self.cam_availible and self.start_camera:
                    img_result, is_fall = self.fall_detect.inference(frame)
                    get_updater().call_latest(self.MainGUI.label_Image.setPixmap, self.img_cv_2_qt(img_result))
                    if is_fall:
                        image_view = img_result.copy()
                        cv2.putText(image_view, 'Person Falling down', (20, 200), 0, 1, [0, 0, 255], thickness=2, lineType=cv2.LINE_AA)
                        get_updater().call_latest(self.MainGUI.label_View.setPixmap, self.img_cv_2_qt(image_view))
                        get_updater().call_latest(self.MainGUI.text_resutl.setText, "Fall")
                        get_updater().call_latest(self.MainGUI.text_resutl.setStyleSheet,"background-color: rgb(255, 0, 0);")
                    else:
                        get_updater().call_latest(self.MainGUI.text_resutl.setText, "OK")
                        get_updater().call_latest(self.MainGUI.text_resutl.setStyleSheet,"background-color: rgb(0, 255, 0);")
    
                else:
                    break
            except Exception as e:
                print("Bug: ", e)
        self.close_camera()
    
    # manual image detection function 
    def manual_image(self, path_image):
        image = cv2.imread(path_image)
        img_result, is_fall = self.fall_detect.inference(image)
        get_updater().call_latest(self.MainGUI.label_Image.setPixmap, self.img_cv_2_qt(img_result))
        if is_fall:
            image_view = img_result.copy()
            cv2.putText(image_view, 'Person Falling down', (20, 50), 0, 1, [0, 0, 255], thickness=2, lineType=cv2.LINE_AA)
            get_updater().call_latest(self.MainGUI.label_View.setPixmap, self.img_cv_2_qt(image_view))
            get_updater().call_latest(self.MainGUI.text_resutl.setText, "Fall")
            get_updater().call_latest(self.MainGUI.text_resutl.setStyleSheet,"background-color: rgb(255, 0, 0);")
        else:
            get_updater().call_latest(self.MainGUI.text_resutl.setText, "OK")
            get_updater().call_latest(self.MainGUI.text_resutl.setStyleSheet,"background-color: rgb(0, 255, 0);")
    
    # close the camera/video capture device 
    def close_camera(self):
        try:
            self.start_camera = False
            if self.cam_availible:
                self.camera.release()
            self.camera = None
            self.cam_availible = False
            
            time.sleep(1)
            self.MainGUI.label_Image.clear()
            self.MainGUI.label_View.clear()
            get_updater().call_latest(self.MainGUI.text_resutl.setText, "STOP")
            get_updater().call_latest(self.MainGUI.text_resutl.setStyleSheet,"background-color: rgb(255, 244, 0);")

        except Exception as e:
                print("Bug: ", e)
