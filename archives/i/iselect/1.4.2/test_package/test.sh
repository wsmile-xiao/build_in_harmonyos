#!/bin/sh
set -eu

iselect -V > version.txt
grep -q "This is iSelect, Version 1.4.2" version.txt
grep -q "GNU General Public License" version.txt

iselect -h > help.out 2>&1
grep -q "Usage: .*iselect" help.out
