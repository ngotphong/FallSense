# Suppress warnings
import warnings
warnings.filterwarnings('ignore')

# Import PyQt5 components
from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5 import QtCore, uic, QtCore, QtGui, QtWidgets

# Standard library imports
import os
import sys
import traceback
import multiprocessing
import time
import psutil
from threading import Thread
import json

# Import custom modules
from src.Main import Main
from qt_thread_updater import get_updater
from src import config as co, Timer

class MainGUI(QtWidgets.QMainWindow):
    # Define custom signal for message boxes
    MessageBox_signal = QtCore.pyqtSignal(str, str)
    
    def __init__(self):
        # Initialize parent class
        super(MainGUI, self).__init__()
        
        # Load UI from file
        self.ui = uic.loadUi(co.MAIN_GUI, self)
        
        # Connect button signals to slots
        self.camera_mode_button.clicked.connect(self.open_camera)  # Camera mode
        self.video_mode_button.clicked.connect(self.open_video)    # Video mode
        self.image_mode_button.clicked.connect(self.manual)        # Image mode
        self.keypoint_toggle_button.clicked.connect(self.toggle_keypoints)  # Toggle keypoints
        self.keypoint_toggle_button.setText("Show Keypoints")      # Set initial button text
        
        # Configure the stop button
        self.stop_button = self.findChild(QPushButton, "pushButton_8")
        if self.stop_button:
            self.stop_button.setText("Stop")
            self.stop_button.setIcon(QIcon("icons/stop.png"))
            self.stop_button.setIconSize(QSize(35, 35))
            self.stop_button.clicked.connect(self.stop)
            self.stop_button.setEnabled(False)  # Initially disabled
        
        # Connect message box signal to slot
        self.MessageBox_signal.connect(self.MessageBox_slot)
        
    def start(self):
        try:
            # Show the main window
            self.show()
            # Initialize the Main class with UI
            self.Main = Main(self.ui)
            # Start performance monitoring in background
            Timer.Timer(function=self.monitor_pc_performance, name="pc_performance", 
                       forever=True, interval=2, type="repeat").start()
        except Exception as e:
            # Show error and exit if initialization fails
            self.MessageBox_signal.emit(str(e), "error")
            sys.exit(1)
    
    def toggle_keypoints(self):
        # Toggle keypoint display via Main class
        self.Main.toggle_keypoints()
    
    def open_camera(self):
        try:
            # Update UI for camera mode
            self.update_window("start", name="auto_camera")
            # Start camera processing in background thread
            Timer.Timer(function=self.Main.auto_camera, name="auto_camera").start()
        except Exception as e:
            # Show error and stop on failure
            self.MessageBox_signal.emit(str(e), "error")
            self.MessageBox_signal.emit("Có lỗi xảy ra !", "error")  # "An error occurred!"
            self.stop()

    def open_video(self):
        try:
            # Update UI for video mode
            self.update_window("start", name="auto_video")
            # Show file dialog to select video
            options = QtWidgets.QFileDialog.Options()
            video_file, _ = QtWidgets.QFileDialog.getOpenFileName(
                self, "QFileDialog.getOpenFileName()", "", 
                "Video (*.mp4 *.avi *.wmv *.mkv)", options=options)
            
            if video_file:
                # Start video processing in background thread
                Timer.Timer(function=self.Main.auto_video, name="auto_video", 
                           args=[video_file]).start()

        except Exception as e:
            # Show error and stop on failure
            self.MessageBox_signal.emit(str(e), "error")
            self.MessageBox_signal.emit("Có lỗi xảy ra !", "error")  # "An error occurred!"
            self.stop()
    
    def manual(self):
        try:
            # Update UI for image mode
            self.update_window("start", name="manual")
            # Show file dialog to select image
            options = QtWidgets.QFileDialog.Options()
            img_file, _ = QtWidgets.QFileDialog.getOpenFileName(
                self, "QFileDialog.getOpenFileName()", "", 
                "Images (*.png *.jpg *.jpeg *.bmp)", options=options)
            
            if img_file:
                # Process selected image
                self.Main.manual_image(img_file)
            
        except Exception as e:
            # Show error on failure
            self.MessageBox_signal.emit(str(e), "error")
            self.MessageBox_signal.emit("Có lỗi xảy ra !", "error")  # "An error occurred!"
    
    def stop(self):
        # Update UI to stopped state
        self.update_window("stop")
        # Close camera/video
        self.Main.close_camera()
        
    def update_window(self, typ, name="auto_camera"):
        # Debug info
        print("update_window called", typ, name)
        
        if typ == "start":
            # Enable stop button when starting
            if hasattr(self, 'stop_button') and self.stop_button:
                self.stop_button.setEnabled(True)
                
            if name == "manual":
                # For image mode
                self.image_mode_button.setStyleSheet("background-color: rgb(0, 204, 255);")
                # Disable mode buttons during processing
                for item in (self.camera_mode_button, self.image_mode_button, self.video_mode_button):
                    item.setEnabled(False)
                # Enable keypoint toggle
                self.keypoint_toggle_button.setEnabled(True)
            else:
                # Enable keypoint toggle for camera/video modes
                self.keypoint_toggle_button.setEnabled(True)
                
                if name == "auto_camera":
                    # For camera mode
                    self.camera_mode_button.setStyleSheet("background-color: rgb(0, 204, 255);")
                    # Disable mode buttons during processing
                    for item in (self.camera_mode_button, self.image_mode_button):
                        item.setEnabled(False)

                elif name == "auto_video":
                    # For video mode
                    for item in (self.camera_mode_button, self.image_mode_button, self.video_mode_button):
                        item.setEnabled(False)
                        item.setStyleSheet("")
                    self.video_mode_button.setStyleSheet("background-color: rgb(0, 204, 255);")

        elif typ == "stop":
            # Disable stop button when stopped
            if hasattr(self, 'stop_button') and self.stop_button:
                self.stop_button.setEnabled(False)
                
            # Disable keypoint toggle when stopped
            for item in [self.keypoint_toggle_button]:
                item.setEnabled(False)
            # Enable all mode buttons and reset styles
            for item in (self.camera_mode_button, self.image_mode_button, self.video_mode_button):
                item.setEnabled(True)
                item.setStyleSheet("")
    
    # Handle window close event
    def closeEvent(self, event):
        # Show confirmation dialog
        reply = QtWidgets.QMessageBox.question(
            self, "Thông báo", "Bạn có chắc chắn muốn thoát không ?",  # "Are you sure you want to exit?"
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No, QtWidgets.QMessageBox.Yes)
        
        if reply == QtWidgets.QMessageBox.Yes:
            event.accept()  # Close the window
        else:
            event.ignore()  # Ignore the close event

    # Handle message box signals
    def MessageBox_slot(self, txt, style):
        if style == "error":
            # Show error message box
            QtWidgets.QMessageBox.critical(self, "Lỗi", txt)  # "Error"
        elif style == "warning":
            # Show warning message box
            QtWidgets.QMessageBox.warning(self, "Cảnh báo", txt)  # "Warning"
        else:
            # Show information message box
            QtWidgets.QMessageBox.information(self, "Thông báo", txt)  # "Information"

    # Monitor system performance (CPU, RAM, disk)
    def monitor_pc_performance(self):
        try:
            # Get CPU usage
            cpu_percent = sum(psutil.cpu_percent(percpu=True))/psutil.cpu_count()
            # Get memory usage
            mem_stats = psutil.virtual_memory()
            # Get disk usage
            disk_stats = psutil.disk_usage("/")
            
            # Update progress bars
            get_updater().call_latest(self.progressBar_CPU.setValue, int(cpu_percent))
            get_updater().call_latest(self.progressBar_RAM.setValue, int(mem_stats.percent))
            get_updater().call_latest(self.progressBar_DISK.setValue, int(disk_stats.percent))
            
            # Update text labels with GB values
            get_updater().call_latest(self.ram.setText, 
                                     f"{round(mem_stats.used/1000000000, 1)}/{round(mem_stats.total/1000000000, 1)}")
            get_updater().call_latest(self.disk.setText, 
                                     f"{round(disk_stats.used/1000000000, 1)}/{round(disk_stats.total/1000000000)}")
        except Exception as e:
            # Silently ignore errors in performance monitoring
            pass


# Application entry point
if __name__ == "__main__":
    # Create Qt application
    app = QApplication(sys.argv)
    # Create main window
    main = MainGUI()
    # Start the application
    main.start()
    # Run event loop
    sys.exit(app.exec_())