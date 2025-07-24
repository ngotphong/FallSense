import os                      # Operating system functions
from re import M               # Regular expressions
from pathlib import Path       # Path handling
import json                    # JSON handling
from yaml import load, dump    # YAML parsing

# Try to use C-based YAML loader for better performance
try:
    from yaml import CLoader as Loader, CDumper as Dumper
except ImportError:
    # Fall back to pure Python implementation if C version not available
    from yaml import Loader, Dumper

# Path to configuration file
path_cfg = 'development_config.yml'
# Load configuration from YAML file
cfg = load(open(path_cfg, 'r'), Loader=Loader)

# Extract camera device from configuration
CAMERA_DEVICE = cfg['CAMERA_DEVICE']

# Function to get absolute path to resources in the GUI directory
def resource_path(relative_path):
    base_path = os.path.abspath("GUI")
    return os.path.join(base_path, relative_path)

# Path to the main UI file
MAIN_GUI = resource_path("Main.ui")  # fetching the main GUI from GUI/Main.ui