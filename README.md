# activity_meter

A small tool for parental control of a PC.

## Installation

Open HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows\CurrentVersion\Run

Add start pythonw path/to/main.py

Options:
* dt - 180
* t-min - 09:00
* t-max - 21:00
* duration-max - 4:00:00
* addr - 0.0.0.0
* port - 8088
* title - That's enough for today

## Usage

URL: https://\<addr\>:\<port\>

Authorization: user 1234
