#!/usr/bin/env python3
"""Conan recipe for gtkdatabox 1.0.0 on OpenHarmony PC."""
import glob
import io
import os
import re
import shlex
import ssl
import subprocess
import tarfile
import urllib.request

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.build import can_run
from conan.tools.files import get, load, save
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class GtkDataboxConan(ConanFile):
    name = "gtkdatabox"
    version = "1.0.0"
    description = "GTK+ widget for plotting large numeric datasets"
    license = "LGPL-2.1-or-later"
    homepage = "https://sourceforge.net/projects/gtkdatabox/"
    url = "https://sourceforge.net/p/gtkdatabox/code/"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def requirements(self):
        # CI fallback: export unpublished local recipes from archives/ and build them with --build=missing.
        self.requires("cairo/1.18.4")
        self.requires("pixman/0.46.4")
        self.requires("libpng/1.6.58")
        self.requires("freetype/2.14.3")
        self.requires("fontconfig/2.18.1")
        self.requires("zlib/1.3.1.1")
        self.requires("expat/2.8.2")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend([
            "--enable-shared" if self.options.shared else "--disable-shared",
            "--disable-static" if self.options.shared else "--enable-static",
            "--disable-glade",
            "--disable-gtk-doc",
            "--disable-gtk-doc-html",
            "--disable-gtk-doc-pdf",
        ])
        tc.generate()

    def _patch_config_sub(self, config_sub):
        """Accept the linux-ohos kernel-OS triplet on this Autotools release."""
        content = load(self, config_sub)
        if "linux-ohos" in content:
            self.output.info("config.sub already accepts linux-ohos")
            return
        content = content.replace(
            "linux-musl* | linux-uclibc* | uclinux-uclibc*",
            "linux-musl* | linux-ohos* | linux-uclibc* | uclinux-uclibc*",
            1,
        )
        content = content.replace(
            "| -linux-newlib* | -linux-musl* | -linux-uclibc* \\",
            "| -linux-newlib* | -linux-musl* | -linux-ohos* | -linux-uclibc* \\",
            1,
        )
        ohos_case = (
            "\t-linux-ohos*)\n"
            "\t\tos=-linux-ohos\n"
            "\t\t;;\n"
        )
        target = "\t-linux*)\n"
        if target in content:
            content = content.replace(target, ohos_case + target, 1)
        save(self, config_sub, content)
        os.chmod(config_sub, 0o755)

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
            self.output.warning("Could not find NetBSD insertion point in config.guess")

    def build(self):
        if str(self.settings.os) == "OHOS":
            self._ensure_system_deps()
            self._patch_config_sub(os.path.join(self.source_folder, "config.sub"))
            self._patch_config_guess(os.path.join(self.source_folder, "config.guess"))
            self._patch_config_status_tmpdir()
        envvars = self._system_env().vars(self)
        with envvars.apply():
            autotools = Autotools(self)
            autotools.configure()
            autotools.make()
            autotools.make(target="check")
            self._build_upstream_examples()

    def _patch_config_status_tmpdir(self):
        """Move config.status awk temp files off HMDFS (E114-compatible)."""
        fixed_tmp = os.path.join(self._system_prefix(), "..", ".gtkdatabox-config-tmp")
        fixed_tmp = os.path.abspath(fixed_tmp)
        os.makedirs(fixed_tmp, exist_ok=True)
        os.chmod(fixed_tmp, 0o700)
        configure_path = os.path.join(self.source_folder, "configure")
        if os.path.exists(configure_path):
            content = load(self, configure_path)
            if "ac_tmp=$tmp" not in content:
                raise ConanException(
                    "ac_tmp=$tmp pattern not found in gtkdatabox configure")
            content = content.replace("ac_tmp=$tmp", "ac_tmp={}".format(fixed_tmp))
            save(self, configure_path, content)
            os.chmod(configure_path, 0o755)
            self.output.info("Patched configure config.status temp dir to {}".format(fixed_tmp))

    def package(self):
        envvars = self._system_env().vars(self)
        with envvars.apply():
            autotools = Autotools(self)
            autotools.install()
        self._sanitize_installed_pc()
        if str(self.settings.os) == "OHOS" and self.options.shared:
            self._sign_shared_libs()

    def _sanitize_installed_pc(self):
        pc_path = os.path.join(self.package_folder, "lib", "pkgconfig", "gtkdatabox.pc")
        if not os.path.isfile(pc_path):
            self.output.warning("Installed gtkdatabox.pc not found at {}".format(pc_path))
            return
        lines = load(self, pc_path).splitlines()
        cleaned = []
        for line in lines:
            if line.startswith("prefix="):
                cleaned.append("prefix={}".format(self.package_folder))
                continue
            if line.startswith("includedir="):
                cleaned.append("includedir=${prefix}/include")
                continue
            if line.startswith("libdir="):
                cleaned.append("libdir=${prefix}/lib")
                continue
            if not line.startswith("Cflags:"):
                cleaned.append(line)
                continue
            flags = []
            tokens = line.split()
            index = 0
            while index < len(tokens):
                token = tokens[index]
                if token == "-I" and index + 1 < len(tokens):
                    include_dir = tokens[index + 1]
                    if include_dir.startswith("${") or os.path.isdir(include_dir):
                        flags.extend((token, include_dir))
                    index += 2
                    continue
                if token.startswith("-I") and len(token) > 2:
                    include_dir = token[2:]
                    if include_dir.startswith("${") or os.path.isdir(include_dir):
                        flags.append(token)
                    index += 1
                    continue
                if len(token) > 1 and token[0].isalpha() and token[-1] == ":":
                    index += 1
                    continue
                flags.append(token)
                index += 1
            if not any(flag == "-I${includedir}" for flag in flags):
                flags.append("-I${includedir}")
            cleaned.append("Cflags: {}".format(" ".join(flags)))
        save(self, pc_path, "\n".join(cleaned) + "\n")
        self.output.info("Sanitized installed gtkdatabox.pc: prefix={}, include={}".format(self.package_folder, os.path.join(self.package_folder, "include")))

    def _build_upstream_examples(self):
        candidates = [
            os.path.join(self.build_folder, "examples"),
            os.path.join(self.source_folder, "examples"),
        ]
        examples_dir = next((path for path in candidates if os.path.isdir(path)), None)
        if not examples_dir:
            raise ConanException("gtkdatabox upstream examples directory was not found")
        self.run("make -C {}".format(shlex.quote(examples_dir)))
        if not can_run(self):
            self.output.warning("gtkdatabox upstream examples were built but not launched because target binaries cannot execute on this host")
            return
        library_path = os.pathsep.join([
            os.path.join(self.build_folder, "gtk"),
            os.path.join(self._system_prefix(), "lib"),
            os.path.join(self._system_prefix(), "lib", "external"),
        ])
        probed = 0
        for name in sorted(os.listdir(examples_dir)):
            executable = os.path.join(examples_dir, name)
            if os.path.isfile(executable) and os.access(executable, os.X_OK):
                self.output.info("Probing upstream example {}".format(name))
                self.run(
                    "GDK_BACKEND=wayland,x11,broadway LD_LIBRARY_PATH={} timeout 5s {} || test $? -eq 124 || test $? -eq 1".format(
                        shlex.quote(library_path), shlex.quote(executable)))
                probed += 1
        if probed == 0:
            raise ConanException("gtkdatabox upstream examples were built but no executable example was found")

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
        for pc_file in sorted(glob.glob("/data/service/hnp/**/gtk+-3.0.pc", recursive=True)):
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
            os.path.isfile(os.path.join(prefix, "lib", "pkgconfig", "gtk+-3.0.pc"))
            or os.path.isfile(os.path.join(prefix, "share", "pkgconfig", "gtk+-3.0.pc"))
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
        missing = [(name, version, pc_name) for name, version, pc_name in deps if not _pc_present(pc_name)]
        if not missing:
            self.output.info("GTK+ system dependencies already present at {}".format(prefix))
        else:
            for name, version, pc_name in missing:
                self._install_cmd_pkg(name, version, prefix)
            if not self._gtk_pc_exists(prefix):
                raise ConanException("GTK+ auto-install from cmd-pkgs did not produce gtk+-3.0.pc")
            self.output.info("GTK+ system dependencies installed at {}".format(prefix))
        self._strip_cairo_gobject_requires(prefix)

    def _install_cmd_pkg(self, name, version, prefix):
        """Download and extract one cmd-pkgs OHOS aarch64 package."""
        url = (
            "https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/"
            "download/pkgs/{}-{}-ohos-aarch64.tar.gz".format(name, version)
        )
        self.output.info("Installing {} {} from cmd-pkgs into {}".format(name, version, prefix))
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
            raise ConanException("Failed to install {} {} from cmd-pkgs: {}".format(name, version, exc))
        if name == "libpng":
            src = os.path.join(prefix, "lib", "pkgconfig", "libpng16.pc")
            dst = os.path.join(prefix, "lib", "pkgconfig", "libpng.pc")
            if os.path.isfile(src) and not os.path.isfile(dst):
                import shutil
                shutil.copy2(src, dst)
                self.output.info("  Created libpng.pc alias for pkg-config")

    def _strip_cairo_gobject_requires(self, prefix):
        """Drop cairo-gobject from GTK pc files and repair literal newline corruption."""
        pc_dir = os.path.join(prefix, "lib", "pkgconfig")
        if not os.path.isdir(pc_dir):
            return
        for filename in sorted(os.listdir(pc_dir)):
            if not filename.endswith(".pc"):
                continue
            path = os.path.join(pc_dir, filename)
            content = load(self, path)
            has_cairo = "cairo-gobject" in content
            malformed = "\\n" in content
            if not has_cairo and not malformed:
                continue
            lines = content.split("\\n") if malformed else content.splitlines()
            changed = malformed
            for index, line in enumerate(lines):
                if has_cairo and line.startswith(("Requires:", "Requires.private:")) and "cairo-gobject" in line:
                    line = re.sub(r"cairo-gobject\s*>=\s*[\d.]+\s*", " ", line)
                    line = re.sub(r"cairo-gobject\s*", " ", line)
                    line = re.sub(r"\s{2,}", " ", line).rstrip()
                    lines[index] = line
                    changed = True
            if changed:
                save(self, path, "\n".join(lines) + "\n")
                reason = "malformed newlines" if malformed else "cairo-gobject"
                self.output.info("Sanitized {} ({})".format(filename, reason))

    def _ensure_gtk_dependency_pcs(self, prefix):
        """Generate pkg-config metadata omitted by the deployed GTK prefix."""
        pc_dir = os.path.join(prefix, "lib", "pkgconfig")
        if os.path.isfile(os.path.join(pc_dir, "cairo-gobject.pc")) and os.path.isfile(os.path.join(pc_dir, "epoxy.pc")):
            self.output.info("GTK dependency pkg-config files already present")
            return
        if not os.access(prefix, os.W_OK):
            self.output.info("GTK prefix is read-only; assuming dependency pkg-config files are deployed")
            return
        external_lib = os.path.join(prefix, "lib", "external")
        if not os.path.isdir(external_lib):
            self.output.warning("GTK external lib dir not found: {}".format(external_lib))
            return
        pcs = {
            "cairo-gobject.pc": (
                "1.18.4",
                "cairo-gobject integration library",
                "gobject-2.0 glib-2.0",
                "-lcairo-gobject",
                "libcairo-gobject.so.2",
            ),
            "epoxy.pc": (
                "1.5.10",
                "OpenGL function pointer management library",
                "",
                "-lepoxy",
                "libepoxy.so.0",
            ),
        }
        for filename, (version, description, requires, libs, soname) in pcs.items():
            pc_file = os.path.join(prefix, "lib", "pkgconfig", filename)
            content = """prefix={prefix}
includedir=${{prefix}}/include
libdir={libdir}

Name: {name}
Description: {description}
Version: {version}
Requires: {requires}
Libs: -L${{libdir}} {libs}
Cflags: -I${{includedir}}/cairo
""".format(
                prefix=prefix,
                libdir=external_lib,
                name=os.path.splitext(filename)[0],
                description=description,
                version=version,
                requires=requires,
                libs=libs,
            )
            save(self, pc_file, content)
            self.output.info("Wrote {} at {}".format(filename, pc_file))
            lib_name = libs.split()[0][2:]
            link_name = os.path.join(external_lib, "lib{}.so".format(lib_name))
            link_target = os.path.join(external_lib, soname)
            stale_names = (os.path.join(external_lib, lib_name), link_name)
            for stale in stale_names:
                if os.path.islink(stale) or os.path.isfile(stale):
                    try:
                        os.remove(stale)
                    except OSError:
                        pass
            if os.path.exists(link_target):
                try:
                    os.symlink(soname, link_name)
                    self.output.info("Created linker symlink {}".format(link_name))
                except OSError:
                    import shutil
                    shutil.copy2(link_target, link_name)
                    self.output.info("Copied linker shim {}".format(link_name))

    def _system_env(self):
        prefix = self._system_prefix()
        if str(self.settings.os) == "OHOS":
            self._ensure_gtk_dependency_pcs(prefix)
        env = Environment()
        for dependency in self.dependencies.values():
            for libdir in dependency.cpp_info.libdirs:
                full_libdir = libdir if os.path.isabs(libdir) else os.path.join(dependency.package_folder, libdir)
                env.prepend_path("PKG_CONFIG_PATH", os.path.join(full_libdir, "pkgconfig"))
                env.prepend_path("LD_LIBRARY_PATH", full_libdir)
                env.append("LDFLAGS", "-L{}".format(full_libdir))
            for includedir in dependency.cpp_info.includedirs:
                full_includedir = includedir if os.path.isabs(includedir) else os.path.join(dependency.package_folder, includedir)
                env.append("CPPFLAGS", "-I{}".format(full_includedir))
        env.prepend_path("PKG_CONFIG_PATH", os.path.join(prefix, "lib", "pkgconfig"))
        env.prepend_path("PKG_CONFIG_PATH", os.path.join(prefix, "share", "pkgconfig"))
        env.prepend_path("LD_LIBRARY_PATH", os.path.join(prefix, "lib", "external"))
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
                self.output.warning("no HNP pkg-config dirs found under /data/service/hnp")
        env.prepend_path("PATH", os.path.join(prefix, "bin"))
        if str(self.settings.os) == "OHOS":
            hnp_runtime_libs = []
            for pattern in ("libpcre2-8.so*", "libffi.so*", "libexpat.so*", "libintl.so*"):
                for match in glob.glob("/data/service/hnp/*/*/lib/{}".format(pattern)):
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
        shared_objects = glob.glob(os.path.join(libdir, "**", "*.so"), recursive=True)
        shared_objects += glob.glob(os.path.join(libdir, "**", "*.so.*"), recursive=True)
        if not shared_objects:
            return
        objcopy = os.environ.get("HNP_LLVM_OBJCOPY", "/data/service/hnp/bin/llvm-objcopy")
        signer = os.environ.get("HNP_BINARY_SIGN_TOOL", "/data/service/hnp/bin/binary-sign-tool")
        for tool in (objcopy, signer):
            if not os.path.isfile(tool):
                raise ConanInvalidConfiguration("Required OHOS signing tool not found: {}".format(tool))
        for shared_object in shared_objects:
            if os.path.islink(shared_object):
                continue
            probe = subprocess.run(
                [objcopy, "--dump-section", ".codesign=/dev/null", shared_object],
                check=False,
                capture_output=True,
                text=True,
            )
            if probe.returncode == 0:
                if self.run("{} --remove-section .codesign {}".format(
                        shlex.quote(objcopy), shlex.quote(shared_object))) != 0:
                    raise ConanException("Failed to remove .codesign from {}".format(shared_object))
            if self.run("{} sign -inFile {} -outFile {} -selfSign 1".format(
                    shlex.quote(signer), shlex.quote(shared_object), shlex.quote(shared_object))) != 0:
                raise ConanException("Failed to sign {}".format(shared_object))

    def package_info(self):
        self.cpp_info.libs = ["gtkdatabox"]
        self.cpp_info.set_property("cmake_file_name", "gtkdatabox")
        self.cpp_info.set_property("cmake_target_name", "gtkdatabox::gtkdatabox")
        self.cpp_info.set_property("pkg_config_name", "gtkdatabox")
        if str(self.settings.os) in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m"]
