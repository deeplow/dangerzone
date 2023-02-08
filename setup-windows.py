#!/usr/bin/env python3
import os

from cx_Freeze import Executable, setup

with open("share/version.txt") as f:
    version = f.read().strip()

packages = ["whisperzone", "whisperzone.gui"]

setup(
    name="whisperzone",
    version=version,
    # On Windows description will show as the app's name in the "Open With" menu. See:
    # https://github.com/freedomofpress/dangerzone/issues/283#issuecomment-1365148805
    description="Whisperzone",
    packages=packages,
    options={
        "build_exe": {
            "packages": packages,
            "excludes": ["test", "tkinter"],
            "include_files": [("share", "share"), ("LICENSE", "LICENSE")],
            "include_msvcr": True,
        }
    },
    executables=[
        Executable(
            "install/windows/whisperzone.py",
            base="Win32GUI",
            icon="share/whisperzone.ico",
        ),
    ],
)
