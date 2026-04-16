@echo off
echo ================================================
echo   SkyBook Pro - Starting Server
echo ================================================
echo.
echo [1/2] Installing required packages...
python -m pip install mysql-connector-python
echo.
echo [2/2] Starting SkyBook Pro server...
echo.
echo  Admin Login:  admin@skybook.com / admin123
echo  User Login:   ravi@skybook.com  / user123
echo.
echo  Press Ctrl+C to stop the server
echo.
python server.py
pause
