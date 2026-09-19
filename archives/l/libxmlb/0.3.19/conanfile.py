#!/usr/bin/env python3
"""Conan recipe — libxmlb 0.3.19 (Meson).

libxmlb is a library to create and query compressed XML binary blobs
(used by fwupd). Ships libxmlb.so.2 plus the xb-tool CLI.

Platform notes (OHOS aarch64):
- glib 2.88.3 shared build: libxmlb exposes GObject types (xb_silo_get_type
  etc.); a static glib would double-register the GObject type system in any
  process that also loads a dynamic glib (glib-networking precedent).
- glib's installed .pc files are prefix=/ (conan meson --prefix=/ convention)
  and list static-only deps under Requires(.private); they are copied to a
  pc-fix dir (prefix rewritten to the glib package, spurious requires
  stripped) and put FIRST on PKG_CONFIG_PATH so meson resolves
  gio-2.0/gio-unix-2.0 through the real glib package.
- lzma/zstd are upstream "auto" features exercised by the upstream test suite
  (test.xml.xz / test.xml.zst) — enabled explicitly, not trimmed.
- meson install rewrites installed ELF files (DT_RUNPATH cleanup), breaking
  the lld link-time self-sign; every installed ELF is re-signed with
  binary-sign-tool after install (gtk/accountsservice pattern), and the
  versioned .so aliases are materialized as regular files (HMDFS-safe).
"""
import glob
import os
import re
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import cross_building
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, rmdir
from conan.tools.meson import Meson, MesonToolchain


