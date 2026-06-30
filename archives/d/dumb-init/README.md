# dumb-init

**dumb-init** is a simple process supervisor and init system designed to run as PID 1 inside minimal container environments (such as Docker).

## Description

A minimal init system for Linux containers that:
- Acts as PID 1 in containers
- Properly handles and forwards signals to child processes
- Prevents zombie processes
- Lightweight (~269KB static binary)

## Why you need an init system

When running containers, the process becomes PID 1 with special responsibilities:
- Signal handling differs for PID 1 (kernel won't use default handlers)
- Without an init system, SIGTERM may have no effect
- Child processes may become zombies

dumb-init solves these problems by:
- Forwarding signals to all child processes
- Reaping zombie processes
- Lightweight overhead

## Features

- Static linking (no external dependencies)
- Simple to use: just prefix your command with `dumb-init`
- Signal rewriting capabilities
- Single-child mode option

## Installation

```bash
curl install.sh | sh -s -- dumb-init 1.2.5
```

## Usage

```bash
dumb-init python -c 'while True: pass'
dumb-init nginx -g 'daemon off;'
dumb-init --single-child my-app
```

## Source

- GitHub: https://github.com/Yelp/dumb-init
- License: MIT