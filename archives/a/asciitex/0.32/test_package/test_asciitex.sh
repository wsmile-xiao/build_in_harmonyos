#!/bin/sh
# R34: Execute the asciitex binary to verify the package works.
# asciitex renders a LaTeX math expression as ASCII art and exits 0 on success.
asciitex "x^2" > /dev/null 2>&1
