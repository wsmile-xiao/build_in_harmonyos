#!/bin/bash
# Consumer test for the direvent daemon, run against the installed package.
# Verifies the core OHOS adaptation: inotify-backed directory watching with
# real event dispatch and handler execution.
set -e

WORK=$(mktemp -d)
PID=""
trap 'kill $PID 2>/dev/null || true; rm -rf "$WORK"' EXIT
DIR="$WORK/watched"
mkdir -p "$DIR"

# direvent execve()s handler commands directly (no shell, no PATH search),
# so the handler must use an absolute path to the tool it runs.
TOUCH="$(command -v touch)"
if [ -z "$TOUCH" ]; then
    echo "FAIL: no touch utility found in PATH"
    exit 1
fi

cat > "$WORK/test.conf" <<EOT
debug 1;
watcher {
    path $DIR;
    event create;
    command "$TOUCH $WORK/marker";
}
EOT

# 1. Smoke: --version exits 0.
direvent --version > /dev/null

# 2. Functional: the config parser accepts a valid watcher definition.
direvent -t "$WORK/test.conf"

# 3. Functional: a real create event in the watched directory must reach the
#    configured handler. The daemon needs a moment to register its watcher, so
#    give it time and retry the trigger.
direvent -f -l debug "$WORK/test.conf" > "$WORK/daemon.log" 2>&1 &
PID=$!
sleep 2

hit=""
attempt=0
while [ -z "$hit" ] && [ "$attempt" -lt 5 ]; do
    attempt=$((attempt + 1))
    touch "$DIR/file$attempt"
    i=0
    while [ "$i" -lt 5 ]; do
        if [ -f "$WORK/marker" ]; then
            hit=yes
            break
        fi
        sleep 1
        i=$((i + 1))
    done
done

kill "$PID" 2>/dev/null || true

if [ -z "$hit" ]; then
    echo "FAIL: create event handler did not fire for watched directory"
    echo "--- daemon log ---"
    cat "$WORK/daemon.log" || true
    exit 1
fi

echo "direvent consumer test passed (create event dispatched to handler)"
