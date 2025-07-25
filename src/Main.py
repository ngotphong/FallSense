# coding=utf-8
import os                  # Operating system functions
import json, time          # JSON handling and time functions
import threading           # Threading for parallel execution
import cv2                 # OpenCV for image processing
import numpy as np         # Numerical operations
from PIL import Image      # Image processing
from PyQt5 import QtGui    # PyQt5 GUI components
from PyQt5.QtWidgets import QLabel, QSizePolicy  # PyQt5 widgets
from qt_thread_updater import get_updater  # Thread-safe UI updates
from src import config as co  # Import configuration
from src.Fall_detection import FallDetector  # Import fall detection class

class Main:
    def __init__(self, MainGUI):
        # Store reference to the main GUI
        self.MainGUI = MainGUI
        # Initialize camera variables
        self.camera = None
        self.cam_availible = False
        self.start_camera = True
        # Create fall detector with keypoints initially hidden
        self.fall_detect = FallDetector('weights/fall_detection_person.pt', 'cpu', show_keypoints=False)
        
    # Toggle keypoints on/off
    def toggle_keypoints(self):
        # Call the toggle method in FallDetector
        show_keypoints = self.fall_detect.toggle_keypoints()
        # Do not set any text on the keypoint toggle button
        return show_keypoints
        
    # Convert OpenCV image to QPixmap for display in Qt GUI
    def img_cv_2_qt(self, img_cv, target_label=None, maintain_aspect_ratio=True, return_padded_img=False):
        # Get image dimensions
        height, width, channel = img_cv.shape
        # Initialize scaling and padding variables
        scale = 1.0
        pad_x = 0
        pad_y = 0
        padded_img = img_cv
        new_width = width
        new_height = height
        
        # If a target label is provided, scale the image to fit it
        if target_label:
            label_size = target_label.size()
            label_w, label_h = label_size.width(), label_size.height()
            
            if maintain_aspect_ratio:
                # Calculate scaling factor to fit image in label while maintaining aspect ratio
                width_ratio = label_w / width
                height_ratio = label_h / height
                scale = min(width_ratio, height_ratio)
                new_width = int(width * scale)
                new_height = int(height * scale)
                
                # Resize image using the calculated scale
                padded_img = cv2.resize(img_cv, (new_width, new_height), interpolation=cv2.INTER_AREA)
                
                # Calculate padding to center the image in the label
                pad_x = (label_w - new_width) // 2
                pad_y = (label_h - new_height) // 2
                
                # Add padding to the image
                padded_img = cv2.copyMakeBorder(padded_img, pad_y, label_h - new_height - pad_y, 
                                               pad_x, label_w - new_width - pad_x, 
                                               cv2.BORDER_CONSTANT, value=[0,0,0])
            else:
                # Resize to fit label exactly (may distort aspect ratio)
                padded_img = cv2.resize(img_cv, (label_w, label_h), interpolation=cv2.INTER_AREA)
                new_width = label_w
                new_height = label_h
                
        # Get dimensions of the padded image
        height, width, channel = padded_img.shape
        bytes_per_line = channel * width
        
        # Convert OpenCV image to Qt image
        img_qt = QtGui.QImage(padded_img, width, height, bytes_per_line, QtGui.QImage.Format_RGB888).rgbSwapped()
        
        # Return either the padded image or the QPixmap based on the parameter
        if return_padded_img:
            return padded_img, scale, pad_x, pad_y, new_width, new_height
        return QtGui.QPixmap.fromImage(img_qt), scale, pad_x, pad_y, new_width, new_height
    
    # Initialize camera or video capture device
    def init_devices(self, url_camera):
        # Create VideoCapture object
        self.camera = cv2.VideoCapture(url_camera) 
        # Read first frame to check if camera/video is available
        self.cam_availible, frame = self.camera.read()
        if not self.cam_availible:
            # If camera not available, show error
            self.start_camera = False
            self.MainGUI.MessageBox_signal.emit("Error: Camera not found", "error")
        else:
            self.start_camera = True

    # Process and display a frame (common function for camera, video, and image)
    def process_and_display(self, frame, orig_img=None):
        # If no original image provided, use the frame
        if orig_img is None:
            orig_img = frame
            
        # Resize and pad the original image to fit the display label
        padded_img, scale, pad_x, pad_y, new_width, new_height = self.img_cv_2_qt(
            orig_img, target_label=self.MainGUI.image_display, return_padded_img=True)
            
        # Run inference on the original image and draw results on padded image
        img_result, is_fall = self.fall_detect.inference_and_draw_on_display(
            orig_img, padded_img, scale, pad_x, pad_y, new_width, new_height)
            
        # Convert result to QPixmap and display it
        pixmap, _, _, _, _, _ = self.img_cv_2_qt(img_result, target_label=self.MainGUI.image_display)
        get_updater().call_latest(self.MainGUI.image_display.setPixmap, pixmap)
        
        # If fall detected, update UI to show warning
        if is_fall:
            # Create copy of result image
            image_view = img_result.copy()
            # Add text indicating fall
            cv2.putText(image_view, 'FALLEN DETECTED', (20, 170), 0, 1, [0, 0, 155], 
                       thickness=2, lineType=cv2.LINE_AA)
            # Display in result label
            pixmap, _, _, _, _, _ = self.img_cv_2_qt(image_view, target_label=self.MainGUI.result_label)
            get_updater().call_latest(self.MainGUI.result_label.setPixmap, pixmap)
            # Update status indicators
            get_updater().call_latest(self.MainGUI.status_label.setText, "FALLEN")
            get_updater().call_latest(self.MainGUI.status_label.setStyleSheet,"background-color: rgb(255, 0, 0);")
        else:
            # If no fall, show OK status
            get_updater().call_latest(self.MainGUI.status_label.setText, "NORMAL")
            get_updater().call_latest(self.MainGUI.status_label.setStyleSheet,"background-color: rgb(0, 255, 0);")

    # Process live camera feed
    def camera_mode(self):
        # Get camera device from config
        url_camera = co.CAMERA_DEVICE
        # Initialize camera
        self.init_devices(url_camera)
        # Process frames while camera is available and not stopped
        while self.cam_availible and self.start_camera:
            try:
                # Read frame from camera
                cam_availible, frame = self.camera.read()
                self.cam_availible = cam_availible
                if self.cam_availible and self.start_camera:
                    # Process and display the frame
                    self.process_and_display(frame)
                else:
                    break
            except Exception as e:
                print("Bug: ", e)
        # Clean up when done
        self.reset_camera()

    # Process video file
    def video_mode(self, path_video):
        # Use video file path as camera source
        url_camera = path_video
        # Initialize video
        self.init_devices(url_camera)
        # Process frames while video is available and not stopped
        while self.cam_availible and self.start_camera:
            try:
                # Read frame from video
                cam_availible, frame = self.camera.read()
                self.cam_availible = cam_availible
                if self.cam_availible and self.start_camera:
                    # Process and display the frame
                    self.process_and_display(frame)
                else:
                    break
            except Exception as e:
                print("Bug: ", e)
        # Clean up when done
        self.reset_camera()
    
    # Reset camera for switching between inputs
    def reset_camera(self):
        try:
            # Set flag to stop current processing
            self.start_camera = False
            
            # Release camera resource if available
            if self.camera is not None and self.cam_availible:
                self.camera.release()
                
            # Reset camera variables
            self.camera = None
            self.cam_availible = False
            
        except Exception as e:
            print("Error in reset_camera:", e)