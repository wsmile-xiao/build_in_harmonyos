#!/bin/sh
set -eu

package_dir=$1
work_dir=$2
pex="$package_dir/bin/pex"

mkdir -p "$work_dir/home" "$work_dir/data" "$work_dir/cache"
export HOME="$work_dir/home"
export XDG_DATA_HOME="$work_dir/data"
export XDG_CACHE_HOME="$work_dir/cache"
export XDG_CONFIG_HOME="$work_dir/home/.config"

pass=0
fail=0

check() {
    description=$1
    shift
    if "$@"; then
        printf '[PASS] %s\n' "$description"
        pass=$((pass + 1))
    else
        printf '[FAIL] %s\n' "$description" >&2
        fail=$((fail + 1))
    fi
}

check "executable is installed" test -x "$pex"
check "manual page is installed" test -f "$package_dir/share/man/man1/pex.1"
check "documentation is installed" test -f "$package_dir/share/doc/pex/README.md"
check "license is installed" test -f "$package_dir/licenses/LICENSE"
check "OHOS-compatible or POSIX shebang is present" sh -c "head -n 1 '$pex' | grep -Eq '^#!/(system/bin/sh|bin/sh)$'"

"$pex" --help > "$work_dir/help.txt"
check "help advertises init" grep -q 'pex init' "$work_dir/help.txt"
check "help advertises install" grep -q 'pex install' "$work_dir/help.txt"

check "cache path follows XDG_CACHE_HOME" test "$("$pex" --cache)" = "$work_dir/cache/pex"
check "repository path follows XDG_DATA_HOME" test "$("$pex" --repository)" = "$work_dir/data/pex/packages"

repo_source="$work_dir/repository"
mkdir -p "$repo_source"
printf '%s\n' \
    'homepage: https://example.invalid/pex-test' \
    'url: https://example.invalid/pex-test.tar.gz' \
    'sha1: 0000000000000000000000000000000000000000' \
    > "$repo_source/pex-test.yaml"
git -C "$repo_source" init -q
git -C "$repo_source" add pex-test.yaml
git -C "$repo_source" -c user.name=pex-test -c user.email=pex-test@example.invalid commit -qm init

"$pex" init "$repo_source"
check "init clones the package repository" test -f "$work_dir/data/pex/packages/pex-test.yaml"
"$pex" search > "$work_dir/search.txt"
check "search finds the local package" grep -q '^pex-test$' "$work_dir/search.txt"
"$pex" cat pex-test > "$work_dir/cat.txt"
check "cat returns package homepage" grep -q 'example.invalid/pex-test' "$work_dir/cat.txt"
check "cat returns package URL" grep -q 'pex-test.tar.gz' "$work_dir/cat.txt"

set +e
"$pex" invalid-command > "$work_dir/invalid.txt" 2>&1
rc=$?
set -e
check "invalid command returns failure" test "$rc" -eq 1
check "invalid command reports a diagnostic" grep -q 'invalid command' "$work_dir/invalid.txt"

printf '%s checks passed; %s failed\n' "$pass" "$fail"
test "$fail" -eq 0
