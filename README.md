# Notes App

A simple and modern web application for managing notes, built with Python Flask and SQLite.

## Features

- Create, read, update, and delete notes
- Clean and responsive user interface
- Real-time updates
- Flash messages for user feedback
- Mobile-friendly design

## Prerequisites

- Python 3.7 or higher
- pip (Python package installer)

## Installation

1. Clone this repository or download the source code.

2. Create a virtual environment (recommended):
```bash
python -m venv venv
```

3. Activate the virtual environment:
- On Windows:
```bash
venv\Scripts\activate
```
- On macOS/Linux:
```bash
source venv/bin/activate
```

4. Install the required packages:
```bash
pip install -r requirements.txt
```

## Running the Application

1. Make sure your virtual environment is activated.

2. Run the Flask application:
```bash
python app.py
```

3. Open your web browser and navigate to:
```
http://localhost:5000
```

## Usage

- Click "Create New Note" to add a new note
- Click "Edit" on any note to modify its content
- Click "Delete" to remove a note
- Notes are automatically sorted by last updated time

## Technologies Used

- Flask - Web framework
- SQLAlchemy - Database ORM
- SQLite - Database
- Bootstrap 5 - Frontend framework
- Bootstrap Icons - Icon library 