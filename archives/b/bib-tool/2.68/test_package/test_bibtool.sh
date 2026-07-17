#!/bin/sh
# R34: Test must actually exercise the tested package's binary
# bibtool is a CLI tool — test by running it on a sample BibTeX file
set -e

BIBTOOL_BIN="${1:-bibtool}"

# Create a sample BibTeX file
TEST_BIB="test_bibtool_input.bib"
OUTPUT_BIB="test_bibtool_output.bib"

cat > "$TEST_BIB" << 'BIBEOF'
@article{test2024,
  author = {Test Author},
  title = {Test Title},
  year = {2024}
}
BIBEOF

# Run bibtool to format the BibTeX file
"$BIBTOOL_BIN" "$TEST_BIB" > "$OUTPUT_BIB"

# Verify the output contains expected content
output=$(cat "$OUTPUT_BIB")
errors=0
case "$output" in
    *"Test Author"*) ;;
    *) echo "FAIL: 'Test Author' not found in output"; errors=1 ;;
esac
case "$output" in
    *"Test Title"*) ;;
    *) echo "FAIL: 'Test Title' not found in output"; errors=1 ;;
esac
case "$output" in
    *"test2024"*) ;;
    *) echo "FAIL: 'test2024' not found in output"; errors=1 ;;
esac

rm -f "$TEST_BIB" "$OUTPUT_BIB"

if [ "$errors" -eq 0 ]; then
    echo "PASS: bibtool binary works correctly"
    exit 0
else
    echo "Output was: $output"
    exit 1
fi
