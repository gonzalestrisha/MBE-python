MBE-python — Quick setup (Windows, VS Code)

1. Open this folder in VS Code.

2. Create a local Python virtual environment:

   `python -m venv .venv`

3. Activate it (PowerShell):

   `.\.venv\Scripts\Activate.ps1`

   Or (Command Prompt):

   `.\.venv\Scripts\activate.bat`

4. Install required packages:

   `pip install -r requirements.txt`

   Otherwise install the basics:

   `pip install streamlit pandas plotly pytest`

5. Run the app:

   `streamlit run MBE-files/app.py`

6. Run tests:

   `pytest`

Note:
- `.venv/` is the local Python environment folder. It is ignored by Git so you do not commit it.
- These steps assume Python is installed and available as `python` in your PATH.