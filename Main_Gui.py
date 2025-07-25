import warnings
warnings.filterwarnings('ignore')

from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5 import QtCore, uic, QtCore, QtGui, QtWidgets

import os
import sys
import traceback
import multiprocessing
import time
import psutil
from threading import Thread
import json

from src.Main import Main
from qt_thread_updater import get_updater
from src import config, Timer

class MainGUI(QtWidgets.QMainWindow):
    MessageBox_signal = QtCore.pyqtSignal(str, str)
    
    def __init__(self):
        super(MainGUI, self).__init__()
        
        self.ui = uic.loadUi(config.MAIN_GUI, self)
        self.Main = Main(self.ui)
        
        self.video_mode_button.clicked.connect(self.open_video)
        self.keypoint_toggle_button.clicked.connect(self.toggle_keypoints)
        self.flip_horizontal_button.clicked.connect(self.toggle_flip_mode)
        self.set_save_folder_button.clicked.connect(self.set_save_folder)

        self.camera_mode_button.setCheckable(True)
        self.camera_mode_button.setChecked(False)
        self.camera_mode_button.toggled.connect(self.toggle_camera_mode)

        self.toggle_recording_button.setCheckable(True)
        self.toggle_recording_button.setChecked(True)
        self.toggle_recording_button.toggled.connect(self.toggle_auto_recording)
        
        self.MessageBox_signal.connect(self.MessageBox_slot)
        
        self.setWindowTitle("FallSense")
        icon_path = os.path.join(os.path.dirname(__file__), "GUI/images/logo.png")
        self.setWindowIcon(QIcon(icon_path))

    def start(self):
        try:
            self.show()
            Timer.Timer(function=self.monitor_pc_performance, name="pc_performance", 
                       forever=True, interval=2, type="repeat").start()
        except Exception as e:
            self.MessageBox_signal.emit(str(e), "error")
            sys.exit(1)

    def toggle_flip_mode(self):
        self.Main.flip_horizontal = not self.Main.flip_horizontal

    def set_save_folder(self):
        self.Main.set_save_folder()
        if self.Main.save_folder:
            self.set_save_folder_button.setToolTip(f"Folder: {self.Main.save_folder}")
        else:
            self.set_save_folder_button.setToolTip("No folder selected, click to select")
    
    def toggle_auto_recording(self, checked):
        if not self.Main.save_folder:
            self.MessageBox_signal.emit("Please set a save folder first!", "error")
            self.toggle_recording_button.setChecked(False)
            return
        self.Main.auto_record_on_fall = checked
        if checked:
            self.toggle_recording_button.setStyleSheet("background-color: rgb(155, 0, 0);")
        else:
            self.toggle_recording_button.setStyleSheet("")
            if self.Main.recording:
                self.Main.stop_recording()

    def toggle_keypoints(self):
        show_keypoints = self.Main.toggle_keypoints()
        self.keypoint_toggle_active = show_keypoints
        if show_keypoints:
            self.keypoint_toggle_button.setStyleSheet("background-color: rgb(3, 161, 17);")
        else:
            self.keypoint_toggle_button.setStyleSheet("")

    def toggle_camera_mode(self, checked):
        if checked:
            if hasattr(self, 'Main') and self.Main:
                self.Main.reset_camera()
            self.update_window(name="camera_mode")
            Timer.Timer(function=self.Main.camera_mode, name="camera_mode").start()
        else:
            if hasattr(self, 'Main') and self.Main:
                self.Main.reset_camera()
            self.camera_mode_button.setStyleSheet("")

    def open_video(self):
        try:
            # Show file dialog to select video
            options = QtWidgets.QFileDialog.Options()
            video_file, _ = QtWidgets.QFileDialog.getOpenFileName(
                self, "QFileDialog.getOpenFileName()", "", 
                "Video (*.mp4 *.avi *.wmv *.mkv)", options=options)
            
            if video_file:
                if hasattr(self, 'Main') and self.Main:
                    self.Main.reset_camera()
                    
                self.update_window(name="video_mode")
                Timer.Timer(function=self.Main.video_mode, name="video_mode", 
                           args=[video_file]).start()

        except Exception as e:
            self.MessageBox_signal.emit(f"Error: {str(e)}") # "An error occurred!"
    
    def update_window(self, name="camera_mode"):
        for item in (self.camera_mode_button, self.video_mode_button, self.keypoint_toggle_button):
            item.setEnabled(True)
            item.setStyleSheet("")
            
        if name == "camera_mode":
            self.camera_mode_button.setStyleSheet("background-color: rgb(0, 204, 255);")
            self.flip_horizontal_button.setEnabled(True)
            self.toggle_recording_button.setEnabled(True)
            self.set_save_folder_button.setEnabled(True)
        elif name == "video_mode":
            self.video_mode_button.setStyleSheet("background-color: rgb(0, 204, 255);")
            self.flip_horizontal_button.setEnabled(False)
            self.toggle_recording_button.setEnabled(False)
            self.set_save_folder_button.setEnabled(False)

    # Handle message box signals
    def MessageBox_slot(self, txt, style):
        if style == "error":
            QtWidgets.QMessageBox.critical(self, "Error", txt)  # "Error"
        elif style == "warning":
            QtWidgets.QMessageBox.warning(self, "Warning", txt)  # "Warning"
        else:
            QtWidgets.QMessageBox.information(self, "Info", txt)  # "Information"

    # Monitor system performance (CPU, RAM, disk)
    def monitor_pc_performance(self):
        try:
            cpu_percent = sum(psutil.cpu_percent(percpu=True))/psutil.cpu_count()
            mem_stats = psutil.virtual_memory()
            disk_stats = psutil.disk_usage("/")
            
            # Update progress bars
            get_updater().call_latest(self.progressBar_CPU.setValue, int(cpu_percent))
            get_updater().call_latest(self.progressBar_RAM.setValue, int(mem_stats.percent))
            get_updater().call_latest(self.progressBar_DISK.setValue, int(disk_stats.percent))
            
            # Update text labels with GB values
            get_updater().call_latest(self.cpu.setText, f"{round(cpu_percent, 1)}")
            get_updater().call_latest(self.ram.setText, 
                                     f"{round(mem_stats.used/1000000000, 1)}/{round(mem_stats.total/1000000000, 1)}")
            get_updater().call_latest(self.disk.setText, 
                                     f"{round(disk_stats.used/1000000000, 1)}/{round(disk_stats.total/1000000000)}")
        except Exception as e:
            self.MessageBox_signal.emit(f"Error: {str(e)}")

# Application entry point
if __name__ == "__main__":
    # Create Qt application
    app = QApplication(sys.argv)
    main = MainGUI()
    main.start()
    sys.exit(app.exec_())