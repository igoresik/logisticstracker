# Builds dist\LogisticsTracker.exe (Windows). Run from the project folder.
.venv\Scripts\python -m pip install --quiet pyinstaller
.venv\Scripts\pyinstaller launcher.py --name LogisticsTracker --onefile --windowed --noconfirm `
    --collect-all streamlit --copy-metadata streamlit `
    --add-data "app.py;." --add-data "schema.sql;." --add-data "style.css;." `
    --add-data ".streamlit/config.toml;.streamlit"
