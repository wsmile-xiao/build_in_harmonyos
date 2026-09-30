#!/bin/sh
# Consumer use cases for the packaged lokalize application (OHOS aarch64).
#
# Invoked from test_package/conanfile.py with the runtime environment already
# prepared (LD_LIBRARY_PATH, QT_PLUGIN_PATH, HOME/XDG directories) and with a
# CWD whose ../../bin reaches the link farm of the dependency shared libraries.
#
# Usage: test_app.sh <lokalize-binary> <package-folder>
#
# Exits 0 only when every use case passes, and prints the evidence each verdict
# is based on so a CI failure can be diagnosed from the log alone.
set -eu

BIN="${1:-}"
PKG="${2:-}"
if [ -z "$BIN" ] || [ -z "$PKG" ]; then
    echo "[fail] usage: test_app.sh <lokalize-binary> <package-folder>"
    exit 1
fi
[ -x "$BIN" ] || { echo "[fail] packaged binary not executable: $BIN"; exit 1; }

WORK="$(pwd)/lokalize-consumer"
rm -rf "$WORK"
mkdir -p "$WORK/logs"

fail() {
    echo "[fail] $1"
    exit 1
}

# ---------------------------------------------------------------------------
# use case 2: open a real translation document through the packaged program
# ---------------------------------------------------------------------------
# A small but genuine PO file (plural forms included) is opened through the
# packaged command-line interface: that is the workflow the application exists
# for, and it drives the KIO file worker, hunspell, the Qt6 SQL
# translation-memory backend and the KF6 plugin closure on the device ABI.
DOC="$WORK/de.po"
cat > "$DOC" <<'PO'
msgid ""
msgstr ""
"Project-Id-Version: lokalize-consumer-test\n"
"MIME-Version: 1.0\n"
"Content-Type: text/plain; charset=UTF-8\n"
"Content-Transfer-Encoding: 8bit\n"
"Language: de\n"
"Plural-Forms: nplurals=2; plural=(n != 1);\n"

msgid "Open"
msgstr "Öffnen"

msgid "Save"
msgstr "Speichern"

msgid "%1 file"
msgid_plural "%1 files"
msgstr[0] "%1 Datei"
msgstr[1] "%1 Dateien"
PO

BOOT_LOG="$WORK/logs/boot.log"
"$BIN" -platform offscreen --noprojectscan "$DOC" > "$BOOT_LOG" 2>&1 &
APP_PID=$!
# Watchdog: give the application 20 s to load the document and settle, then
# terminate it so the test stays bounded.
( sleep 20; kill -TERM "$APP_PID" 2>/dev/null || true ) &
WATCHDOG_PID=$!

# The bounded run is expected to end with SIGTERM, so a non-zero wait status is
# a valid outcome here and must not trip the strict mode.
APP_RC=0
wait "$APP_PID" 2>/dev/null || APP_RC=$?
kill -TERM "$WATCHDOG_PID" 2>/dev/null || true
wait "$WATCHDOG_PID" 2>/dev/null || true

echo "[info] use case 2 application output (last 15 lines):"
tail -n 15 "$BOOT_LOG" | sed 's/^/    | /'

if grep -qiE "error while loading shared libraries|cannot open shared object file|symbol not found|undefined symbol" "$BOOT_LOG"; then
    fail "use case 2: the OHOS loader could not resolve a dependency"
fi
if grep -qiE "segmentation fault|aborted|core dumped|fatal error" "$BOOT_LOG"; then
    fail "use case 2: the application reported a crash while opening the document"
fi
# The application owns a document, so an orderly shutdown only happens when the
# watchdog terminates it (SIGTERM -> 143) or the watchdog itself fires (124).
case "$APP_RC" in
    143 | 124)
        echo "[ok] use case 2: document session survived the whole 20s window (exit $APP_RC)"
        ;;
    0)
        echo "[warn] use case 2: application exited on its own (exit 0) before the watchdog fired"
        ;;
    *)
        fail "use case 2: application died with exit code $APP_RC"
        ;;
esac

# ---------------------------------------------------------------------------
# use case 3: the installed payload a desktop consumer actually needs
# ---------------------------------------------------------------------------
# Installing the executable alone is not a usable application package: the
# desktop shell needs the desktop entry, the software centre reads the appdata
# file, the launcher draws the icon and KConfig reads the kcfg schema. These
# are the files the upstream install() rules promise, checked against the
# packaged tree (not the build tree).
PAYLOAD_MISSING=0
for rel in \
    "share/applications/org.kde.lokalize.desktop" \
    "share/metainfo/org.kde.lokalize.appdata.xml" \
    "share/config.kcfg/lokalize.kcfg"
do
    if [ -e "$PKG/$rel" ]; then
        echo "[info] use case 3: found $rel"
    else
        echo "[fail] use case 3: missing installed file $rel"
        PAYLOAD_MISSING=1
    fi
done
ICON_COUNT=$(find "$PKG/share/icons" -name '*lokalize*.png' 2>/dev/null | wc -l)
if [ "$ICON_COUNT" -gt 0 ]; then
    echo "[info] use case 3: found $ICON_COUNT installed lokalize icon(s)"
else
    echo "[fail] use case 3: no lokalize icon installed under share/icons"
    PAYLOAD_MISSING=1
fi
[ "$PAYLOAD_MISSING" -eq 0 ] || fail "use case 3: the installed application payload is incomplete"
echo "[ok] use case 3: installed desktop payload complete (desktop entry, appdata, kcfg, icons)"

echo "[ok] all consumer use cases passed"
exit 0
