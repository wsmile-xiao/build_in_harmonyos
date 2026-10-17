#!/usr/bin/env bash
# Check the packaged CLI and enumerate formats on accessible V4L2 devices.
set -euo pipefail

help_output="$(yavta --help)"
printf '%s\n' "$help_output" | grep -F 'Usage:'
printf '%s\n' 'PASS: usage line'
printf '%s\n' "$help_output" | grep -F -e '--help'
printf '%s\n' 'PASS: --help option'

accessible_video_devices=0
for device in /dev/video*; do
	[ -e "$device" ] || continue
	if [ -r "$device" ] && [ -w "$device" ]; then
		yavta --enum-formats "$device"
		accessible_video_devices=$((accessible_video_devices + 1))
	fi
done

if [ "$accessible_video_devices" -gt 0 ]; then
	printf '%s\n' 'PASS: V4L2 format enumeration'
else
	printf '%s\n' 'SKIP: no accessible V4L2 video device'
fi
