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
        # Remove image mode button connection
        self.keypoint_toggle_button.clicked.connect(self.toggle_keypoints)  # Toggle keypoints
        self.keypoint_toggle_active = False  # Track toggle state
        
        # Stop button removed - pushButton_8 remains in original state
        
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
        show_keypoints = self.Main.toggle_keypoints()
        self.keypoint_toggle_active = show_keypoints
        if show_keypoints:
            self.keypoint_toggle_button.setStyleSheet("background-color: rgb(0, 204, 255);")
        else:
            self.keypoint_toggle_button.setStyleSheet("")
    
    def open_camera(self):
        try:
            # Close any existing camera/video first
            if hasattr(self, 'Main') and self.Main:
                self.Main.reset_camera()
                
            # Update UI for camera mode
            self.update_window(name="auto_camera")
            # Start camera processing in background thread
            Timer.Timer(function=self.Main.auto_camera, name="auto_camera").start()
        except Exception as e:
            # Show error on failure
            self.MessageBox_signal.emit(str(e), "error")
            self.MessageBox_signal.emit("Có lỗi xảy ra !", "error")  # "An error occurred!"

    def open_video(self):
        try:
            # Show file dialog to select video
            options = QtWidgets.QFileDialog.Options()
            video_file, _ = QtWidgets.QFileDialog.getOpenFileName(
                self, "QFileDialog.getOpenFileName()", "", 
                "Video (*.mp4 *.avi *.wmv *.mkv)", options=options)
            
            if video_file:
                # Close any existing camera/video first
                if hasattr(self, 'Main') and self.Main:
                    self.Main.reset_camera()
                    
                # Update UI for video mode
                self.update_window(name="auto_video")
                # Start video processing in background thread
                Timer.Timer(function=self.Main.auto_video, name="auto_video", 
                           args=[video_file]).start()

        except Exception as e:
            # Show error on failure
            self.MessageBox_signal.emit(str(e), "error")
            self.MessageBox_signal.emit("Có lỗi xảy ra !", "error")  # "An error occurred!"
    
    # Stop method removed
    
    def update_window(self, name="auto_camera"):
        # Debug info
        print("update_window called", name)
        
        # Reset all button styles
        for item in (self.camera_mode_button, self.video_mode_button, self.keypoint_toggle_button):
            item.setEnabled(True)
            item.setStyleSheet("")
            
        # Set specific mode button style
        if name == "auto_camera":
            self.camera_mode_button.setStyleSheet("background-color: rgb(0, 204, 255);")
        elif name == "auto_video":
            self.video_mode_button.setStyleSheet("background-color: rgb(0, 204, 255);")
        
        # Enable keypoint toggle for all modes
        self.keypoint_toggle_button.setEnabled(True)
    
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
            get_updater().call_latest(self.ui.progressBar_CPU.setValue, int(cpu_percent))
            get_updater().call_latest(self.ui.progressBar_RAM.setValue, int(mem_stats.percent))
            get_updater().call_latest(self.ui.progressBar_DISK.setValue, int(disk_stats.percent))
            
            # Update text labels with GB values
            get_updater().call_latest(self.ui.cpu.setText, f"{round(cpu_percent, 1)}")
            get_updater().call_latest(self.ui.ram.setText, 
                                     f"{round(mem_stats.used/1000000000, 1)}/{round(mem_stats.total/1000000000, 1)}")
            get_updater().call_latest(self.ui.disk.setText, 
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