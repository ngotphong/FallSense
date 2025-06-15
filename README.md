## Step 1: Prepare Environment
  - Install Miniconda
  - Create new virtual environment: `conda create -n <env_name> python=3.11.10`

## Step 2: Clone this repo:
  - `git clone https://github.com/ngotphong/fall-detection.git`
  - Install all the dependencies in the requirments.txt: `pip install -r requirements.txt`

## Step 3: Install Libraries and Dependencies:
  - `pip install -r requirements.txt`

## Step 4: Prepare Weight:
```
App_falling/ 
├── weights/ 
│ ├── fall_detection_person.pt
```
  - Download and put this in the same position, make any changes if needed

## Step 5: Run The Model:
  - `cd App_falling`
  - `python Main_Gui.py`
