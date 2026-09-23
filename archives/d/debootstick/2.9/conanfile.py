#!/usr/bin/env python3
"""Conan recipe - debootstick 2.9 (Makefile, shell tool).

debootstick turns a chroot environment into a bootable live image.
Pure bash + Makefile project: no configure script, no compilation,
no external dependencies. The recipe installs the version-stamped
script plus its scripts/ and disk-layouts/ data directories.
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class DebootstickConan(ConanFile):
    name = "debootstick"
    version = "2.9"
    description = "Turn a chroot environment into a bootable live image"
    license = "BSD-3-Clause"
    homepage = "https://github.com/drakkar-lig/debootstick"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    # No shared/static options: pure shell tool, no library artifact.

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Pure shell, libc only at runtime; no Conan dependencies.
        pass

    # Layout: repo-standard basic_layout (src/ + build/ separated).
    # Previous cycles pinned folders.source="." which aliased
    # source_folder to the build base (log: source_folder=.../b with
    # listing [build, conanbuild.sh, ..., debootstick-2.9]), mixing
    # generators with sources. basic_layout keeps them apart like the
    # dos2unix 7.5.4 reference recipe.
    def layout(self):
        basic_layout(self)

    def source(self):
        # Keep strip_root=False so get() never fails regardless of
        # whether the Debian tarball has a top-level dir or not; the
        # actual root is resolved at use time by _source_root().
        # Evidence: last preflight showed source_folder/.../b containing
        # a 'debootstick-2.9' subdir, i.e. the archive DOES carry a
        # top-level directory, so a flat-root assumption misses.
        get(self, **self.conan_data["sources"], strip_root=False)

    def validate(self):
        # R32: OHOS is a Linux-like platform, allow both.
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"OS {self.settings.os} not supported, requires Linux or OHOS"
            )

    def _ensure_writable_tmp(self):
        # HMBS [readonly_tmp]: /tmp is read-only on the device sandbox.
        # Reuse the injected writable dir (HMBS_TMPDIR/TMPDIR/TMP/TEMP)
        # so Conan's run wrappers and shell temp files avoid /tmp.
        cands = [
            os.environ.get("HMBS_TMPDIR"),
            os.environ.get("TMPDIR"),
            os.environ.get("TMP"),
            os.environ.get("TEMP"),
        ]
        chosen = None
        for c in cands:
            if c and os.path.isdir(c):
                chosen = c
                break
        if chosen is None:
            # Fall back to the build folder (always present & writable).
            # Use getattr: base_build_folder is unavailable in this
            # Conan build context (previous AttributeError).
            fallback_base = getattr(self, "build_folder", None) or os.getcwd()
            chosen = os.path.join(fallback_base, "hmbs-tmp")
            try:
                os.makedirs(chosen, exist_ok=True)
            except OSError:
                pass
        for var in ("TMPDIR", "TMP", "TEMP"):
            os.environ[var] = chosen
        self.output.info(f"[HMBS tmp] TMPDIR redirected to {chosen}")
        return chosen

    def _resolve_shell(self):
        # POSIX sh for generic wrappers (kept for compatibility).
        cands = [
            os.environ.get("SHELL"),
            shutil.which("sh"),
            "/bin/sh",
        ]
        for c in cands:
            if c and os.path.isfile(c) and os.access(c, os.X_OK):
                return c
        return "sh"

    def _source_root(self):
        # Resolve the real extraction root without touching
        # base_source_folder (missing attribute in this context).
        # Handles: (a) flat files at source_folder, (b) nested
        # source_folder/debootstick-2.9/, (c) any single subdir holding
        # the 'debootstick' launcher (recursive walk, depth <= 4).
        direct = os.path.join(self.source_folder, "debootstick")
        if os.path.isfile(direct):
            return self.source_folder
        nested = os.path.join(
            self.source_folder, f"{self.name}-{self.version}", "debootstick")
        if os.path.isfile(nested):
            return os.path.join(
                self.source_folder, f"{self.name}-{self.version}")
        try:
            for entry in sorted(os.listdir(self.source_folder)):
                cand_dir = os.path.join(self.source_folder, entry)
                if os.path.isdir(cand_dir) and os.path.isfile(
                        os.path.join(cand_dir, "debootstick")):
                    self.output.info(f"[HMBS src] using nested root {cand_dir}")
                    return cand_dir
        except OSError:
            pass
        # Recursive fallback (tarball shape drift).
        for root, _dirs, files in os.walk(self.source_folder):
            depth = root[len(self.source_folder):].count(os.sep)
            if depth > 4:
                continue
            if "debootstick" in files:
                self.output.info(f"[HMBS src] walk found root {root}")
                return root
        return self.source_folder

    def _find_source_entry(self, rel):
        root = self._source_root()
        primary = os.path.join(root, rel)
        if os.path.isfile(primary) or os.path.isdir(primary):
            return primary
        # Sibling-dir probe: check one level of subdirs before giving up.
        try:
            for entry in sorted(os.listdir(root)):
                cand = os.path.join(root, entry, os.path.basename(rel))
                if os.path.isfile(cand) or os.path.isdir(cand):
                    self.output.warning(
                        f"source entry '{rel}' found at fallback {cand}")
                    return cand
        except OSError:
            pass
        try:
            listing = sorted(os.listdir(self.source_folder))
        except OSError as e:
            listing = [f"<listdir failed: {e}>"]
        try:
            root_listing = sorted(os.listdir(root)) if root != self.source_folder else listing
        except OSError as e:
            root_listing = [f"<listdir failed: {e}>"]
        self.output.error(f"source entry '{rel}' not found; source_folder={self.source_folder} "
                          f"root={root} listing={listing} root_listing={root_listing}")
        raise ConanInvalidConfiguration(
            f"debootstick source entry '{rel}' missing after get(); "
            f"checked root={root}"
        )

    def build(self):
        # Upstream ships no test suite (Makefile all:/clean: are empty).
        # NOTE: shell -n on the launcher is an INVALID check here: the
        # script uses a `with <mount>; do ... done` DSL later in the file
        # (preflight: line 299 "unexpected 'do'") which no shell can
        # parse with -n (bash included), yet runtime --version/--help
        # exits in parse_args long before those lines are parsed. So the
        # launcher gets content validation (falsifiable: missing file,
        # empty file, or lost @VERSION@/CLI flags fail here), while only
        # the two pure-POSIX helpers sourced at startup get `sh -n`.
        self._ensure_writable_tmp()
        launcher = self._find_source_entry("debootstick")
        size = os.path.getsize(launcher)
        if size == 0:
            raise ConanInvalidConfiguration(
                f"debootstick launcher is empty: {launcher}")
        with open(launcher, encoding="utf-8") as f:
            content = f.read()
        for token in ("@VERSION@", "--help-os-support", "--version",
                      "parse_args"):
            if token not in content:
                raise ConanInvalidConfiguration(
                    f"debootstick launcher lost expected token {token!r}")
        self.output.info(f"[HMBS build] launcher content ok ({size} bytes)")
        shell = self._resolve_shell()
        for rel in (os.path.join("scripts", "create-image", "cmdline"),
                    os.path.join("scripts", "create-image", "os-detect")):
            target = self._find_source_entry(rel)
            self.run(f'"{shell}" -n "{target}"', env="conanbuild")

    def package(self):
        # Install the version-stamped launcher into bin/.
        # (Upstream Makefile does sed s/@VERSION@/<ver>/ at install time;
        #  replicate it here to avoid its chown-to-root and absolute
        #  /usr/share/doc mkdir steps.)
        launcher = self._find_source_entry("debootstick")
        with open(launcher, encoding="utf-8") as f:
            content = f.read()
        assert "@VERSION@" in content, "upstream launcher lost its @VERSION@ token"
        content = content.replace("@VERSION@", "2.9")
        # OHOS portability (no /bin/bash on target; HMBS SHELL=/bin/sh):
        # upstream resolves its dir via ${BASH_SOURCE[0]} which POSIX sh
        # cannot parse (arrays). $0 works identically under both bash and
        # sh for our `bash|sh bin/debootstick ...` invocations, and the
        # --version/--help/negative CLI paths exit before the `with` DSL
        # lines, so the installed launcher runs under either interpreter.
        for _tok in ("${BASH_SOURCE[0]}", "${BASH_SOURCE}", "$BASH_SOURCE"):
            if _tok in content:
                content = content.replace(_tok, "$0")
        assert "BASH_SOURCE" not in content, \
            "installed launcher must not reference BASH_SOURCE (no bash on OHOS)"
        bindir = os.path.join(self.package_folder, "bin")
        os.makedirs(bindir, exist_ok=True)
        installed = os.path.join(bindir, "debootstick")
        with open(installed, "w", encoding="utf-8", newline="\n") as f:
            f.write(content)
        try:
            os.chmod(installed, 0o755)
        except OSError as e:
            # HMDFS ignores chmod (HMBS_CAP_CHMOD=0); the script is
            # always invoked via an explicit interpreter, so a missing
            # +x bit must not fail packaging.
            self.output.warning(f"chmod 755 ignored/failed: {e}")

        # Canonical data location.
        share_base = os.path.join(self.package_folder, "share", "debootstick")
        copy(self, "*", src=os.path.join(self._source_root(), "scripts"),
             dst=os.path.join(share_base, "scripts"))
        copy(self, "*", src=os.path.join(self._source_root(), "disk-layouts"),
             dst=os.path.join(share_base, "disk-layouts"))

        # Fallback copies beside the binary: upstream resolves DBSTCK_DIR to
        # /usr/share/debootstick and otherwise to the script's own directory.
        # /usr/share/debootstick does not exist on consumer machines, so the
        # sibling copies keep the script working with zero source patches.
        copy(self, "*", src=os.path.join(self._source_root(), "scripts"),
             dst=os.path.join(bindir, "scripts"))
        copy(self, "*", src=os.path.join(self._source_root(), "disk-layouts"),
             dst=os.path.join(bindir, "disk-layouts"))

        # Manual page and docs.
        copy(self, "debootstick.8", src=self._source_root(),
             dst=os.path.join(self.package_folder, "share", "man", "man8"))
        copy(self, "README.md", src=self._source_root(),
             dst=os.path.join(self.package_folder, "share", "doc", "debootstick"))
        copy(self, "copyright", src=os.path.join(self._source_root(), "debian"),
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        # Command-line tool, not a library.
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
