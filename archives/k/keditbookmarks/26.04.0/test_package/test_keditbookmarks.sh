#!/bin/sh
# Smoke script for keditbookmarks 26.04.0 test_package.
# Kept as the L0c test source file; the actual assertions run from
# test_package/conanfile.py (test()) which invokes the packaged
# executables with self.run() — see conanfile.py for the full sequence:
#   1. kbookmarkmerger --help          (QCommandLineParser usage, exit 0)
#   2. keditbookmarks --importkde3 bookmarks.xml --exportns out.html
#                                      (headless model/importer/exporter round trip)
# This script documents the sequence and is executed standalone when a
# shell smoke is preferred:
set -e
BIN_DIR="${1:?usage: test_keditbookmarks.sh <package bin dir> <work dir>}"
WORK_DIR="${2:?usage: test_keditbookmarks.sh <package bin dir> <work dir>}"
export QT_QPA_PLATFORM=offscreen
"${BIN_DIR}/kbookmarkmerger" --help
"${BIN_DIR}/keditbookmarks" --importkde3 "$WORK_DIR/bookmarks.xml" --exportns "$WORK_DIR/bookmarks-export.html"
test -f "$WORK_DIR/bookmarks-export.html"
echo "keditbookmarks smoke OK"
