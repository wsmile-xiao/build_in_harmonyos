#!/bin/sh
# PGXS build hint for clean-verify
# PostgreSQL extensions using PGXS don't have configure script
# This script skips the configure step and runs make directly

echo "PGXS build system detected: skipping configure, running make directly"

# PGXS extensions use 'make' directly without configure
# The build system is detected by presence of:
# - Makefile with 'include $(PGXS)'
# - META.json or .control file

# Exit with success to skip configure check
exit 0