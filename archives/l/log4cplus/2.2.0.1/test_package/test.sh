#!/system/bin/sh
set -eu

bin="${1:-bin/log4cplus_consumer}"
if [ ! -x "$bin" ]; then
    echo "consumer binary is not executable: $bin" >&2
    exit 2
fi

"$bin" >/dev/null
printf '%s\n' 'log4cplus consumer smoke passed'
