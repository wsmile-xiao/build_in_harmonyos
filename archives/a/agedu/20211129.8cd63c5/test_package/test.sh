#!/bin/sh
set -eu

mkdir -p input
printf 'fixture data\n' > input/file.txt

agedu -s input
test -s agedu.dat

# agedu -t stays silent when stdout is not a terminal (conan self.run), and
# neither busybox `script` nor --cgi produce a usable text report here. Switch
# to `agedu -D` which dumps the index on stdout regardless of tty-ness; the
# dump carries the scanned directory name so it proves the scan + index worked.
agedu -D > report.txt
test -s report.txt
grep -Fq 'input' report.txt
