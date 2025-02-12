# activity_meter

A small tool for parental control of a PC.

## Installation

Open HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows\CurrentVersion\Run

Add pythonw path/to/main.py

Options:
* dt - 180 (inactivity interval in seconds)
* t-min - 09:00 (hh:mm)
* t-max - 21:00 (hh:mm)
* duration-max - 4:00:00 (h:mm:ss)
* addr - 0.0.0.0
* port - 8088
* title - That's enough for today

## Usage

URL: https://\<addr\>:\<port\>

Authorization: user 1234
