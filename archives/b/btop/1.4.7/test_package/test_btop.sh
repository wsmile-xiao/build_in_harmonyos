#!/usr/bin/env sh
set -eu
if (set -o pipefail) 2>/dev/null; then
	set -o pipefail
fi

for _tool_dir in /system/bin /usr/bin /bin; do
	case ":${PATH:-}:" in
		*":$_tool_dir:"*) ;;
		*) PATH="${PATH:+$PATH:}$_tool_dir" ;;
	esac
done
export PATH

btop --version >version.out 2>&1
grep "btop version: .*1.4.7" version.out >/dev/null

btop --help >help.out 2>&1
grep "Usage:" help.out >/dev/null
grep "Options:" help.out >/dev/null

btop --default-config >default-config.out 2>&1
grep "shown_boxes" default-config.out >/dev/null
grep "cpu mem net proc" default-config.out >/dev/null

echo "=== btop tests PASSED ==="

