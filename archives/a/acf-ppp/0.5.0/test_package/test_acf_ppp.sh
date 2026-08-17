#!/bin/sh
set -eu

pkg_root=${1:?acf-ppp package root is required}
acf_core_root=${2:?acf-core package root is required}
app_dir="$pkg_root/usr/share/acf/app/ppp"
shared_dir="$acf_core_root/share/acf/app"
test_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
lua_runner="$test_dir/lua-runner"

for file in \
    ppp-controller.lua \
    ppp-model.lua \
    ppp-expert-html.lsp \
    ppp-listpeers-html.lsp \
    ppp.menu \
    ppp.roles
do
    test -s "$app_dir/$file"
done

cmp -s "$app_dir/ppp-editchap-html.lsp" "$shared_dir/filedetails-html.lsp"
cmp -s "$app_dir/ppp-editpap-html.lsp" "$shared_dir/filedetails-html.lsp"
cmp -s "$app_dir/ppp-editpeer-html.lsp" "$shared_dir/filedetails-html.lsp"
cmp -s "$app_dir/ppp-status-html.lsp" "$shared_dir/status-html.lsp"

for file in \
    ppp-editchap-html.lsp \
    ppp-editpap-html.lsp \
    ppp-editpeer-html.lsp \
    ppp-status-html.lsp
do
    test -f "$app_dir/$file"
    test ! -L "$app_dir/$file"
done

test -x "$lua_runner"
"$lua_runner" "$test_dir/test_acf_ppp.lua" "$app_dir"
