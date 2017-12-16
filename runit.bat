SETLOCAL ENABLEEXTENSIONS
SET me=%~n0
SET parent=%~dp0
echo %parent%
SET anaconda_dir=%userprofile%/Anaconda3
call %anaconda_dir%/Scripts/activate.bat
bokeh serve --show --allow-websocket-origin 192.168.0.3:6004 --allow-websocket-origin localhost:6004 --port 6004 %parent% 