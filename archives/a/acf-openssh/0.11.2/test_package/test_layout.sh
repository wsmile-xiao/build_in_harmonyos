#!/bin/sh
set -eu

pkg="$1"
core="$2"
app="$pkg/usr/share/acf/app/openssh"
core_app="$core/share/acf/app"

for file in \
    openssh-controller.lua \
    openssh-model.lua \
    openssh-config-html.lsp \
    openssh-connectedpeers-html.lsp \
    openssh-listauth-html.lsp \
    openssh-listusers-html.lsp \
    openssh-expert-html.lsp \
    openssh-logfile-html.lsp \
    openssh-status-html.lsp \
    openssh-welcome-html.lsp \
    openssh.menu \
    openssh.roles
do
    test -f "$app/$file"
    echo "[PASS] packaged $file"
done

check_materialized_view() {
    name="$1"
    source_name="$2"
    if test -L "$app/$name"; then
        echo "[FAIL] $name must be a regular file on no-link OHOS storage" >&2
        exit 1
    fi
    if ! cmp -s "$app/$name" "$core_app/$source_name"; then
        echo "[FAIL] $name differs from acf-core/$source_name" >&2
        exit 1
    fi
    echo "[PASS] $name materializes acf-core/$source_name"
}

check_materialized_view openssh-expert-html.lsp expert-html.lsp
check_materialized_view openssh-logfile-html.lsp logfile-html.lsp
check_materialized_view openssh-status-html.lsp status-html.lsp

count=$(find "$app" -mindepth 1 -maxdepth 1 | wc -l | tr -d ' ')
test "$count" = 12
echo "[PASS] packaged exactly 12 upstream openssh resources"
