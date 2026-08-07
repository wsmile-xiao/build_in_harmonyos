#!/bin/sh
set -eu

nvim --version
nvim --headless -u NONE -i NONE '+lua print(vim.version().major)' +qa
