import os         
import json, time       
import threading        
import cv2         
import numpy as np       
from PIL import Image
from PyQt5 import QtGui  
from PyQt5.QtWidgets import QLabel, QSizePolicy, QFileDialog  
from qt_thread_updater import get_updater  
from src import config  
from src.Fall_detection import FallDetector  

class Main:
    def __init__(self, MainGUI):
        self.MainGUI = MainGUI
        self.flip_horizontal = False

        self.camera = None
        self.cam_availible = False
        self.start_camera = True

        self.fall_detect = FallDetector('weights/fall_detection_person.pt', 'cpu', show_keypoints=False)
        
        self.auto_record_on_fall = False
        self.save_folder = None
        self.recording = False
        self.video_writer = None

    def set_save_folder(self):
        folder = QFileDialog.getExistingDirectory(self.MainGUI, "Select Save Folder")
        if folder:
            self.save_folder = folder

    def start_recording(self):
        if self.recording:
            # print("[DEBUG] Already recording, not starting again.")
            return
        if not self.recording and self.cam_availible and self.save_folder:
            self.recording = True
            get_updater().call_latest(self.MainGUI.record_display.setText, "RECORDING")
            get_updater().call_latest(self.MainGUI.record_display.setStyleSheet,"background-color: rgb(255, 0, 0);")
            filename = time.strftime("recording_%Y_%m_%d_%H_%M_%S.mp4")  # <-- MP4
            save_path = os.path.join(self.save_folder, filename)
            # Get frame size (width, height)
            width = int(self.camera.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(self.camera.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = 20  # or use self.camera.get(cv2.CAP_PROP_FPS)
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')  # <-- MP4 codec
            self.video_writer = cv2.VideoWriter(save_path, fourcc, fps, (width, height))
            # print(f"[DEBUG] Started recording to {save_path}")
        else:
            self.MainGUI.MessageBox_signal.emit("Please set a save folder first or select a video source!", "error")
            return

    def stop_recording(self):
        if not self.recording:
            # print("[DEBUG] Not recording, nothing to stop.")
            return
        if self.video_writer:
            self.video_writer.release()
            self.video_writer = None
            get_updater().call_latest(self.MainGUI.record_display.setText, "STOPPED RECORDING")
            get_updater().call_latest(self.MainGUI.record_display.setStyleSheet,"background-color: rgb(0, 255, 0);")
            self.recording = False
            # print(f"[DEBUG] Stopped recording")


    # Toggle keypoints on/off
    def toggle_keypoints(self):
        # Call the toggle method in FallDetector
        show_keypoints = self.fall_detect.toggle_keypoints()
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
        self.camera = cv2.VideoCapture(url_camera) 
        self.cam_availible, frame = self.camera.read()
        if not self.cam_availible:
            self.start_camera = False
            self.MainGUI.MessageBox_signal.emit("Error: Camera not found", "error")
        else:
            self.start_camera = True

    # Process and display a frame (common function for camera, video, and image)
    def process_and_display(self, frame, orig_img=None):
        # Flip frame if needed
        if self.flip_horizontal:
            frame = cv2.flip(frame, 1)

        if orig_img is None:
            orig_img = frame
        padded_img, scale, pad_x, pad_y, new_width, new_height = self.img_cv_2_qt(
            orig_img, target_label=self.MainGUI.image_display, return_padded_img=True)
        img_result, is_fall = self.fall_detect.inference_and_draw_on_display(
            orig_img, padded_img, scale, pad_x, pad_y, new_width, new_height)
        pixmap, _, _, _, _, _ = self.img_cv_2_qt(img_result, target_label=self.MainGUI.image_display)
        get_updater().call_latest(self.MainGUI.image_display.setPixmap, pixmap)

        # Robust auto-recording logic
        try:
            if self.auto_record_on_fall:
                if is_fall:
                    if not self.recording and self.cam_availible and self.save_folder:
                        # print("[DEBUG] Auto recording on fall: True")
                        self.start_recording()
                else:
                    if self.recording:
                        self.stop_recording()
        except Exception as e:
            # print(f"[ERROR] Auto-recording logic: {e}")
            self.MainGUI.MessageBox_signal.emit(f"Error: {str(e)}")

        if is_fall:
            image_view = img_result.copy()
            cv2.putText(image_view, 'FALLEN DETECTED', (20, 170), 0, 1, [0, 0, 255], thickness=2, lineType=cv2.LINE_AA)
            pixmap, _, _, _, _, _ = self.img_cv_2_qt(image_view, target_label=self.MainGUI.result_label)
            get_updater().call_latest(self.MainGUI.result_label.setPixmap, pixmap)
            get_updater().call_latest(self.MainGUI.status_label.setText, "FALLEN")
            get_updater().call_latest(self.MainGUI.status_label.setStyleSheet,"background-color: rgb(255, 0, 0);")
        else:
            get_updater().call_latest(self.MainGUI.status_label.setText, "NORMAL")
            get_updater().call_latest(self.MainGUI.status_label.setStyleSheet,"background-color: rgb(0, 255, 0);")

        # Save frame if recording
        try:
            if self.recording and self.video_writer:
                self.video_writer.write(frame)
        except Exception as e:
            # print(f"[ERROR] Writing video frame: {e}")
            self.MainGUI.MessageBox_signal.emit(f"Error: {str(e)}")

    # Process live camera feed
    def camera_mode(self):
        url_camera = config.CAMERA_DEVICE
        self.init_devices(url_camera)
        while self.cam_availible and self.start_camera:
            try:
                cam_availible, frame = self.camera.read()
                if not cam_availible:
                    time.sleep(0.05)  # Small delay before retrying
                    continue
                self.cam_availible = cam_availible
                if self.start_camera and self.cam_availible:
                    self.process_and_display(frame)
                else:
                    break
            except Exception as e:
                self.MainGUI.MessageBox_signal.emit(f"Error: {str(e)}")
        self.reset_camera()

    # Process video file
    def video_mode(self, path_video):
        url_camera = path_video
        self.init_devices(url_camera)
        if self.camera is None:
            self.MainGUI.MessageBox_signal.emit("Error: Could not open video source.", "error")
            return
        last_is_fall = False
        while self.cam_availible and self.start_camera:
            try:
                cam_availible, frame = self.camera.read()
                if not cam_availible:
                    time.sleep(0.05)
                    continue
                self.cam_availible = cam_availible
                if self.start_camera and self.cam_availible:
                    try:
                        padded_img, scale, pad_x, pad_y, new_width, new_height = self.img_cv_2_qt(
                            frame, target_label=self.MainGUI.image_display, return_padded_img=True)
                        img_result, is_fall = self.fall_detect.inference_and_draw_on_display(
                            frame, padded_img, scale, pad_x, pad_y, new_width, new_height)
                        last_is_fall = is_fall
                        self.process_and_display(frame, orig_img=frame)
                    except Exception as e:
                        self.MainGUI.MessageBox_signal.emit(f"Error: {str(e)}", "error")
                else:
                    break
            except Exception as e:
                self.MainGUI.MessageBox_signal.emit(f"Error: {str(e)}", "error")
        self.reset_camera()
    
    # Reset camera for switching between inputs
    def reset_camera(self):
        try:
            self.start_camera = False
            
            if self.camera is not None and self.cam_availible:
                self.camera.release()
                
            self.camera = None
            self.cam_availible = False
            
        except Exception as e:
            self.MainGUI.MessageBox_signal.emit(f"Error: {str(e)}")