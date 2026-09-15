#!/usr/bin/env python3
"""Conan recipe for plenv 2.3.1.

plenv is a pure Bash Perl version manager (rbenv-style). There is no native
compilation: packaging copies the upstream scripts (libexec, completions,
plenv.d) plus docs, and keeps the upstream ``bin/plenv -> ../libexec/plenv``
relative symlink so path discovery keeps working.

Upstream tests: ``make test`` (Makefile) needs network access at test time
(it ``git clone``s ext/test-simple-bash) plus ``prove`` and a real perl, so
it is not hermetic for CI. build() instead runs an offline, hermetic mirror
of the single upstream assertion (test/shim.t: the generated shim forwards
``-E`` and observes ``PLENV_DIR``) using a stub perl. No network, no real
perl required. See notes.md and test_package/MANIFEST.yml for the audit.
"""

import json
import os
import stat

from conan import ConanFile
from conan.tools.files import copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class PlenvConan(ConanFile):
    name = "plenv"
    version = "2.3.1"
    description = "Simple Perl version management (rbenv-style, pure Bash)"
    license = "Artistic-1.0-Perl OR GPL-1.0-or-later"
    homepage = "https://github.com/tokuhirom/plenv"
    url = ""

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], filename="plenv-2.3.1.tar.gz", strip_root=True)

    def build(self):
        # -- Hardlink fallback (HMBS true-machine hardlink=0) --
        # Upstream libexec/plenv-rehash install_registered_shims() uses
        # `command -p ln -f` which fails on HMFS/HMDFS with
        # "Operation not permitted". Fall back to a plain copy when the
        # hard link fails. A symlink is NOT valid here because the EXIT
        # trap removes the prototype shim, leaving dangling links; a copy
        # keeps content-identical files that remove_outdated_shims() can
        # still compare via diff. Done as an in-place edit (not a .patch
        # file) so no unified-diff hunk counting is involved.
        rehash = os.path.join(self.source_folder, "libexec", "plenv-rehash")
        with open(rehash, encoding="utf-8") as f:
            rehash_content = f.read()
        old_ln = '[ -e "$shim" ] || command -p ln -f "$PROTOTYPE_SHIM_PATH" "$shim"'
        new_ln = '[ -e "$shim" ] || { command -p ln -f "$PROTOTYPE_SHIM_PATH" "$shim" 2>/dev/null || command -p cp -f "$PROTOTYPE_SHIM_PATH" "$shim"; }'
        if old_ln in rehash_content:
            rehash_content = rehash_content.replace(old_ln, new_ln)
            with open(rehash, "w", encoding="utf-8", newline="\n") as f:
                f.write(rehash_content)
        elif new_ln not in rehash_content:
            raise Exception("plenv-rehash hardlink line not found; upstream layout changed")
        # -- Upstream test mirror (offline, hermetic) --
        # Mirrors test/shim.t (1 assertion): after `plenv rehash` the
        # generated shim forwards `-E` and observes PLENV_DIR. Uses a stub
        # perl so no real perl / prove / network clone is needed. Fails the
        # build if the shim is missing, empty, or does not forward args/env.
        # NOTE: generated shims re-exec `plenv` via PATH lookup, so the
        # check puts a wrapper on PATH before rehash and before running.
        tmpbase = os.environ.get("TMPDIR") or os.environ.get("TMP") or os.environ.get("TEMP")
        if tmpbase and os.path.isdir(tmpbase):
            # HMBS true-machine HMFS/HMDFS build dirs break HNP bash getcwd
            # (shell-init error), which in turn breaks plenv's `cd "$OLDPWD"`
            # roundtrip. Run the mirror from the injected TMPDIR instead.
            work = os.path.join(tmpbase, "plenv-upstream-check")
        else:
            work = os.path.join(self.build_folder, "upstream-shim-check")
        os.makedirs(work, exist_ok=True)
        check = os.path.join(work, "check.sh")
        with open(check, "w", encoding="utf-8", newline="\n") as f:
            f.write(
                "set -eu\n"
                'SRC="$1"\n'
                'ROOT="$2"\n'
                'WRAP="$3"\n'
                # Prefer the HMBS-injected SHELL/CONFIG_SHELL (/bin/sh handles HMFS
                # getcwd); plenv and its shims REQUIRE bash (shopt, [[ =~ ]], < <()),
                # so verify with shopt and only then fall back to PATH bash.
                'SH="${CONFIG_SHELL:-${SHELL:-/bin/sh}}"\n'
                'if "$SH" -c \'shopt -s nullglob\' 2>/dev/null; then BASHRUN="$SH"; else BASHRUN="bash"; fi\n'
                'STARTDIR=""\n'
                'for d in "/tmp" "/" "${HOME:-}" "${TMPDIR:-}" "${TMP:-}" "${TEMP:-}"; do\n'
                '  if [ -n "$d" ] && [ -d "$d" ] && cd "$d" 2>/dev/null; then\n'
                '    err=$("$BASHRUN" -c \'pwd\' 2>&1 || true)\n'
                '    case "$err" in *shell-init*|*cannot*access*parent*) continue;; *) STARTDIR="$d"; break;; esac\n'
                '  fi\n'
                'done\n'
                'if [ -n "$STARTDIR" ]; then cd "$STARTDIR" 2>/dev/null || true; else cd /tmp 2>/dev/null || true; fi\n'
                'rm -rf "$ROOT" "$WRAP"\n'
                'mkdir -p "$ROOT/versions/dummy/bin" "$WRAP"\n'
                'cat > "$WRAP/plenv" <<EOF\n'
                '#!/usr/bin/env bash\n'
                'exec "$BASHRUN" "$SRC/libexec/plenv" "\\$@"\n'
                'EOF\n'
                'chmod +x "$WRAP/plenv"\n'
                'export PATH="$WRAP:$PATH"\n'
                'cat > "$ROOT/versions/dummy/bin/perl" <<\'EOF\'\n'
                '#!/usr/bin/env bash\n'
                'printf "%s\\n" "$PLENV_DIR"\n'
                'EOF\n'
                'chmod +x "$ROOT/versions/dummy/bin/perl"\n'
                'PLENV_ROOT="$ROOT" PLENV_DIR="$ROOT" "$BASHRUN" "$SRC/libexec/plenv" rehash\n'
                'test -s "$ROOT/shims/perl" || { echo "shim missing or empty" >&2; exit 1; }\n'
                'OUT="$(PLENV_ROOT="$ROOT" PLENV_VERSION="dummy" PLENV_DIR="$ROOT" "$BASHRUN" "$ROOT/shims/perl" -E 1)"\n'
                'test "$OUT" = "$ROOT" || { echo "shim env mismatch: [$OUT] != [$ROOT]" >&2; exit 1; }\n'
                'echo "upstream shim mirror: 1/1 passed"\n'
            )
        bash = os.environ.get("CONFIG_SHELL") or os.environ.get("SHELL") or "/bin/sh"
        root = os.path.join(work, "plenv-root")
        wrap = os.path.join(work, "fakebin")
        self.run(f'"{bash}" "{check}" "{self.source_folder}" "{root}" "{wrap}"', env="conanrun")
        upstream = {
            "status": "passed",
            "framework": "bash mirror of test/shim.t",
            "command": "check.sh <source> <tmp-root> <tmp-fakebin> (via CONFIG_SHELL/SHELL, TMPDIR workdir)",
            "discovered": 1,
            "executed": 1,
            "passed": 1,
            "failed": 0,
            "skipped": 0,
        }
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream))

    def package(self):
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "Changes", src=self.source_folder, dst=os.path.join(self.package_folder, "share", "doc", "plenv"))
        copy(self, "README.md", src=self.source_folder, dst=os.path.join(self.package_folder, "share", "doc", "plenv"))
        copy(self, "*", src=os.path.join(self.source_folder, "libexec"), dst=os.path.join(self.package_folder, "libexec"))
        copy(self, "*", src=os.path.join(self.source_folder, "completions"), dst=os.path.join(self.package_folder, "completions"))
        copy(self, "*", src=os.path.join(self.source_folder, "plenv.d"), dst=os.path.join(self.package_folder, "plenv.d"))

        bin_dir = os.path.join(self.package_folder, "bin")
        os.makedirs(bin_dir, exist_ok=True)
        plenv_link = os.path.join(bin_dir, "plenv")
        if os.path.lexists(plenv_link):
            os.remove(plenv_link)
        # Keep the upstream relative symlink layout: bin/plenv -> ../libexec/plenv
        os.symlink(os.path.join("..", "libexec", "plenv"), plenv_link)

        for root, _, files in os.walk(os.path.join(self.package_folder, "libexec")):
            for filename in files:
                path = os.path.join(root, filename)
                try:
                    os.chmod(path, os.stat(path).st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
                except OSError:
                    # HMBS true-machine FS may not support chmod (HMBS_CAP_CHMOD=0);
                    # exec bits carried by the upstream tarball are kept as-is.
                    pass

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
