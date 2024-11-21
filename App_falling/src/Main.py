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
        self.ret = False
        self.start_camera = True
        self.fall_detect = FallDetector('weights/fall_detection_person.pt')
        
    def img_cv_2_qt(self, img_cv):
        height, width, channel = img_cv.shape
        bytes_per_line = channel * width
        img_qt = QtGui.QImage(img_cv, width, height, bytes_per_line, QtGui.QImage.Format_RGB888).rgbSwapped()
        return QtGui.QPixmap.fromImage(img_qt)
    
    def init_devices(self, url_camera):
        self.camera = cv2.VideoCapture(url_camera) 
        self.ret, frame = self.camera.read()
        if not self.ret:
            self.start_camera = False
            self.MainGUI.MessageBox_signal.emit("Có lỗi xảy ra ! \n Không tìm thấy camera/video", "error")
        else:
            self.start_camera = True
        
    def auto_camera(self):
        url_camera = co.CAMERA_DEVICE
        self.init_devices(url_camera)
        while self.ret and self.start_camera:
            try:
                ret, frame = self.camera.read()
                self.ret = ret
                if self.ret and self.start_camera:
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
    
    def auto_video(self, path_video):
        url_camera = path_video
        self.init_devices(url_camera)
        while self.ret and self.start_camera:
            try:
                ret, frame = self.camera.read()
                self.ret = ret
                if self.ret and self.start_camera:
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
    
    def close_camera(self):
        try:
            self.start_camera = False
            if self.ret:
                self.camera.release()
            self.camera = None
            self.ret = False
            
            time.sleep(1)
            self.MainGUI.label_Image.clear()
            self.MainGUI.label_View.clear()
            get_updater().call_latest(self.MainGUI.text_resutl.setText, "STOP")
            get_updater().call_latest(self.MainGUI.text_resutl.setStyleSheet,"background-color: rgb(255, 244, 0);")

        except Exception as e:
                print("Bug: ", e)
