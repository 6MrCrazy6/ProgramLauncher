# Security Policy

## Security

Program Launcher is an open-source desktop application written in Python.

The project is designed to help users quickly launch programs, manage launch presets, and configure automatic startup (optional).

## Data Collection

Program Launcher **does not**:

* collect personal information;
* collect telemetry;
* send analytics;
* communicate with external servers;
* upload files;
* access cloud services.

The application works entirely offline.

## Internet Access

Program Launcher does not require an Internet connection to function.

Any network activity originates only from applications launched by the user, not from Program Launcher itself.

## Local Storage

The application stores only local configuration files, including:

* launcher settings;
* program list;
* presets;
* themes.

These files are stored on the local computer and are never transmitted anywhere.

## Windows Startup

Program Launcher can optionally register itself to start with Windows.

This feature is **disabled by default** and is enabled only after the user explicitly selects the option in the application settings.

## Source Code

The complete source code is publicly available in this repository.

Anyone can inspect, build, or audit the project.

## Reporting Security Issues

If you discover a security issue or believe the application behaves unexpectedly, please open an Issue in this repository with as much detail as possible.

All legitimate security reports are appreciated and will be investigated.
