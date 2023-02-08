#!/usr/bin/env python3
import os
import sys

import setuptools

with open("share/version.txt") as f:
    version = f.read().strip()


def file_list(path):
    files = []
    for filename in os.listdir(path):
        if os.path.isfile(os.path.join(path, filename)):
            files.append(os.path.join(path, filename))
    return files


setuptools.setup(
    name="whisperzone",
    version=version,
    author="Deeplow",
    author_email="deeplower@protonmail.com",
    license="MIT",
    description="Offline user interface for OpenAI's Whisper transcription tool",
    long_description="""\
Transcribe sensitive interviews offline with whisperzone.
""",
    url="https://github.com/deeplow/whisperzone",
    packages=["whisperzone", "whisperzone.gui"],
    data_files=[
        (
            "share/applications",
            ["install/linux/whisperzone.desktop"],
        ),
        (
            "share/icons/hicolor/64x64/apps",
            ["install/linux/whisperzone.png"],
        ),
        ("share/whisperzone", file_list("share")),
    ],
    classifiers=[
        "Programming Language :: Python",
        "Intended Audience :: End Users/Desktop",
        "Operating System :: OS Independent",
    ],
    entry_points={
        "console_scripts": [
            "whisperzone = whisperzone:main",
        ]
    },
)
