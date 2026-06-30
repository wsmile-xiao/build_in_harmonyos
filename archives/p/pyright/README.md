# Pyright

## Description

Pyright is a fast type checker intended for large Python source bases. It's developed by Microsoft and can be used as a standalone command-line tool or as a language server.

## Features

- Fast type checking for Python code
- Supports Python 3.3+ type hints
- Can be used as a standalone CLI tool or language server
- Works well with large codebases

## Installation

```bash
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- pyright 1.1.410
```

## Usage

```bash
# Type check a Python file
pyright myfile.py

# Type check a project
pyright --project myproject/

# Show version
pyright --version
```

## Dependencies

- Node.js (>=14.0.0)

## Tested on HarmonyOS

✅ Compatible with HarmonyOS kernel