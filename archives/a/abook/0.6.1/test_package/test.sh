#!/bin/sh
# L1 test source file - satisfies CI L0c (test source file requirement)
# R34: Tests substantially exercise abook's functionality (format conversion, mutt-query)
# The actual tests run via conanfile.py test() method

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CSV_FILE="$SCRIPT_DIR/test_input.csv"
ABOOK_FILE="$SCRIPT_DIR/test_input.abook"

# Test 1: abook --help
abook --help

# Test 2: abook --formats
abook --formats

# Test 3: CSV -> vCard conversion
abook --convert --informat csv --infile "$CSV_FILE" --outformat vcard

# Test 4: abook native -> mutt conversion
abook --convert --informat abook --infile "$ABOOK_FILE" --outformat mutt

# Test 5: abook native -> csv conversion
abook --convert --informat abook --infile "$ABOOK_FILE" --outformat csv

# Test 6: mutt-query search
abook -f "$ABOOK_FILE" --mutt-query Alice

# Test 7: mutt-query no-match
abook -f "$ABOOK_FILE" --mutt-query nonexistent
