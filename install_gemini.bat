@echo off
REM Install dependencies for Katiba AI with Gemini support

echo Installing required packages...
pip install google-generativeai

echo.
echo ============================================
echo Installation complete!
echo ============================================
echo.
echo Next steps:
echo 1. Go to https://aistudio.google.com/apikey
echo 2. Click "Create API Key"
echo 3. Copy your API key
echo 4. Open .env and add:
echo    GEMINI_API_KEY=your-key-here
echo 5. Run: python katiba_rag.py
echo.
echo For more details, see QUICKSTART.md
echo ============================================
