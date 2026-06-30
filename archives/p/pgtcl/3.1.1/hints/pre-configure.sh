#!/bin/sh
# Pre-configure step for pgtcl - TEA extension without configure script
# 1. Generate configure script using autoconf
# 2. Fix umask 077 issue in generated configure (HarmonyOS HMDFS limitation)

# Generate configure from configure.in
autoconf configure.in -o configure 2>/dev/null
chmod +x configure

# Fix umask 077 issue in configure - removes problematic umask that creates
# unreadable temp directories on HarmonyOS HMDFS
sed -i 's/umask 077 && mktemp/mktemp/g' configure
sed -i 's/umask 077 && mkdir/mkdir/g' configure

echo "Pre-configure steps completed: autoconf + umask fix"
