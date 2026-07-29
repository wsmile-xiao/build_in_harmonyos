#!/usr/bin/env python3
"""Conan recipe for flex — Fast Lexical Analyzer Generator.

flex generates scanners (tokenizers) for pattern matching.
常与 bison/yacc 配合使用。

Build system: autotools
Dependencies: 无外部依赖（可选 bison 用于 flex 自身构建）
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy
from conan.tools.layout import basic_layout
from conan.tools.gnu import Autotools, AutotoolsToolchain


class FlexConan(ConanFile):
    name = "flex"
    version = "2.6.4"
    description = "Fast Lexical Analyzer Generator — generates scanners (tokenizers) for pattern matching"
    license = "BSD-2-Clause"
    homepage = "https://github.com/westes/flex"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    @staticmethod
    def _arch_to_gnu(arch):
        """Map Conan arch to GNU triplet machine component."""
        return {
            "x86_64": "x86_64",
            "x86": "i686",
            "armv8": "aarch64",
            "armv8_3": "aarch64",
            "armv8_aes": "aarch64",
            "armv8_sha": "aarch64",
            "armv8_crypto": "aarch64",
            "armv9": "aarch64",
            "armv9_aes": "aarch64",
            "armv9_sha": "aarch64",
            "armv9_crypto": "aarch64",
            "riscv64": "riscv64",
            "s390x": "s390x",
            "ppc64le": "powerpc64le",
        }.get(str(arch), str(arch))

    def generate(self):
        tc = AutotoolsToolchain(self)
        if self.settings.os == "OHOS":
            tc.extra_ldflags.append("-static")
            machine = self._arch_to_gnu(self.settings.arch)
            triplet = f"{machine}-unknown-linux-gnu"
            tc.configure_args.append(f"--host={triplet}")
            tc.configure_args.append(f"--build={triplet}")
            tc.configure_args.append("ac_cv_func_reallocarray=no")
        tc.generate()

    @staticmethod
    def _patch_configure_for_hmdfs(configure_path):
        """Inject `chmod 644` after every $ac_tmp/*.awk creation in the
        configure template, so the generated config.status makes the awk
        scripts readable on HMDFS (which otherwise gives heredoc-created
        files mode 000, breaking `sed < subs1.awk` with Permission denied).

        Three awk files flow through config.status:
          subs1.awk  -> subs.awk  (used by $AWK -f subs.awk)
          defines.awk              (used by $AWK -f defines.awk)

        All creation/reading points live inside `configure` itself
        (some as plain code, most inside `cat >>$CONFIG_STATUS <<_ACEOF`
        heredocs that become config.status's body). Patching `configure`
        once fixes both configure-time and config.status-time reads.
        """
        with open(configure_path, encoding="utf-8") as f:
            src = f.read()

        # Idempotency guard: if any chmod already present, the patch was
        # applied on a previous `conan create` (source_folder is cached).
        # Exit early to avoid a missed-anchor RuntimeError on repeat builds.
        if 'chmod 644 "$ac_tmp/subs1.awk"' in src:
            return

        # Insert `chmod 644 "$ac_tmp/<name>.awk"` after each creation point.
        # Anchor on the exact unique lines from the upstream 2.6.4 template.
        # `names[i]` is the awk filename each anchor guards, for error reporting.
        names = ["subs1.awk", "subs.awk"]
        replacements = [
            # subs1.awk — first line written by configure itself
            ('echo \'BEGIN {\' >"$ac_tmp/subs1.awk" &&',
             'echo \'BEGIN {\' >"$ac_tmp/subs1.awk" &&\nchmod 644 "$ac_tmp/subs1.awk" &&'),
            # subs.awk — converted from subs1.awk inside a config.status heredoc
            ('fi < "$ac_tmp/subs1.awk" > "$ac_tmp/subs.awk" \\\n'
             '  || as_fn_error $? "could not setup config files machinery" "$LINENO" 5',
             'chmod 644 "$ac_tmp/subs1.awk"\n'
             'fi < "$ac_tmp/subs1.awk" > "$ac_tmp/subs.awk" \\\n'
             '  || as_fn_error $? "could not setup config files machinery" "$LINENO" 5\n'
             'chmod 644 "$ac_tmp/subs.awk"'),
        ]

        patched = src
        missed = []
        for i, (old, _new) in enumerate(replacements):
            if old in patched:
                patched = patched.replace(old, replacements[i][1], 1)
            else:
                # Anchor drifted upstream — record for the error below.
                missed.append(names[i])

        if missed:
            raise RuntimeError(
                "configure template patches missed anchors for: "
                + ", ".join(missed)
                + " — upstream template may have changed; verify configure "
                  "lines around subs1.awk/subs.awk/defines.awk creation"
            )

        with open(configure_path, "w", encoding="utf-8") as f:
            f.write(patched)

    def build(self):
        apply_conandata_patches(self)

        autotools = Autotools(self)

        if self.settings.os == "OHOS":
            # HMDFS workaround: configure's tmp-dir awk scripts get mode 000
            # on HMDFS (heredoc-created), so config.status dies on the first
            # `sed < subs1.awk` with "Permission denied". Patch 0006 already
            # moves the tmp dir to ${TMPDIR:-/tmp} and chmods the dir itself;
            # here we additionally inject chmod on the awk *files* before
            # configure runs (so the chmods flow into the generated
            # config.status template and apply at read time).
            #
            # Patch BOTH source_folder (cached copy) and build_folder
            # (working copy).  Conan 2.x copies sources from source_folder
            # to build_folder BEFORE build() is called, so patching only
            # source_folder leaves the build_folder's configure unmodified.
            for folder in (self.source_folder, self.build_folder):
                configure_path = os.path.join(folder, "configure")
                if os.path.isfile(configure_path):
                    self._patch_configure_for_hmdfs(configure_path)

            # conanbuild.sh (generated by AutotoolsToolchain) may override
            # TMPDIR to the build folder (on HMDFS).  Restore the original
            # system TMPDIR (/data/storage/el2/base/cache on /data
            # partition, typically ext4/f2fs — NOT HMDFS) so heredoc-created
            # awk files get normal permissions instead of mode 000.
            os.environ["TMPDIR"] = "/data/storage/el2/base/cache"
            old_umask = os.umask(0o022)
            try:
                autotools.configure()
            finally:
                os.umask(old_umask)
        else:
            autotools.configure()

        # CI lacks texinfo (makeinfo), causing doc/ to fail.  Only
        # src/ is needed for packaging (flex binary, libfl.a, headers).
        autotools.make(args=["SUBDIRS=src"])

    def package(self):
        build_src = os.path.join(self.build_folder, "src")
        lib_dir = os.path.join(build_src, ".libs")
        # flex binary may be a libtool wrapper in src/; copy the real binary from .libs/ if it exists
        flex_src = lib_dir if os.path.isdir(lib_dir) else build_src
        copy(self, "flex", flex_src, os.path.join(self.package_folder, "bin"),
             keep_path=False)
        # libfl.a may also be in .libs/ (libtool) or build_src (plain make)
        libfl_src = lib_dir if os.path.isdir(lib_dir) else build_src
        copy(self, "libfl.a", libfl_src, os.path.join(self.package_folder, "lib"),
             keep_path=False)
        copy(self, "FlexLexer.h", os.path.join(self.source_folder, "src"),
             os.path.join(self.package_folder, "include"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = ["fl"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = ["include"]
