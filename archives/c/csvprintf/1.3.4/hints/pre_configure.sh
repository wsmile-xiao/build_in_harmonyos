#!/bin/sh
# Pre-configure bootstrap for csvprintf
# Original tarball lacks configure script, needs autoreconf
touch AUTHORS ChangeLog NEWS
CONFIG_SHELL=/data/service/hnp/bin/bash autoreconf -fi
# Fix umask 077 issue on HMDFS (E046: chmod not effective)
perl -pi -e 's/umask 077/umask 000/g' configure
