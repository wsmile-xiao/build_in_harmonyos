#!/bin/sh
set -eu

if [ "$#" -ne 2 ]; then
    echo "usage: test_keyboards_rg.sh PACKAGE_ROOT INVENTORY" >&2
    exit 2
fi

package_root=$1
inventory=$2
assertions=0

fail() {
    echo "KEYBOARDS_RG_OHOS_SHELL=FAIL reason=$1" >&2
    exit 1
}

[ -d "$package_root" ] || fail "package root is missing"
assertions=$((assertions + 1))
[ -s "$inventory" ] || fail "source inventory is missing"
grep -F -q "D3139512D68C2A93DB71315F3D1ECEB431DA237C47F4A723F87F9BB62D8D3DF4" "$inventory" \
    || fail "inventory is not bound to the official source archive"
assertions=$((assertions + 1))

check_file() {
    relative=$1
    expected_hash=$2
    path="$package_root/$relative"
    [ -f "$path" ] || fail "missing file: $relative"
    [ -s "$path" ] || fail "empty file: $relative"
    actual_hash=$(sha256sum "$path" | sed 's/[[:space:]].*//')
    [ "$actual_hash" = "$expected_hash" ] || fail "hash mismatch: $relative"
    if grep -F -q "/usr/" "$path" || grep -F -q "/etc/" "$path"; then
        fail "absolute system path in: $relative"
    fi
    assertions=$((assertions + 4))
}

check_file "share/X11/xkb/symbols/eo_rg" "b9a721d65d2fa3c173e7967c1519279aa61d26cbefef677a8be70857ae1159c1"
check_file "share/X11/xkb/symbols/pancyr" "6990ba9fee73350517ad952d7414cdf9550cb4092acf31b6697e9f01dab3eccc"
check_file "share/X11/xkb/symbols/sk_rg" "5f0f8fad8083365fb29ce64f52685aedb2594b40c7532474f6d8280e39c7f856"
check_file "share/X11/xkb/symbols/sk_snk" "7cd2fc03684c3b0cd6931b24bf5c59707619a9e9c251acb1037a09a4d837b8c6"
check_file "share/keymaps/i386/qwerty/ru_rg.kmap" "f65ca34bda32309eb5ecb3cbb42f8e42144f0aab47f8704f0ed005e26954c525"
check_file "share/keymaps/i386/qwerty/sk_rg.kmap" "75bbe0f8b2c3a2efb73374b61aa40e85bc266c4eef235d1d56abcec1fa114543"
check_file "bin/cyrx" "b14f377bad57e225ed39a21c20accf8c3be9464f9cdf5bc829d17a22066d98fe"
check_file "bin/eox" "f0778b1f9abf15ee8b1178740bebb79bfb9f7bcf11865e66f294c7ffee22c2c5"
check_file "bin/skx" "67245dbf2a0679d0260f17a89ac756188c8113be6a71e5287c8266ca25cac1ee"
check_file "licenses/COPYING" "777564a4fdd79020e506a2a5c7c90feaaf1f6ddc91e767cd811c04ccac1aacc0"

[ ! -e "$package_root/oldfiles" ] || fail "obsolete oldfiles payload was installed"
assertions=$((assertions + 1))

for layout in eo_rg pancyr sk_rg sk_snk; do
    grep -F -q "xkb_symbols" "$package_root/share/X11/xkb/symbols/$layout" \
        || fail "XKB declaration missing: $layout"
    assertions=$((assertions + 1))
done

for keymap in ru_rg.kmap sk_rg.kmap; do
    grep -F -q "keymaps " "$package_root/share/keymaps/i386/qwerty/$keymap" \
        || fail "console keymap header missing: $keymap"
    assertions=$((assertions + 1))
done

for script in cyrx eox skx; do
    sh -n "$package_root/bin/$script" || fail "shell syntax check failed: $script"
    assertions=$((assertions + 1))
done

flow_root="${TMPDIR:-/data/local/tmp}/keyboards-rg-flow-$$"
flow_log="$flow_root/setxkbmap.log"
mkdir -p "$flow_root"
trap 'rm -rf "$flow_root"' EXIT HUP INT TERM
printf '%s\n' '#!/bin/sh' \
    'printf "%s\n" "$*" >> "$KEYBOARDS_RG_SETXKBMAP_LOG"' \
    > "$flow_root/setxkbmap"
chmod +x "$flow_root/setxkbmap"
: > "$flow_log"

run_keyboard_flow() {
    script=$1
    expected=$2
    shift 2
    PATH="$flow_root:$PATH" \
    KEYBOARDS_RG_SETXKBMAP_LOG="$flow_log" \
        sh "$package_root/bin/$script" "$@"
    actual=$(sed -n '$p' "$flow_log")
    [ "$actual" = "$expected" ] || fail "backend invocation mismatch: $script"
    assertions=$((assertions + 2))
}

run_keyboard_flow eox \
    "us,eo_rg -option grp:shift_toggle,compose:menu,lv3:ralt_switch"
run_keyboard_flow skx \
    "us,sk_rg -option grp:shift_toggle,compose:menu,lv3:ralt_switch"
run_keyboard_flow cyrx \
    "us,pancyr(ukrainian) -option grp:shift_toggle,compose:menu,lv3:ralt_switch" \
    uk
run_keyboard_flow cyrx \
    "us,pancyr(belarussian) -option grp:shift_toggle,compose:menu,lv3:ralt_switch" \
    by
run_keyboard_flow cyrx \
    "us,pancyr -option grp:shift_toggle,compose:menu,lv3:ralt_switch"

[ -z "$(sed -n '6p' "$flow_log")" ] || fail "unexpected extra backend invocation"
assertions=$((assertions + 1))

echo "KEYBOARDS_RG_OHOS_FLOW=PASS invocations=5"
echo "KEYBOARDS_RG_OHOS_SHELL=PASS scripts=3"
echo "KEYBOARDS_RG_CONSUMER=PASS assertions=$assertions"
