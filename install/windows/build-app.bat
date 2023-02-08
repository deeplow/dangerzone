REM delete old dist and build files
rmdir /s /q dist
rmdir /s /q build

REM build the exe
python .\setup-windows.py build

REM code sign whisperzone.exe
signtool.exe sign /v /d "Whisperzone" /sha1 1a0345732140749bdaa03efe8591b2c2a036884c /tr http://timestamp.digicert.com build\exe.win-amd64-3.10\whisperzone.exe

REM build the wix file
python install\windows\build-wxs.py > build\Whisperzone.wxs

REM build the msi package
cd build
candle.exe Whisperzone.wxs
light.exe -ext WixUIExtension Whisperzone.wixobj

REM code sign whisperzone.msi
insignia.exe -im Whisperzone.msi
signtool.exe sign /v /d "Whisperzone" /sha1 1a0345732140749bdaa03efe8591b2c2a036884c /tr http://timestamp.digicert.com Whisperzone.msi

REM moving Whisperzone.msi to dist
cd ..
mkdir dist
move build\Whisperzone.msi dist
