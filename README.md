# Make It Make Sense

A Python-based CSV data quality checker that identifies common data issues and helps repair inconsistent CSV structures.

## Features

- **CSV structure validation:** Detects rows with missing or extra fields.
- **Structure repair:** Creates a repaired CSV while preserving extra values in a separate report.
- **Missing-value detection:** Identifies missing values in columns.
- **Duplicate detection:** Finds duplicate values in selected columns.
- **Data type detection:** Identifies columns containing identifiers, dates, numbers, text, or empty values.
- **Data validation:** Checks for invalid numbers and future dates.
- **Quality summaries:** Reports detected issues in a readable format.
- **Automated tests:** Uses Python's `unittest` framework to test functionality.

## Tech Stack

- Python
- CSV processing
- `unittest`

## Project Structure

```text
make-it-make-sense/
├── Data/
│   ├── employees.csv
│   └── orders.csv
├── main.py
├── explain.py
├── test_main.py
└── README.md
```

## Getting Started

### Requirements

Python 3.11 or a compatible Python version.

### Run the program

From the project directory, activate your virtual environment and run:

```bash
python main.py
```

Enter the path to your CSV file when prompted.

### Run the tests

```bash
python test_main.py
```

## How It Works

The tool inspects a CSV file, identifies potential data-quality issues, and displays a summary. When inconsistent row structures are found, the user can choose to generate a repaired CSV and a separate report containing extra values.

The original CSV is preserved during the repair process.

## Project Goals

This project explores practical data-quality validation, defensive programming, CSV processing, and automated testing in Python.
