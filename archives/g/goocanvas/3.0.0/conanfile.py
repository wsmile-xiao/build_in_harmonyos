#!/usr/bin/env python3
"""Conan recipe — goocanvas 3.0.0 (Autotools, GTK+3 canvas widget, library).

Product: libgoocanvas-3.0.so (pkg-config name: goocanvas-3.0).

Dependency strategy (same as published gtkdatabox/1.0.0):
- The GTK+3 stack (gtk+, glib, pango, gdk-pixbuf, atk, epoxy, fribidi,
  harfbuzz, fontconfig, freetype, pixman, libpng, libjpeg-turbo, zlib) is
  pulled from the OHOS system prefix (cmd-pkgs ohos-aarch64 packages) into
  ~/usr/local at build time when missing.
- Conan-managed deps are only the ones the system prefix does NOT ship:
  cairo/1.18.4 + cairo-gobject/1.18.4 (system gtk+-3.0.pc Requires cairo,
  cairo-gobject; the system prefix has no cairo).
"""
import glob
import os
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.env import Environment
from conan.tools.build import can_run
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
    load,
    save,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class GooCanvasConan(ConanFile):
    name = "goocanvas"
    version = "3.0.0"
    description = "A canvas widget for GTK+ that uses cairo for drawing"
    license = "LGPL-2.0-or-later"
    homepage = "https://wiki.gnome.org/Projects/GooCanvas"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        # GTK+3 stack (gtk+/glib/pango/gdk-pixbuf/atk/...) comes from the OHOS
        # system prefix (cmd-pkgs), see _ensure_system_deps().
        # System prefix ships no cairo, so cairo + cairo-gobject are conan deps
        # (both published on ohpcd, verified with conan download --only-recipe).
        self.requires(
            "cairo/1.18.4", transitive_headers=True, transitive_libs=True
        )
        self.requires(
            "cairo-gobject/1.18.4",
            transitive_headers=True,
            transitive_libs=True,
        )

    def layout(self):
        basic_layout(self)

    def source(self):
        sources = dict(self.conan_data["sources"])
        mirror_url = sources.pop("mirror_url", None)
        try:
            get(self, **sources, strip_root=True)
        except Exception as error:
            if not mirror_url:
                raise
            self.output.warning(
                "Primary source failed (%s), trying mirror", error
            )
            get(self, url=mirror_url, sha256=sources["sha256"], strip_root=True)

    def generate(self):
        PkgConfigDeps(self).generate()
        tools_folder = self._prepare_glib_build_tools()
        self._augment_glib_pkg_config(tools_folder)
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend(
            [
                "--disable-introspection",
                "--disable-python",
                "--disable-gtk-doc",
                "--disable-gtk-doc-html",
                "--disable-gtk-doc-pdf",
            ]
        )
        tc.generate()

    def _glib_tools_folder(self):
        return os.path.join(self.build_folder, "conan-native-tools")

    def _find_good_python(self):
        """Locate a python3 interpreter with a complete stdlib.

        The hnp python3 (first on the build PATH) lacks modules such as
        'math', so glib-mkenums/glib-genmarshal cannot run under it.
        Prefer the healthy 3.12.9 interpreter in the user's local prefix.
        """
        candidates = [
            os.path.expanduser("~/usr/local/bin/python3"),
            "/usr/local/bin/python3",
            shutil.which("python3"),
        ]
        for candidate in candidates:
            if not candidate or not os.path.isfile(candidate):
                continue
            try:
                self.run(
                    "{} -c 'import math, tempfile, random'".format(
                        shlex.quote(candidate)
                    ),
                    ignore_errors=True,
                )
                return candidate
            except Exception:
                continue
        raise ConanException(
            "No python3 with a complete stdlib found for glib codegen tools"
        )

    def _prepare_glib_build_tools(self):
        glib_bin = os.path.join(
            self.dependencies["glib"].package_folder, "bin"
        )
        tools_folder = self._glib_tools_folder()
        os.makedirs(tools_folder, exist_ok=True)
        python = self._find_good_python()
        for tool in ("glib-mkenums", "glib-genmarshal"):
            script = os.path.join(glib_bin, tool)
            if not os.path.isfile(script):
                raise FileNotFoundError("GLib build tool is missing: %s" % script)
            wrapper = os.path.join(tools_folder, tool)
            with open(wrapper, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(
                    "#!/bin/sh\nexec {} {} \"$@\"\n".format(
                        shlex.quote(python), shlex.quote(script)
                    )
                )
            os.chmod(wrapper, 0o755)
        return tools_folder

    def _augment_glib_pkg_config(self, tools_folder):
        """Expose glib codegen tools through the generated glib-2.0.pc.

        goocanvas configure reads `$PKG_CONFIG --variable=glib_mkenums` /
        `--variable=glib_genmarshal` from glib-2.0.pc. The PkgConfigDeps
        generated pc file omits these variables, leaving the build rules
        empty. Add them pointing at python wrapper scripts (the hnp python
        cannot run the upstream glib python scripts).
        """
        pkg_config = os.path.join(self.generators_folder, "glib-2.0.pc")
        if not os.path.isfile(pkg_config):
            self.output.warning(
                "PkgConfigDeps output is missing: glib-2.0.pc"
            )
            return
        content = load(self, pkg_config)
        if "glib_mkenums" in content:
            return
        variable_block = "".join(
            "{name}={value}\n".format(name=name, value=value)
            for name, value in (
                ("glib_genmarshal", os.path.join(tools_folder, "glib-genmarshal")),
                ("gobject_query", os.path.join(tools_folder, "gobject-query")),
                ("glib_mkenums", os.path.join(tools_folder, "glib-mkenums")),
            )
        )
        marker = "\nName:"
        if marker not in content:
            raise ValueError(
                "Invalid PkgConfigDeps output: glib-2.0.pc has no Name field"
            )
        content = content.replace(marker, "\n" + variable_block + marker, 1)
        save(self, pkg_config, content, encoding="utf-8")
        self.output.info("Augmented conan glib-2.0.pc with codegen tool variables")

    def build(self):
        apply_conandata_patches(self)
        if str(self.settings.os) == "OHOS":
            self._ensure_system_deps()
            self._patch_config_sub(os.path.join(self.source_folder, "config.sub"))
            self._patch_config_guess(os.path.join(self.source_folder, "config.guess"))
            self._patch_config_status_tmpdir()
        envvars = self._system_env().vars(self)
        with envvars.apply():
            autotools = Autotools(self)
            autotools.configure()
            autotools.make(args=["-j1"])

    def package(self):
        envvars = self._system_env().vars(self)
        with envvars.apply():
            autotools = Autotools(self)
            autotools.install()
        self._sanitize_installed_pc()
        if str(self.settings.os) == "OHOS" and self.options.shared:
            self._sign_shared_libs()

    def _sanitize_installed_pc(self):
        pc_path = os.path.join(
            self.package_folder, "lib", "pkgconfig", "goocanvas-3.0.pc"
        )
        if not os.path.isfile(pc_path):
            self.output.warning("Installed goocanvas-3.0.pc not found at {}".format(pc_path))
            return
        content = load(self, pc_path)
        lines = []
        for line in content.splitlines():
            if line.startswith("prefix="):
                lines.append("prefix={}".format(self.package_folder))
                continue
            if line.startswith("libdir="):
                lines.append("libdir=${prefix}/lib")
                continue
            if line.startswith("includedir="):
                lines.append("includedir=${prefix}/include")
                continue
            lines.append(line)
        save(self, pc_path, "\n".join(lines) + "\n")
        self.output.info("Sanitized installed goocanvas-3.0.pc")

    def package_info(self):
        self.cpp_info.libs = ["goocanvas-3.0"]
        self.cpp_info.includedirs = ["include/goocanvas-3.0", "include"]
        self.cpp_info.set_property("cmake_file_name", "goocanvas")
        self.cpp_info.set_property("cmake_target_name", "goocanvas::goocanvas")
        self.cpp_info.set_property("pkg_config_name", "goocanvas-3.0")
        if str(self.settings.os) in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m", "pthread", "dl"]

    # ------------------------------------------------------------------
    # OHOS system GTK+ stack helpers (mirror gtkdatabox/1.0.0 recipe)
    # ------------------------------------------------------------------

    def _patch_config_sub(self, config_sub):
        """Accept the linux-ohos kernel-OS triplet on this Autotools release."""
        content = load(self, config_sub)
        if "linux-ohos" in content:
            self.output.info("config.sub already accepts linux-ohos")
            return
        patterns = [
            (
                "linux-gnu* | linux-dietlibc* | linux-android* | linux-newlib* "
                "| linux-musl* | linux-uclibc* )",
                "linux-gnu* | linux-dietlibc* | linux-android* | linux-newlib* "
                "| linux-musl* | linux-ohos* | linux-uclibc* )",
            ),
            (
                " | qnx* | emx*)",
                " | qnx* | emx* | ohos*)",
            ),
            (
                "linux-musl* | linux-uclibc* | uclinux-uclibc*",
                "linux-musl* | linux-ohos* | linux-uclibc* | uclinux-uclibc*",
            ),
            (
                "| -linux-newlib* | -linux-musl* | -linux-uclibc* \\",
                "| -linux-newlib* | -linux-musl* | -linux-ohos* | -linux-uclibc* \\",
            ),
        ]
        applied = False
        for target, replacement in patterns:
            if target in content:
                content = content.replace(target, replacement, 1)
                applied = True
        ohos_case = (
            "\t-linux-ohos*)\n"
            "\t\tos=-linux-ohos\n"
            "\t\t;;\n"
        )
        anchor = "\t-linux*)\n"
        if anchor in content:
            content = content.replace(anchor, ohos_case + anchor, 1)
            applied = True
        if not applied:
            raise ConanException(
                "config.sub patterns not found for linux-ohos support"
            )
        save(self, config_sub, content)
        os.chmod(config_sub, 0o755)
        self.output.info("Patched config.sub for linux-ohos")

    def _patch_config_guess(self, config_guess):
        """Detect HarmonyOS in config.guess before NetBSD (2020 release)."""
        content = load(self, config_guess)
        if "HarmonyOS" in content:
            self.output.info("config.guess already detects HarmonyOS")
            return
        harmony_block = (
            "    *:HarmonyOS:*:*)\n"
            "\tcase \"$UNAME_MACHINE\" in\n"
            "\t    aarch64|arm64) MACHINE=aarch64 ;;\n"
            "\t    armv7*|armv8*) MACHINE=arm ;;\n"
            "\t    x86_64|amd64)  MACHINE=x86_64 ;;\n"
            "\t    i?86)          MACHINE=i686 ;;\n"
            "\t    *)             MACHINE=\"$UNAME_MACHINE\" ;;\n"
            "\tesac\n"
            "\tGUESS=${MACHINE}-unknown-linux-ohos\n"
            "\techo \"$GUESS\"; exit ;;\n"
            "\n"
        )
        target = "    *:NetBSD:*:*)\n"
        if target in content:
            content = content.replace(target, harmony_block + target, 1)
            save(self, config_guess, content)
            os.chmod(config_guess, 0o755)
            self.output.info("Patched config.guess for HarmonyOS detection")
        else:
            self.output.warning(
                "Could not find NetBSD insertion point in config.guess"
            )

    def _patch_config_status_tmpdir(self):
        """Move config.status awk temp files off HMDFS (E114-compatible)."""
        fixed_tmp = os.path.join(self._system_prefix(), "..", ".goocanvas-config-tmp")
        fixed_tmp = os.path.abspath(fixed_tmp)
        os.makedirs(fixed_tmp, exist_ok=True)
        os.chmod(fixed_tmp, 0o700)
        configure_path = os.path.join(self.source_folder, "configure")
        if not os.path.exists(configure_path):
            return
        content = load(self, configure_path)
        if "ac_tmp=$tmp" not in content:
            raise ConanException(
                "ac_tmp=$tmp pattern not found in goocanvas configure"
            )
        content = content.replace("ac_tmp=$tmp", "ac_tmp={}".format(fixed_tmp))
        save(self, configure_path, content)
        os.chmod(configure_path, 0o755)
        self.output.info(
            "Patched configure config.status temp dir to {}".format(fixed_tmp)
        )

    def _system_prefix(self):
        return self._find_gtk_prefix()

    def _find_gtk_prefix(self):
        candidates = []
        for env_name in ("GTK_PREFIX", "DEFAULT_PREFIX"):
            value = os.environ.get(env_name)
            if value:
                candidates.append(os.path.normpath(value))
        candidates.append("/storage/Users/currentUser/usr/local")
        for pattern in (
            "/data/service/hnp/*/*/lib/pkgconfig",
            "/data/service/hnp/*/*/share/pkgconfig",
        ):
            for pc_dir in sorted(glob.glob(pattern)):
                candidates.append(os.path.dirname(os.path.dirname(pc_dir)))
        for pc_file in sorted(
            glob.glob("/data/service/hnp/**/gtk+-3.0.pc", recursive=True)
        ):
            candidates.append(os.path.dirname(os.path.dirname(pc_file)))

        seen = set()
        for prefix in candidates:
            if prefix in seen:
                continue
            seen.add(prefix)
            if self._gtk_pc_exists(prefix):
                self.output.info("Using GTK+ prefix {}".format(prefix))
                return prefix
        return candidates[0] if candidates else "/storage/Users/currentUser/usr/local"

    def _gtk_pc_exists(self, prefix):
        return (
            os.path.isfile(
                os.path.join(prefix, "lib", "pkgconfig", "gtk+-3.0.pc")
            )
            or os.path.isfile(
                os.path.join(prefix, "share", "pkgconfig", "gtk+-3.0.pc")
            )
        )

    def _ensure_system_deps(self):
        """Install the OpenHarmony GTK+ stack from cmd-pkgs when missing."""
        prefix = os.path.expanduser("~/usr/local")
        pc_dir = os.path.join(prefix, "lib", "pkgconfig")
        share_pc_dir = os.path.join(prefix, "share", "pkgconfig")

        def _pc_present(name):
            return (
                os.path.isfile(os.path.join(pc_dir, name))
                or os.path.isfile(os.path.join(share_pc_dir, name))
            )

        deps = [
            ("glib", "2.88.0", "glib-2.0.pc"),
            ("gdk-pixbuf", "2.42.12", "gdk-pixbuf-2.0.pc"),
            ("atk", "2.38.0", "atk.pc"),
            ("fribidi", "1.0.13", "fribidi.pc"),
            ("libepoxy", "1.5.10", "epoxy.pc"),
            ("libpng", "1.6.43", "libpng.pc"),
            ("libjpeg-turbo", "3.1.4.1", "libjpeg.pc"),
            ("fontconfig", "2.16.0", "fontconfig.pc"),
            ("freetype", "2.14.3", "freetype2.pc"),
            ("harfbuzz", "14.2.0", "harfbuzz.pc"),
            ("pixman", "0.46.4", "pixman-1.pc"),
            ("pango", "1.50.14", "pango.pc"),
            ("zlib", "1.3.1", "zlib.pc"),
            ("gtk+", "3.24.38", "gtk+-3.0.pc"),
        ]
        missing = [
            (name, version, pc_name)
            for name, version, pc_name in deps
            if not _pc_present(pc_name)
        ]
        if not missing:
            self.output.info(
                "GTK+ system dependencies already present at {}".format(prefix)
            )
        else:
            for name, version, pc_name in missing:
                self._install_cmd_pkg(name, version, prefix)
            if not self._gtk_pc_exists(prefix):
                raise ConanException(
                    "GTK+ auto-install from cmd-pkgs did not produce gtk+-3.0.pc"
                )
            self.output.info("GTK+ system dependencies installed at {}".format(prefix))

    def _install_cmd_pkg(self, name, version, prefix):
        """Download and extract one cmd-pkgs OHOS aarch64 package."""
        url = (
            "https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/"
            "download/pkgs/{}-{}-ohos-aarch64.tar.gz".format(name, version)
        )
        self.output.info(
            "Installing {} {} from cmd-pkgs into {}".format(name, version, prefix)
        )
        import io
        import ssl
        import tarfile
        import urllib.request

        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        try:
            with urllib.request.urlopen(url, context=ctx, timeout=300) as response:
                data = response.read()
            with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as tf:
                tf.extractall(prefix)
            self.output.info("  Installed {} {} from cmd-pkgs".format(name, version))
        except Exception as exc:
            raise ConanException(
                "Failed to install %s %s from cmd-pkgs: %s" % (name, version, exc)
            )
        if name == "libpng":
            src = os.path.join(prefix, "lib", "pkgconfig", "libpng16.pc")
            dst = os.path.join(prefix, "lib", "pkgconfig", "libpng.pc")
            if os.path.isfile(src) and not os.path.isfile(dst):
                shutil.copy2(src, dst)
                self.output.info("  Created libpng.pc alias for pkg-config")

    def _system_env(self):
        prefix = self._system_prefix()
        env = Environment()
        for dependency in self.dependencies.values():
            package_folder = getattr(dependency, "package_folder", None)
            if not package_folder:
                continue
            for libdir in dependency.cpp_info.libdirs or []:
                if not libdir:
                    continue
                full_libdir = (
                    libdir
                    if os.path.isabs(libdir)
                    else os.path.join(package_folder, libdir)
                )
                env.prepend_path(
                    "PKG_CONFIG_PATH", os.path.join(full_libdir, "pkgconfig")
                )
                env.prepend_path("LD_LIBRARY_PATH", full_libdir)
                env.append("LDFLAGS", "-L{}".format(full_libdir))
            for includedir in dependency.cpp_info.includedirs or []:
                if not includedir:
                    continue
                full_includedir = (
                    includedir
                    if os.path.isabs(includedir)
                    else os.path.join(package_folder, includedir)
                )
                env.append("CPPFLAGS", "-I{}".format(full_includedir))
        env.prepend_path(
            "PKG_CONFIG_PATH", os.path.join(prefix, "lib", "pkgconfig")
        )
        env.prepend_path(
            "PKG_CONFIG_PATH", os.path.join(prefix, "share", "pkgconfig")
        )
        env.prepend_path(
            "LD_LIBRARY_PATH", os.path.join(prefix, "lib", "external")
        )
        env.append("LDFLAGS", "-L{}".format(os.path.join(prefix, "lib", "external")))
        if str(self.settings.os) == "OHOS":
            hnp_pkgconfigs = sorted(
                glob.glob("/data/service/hnp/*/*/lib/pkgconfig"),
                key=lambda p: (p.count("/"), p),
            )
            if hnp_pkgconfigs:
                for pkgconfig_dir in hnp_pkgconfigs:
                    env.prepend_path("PKG_CONFIG_PATH", pkgconfig_dir)
            else:
                self.output.warning(
                    "no HNP pkg-config dirs found under /data/service/hnp"
                )
        env.prepend_path("PATH", os.path.join(prefix, "bin"))
        if str(self.settings.os) == "OHOS":
            hnp_runtime_libs = []
            for pattern in (
                "libpcre2-8.so*",
                "libffi.so*",
                "libexpat.so*",
                "libintl.so*",
            ):
                for match in glob.glob(
                    "/data/service/hnp/*/*/lib/{}".format(pattern)
                ):
                    hnp_runtime_libs.append(os.path.dirname(match))
            for libdir in sorted(set(hnp_runtime_libs)):
                env.append_path("LD_LIBRARY_PATH", libdir)
        env.append("CPPFLAGS", "-I{}".format(os.path.join(prefix, "include")))
        env.append("LDFLAGS", "-L{}".format(os.path.join(prefix, "lib")))
        env.prepend_path("LD_LIBRARY_PATH", os.path.join(prefix, "lib"))
        return env

    def _sign_shared_libs(self):
        if str(self.settings.os) != "OHOS":
            return
        libdir = os.path.join(self.package_folder, "lib")
        shared_objects = glob.glob(
            os.path.join(libdir, "**", "*.so"), recursive=True
        )
        shared_objects += glob.glob(
            os.path.join(libdir, "**", "*.so.*"), recursive=True
        )
        if not shared_objects:
            return
        objcopy = os.environ.get(
            "HNP_LLVM_OBJCOPY", "/data/service/hnp/bin/llvm-objcopy"
        )
        signer = os.environ.get(
            "HNP_BINARY_SIGN_TOOL", "/data/service/hnp/bin/binary-sign-tool"
        )
        for tool in (objcopy, signer):
            if not os.path.isfile(tool):
                self.output.warning("Required OHOS signing tool not found: {}".format(tool))
                return
        for shared_object in shared_objects:
            if os.path.islink(shared_object):
                continue
            probe = self.run(
                "{} --dump-section .codesign=/dev/null {}".format(
                    shlex.quote(objcopy), shlex.quote(shared_object)
                ),
                ignore_errors=True,
            )
            if probe == 0:
                self.run(
                    "{} --remove-section .codesign {}".format(
                        shlex.quote(objcopy), shlex.quote(shared_object)
                    ),
                    ignore_errors=True,
                )
            self.run(
                "{} sign -inFile {} -outFile {} -selfSign 1".format(
                    shlex.quote(signer),
                    shlex.quote(shared_object),
                    shlex.quote(shared_object),
                )
            )
