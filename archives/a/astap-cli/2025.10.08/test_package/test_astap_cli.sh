#!/data/service/hnp/bin/bash
set -eu

help_output=$(astap_cli -h)
printf '%s\n' "$help_output" | grep -Fx 'ASTAP astrometric solver version CLI-2025.10.08'
printf '%s\n' "$help_output" | grep -F 'Usage:'
printf '%s\n' "$help_output" | grep -F -- '-f  filename'
printf '%s\n' "$help_output" | grep -F -- '-analyse snr_min'

no_arg_output=$(astap_cli)
printf '%s\n' "$no_arg_output" | grep -F 'Usage:'
missing_output=$(astap_cli -f /definitely/missing/astap-input.fits 2>&1)
printf '%s\n' "$missing_output" | grep -F 'Error, accessing the file!'
printf '%s\n' "$missing_output" | grep -F 'File not found.'

fixture="$PWD/astap-cli-synthetic-stars.fits"
/data/service/hnp/bin/python3 "$TEST_SOURCE_DIR/generate_test_fits.py" "$fixture"
analyse_output=$(astap_cli -f "$fixture" -analyse 5)
printf '%s\n' "$analyse_output" | grep -E '^HFD_MEDIAN=[0-9]+([.][0-9]+)?$'
printf '%s\n' "$analyse_output" | grep -E '^STARS=[1-9][0-9]*$'
printf '%s\n' 'astap-cli runtime integration tests: PASS'
