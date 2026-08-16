#!/usr/bin/env bash
set -euo pipefail

wrapper=$1
output=$("$wrapper" --activity-id ohos-workspace-7 \
    --activity-name "Study Room 7" --probe-context)

grep -Fx 'provider=explicit' <<<"$output"
grep -Fx 'id=ohos-workspace-7' <<<"$output"
grep -Fx 'name=Study Room 7' <<<"$output"
grep -Fx 'profile_key=StudyRoom7_ohos-workspace-7' <<<"$output"

if "$wrapper" --activity-id incomplete --probe-context >/dev/null 2>&1; then
    echo "FAIL: incomplete explicit context was accepted" >&2
    exit 1
fi

for unsafe_id in '../escape' 'has whitespace'; do
    if "$wrapper" --activity-id "$unsafe_id" \
        --activity-name Unsafe --probe-context >/dev/null 2>&1; then
        echo "FAIL: unsafe activity ID was accepted: $unsafe_id" >&2
        exit 1
    fi
done

test_root=$(mktemp -d)
test_home="$test_root/home"
firefox_log="$test_root/firefox.log"
wrapper_log="$test_root/wrapper.log"
fake_firefox="$test_root/firefox"
cleanup() {
    status=$?
    if [ "$status" -ne 0 ]; then
        echo "FAIL: activity-aware-firefox functional test" >&2
        echo "--- firefox log ---" >&2
        test ! -f "$firefox_log" || cat "$firefox_log" >&2
        echo "--- wrapper log ---" >&2
        test ! -f "$wrapper_log" || cat "$wrapper_log" >&2
    fi
    rm -rf "$test_root"
    exit "$status"
}
trap cleanup EXIT
mkdir -p "$test_home/.mozilla/firefox/base1234.default-release"

cat >"$fake_firefox" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail

if [ "$1" = "-CreateProfile" ]; then
    name=$2
    case "$name" in
        template-profile) prefix=tmpl1234 ;;
        *) prefix=actv1234 ;;
    esac
    mkdir -p "$HOME/.mozilla/firefox/$prefix.$name"
    printf 'create=%s\n' "$name" >>"$FAKE_FIREFOX_LOG"
elif [ "$1" = "--profile" ]; then
    profile=$2
    shift 2
    printf 'launch=%s args=%s\n' "$profile" "$*" >>"$FAKE_FIREFOX_LOG"
else
    printf 'unexpected=%s\n' "$*" >>"$FAKE_FIREFOX_LOG"
    exit 1
fi
EOF
chmod +x "$fake_firefox"

run_wrapper() {
    HOME="$test_home" \
    ACTIVITY_AWARE_FIREFOX_BIN="$fake_firefox" \
    FAKE_FIREFOX_LOG="$firefox_log" \
        "$wrapper" --activity-id ohos-workspace-7 \
        --activity-name "Study Room 7" --copy-type new --foreground \
        -- --private-window \
        >>"$wrapper_log" 2>&1
}

wait_for_launches() {
    expected=$1
    for _ in 1 2 3 4 5 6 7 8 9 10; do
        [ "$(grep -c '^launch=' "$firefox_log" 2>/dev/null || true)" -ge "$expected" ] && return 0
        # OpenHarmony's toybox sleep only accepts whole seconds.  The fake
        # Firefox is normally observed immediately; yield for one second only
        # while the background launch is still pending.
        sleep 1
    done
    return 1
}

run_wrapper
wait_for_launches 1
activity_profile="$test_home/.mozilla/firefox/actv1234.StudyRoom7_ohos-workspace-7"
test -d "$test_home/.mozilla/firefox/tmpl1234.template-profile"
test -d "$activity_profile"
grep -Fx 'create=StudyRoom7_ohos-workspace-7' "$firefox_log"
grep -Fx "launch=$activity_profile args=--private-window" "$firefox_log"

run_wrapper
wait_for_launches 2
test "$(grep -Fxc 'create=StudyRoom7_ohos-workspace-7' "$firefox_log")" -eq 1
test "$(grep -Fxc "launch=$activity_profile args=--private-window" "$firefox_log")" -eq 2
if grep -F 'DirectoryNotFound' "$wrapper_log"; then
    echo "FAIL: profile flow used an unresolved directory" >&2
    exit 1
fi

echo "PASS: portable provider and Firefox profile flow assertions=14/14"
