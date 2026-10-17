#!/bin/sh
set -euo pipefail
# cht.sh smoke test — the --help branch exits 0 before the rlwrap/mktemp
# dependency checks, so no runtime deps are needed.
#
# NOTE: no here-documents — /bin/sh here is zsh and /tmp is read-only on
# this platform (zsh here-docs create /tmp temp files).

if command -v cht.sh >/dev/null 2>&1; then
    INSTALLED="$(command -v cht.sh)"
else
    echo "FAIL: cht.sh not found in PATH"
    exit 1
fi
echo "cht.sh found: $INSTALLED"

# assertion 1: non-empty file
[ -s "$INSTALLED" ] || { echo "FAIL: cht.sh is empty"; exit 1; }
echo "installed script is non-empty: OK"

# assertion 2: bash syntax check
bash -n "$INSTALLED"
echo "bash -n: OK"

# assertion 3: --help via DIRECT execution (shebang path) exits 0 and
# prints Usage. Direct execution (not `bash <script>`) is required: it is
# the only way to prove the shebang resolves on this platform (OHOS has
# no /bin/bash hardlink — the shebang was patched to #!/usr/bin/env bash).
if ! [ -x "$INSTALLED" ]; then
    echo "FAIL: cht.sh is not executable"
    exit 1
fi
HELP_OUT="$("$INSTALLED" --help 2>/dev/null)"
if [ $? -eq 0 ] && printf '%s' "$HELP_OUT" | grep -q "Usage:"; then
    echo "direct execution --help exit 0 with Usage: OK"
else
    echo "FAIL: direct --help did not print Usage"
    exit 1
fi

# assertion 4: shell completion files installed
PKGDIR="$(dirname "$(dirname "$INSTALLED")")"
for f in \
    "share/bash-completion/completions/cht.sh" \
    "share/fish/vendor_completions.d/cht.sh.fish" \
    "share/zsh/site-functions/_cht.sh"
do
    if [ -s "$PKGDIR/$f" ]; then
        echo "completion $f: OK"
    else
        echo "FAIL: completion missing at $PKGDIR/$f"
        exit 1
    fi
done

echo "ALL TESTS PASSED"

# assertion 5 (HarmonyOS-specific): the installed shebang must be the
# portable `#!/usr/bin/env bash` form. OHOS has no /bin/bash hardlink
# (bash lives on $PATH), so the upstream `#!/bin/bash` would fail with
# exit 127 on direct execution — the recipe rewrites it at build time,
# and this check proves the patch actually landed in the package.
if [ "$(head -n 1 "$INSTALLED")" = "#!/usr/bin/env bash" ]; then
    echo "harmony-specific shebang check (#!/usr/bin/env bash): OK"
else
    echo "FAIL: harmony-specific shebang check — got '$(head -n 1 "$INSTALLED")', expected '#!/usr/bin/env bash' (OHOS has no /bin/bash hardlink)"
    exit 1
fi
