# Development environment

## Debian/Ubuntu

Install dependencies:

```sh
sudo apt install -y podman dh-python make libqt5gui5 \
    python3 python3-dev python3-venv python3-pip python3-stdeb
```

Install poetry (you may need to add `~/.local/bin/` to your `PATH` first):

```sh
python3 -m pip install poetry
```

Change to the `whisperzone` folder, and install the poetry dependencies:

> **Note**: due to an issue with [poetry](https://github.com/python-poetry/poetry/issues/1917), if it prompts for your keying, disable the keyring with `keyring --disable` and run the command again.

```
poetry install
```

Run from source tree:

```sh
# start a shell in the virtual environment
poetry shell

# run the GUI
./dev_scripts/whisperzone
```

Create a .deb:

```sh
./install/linux/build-deb.py
```

## Fedora

Install dependencies:

```sh
sudo dnf install -y rpm-build podman python3 python3-pip qt5-qtbase-gui
```

Install poetry:

```sh
python -m pip install poetry
```

Change to the `whisperzone` folder, and install the poetry dependencies:

> **Note**: due to an issue with [poetry](https://github.com/python-poetry/poetry/issues/1917), if it prompts for your keying, disable the keyring with `keyring --disable` and run the command again.

```
poetry install
```

Run from source tree:

```sh
# start a shell in the virtual environment
poetry shell

# run the GUI
./dev_scripts/whisperzone
```

Create a .rpm:

```sh
./install/linux/build-rpm.py
```

## QubesOS

Create a Debian- or Fedora-based standalone VM with at least 8GB of private storage space, and follow the relevant instructions above.

Over time, you may need to increase disk space or prune outdated Docker images if you run into build issues on this VM.

## macOS

Install the latest version of Python 3.10 [from python.org](https://www.python.org/downloads/macos/), and make sure `/Library/Frameworks/Python.framework/Versions/3.10/bin` is in your `PATH`.

Install Python dependencies:

```sh
python3 -m pip install poetry
poetry install
```

Install [Homebrew](https://brew.sh/) dependencies:

```sh
brew install create-dmg
```

Run from source tree:

```sh
# start a shell in the virtual environment
poetry shell

# run the GUI
./dev_scripts/whisperzone
```

To create an app bundle, use the `build_app.py` script:

```sh
poetry run ./install/macos/build-app.py
```

If you want to build for distribution, you'll need a codesigning certificate, and then run:

```sh
poetry run ./install/macos/build-app.py --with-codesign
```

The output is in the `dist` folder.

## Windows

Install the latest version of Python 3.10 (64-bit) [from python.org](https://www.python.org/downloads/windows/). Make sure to check the "Add Python 3.10 to PATH" checkbox on the first page of the installer.

Install Microsoft Visual C++ 14.0 or greater. Get it with ["Microsoft C++ Build Tools"](https://visualstudio.microsoft.com/visual-cpp-build-tools/) and make sure to select "Desktop development with C++" when installing.

Install [poetry](https://python-poetry.org/). Open PowerShell, and run:

```
python -m pip install poetry
```

Change to the `whisperzone` folder, and install the poetry dependencies:

```
poetry install
```

After that you can launch whisperzone during development with:

```
# start a shell in the virtual environment
poetry shell

# run the GUI
.\dev_scripts\whisperzone.bat
```

### If you want to build the installer

* Go to https://dotnet.microsoft.com/download/dotnet-framework and download and install .NET Framework 3.5 SP1 Runtime. I downloaded `dotnetfx35.exe`.
* Go to https://wixtoolset.org/releases/ and download and install WiX toolset. I downloaded `wix311.exe`.
* Add `C:\Program Files (x86)\WiX Toolset v3.11\bin` to the path.

### If you want to sign binaries with Authenticode

You'll need a code signing certificate.

## To make a .exe

Open a command prompt, cd into the whisperzone directory, and run:

```
poetry run python .\setup-windows.py build
```

In `build\exe.win32-3.10\` you will find `whisperzone.exe` and all supporting files.

### To build the installer

Note that you must have a codesigning certificate installed in order to use the `install\windows\build-app.bat` script, because it codesigns `whisperzone.exe` and `Whisperzone.msi`.

```
poetry run .\install\windows\build-app.bat
```

When you're done you will have `dist\Whisperzone.msi`.