class LibxmlbConan(ConanFile):
    name = "libxmlb"
    version = "0.3.19"
    description = "Library to create and query compressed XML binary blobs"
    license = "LGPL-2.1-or-later"
    homepage = "https://github.com/hughsie/libxmlb"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    # PkgConfigDeps emits liblzma.pc / libzstd.pc for the feature deps;
    # the glib family resolves through the pc-fix copies (see generate()).
    generators = "PkgConfigDeps"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("glib/2.88.3")
        self.requires("liblzma/5.8.1")
        self.requires("zstd/1.5.7.1")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        self.settings.rm_safe("compiler.cppstd")
        self.settings.rm_safe("compiler.libcxx")

    def layout(self):
        # meson_layout() was removed in conan 2.29.x; replicate its folders.
        self.folders.build = "builddir"
        self.folders.generators = "builddir/generators"

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # The CI worker exports AR/AS/STRIP/NM/RANLIB as llvm-* bare names that
        # are not on its PATH; meson's tool probing aborts at configure. Drop
        # the broken env values and pin the real tools by absolute path
        # (glib-networking / at-spi2-core precedent).
        for _var in ("AR", "AS", "STRIP", "NM", "RANLIB"):
            os.environ.pop(_var, None)
        tools = {
            name: shutil.which(name)
            for name in ("ar", "as", "strip", "nm", "ranlib")
        }
        missing = [name for name, path in tools.items() if path is None]
        if missing:
            raise ConanInvalidConfiguration(
                f"Required build tools not found in PATH: {', '.join(missing)}"
            )
        tc = MesonToolchain(self)
        tc.ar = tools["ar"]
        tc.as_ = tools["as"]
        # Do NOT strip installed artifacts: stripping rewrites the ELF and
        # invalidates the re-embedded .codesign (OHOS loader EPERM).
        tc.strip = None
        tc.binaries["nm"] = tools["nm"]
        tc.binaries["ranlib"] = tools["ranlib"]
        tc.project_options["default_library"] = (
            "shared" if self.options.shared else "static"
        )
        tc.project_options["wrap_mode"] = "nodownload"
        # g-ir-scanner / gtkdoc-scan are not available on OHOS workers; the
        # GIR is a binding artifact, not part of the C API surface.
        tc.project_options["introspection"] = "false"
        tc.project_options["gtkdoc"] = "false"
        # Upstream test suite runs on the OHOS target (xb-self-test).
        tc.project_options["tests"] = "true"
        # Upstream "auto" features, exercised by the test suite: keep enabled.
        tc.project_options["lzma"] = "enabled"
        tc.project_options["zstd"] = "enabled"
        # xb-tool CLI is part of the upstream deliverable (cli default true).
        tc.project_options["cli"] = "true"

        # glib pc-fix: PkgConfigDeps only emits .pc for components declared
        # in package_info; gio-unix-2.0.pc exists solely in the glib package
        # (lib/pkgconfig). Copy the real set, rewrite prefix (installed as
        # prefix=/), strip Requires(.private) entries that only apply to the
        # static-embedded internals (proxy-libintl/libpcre2-8/zlib/libffi);
        # the fixed copies win over the PkgConfigDeps-generated ones.
        extra_pc = []
        glib_pkg = self.dependencies["glib"].package_folder
        pc_fix_dir = os.path.join(self.build_folder, "glib-pc-fix")
        os.makedirs(pc_fix_dir, exist_ok=True)
        for pc in os.listdir(os.path.join(glib_pkg, "lib", "pkgconfig")):
            if not pc.endswith(".pc"):
                continue
            src = os.path.join(glib_pkg, "lib", "pkgconfig", pc)
            dst = os.path.join(pc_fix_dir, pc)
            with open(src, "r", encoding="utf-8") as fh:
                text = fh.read()
            text = re.sub(
                r"^prefix=.*$", f"prefix={glib_pkg}", text, count=1, flags=re.M
            )
            text = re.sub(
                r"^(Requires(?:\.private)?):\s*([^\n]*)$",
                lambda m: m.group(1) + ": "
                + re.sub(
                    r"\b(?:proxy-libintl|zlib|libpcre2-8|libffi)\b(?:\s*>=\s*[0-9.]+)?(?:\s*,\s*|\s*$)",
                    "",
                    m.group(2),
                ).strip().rstrip(",")
                if any(
                    t in m.group(2)
                    for t in ("proxy-libintl", "zlib", "libpcre2-8", "libffi")
                )
                else m.group(0),
                text,
                flags=re.M,
            )
            text = re.sub(
                r"^Requires\.private:\s*$", "Requires.private:", text, flags=re.M
            )
            with open(dst, "w", encoding="utf-8") as fh:
                fh.write(text)
        extra_pc.insert(0, pc_fix_dir)
        # pc-fix must win over the PkgConfigDeps-generated .pc files.
        tc.pkg_config_path = os.pathsep.join(extra_pc + [tc.pkg_config_path])
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()
        if cross_building(self):
            self.output.info(
                "cross-building: skip meson.test() (target binaries not runnable here)"
            )
            return
        if hasattr(os, "uname") and os.uname().sysname in ("OHOS", "HarmonyOS"):
            # Run the upstream suite natively on the OHOS target: xb-self-test
            # (49 g_test registrations; 2 more under --perf) resolves the
            # shared glib / zstd and the build-tree libxmlb.so.2 through
            # LD_LIBRARY_PATH; TMPDIR must be writable (root /tmp is RO).
            run_lib_dirs = []
            for dep in self.dependencies.host.values():
                if dep.package_folder:
                    for libdir in dep.cpp_info.libdirs:
                        if not os.path.isabs(libdir):
                            libdir = os.path.join(dep.package_folder, libdir)
                        if os.path.isdir(libdir):
                            run_lib_dirs.append(libdir)
            run_lib_dirs.append(os.path.join(self.build_folder, "src"))
            tmpdir = os.path.join(self.build_folder, "tmp")
            os.makedirs(tmpdir, exist_ok=True)
            ld_path = ":".join(dict.fromkeys(run_lib_dirs))
            self.run(
                'TMPDIR="{tmpdir}" LD_LIBRARY_PATH="{ld_path}:$LD_LIBRARY_PATH" '
                'meson test -v -C "{builddir}" --timeout-multiplier=16'.format(
                    tmpdir=tmpdir, ld_path=ld_path, builddir=self.build_folder
                )
            )
        else:
            meson.test()

    def package(self):
        meson = Meson(self)
        meson.install()
        if self.settings.os == "OHOS" and self.options.shared:
            self._materialize_shared_lib_aliases(
                os.path.join(self.package_folder, "lib")
            )
        # GNOME installed-tests infrastructure is not used on OHOS (glib
        # packaging drops it too); the suite already ran in build(). Note
        # conan's MesonToolchain remaps libexecdir to the bindir, so the
        # test binary/data land under bin/installed-tests.
        rmdir(self, os.path.join(self.package_folder, "bin", "installed-tests"))
        rmdir(self, os.path.join(self.package_folder, "share", "installed-tests"))
        rmdir(self, os.path.join(self.package_folder, "libexec", "installed-tests"))
        # xmlb.pc is installed with prefix=/ (conan meson convention);
        # rewrite it so consumers resolve the package location.
        pc_path = os.path.join(self.package_folder, "lib", "pkgconfig", "xmlb.pc")
        if os.path.isfile(pc_path):
            with open(pc_path, "r", encoding="utf-8") as fh:
                text = fh.read()
            text = re.sub(
                r"^prefix=.*$",
                f"prefix={self.package_folder}",
                text,
                count=1,
                flags=re.M,
            )
            with open(pc_path, "w", encoding="utf-8") as fh:
                fh.write(text)
        if self.settings.os == "OHOS":
            self._sign_installed_elfs()

    @staticmethod
    def _is_elf(path):
        try:
            with open(path, "rb") as stream:
                return stream.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _materialize_shared_lib_aliases(self, libdir):
        # meson installs libxmlb.so.2.0.0 with .so.2/.so symlinks; materialize
        # the aliases as regular copies (HMDFS symlink semantics, glib/gtk
        # packaging pattern). Signature stays valid (byte-identical copies).
        pattern = re.compile(r"^libxmlb[.]so[.](\d+)\.(\d+)\.(\d+)$")
        sources = []
        if os.path.isdir(libdir):
            for name in os.listdir(libdir):
                path = os.path.join(libdir, name)
                if (
                    pattern.fullmatch(name)
                    and os.path.isfile(path)
                    and not os.path.islink(path)
                ):
                    sources.append(path)
        if len(sources) != 1:
            raise ConanInvalidConfiguration(
                f"expected one versioned libxmlb shared object in {libdir!r}, "
                f"found {len(sources)}"
            )
        source = sources[0]
        for alias in ("libxmlb.so.2", "libxmlb.so"):
            target = os.path.join(libdir, alias)
            if os.path.lexists(target):
                os.unlink(target)
            shutil.copyfile(source, target)
            shutil.copymode(source, target)
            self.output.info(f"materialized shared-library alias {alias}")

    def _sign_installed_elfs(self):
        # meson install rewrites installed ELF files (DT_RUNPATH cleanup),
        # invalidating the lld link-time .codesign; OHOS loader then rejects
        # the file (EPERM). Re-sign every installed ELF with the self signer
        # (gtk/accountsservice pattern).
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        for tool in (objcopy, signer):
            if not os.path.isfile(tool):
                self.output.warning(
                    f"{tool} not found; installed ELF files left with the "
                    "link-time signature"
                )
                return
        targets = []
        for pattern in (
            os.path.join(self.package_folder, "bin", "*"),
            os.path.join(self.package_folder, "lib", "**", "*.so"),
            os.path.join(self.package_folder, "lib", "**", "*.so.*"),
        ):
            targets.extend(glob.glob(pattern, recursive=True))
        signed = 0
        for target in sorted(set(targets)):
            if not os.path.isfile(target) or os.path.islink(target):
                continue
            if not self._is_elf(target):
                continue
            self.run(f'"{objcopy}" --remove-section .codesign "{target}" 2>/dev/null || true')
            self.run(
                f'"{signer}" sign -inFile "{target}" -outFile "{target}" -selfSign 1'
            )
            signed += 1
        self.output.info(f"PACKAGE_CODESIGN=PASS signed_elfs={signed}")

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "libxmlb")
        self.cpp_info.set_property("cmake_target_name", "libxmlb::libxmlb")
        self.cpp_info.set_property("pkg_config_name", "xmlb")
        # xb-tool CLI ships in bin/ (R38/L0k: commands.json declares the tool)
        self.cpp_info.bindirs = ["bin"]

        lib = self.cpp_info.components["libxmlb"]
        lib.libs = ["xmlb"]
        lib.includedirs = ["include/libxmlb-2"]
        lib.libdirs = ["lib"]
        # glib 2.88.3 declares components named glib/gobject/gio (their
        # pkg_config_name properties map to glib-2.0/gio-2.0 .pc files).
        lib.requires = [
            "glib::glib",
            "glib::gobject",
            "glib::gio",
            "liblzma::liblzma",
            "zstd::zstd",
        ]
        lib.set_property("cmake_target_name", "libxmlb::libxmlb")
        lib.set_property("pkg_config_name", "xmlb")
        if self.settings.os in ("Linux", "OHOS"):
            lib.system_libs = ["m", "pthread"]
        if self.settings.os == "OHOS" and self.options.shared:
            self.runenv_info.prepend_path(
                "LD_LIBRARY_PATH", os.path.join(self.package_folder, "lib")
            )
