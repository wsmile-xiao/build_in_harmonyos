#!/bin/sh
# ocl-icd requires autoreconf to generate configure script
# The tarball only includes configure.ac, not a pre-generated configure
autoreconf -vi -Wall
