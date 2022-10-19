SETLOCAL ENABLEEXTENSIONS
SET envName=mc_app
SET me=%~n0
SET parent=%~dp0
echo %parent%
SET anaconda_dir=%userprofile%/miniconda3
call %anaconda_dir%/Scripts/activate.bat
call conda activate %envName%
bokeh serve --show %parent%\..\src\mc_app\main.py
pause