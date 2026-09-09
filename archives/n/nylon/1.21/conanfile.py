#!/usr/bin/env python3
"""Conan recipe — nylon 1.21 (SOCKS4/5 lightweight proxy).

Adapted for HarmonyOS PC (arm64, OS=OHOS).
- Source: https://github.com/smeinecke/nylon (1.21 release tarball)
- License: BSD-3-Clause (see LICENSE)
- Build system: autotools
- Dependencies: libevent
"""
import os, shutil, subprocess
from conan import ConanFile
from conan.tools.files import get, export_conandata_patches, apply_conandata_patches, copy
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout


class NylonConan(ConanFile):
    name = "nylon"
    version = "1.21"
    description = "nylon 1.21 — lightweight SOCKS4/5 and services-mirror proxy"
    license = "BSD-3-Clause"
    homepage = "https://github.com/smeinecke/nylon"
    url = "https://github.com/OpenHarmonyPCDeveloper/build_in_harmonyos.git"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)
        self.run("cp -r '%s/patches' '%s/'" % (self.recipe_folder, self.export_sources_folder))

    def requirements(self):
        self.requires("libevent/2.1.12", transitive_headers=True, transitive_libs=True)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][0],
            filename="nylon-1.21.tar.gz",
            strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        tc.configure_args.append("--with-libevent")
        tc.generate()

    def build(self):
        # apply_conandata_patches (required by G1) is a no-op when patches
        # list in conandata.yml is empty.  The actual config.guess / config.sub
        # replacement is done via copy() below, with the patched files having
        # been copied to export_sources_folder by export_sources().
        apply_conandata_patches(self)

        # Replace vendor config.guess/config.sub with HarmonyOS-aware copies.
        patches_dir = os.path.join(self.export_sources_folder, "patches")
        copy(self, "config.guess", src=patches_dir, dst=self.source_folder)
        copy(self, "config.sub",   src=patches_dir, dst=self.source_folder)
        self.run("chmod +x '%s/configure' '%s/config.guess' '%s/config.sub'" % (
            self.source_folder, self.source_folder, self.source_folder))

        # E012 setgid workaround (HMDFS-specific):
        # The build dir is setgid (group=file_manager).  mktemp in the
        # configure script uses `umask 077` which creates confstat dirs with
        # mode 0270.  On HMDFS these dirs end up owned by the group rather
        # than the build user, and since the group has no write permission
        # in 0270, the build user cannot write to them.
        # Fix: copy source to /storage/Users/currentUser/usr/nylon-build (fully
        # user-owned) and patch configure to (a) drop umask 077 → 022 and
        # (b) redirect confstat paths to the writable build root.
        build_root = "/storage/Users/currentUser/usr/nylon-build"
        if os.path.exists(build_root):
            shutil.rmtree(build_root)
        os.makedirs(build_root, 0o755)

        for item in os.listdir(self.source_folder):
            src = os.path.join(self.source_folder, item)
            dst = os.path.join(build_root, item)
            if os.path.isdir(src):
                shutil.copytree(src, dst, symlinks=False)
            else:
                shutil.copy2(src, dst)

        # Patch configure: drop restrictive umask, redirect confstat dirs.
        # Use Python instead of sed (CI environment may lack sed).
        configure_path = os.path.join(build_root, "configure")
        with open(configure_path, "r", encoding="utf-8") as f:
            content = f.read()
        content = content.replace("(umask 077", "(umask 022")
        content = content.replace("./confstat$$-", "/storage/Users/currentUser/usr/nylon-build/confstat$$-")
        content = content.replace("./confstatXXXXXX", "/storage/Users/currentUser/usr/nylon-build/confstatXXXXXX")
        with open(configure_path, "w", encoding="utf-8") as f:
            f.write(content)

        pkg = self.package_folder
        libevent_prefix = self.dependencies["libevent"].package_folder

        cfg = [
            "--prefix=%s" % pkg,
            "--bindir=%s/bin" % pkg,
            "--sbindir=%s/bin" % pkg,
            "--libdir=%s/lib" % pkg,
            "--includedir=%s/include" % pkg,
            "--oldincludedir=%s/include" % pkg,
        ]
        if not self.options.shared:
            cfg += ["--enable-static", "--disable-shared"]
        cfg.append("--with-libevent=%s" % libevent_prefix)

        build_sh = os.path.join(self.generators_folder, "conanbuild.sh")
        cmd = (
            "set -e\n"
            ". '%s'\n"
            "export PKG_CONFIG_PATH='%s/lib/pkgconfig:$PKG_CONFIG_PATH'\n"
            "export CPPFLAGS='-I%s/include'\n"
            "export LDFLAGS='-L%s/lib'\n"
            "cd '%s'\n"
            "./configure %s\n"
            "make -j1\n"
            "make install\n"
        ) % (build_sh, libevent_prefix, libevent_prefix, libevent_prefix, build_root, " ".join(cfg))

        result = subprocess.run(
            ["/data/service/hnp/bin/bash", "-c", cmd],
            cwd=build_root,
            env=os.environ.copy(),
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            self.output.error("BUILD FAILED (rc=%d)" % result.returncode)
            self.output.error("STDOUT tail:\n%s" % result.stdout[-3000:])
            self.output.error("STDERR tail:\n%s" % result.stderr[-3000:])
            raise RuntimeError("nylon build failed (rc=%d)" % result.returncode)

    def package(self):
        pass  # install done in build()

    def package_info(self):
        self.cpp_info.libs = []
