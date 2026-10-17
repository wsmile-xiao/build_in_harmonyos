#!/bin/sh
set -eu
output=$("$1" --version 2>&1) || {
    status=$?
    printf '%s\n' "$output" >&2
    exit "$status"
}
case "$output" in
    [Aa][Vv][Rr][Dd][Uu][Dd][Ee]\ [Vv][Ee][Rr][Ss][Ii][Oo][Nn]\ 8.1*) ;;
    *)
        printf '%s\n' "$output" >&2
        exit 1
        ;;
esac

device=/dev/ohpcd-avrdude-no-device
set +e
serial_output=$("$1" -C "$2" -c arduino -p m328p -P "$device" -n 2>&1)
serial_status=$?
set -e

if [ "$serial_status" -eq 0 ]; then
    printf '%s\n' "Expected the nonexistent serial device to fail" >&2
    exit 1
fi

case "$serial_output" in
    *"$device"*)
        ;;
    *)
        printf '%s\n' "$serial_output" >&2
        printf '%s\n' "AVRDUDE did not reach the POSIX serial-device path" >&2
        exit 1
        ;;
esac
