# Development environment

## Debian/Ubuntu

Install dependencies:

```sh
sudo apt install -y podman dh-python build-essential fakeroot make libqt5gui5 \
    pipx python3 python3-dev python3-stdeb python3-all
```

Install Poetry using `pipx` (recommended) and add it to your `$PATH`:

_(See also a list of [alternative installation
methods](https://python-poetry.org/docs/#installation))_

```sh
pipx ensurepath
pipx install poetry
```

After this, restart the terminal window, for the `poetry` command to be in your
`$PATH`.

Change to the `dangerzone` folder, and install the poetry dependencies:

> **Note**: due to an issue with [poetry](https://github.com/python-poetry/poetry/issues/1917), if it prompts for your keyring, disable the keyring with `keyring --disable` and run the command again.

```
poetry install
```

Build the latest container:

```sh
./install/linux/build-image.sh
```

Run from source tree:

```sh
# start a shell in the virtual environment
poetry shell

# run the CLI
./dev_scripts/dangerzone-cli --help

# run the GUI
./dev_scripts/dangerzone
```

Create a .deb:

```sh
./install/linux/build-deb.py
```

## Fedora

Install dependencies:

```sh
sudo dnf install -y rpm-build podman python3 pipx qt5-qtbase-gui
```

Install Poetry using `pipx`:

```sh
pipx install poetry
```

Change to the `dangerzone` folder, and install the poetry dependencies:

> **Note**: due to an issue with [poetry](https://github.com/python-poetry/poetry/issues/1917), if it prompts for your keyring, disable the keyring with `keyring --disable` and run the command again.

```
poetry install
```

Build the latest container:

```sh
./install/linux/build-image.sh
```

Run from source tree:

```sh
# start a shell in the virtual environment
poetry shell

# run the CLI
./dev_scripts/dangerzone-cli --help

# run the GUI
./dev_scripts/dangerzone
```

Create a .rpm:

```sh
./install/linux/build-rpm.py
```

## Qubes OS

Create a Debian or Fedora-based development standalone qube with at least 8GB of private storage space, and follow the relevant instructions above for the respective template.

Over time, you may need to increase disk space or prune outdated Docker images if you run into build issues on this VM.

### Initial Setup

In dom0 run:
    `qvm-clone fedora-37 fedora-37-dz`
1. Copy the built `.rpm` to the `fedora-37-dz` via qvm-copy
2. Install the `.rpm` in the `fedora-37-dz` template by running:
    `sudo dnf install ~/QubesIncoming/<DEV_QUBE_NAME>/dangerzone*.rpm`
3. Create an disposable app qube (where the conversion will take place):
    `qvm-create --class AppVM --label red --template fedora-37-dz --prop netvm="" --prop template_for_dispvms=True dz-dvm`
4. Create a qube from to call the conversion:
    `qvm-create --class AppVM --label red --template fedora-37-dz dz`
5. In dom0 add the following RPC policy in the file `/etc/qubes/policy.d/50-dangerzone.policy`:
    `dz.Convert      *       @anyvm          @dispvm:dz-dvm  allow`

### Compiling and testing

1. Ensure you are not on any python virtualenv (otherwise RPM installation will fail)
2. Build the RPM package with the following command:
    `./install/linux/build-rpm.py --qubes`
3. Copy the built `dangerzone.rpm` to `fedora-37-dz`
    `qvm-copy dist/dangerzone-0.4.1-1.noarch.rpm`

Run on `fedora-37-dz`:
1. `sudo dnf install -y ~/QubesIncoming/<DEV_VM>/dangerzone-*.rpm` (replace `<DEV_VM>`)
2. Shut down the template `fedora-37-dz`

Run `dangerzone-cli` on the `dz` qube (make sure you only start it after the template has shut down)

## Initial Setup (apyrgio proposal)

1. Clone the repo into an app qube of your choice.
2. Go to the template of the app qube and install LibreOffice and python3-magic.
3. Create a disposable template qube (`dz-dvm`) with no access to the Internet,
   based on the same template as your App qube.
5. In dom0 add the following RPC policy in the file `/etc/qubes/policy.d/50-dangerzone.policy`:

   ```
   dz.Convert      *       @anyvm          @dispvm:dz-dvm  allow
   dz.ConvertDev      *       @anyvm       @dispvm:dz-dvm  allow
   ```

4. Copy the `./qubes/dz.ConvertDev` file into the
   `/rw/usrlocal/etc/qubes-rpc/dz.ConvertDev` path of the disposable template
   qube.
5. Install Poetry and the project's packages.

## Testing (apyrgio proposal)

Testing can continue as usual. For changes in the server side components, you
can simply edit them locally, and they will be mirrored to the disposable qube
through the dz.ConvertDev RPC call.

The only reason to update any template from there on is if:
1. The project requires new server-side components. Update the base Fedora 37
   template in that case.
2. The code for dz.ConvertDev needs to be updated. Copy the updated file in the
   `/rw/usrlocal/etc/qubes-rpc` path of the `dz-dvm` template in that case.

## macOS

Install [Docker Desktop](https://www.docker.com/products/docker-desktop). Make sure to choose your correct CPU, either Intel Chip or Apple Chip.

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

Build the dangerzone container image:

```sh
./install/macos/build-image.sh
```

Run from source tree:

```sh
# start a shell in the virtual environment
poetry shell

# run the CLI
./dev_scripts/dangerzone-cli --help

# run the GUI
./dev_scripts/dangerzone
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

Install [Docker Desktop](https://www.docker.com/products/docker-desktop).

Install the latest version of Python 3.10 (64-bit) [from python.org](https://www.python.org/downloads/windows/). Make sure to check the "Add Python 3.10 to PATH" checkbox on the first page of the installer.


Install Microsoft Visual C++ 14.0 or greater. Get it with ["Microsoft C++ Build Tools"](https://visualstudio.microsoft.com/visual-cpp-build-tools/) and make sure to select "Desktop development with C++" when installing.

Install [poetry](https://python-poetry.org/). Open PowerShell, and run:

```
python -m pip install poetry
```

Change to the `dangerzone` folder, and install the poetry dependencies:

```
poetry install
```

Build the dangerzone container image:

```sh
python .\install\windows\build-image.py
```

After that you can launch dangerzone during development with:

```
# start a shell in the virtual environment
poetry shell

# run the CLI
.\dev_scripts\dangerzone-cli.bat --help

# run the GUI
.\dev_scripts\dangerzone.bat
```

### If you want to build the installer

* Go to https://dotnet.microsoft.com/download/dotnet-framework and download and install .NET Framework 3.5 SP1 Runtime. I downloaded `dotnetfx35.exe`.
* Go to https://wixtoolset.org/releases/ and download and install WiX toolset. I downloaded `wix311.exe`.
* Add `C:\Program Files (x86)\WiX Toolset v3.11\bin` to the path ([instructions](https://web.archive.org/web/20230221104142/https://windowsloop.com/how-to-add-to-windows-path/)).

### If you want to sign binaries with Authenticode

You'll need a code signing certificate.

## To make a .exe

Open a command prompt, cd into the dangerzone directory, and run:

```
poetry run python .\setup-windows.py build
```

In `build\exe.win32-3.10\` you will find `dangerzone.exe`, `dangerzone-cli.exe`, and all supporting files.

### To build the installer

Note that you must have a codesigning certificate installed in order to use the `install\windows\build-app.bat` script, because it codesigns `dangerzone.exe`, `dangerzone-cli.exe` and `Dangerzone.msi`.

```
poetry run .\install\windows\build-app.bat
```

When you're done you will have `dist\Dangerzone.msi`.
