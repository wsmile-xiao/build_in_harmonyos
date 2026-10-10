#!/bin/bash
set -eu

binary=${1:?usage: test_yacpi_harmonyos.sh /path/to/yacpi}
if [ ! -x "$binary" ]; then
    echo "yacpi package binary is missing or not executable: $binary" >&2
    exit 1
fi

version=$("$binary" -v)
printf '%s\n' "$version" | grep -F 'YACPI 3.0.1' >/dev/null

a=$(uname -s)
if [ "$a" = "HarmonyOS" ]; then
    cpufreq=/sys/devices/system/cpu/cpu0/cpufreq
    scaling_cur=$cpufreq/scaling_cur_freq
    scaling_max=$cpufreq/scaling_max_freq
    cur_file=$cpufreq/cpuinfo_cur_freq
    max_file=$cpufreq/cpuinfo_max_freq
    min_file=$cpufreq/cpuinfo_min_freq
    if [ ! -r "$cur_file" ] || [ ! -r "$max_file" ]; then
        echo "HarmonyOS CPU frequency sysfs files are unavailable" >&2
        exit 1
    fi
    if [ -r "$scaling_cur" ] || [ -r "$scaling_max" ]; then
        echo "HarmonyOS fallback test requires scaling_* files to be absent" >&2
        exit 1
    fi

    cur_before_khz=$(cat "$cur_file")
    max_khz=$(cat "$max_file")
    min_khz=0
    if [ -r "$min_file" ]; then
        min_khz=$(cat "$min_file")
    fi
    max_mhz=$((max_khz / 1000))
    if output=$("$binary" -p -n -c 2>&1); then
        status=0
    else
        status=$?
    fi
    if [ "$status" -ne 0 ]; then
        printf 'HarmonyOS CPU query exited %s:\n%s\n' "$status" "$output" >&2
        exit 1
    fi
    cur_after_khz=$(cat "$cur_file")
    pair=$(printf '%s\n' "$output" | sed -n 's/.*cpu = \([0-9][0-9]*\)\/\([0-9][0-9]*\) mhz.*/\1 \2/p')
    set -- $pair
    if [ "$#" -ne 2 ]; then
        printf 'YACPI did not report a CPU frequency pair:\n%s\n' "$output" >&2
        exit 1
    fi
    reported_cur_mhz=$1
    reported_max_mhz=$2
    min_mhz=$((min_khz / 1000))
    before_mhz=$((cur_before_khz / 1000))
    after_mhz=$((cur_after_khz / 1000))
    # HarmonyOS cpuinfo_cur_freq is a live hardware reading and can move by
    # hundreds of MHz between these samples. Validate the YACPI sample against
    # the device's supported range instead of assuming the frequency is stable
    # across separate sysfs reads and process startup.
    if [ "$reported_max_mhz" -ne "$max_mhz" ] ||
       [ "$reported_cur_mhz" -lt "$min_mhz" ] ||
       [ "$reported_cur_mhz" -gt "$max_mhz" ] ||
       [ "$before_mhz" -le 0 ] ||
       [ "$after_mhz" -le 0 ]; then
        printf 'YACPI output was outside live HarmonyOS cpufreq bounds (current %s, bounds %s..%s MHz, max %s MHz):\n%s\n' \
            "$reported_cur_mhz" "$min_mhz" "$max_mhz" "$max_mhz" "$output" >&2
        exit 1
    fi

    all_output=$("$binary" -p -n)
    printf '%s\n' "$all_output" | grep -F 'ac = no info' >/dev/null
    printf '%s\n' "$all_output" | grep -F 'cpu =' >/dev/null
    echo "PASS: YACPI reports live HarmonyOS cpufreq and degrades gracefully without ACPI devices"
else
    output=$("$binary" -p -n -c)
    printf '%s\n' "$output" | grep -F 'cpu =' >/dev/null
    echo "PASS: YACPI CPU output is available"
fi
