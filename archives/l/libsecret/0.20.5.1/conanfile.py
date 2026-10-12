#!/usr/bin/env python3
"""Conan recipe — libsecret 0.20.5.1 (Meson).

GObject-based secret storage client library (freedesktop.org Secrets API).
Builds the C library + libegg; introspection/vapi/tpm2 disabled (no tss2/gjs in CI).
"""
import os
import shutil
import stat
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import PkgConfigDeps
from conan.tools.meson import Meson, MesonToolchain


class LibsecretConan(ConanFile):
    name = "libsecret"
    version = "0.20.5.1"
    description = "GObject based library for accessing the Secret Service API"
    license = "LGPL-2.1-or-later"
    homepage = "https://gitlab.gnome.org/GNOME/libsecret"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False], "gcrypt": [True, False]}
    default_options = {"shared": True, "fPIC": True, "gcrypt": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("glib/2.88.3")
        # glib-2.0.pc Requires: proxy-libintl + libpcre2-8; meson resolves the
        # .pc chain via pkg-config, so both must be direct dependencies too.
        self.requires("proxy-libintl/0.5")
        self.requires("pcre2/10.47")
        # gobject-2.0.pc Requires: libffi
        self.requires("libffi/3.5.2")
        # gio-2.0.pc Requires: zlib
        self.requires("zlib/1.3.2")
        # libgcrypt.pc Requires.private: gpg-error; gcrypt.h includes
        # gpg-error.h unconditionally, so expose libgpg-error directly.
        self.requires("libgpg-error/1.55")
        if self.options.gcrypt:
            self.requires("libgcrypt/1.12.2")

    def build_requirements(self):
        # Build tool must come from the Conan graph: CI workers and the local
        # sandbox do not ship a global `meson` on PATH, and R33 forbids relying
        # on an undefined shell environment. The repo's standard
        # tool_requires is meson/1.11.0 (same pin as cairo / c-* recipes).
        self.tool_requires("meson/1.11.0")

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def layout(self):
        self.folders.source = "."
        self.folders.build = "build"
        self.folders.generators = "build"

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # R33: meson resolves its static archiver from $AR. A bare, inherited
        # "AR=llvm-ar" (leaks from the CI/agent shell) makes every meson
        # project() call die with `Unknown linker(s): [['llvm-ar']]` because the
        # conan subprocess cannot resolve that name. Normalise it to an absolute
        # tool that exists, or drop it entirely — and pin it in the meson
        # [binaries] section so the value never depends on the shell.
        ar_path = self._resolve_archiver()
        if ar_path:
            os.environ["AR"] = ar_path
        else:
            os.environ.pop("AR", None)
        # Expose glib/libgcrypt via pkg-config so meson finds glib-2.0 etc.
        PkgConfigDeps(self).generate()
        # glib package ships its own full set of .pc (incl. gio-unix-2.0);
        # copy the .pc files into the generators folder so meson resolves
        # every glib component, rewriting their "prefix=/" to the real
        # package folder (upstream ships them with a root prefix).
        import re as _re
        for dep in self.dependencies.values():
            if not dep.package_folder:
                continue
            src_pc = os.path.join(dep.package_folder, "lib", "pkgconfig")
            if os.path.isdir(src_pc):
                real_prefix = dep.package_folder.replace(os.sep, "/")
                for pc_name in os.listdir(src_pc):
                    if not pc_name.endswith(".pc"):
                        continue
                    with open(os.path.join(src_pc, pc_name), encoding="utf-8") as handle:
                        content = handle.read()
                    rewritten = _re.sub(
                        r"^prefix=.*$", "prefix={}".format(real_prefix),
                        content, flags=_re.MULTILINE,
                    )
                    with open(
                        os.path.join(self.generators_folder, pc_name),
                        "w", encoding="utf-8", newline="\n",
                    ) as handle:
                        handle.write(rewritten)
        # libgcrypt.pc only lists gpg-error under Requires.private, so
        # pkg-config does not propagate its Cflags — gcrypt.h includes
        # gpg-error.h unconditionally. Append the gpg-error include dir.
        gp_err_dep = self.dependencies.get("libgpg-error")
        libgcrypt_pc = os.path.join(self.generators_folder, "libgcrypt.pc")
        if gp_err_dep and gp_err_dep.package_folder and os.path.isfile(libgcrypt_pc):
            gp_err_inc = os.path.join(gp_err_dep.package_folder, "include")
            with open(libgcrypt_pc, encoding="utf-8") as handle:
                content = handle.read()
            if "-I{}".format(gp_err_inc) not in content:
                rewritten = _re.sub(
                    r"^(Cflags:.*)$",
                    r"\1 -I{}".format(gp_err_inc),
                    content,
                    count=1,
                    flags=_re.MULTILINE,
                )
                with open(libgcrypt_pc, "w", encoding="utf-8", newline="\n") as handle:
                    handle.write(rewritten)
        # proxy-libintl ships only libintl.a/libintl.h (no .pc), but
        # glib-2.0.pc has "Requires: proxy-libintl" — synthesize it.
        intl_dep = self.dependencies.get("proxy-libintl")
        if intl_dep and intl_dep.package_folder:
            intl_prefix = intl_dep.package_folder.replace(os.sep, "/")
            with open(
                os.path.join(self.generators_folder, "proxy-libintl.pc"),
                "w",
                encoding="utf-8",
                newline="\n",
            ) as handle:
                handle.write(
                    "prefix={}\n".format(intl_prefix)
                    + "libdir=${prefix}/lib\n"
                    + "includedir=${prefix}/include\n\n"
                    + "Name: proxy-libintl\n"
                    + "Description: Minimal gettext-compatible proxy library\n"
                    + "Version: 0.5\n"
                    + "Libs: -L${libdir} -lintl\n"
                    + "Cflags: -I${includedir}\n"
                )
        # PkgConfigDeps-generated glib*.pc files carry broken tool variables
        # ("//bin/gdbus-codegen", "//bin/glib-mkenums"); repoint each at the
        # real script inside the resolved glib package.
        glib_dep = self.dependencies.get("glib")
        if glib_dep and glib_dep.package_folder:
            tool_scripts = {
                "gdbus_codegen": "gdbus-codegen",
                "glib_mkenums": "glib-mkenums",
                "glib_genmarshal": "glib-genmarshal",
                "gdbus": "gdbus",
            }
            import re as _re
            for pc_file in os.listdir(self.generators_folder):
                if not pc_file.endswith(".pc"):
                    continue
                pc_path = os.path.join(self.generators_folder, pc_file)
                with open(pc_path, encoding="utf-8") as handle:
                    content = handle.read()
                rewritten = content
                for var, script in tool_scripts.items():
                    real = os.path.join(glib_dep.package_folder, "bin", script)
                    if os.path.isfile(real):
                        rewritten = _re.sub(
                            r"^{}=.*$".format(var),
                            "{}={}".format(var, real),
                            rewritten,
                            flags=_re.MULTILINE,
                        )
                if rewritten != content:
                    with open(pc_path, "w", encoding="utf-8", newline="\n") as handle:
                        handle.write(rewritten)
        tc = MesonToolchain(self)
        if ar_path:
            # Pin the archiver in the meson [binaries] section too: the
            # machine-file value wins over anything in the shell environment.
            tc.binaries["ar"] = ar_path
        tc.project_options["default_library"] = (
            "shared" if self.options.shared else "static"
        )
        # R49: keep everything inside the Conan build folder (private prefix)
        tc.project_options["introspection"] = "false"
        tc.project_options["vapi"] = "false"
        tc.project_options["gcrypt"] = "true" if self.options.gcrypt else "false"
        tc.project_options["tpm2"] = "false"
        tc.project_options["bash_completion"] = "disabled"
        tc.project_options["manpage"] = "false"
        tc.project_options["gtk_doc"] = "false"
        tc.generate()

    def build(self):
        # meson/ninja come from tool_requires (see build_requirements), so no
        # runtime "pip install" fallback is needed. The ELF signing fix lives in
        # package() (_resign_ohos_elfs), after meson install has rewritten the
        # RPATHs — see the docstring there for the E077 background.
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        meson = Meson(self)
        meson.install()
        self._resign_ohos_elfs()

    # --------------------------------------------------------------- ELF sign
    def _resign_ohos_elfs(self):
        """E077 / ML-0043: re-sign the ELFs that `meson install` invalidated.

        The OHOS linker self-signs every ELF it produces (a 4 KiB ``.codesign``
        section) and the HarmonyOS loader refuses to map/exec an ELF whose
        signature does not verify (``dlopen`` -> EACCES "Permission denied",
        exec -> "Operation not permitted").  ``meson install`` rewrites the
        RPATH of every installed target with patchelf, which silently
        invalidates that signature.  Upstream libsecret's meson build always
        installs its shared library and its ``secret-tool`` executable with a
        rewritten RPATH, so *every* artifact this recipe ships is affected.

        That is exactly the defect the published ``libsecret/0.20.5`` binary
        shipped with, and why it had to be re-built as ``0.20.5.1``.

        Order matters (four-step post-install flow): strip the stale
        ``.codesign`` -> re-sign with ``binary-sign-tool -selfSign 1`` ->
        restore the exec bit.  Tools come from the Conan toolchain
        configuration / the OHOS SDK, never from an undefined shell variable
        (R33); subprocess is used in list form so no ``/bin/sh`` temp file is
        needed (``/tmp`` is read-only on OHOS, E002).
        """
        targets = []
        for subdir in ("lib", "bin"):
            for dirpath, _dirnames, filenames in os.walk(
                os.path.join(self.package_folder, subdir)
            ):
                for name in filenames:
                    path = os.path.join(dirpath, name)
                    # Sign each real object exactly once; the SONAME symlinks
                    # (libsecret-1.so, libsecret-1.so.0) follow the real file.
                    if os.path.islink(path) or not os.path.isfile(path):
                        continue
                    with open(path, "rb") as handle:
                        if handle.read(4) != b"\x7fELF":
                            continue
                        blob = handle.read()
                    # Only OHOS-toolchain ELFs carry these sections; a plain
                    # glibc/Linux build has neither and needs no re-signing.
                    if b".codesign" not in blob and b".note.ohos.ident" not in blob:
                        continue
                    targets.append(path)
        if not targets:
            self.output.info("PACKAGE_CODESIGN: no OHOS ELF in package, nothing to do")
            return

        objcopy = self._find_ohos_tool("llvm-objcopy")
        signer = self._find_ohos_tool("binary-sign-tool")
        if not objcopy or not signer:
            raise ConanException(
                "PACKAGE_CODESIGN: package contains OHOS ELFs "
                "({}) but llvm-objcopy/binary-sign-tool were not found; "
                "the produced artifact would be rejected by the OHOS loader "
                "with EACCES".format(", ".join(os.path.basename(t) for t in targets))
            )

        for path in targets:
            mode = stat.S_IMODE(os.stat(path).st_mode)
            subprocess.run(
                [objcopy, "--remove-section", ".codesign", path],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=120,
            )
            signed = path + ".codesign.tmp"
            subprocess.run(
                [signer, "sign", "-inFile", path, "-outFile", signed,
                 "-selfSign", "1"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                timeout=120, check=True,
            )
            os.replace(signed, path)
            os.chmod(path, mode | 0o755)
        self.output.info(
            "PACKAGE_CODESIGN: re-signed {} OHOS ELF(s): {}".format(
                len(targets), ", ".join(sorted(os.path.basename(t) for t in targets))
            )
        )

    def _resolve_archiver(self):
        """Absolute path of the static archiver meson should use, or "".

        R33: never hand a shell-derived name to the build. Either we have an
        existing absolute tool, or we drop $AR and let meson auto-detect.
        """
        candidates = []
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        compiler = executables.get("c") or ""
        if compiler:
            candidates.append(
                os.path.join(os.path.dirname(os.path.normpath(compiler)), "llvm-ar")
            )
        candidates += ["/data/service/hnp/bin/llvm-ar", "/data/service/hnp/bin/ar"]
        candidates += [shutil.which("llvm-ar") or "", shutil.which("ar") or ""]
        for candidate in candidates:
            if candidate and os.path.isfile(candidate) and os.access(candidate, os.X_OK):
                return os.path.abspath(candidate)
        return ""

    def _find_ohos_tool(self, name):
        """Locate an OHOS SDK tool without depending on shell env (R33)."""
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        compiler = executables.get("c") or ""
        candidates = []
        if compiler:
            candidates.append(
                os.path.join(os.path.dirname(os.path.normpath(compiler)), name)
            )
        candidates.append(os.path.join("/data/service/hnp/bin", name))
        candidates.append(shutil.which(name) or "")
        for candidate in candidates:
            if candidate and os.path.isfile(candidate) and os.access(candidate, os.X_OK):
                return os.path.abspath(candidate)
        return None

    def package_info(self):
        # libegg is an internal static lib linked into libsecret-1 and is
        # not installed by meson; consumers only need secret-1.
        self.cpp_info.libs = ["secret-1"]
        self.cpp_info.includedirs = ["include/libsecret-1"]
        # The package also ships the `secret-tool` CLI (meson installs it to
        # bin/), so declare bindirs explicitly — R38 requires a software-level
        # commands.json for CLI-bearing packages (archives/l/libsecret/
        # commands.json lists this version).
        self.cpp_info.bindirs = ["bin"]
        if self.options.shared and str(self.settings.os) in ("Linux", "OHOS"):
            self.runenv_info.prepend_path(
                "LD_LIBRARY_PATH", os.path.join(self.package_folder, "lib")
            )
        # Propagate dependency targets so consumers get glib include/link paths
        # (cpp_info.requires uses the recipe name, not cmake_file_name)
        self.cpp_info.requires = [
            "glib::glib", "glib::gobject", "glib::gio", "glib::gmodule",
            "glib::gthread", "proxy-libintl::proxy-libintl",
            # direct deps required to be referenced (pkg-config chain carriers)
            "pcre2::pcre2", "libffi::libffi", "zlib::zlib", "libgpg-error::libgpg-error",
        ]
        if self.options.gcrypt:
            self.cpp_info.requires.append("libgcrypt::libgcrypt")
