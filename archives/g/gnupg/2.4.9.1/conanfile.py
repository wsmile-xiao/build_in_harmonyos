#!/usr/bin/env python3
"""Minimal GnuPG 2.4.9 package for OHOS gpg/gpg-agent consumers."""

import hashlib
import os
import shlex
import shutil
from contextlib import contextmanager

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import copy, export_conandata_patches, get, patch, replace_in_file
from conan.tools.gnu import AutotoolsDeps, AutotoolsToolchain
from conan.tools.gnu.autotools import load_toolchain_args
from conan.tools.layout import basic_layout


class GnuPGConan(ConanFile):
    name = "gnupg"
    version = "2.4.9.1"
    description = "GNU Privacy Guard command-line tools and agent"
    license = "GPL-3.0-or-later"
    homepage = "https://gnupg.org/software/gnupg/"
    url = "https://gnupg.org/ftp/gcrypt/gnupg/"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def validate(self):
        if str(self.settings.os) != "OHOS" or str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration("gnupg/2.4.9.1 supports OHOS armv8 only")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        for ref in ("libgpg-error/1.55", "libgcrypt/1.12.2", "libassuan/3.0.2", "npth/1.8", "libksba/1.6.7.1", "libiconv/1.17"):
            self.requires(ref, transitive_headers=True, transitive_libs=True)

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        AutotoolsDeps(self).generate()
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend([
            "--prefix=/", "--bindir=/bin", "--libdir=/lib",
            "--build=aarch64-unknown-linux-musl", "--host=aarch64-unknown-linux-musl",
            "--disable-doc", "--disable-nls", "--disable-gpgsm", "--disable-scdaemon",
            "--disable-dirmngr", "--disable-keyboxd", "--disable-wks-tools", "--disable-ntbtls",
            "--with-libgcrypt-prefix={0}".format(self.dependencies["libgcrypt"].package_folder),
            "--with-libassuan-prefix={0}".format(self.dependencies["libassuan"].package_folder),
            "--with-libgpg-error-prefix={0}".format(self.dependencies["libgpg-error"].package_folder),
            "--with-npth-prefix={0}/npth-prefix".format(self._native_root()),
            "--with-libksba-prefix={0}".format(self.dependencies["libksba"].package_folder),
            "--with-libiconv-prefix={0}".format(self.dependencies["libiconv"].package_folder),
        ])
        tc.generate()

    def build(self):
        root = self._native_root()
        self._remove(root, "before build")
        source, build, stage = os.path.join(root, "source"), os.path.join(root, "build"), os.path.join(root, "stage")
        shutil.copytree(self.source_folder, source, symlinks=True)
        os.makedirs(build)
        self._apply_patches(source)
        args = load_toolchain_args(self.generators_folder)["configure_args"]
        try:
            with self._environment(root):
                self.run("{} {}".format(shlex.quote(os.path.join(source, "configure")), args), cwd=build)
                self.run("make -j1", cwd=build)
                test_home = os.path.join(build, "tests", "openpgp")
                os.makedirs(test_home, exist_ok=True)
                os.chmod(test_home, 0o700)
                self.run("make check -j1", cwd=build)
                self.run("make install DESTDIR={} -j1".format(shlex.quote(stage)), cwd=build)
            copy(self, "COPYING*", src=source, dst=os.path.join(stage, "licenses"))
        except Exception:
            self._remove(root, "after build failure")
            raise

    def package(self):
        root = self._native_root()
        stage = os.path.join(root, "stage")
        if not os.path.isdir(stage):
            raise ConanException("device-local package stage is missing")
        try:
            copy(self, "*", src=stage, dst=self.package_folder)
        finally:
            self._remove(root, "after package")

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.append_path("PATH", os.path.join(self.package_folder, "bin"))

    def _native_root(self):
        # OHOS has a shorter AF_UNIX path budget than the host Linux runner.
        # Keep the OpenPGP test home short enough for gpg-agent's socket names.
        digest = hashlib.sha256(repr((self.build_folder, self.package_folder)).encode("utf-8")).hexdigest()[:4]
        return os.path.join("/data/storage/el2/base", "g" + digest)

    def _remove(self, root, reason):
        if os.path.exists(root):
            shutil.rmtree(root)
        if os.path.exists(root):
            raise ConanException("failed to remove {} {}".format(root, reason))

    def _apply_patches(self, source):
        for entry in self.conan_data.get("patches", []):
            args = entry.copy()
            patch_file = args.pop("patch_file")
            patch(self, base_path=source, patch_file=os.path.join(self.export_sources_folder, patch_file), **args)

    @contextmanager
    def _environment(self, root):
        env = AutotoolsToolchain(self).environment()
        env.compose_env(AutotoolsDeps(self).vars())
        local = Environment()
        tmpdir = os.path.join(root, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        local.define("TMPDIR", tmpdir)
        gpgscm_ffi = os.path.join(root, "source", "tests", "gpgscm", "ffi.c")
        replace_in_file(
            self,
            gpgscm_ffi,
            "#else\n  FFI_RETURN_STRING (sc, \"/tmp\");",
            "#else\n# if defined(HAVE_ANDROID_SYSTEM) || defined(__OHOS__)\n  {\n    const char *tmpdir = getenv (\"TMPDIR\");\n    FFI_RETURN_STRING (sc, (tmpdir && *tmpdir) ? tmpdir : \"/tmp\");\n  }\n# else\n  FFI_RETURN_STRING (sc, \"/tmp\");\n# endif",
        )
        gpgconf_comp = os.path.join(root, "source", "tools", "gpgconf-comp.c")
        replace_in_file(
            self,
            gpgconf_comp,
            "#ifdef HAVE_W32_SYSTEM\nint\ncopy_file",
            "#if defined(HAVE_W32_SYSTEM) || defined(__OHOS__)\nint\ncopy_file",
        )
        replace_in_file(
            self,
            gpgconf_comp,
            "#ifdef HAVE_W32_SYSTEM\n  res = copy_file (dest_filename, orig_filename);\n#else\n  res = link (dest_filename, orig_filename);\n#endif",
            "#if defined(HAVE_W32_SYSTEM) || defined(__OHOS__)\n  res = copy_file (dest_filename, orig_filename);\n#else\n  res = link (dest_filename, orig_filename);\n#endif",
        )
        replace_in_file(
            self,
            gpgconf_comp,
            "#ifdef HAVE_W32_SYSTEM\n              /* We skip the unlink if we expect the file not to be\n               * there.  */\n              err = gnupg_rename_file (src_filename, dest_filename, NULL);\n#else /* HAVE_W32_SYSTEM */",
            "#if defined(HAVE_W32_SYSTEM) || defined(__OHOS__)\n              /* OHOS does not allow hard links; use rename for the new file. */\n              err = gnupg_rename_file (src_filename, dest_filename, NULL);\n#else /* HAVE_W32_SYSTEM */",
        )
        tests_makefile = os.path.join(root, "source", "tests", "Makefile.in")
        replace_in_file(
            self,
            tests_makefile,
            "SUBDIRS = gpgscm openpgp cms migrations gpgme pkits $(tpm2dtests) .",
            "SUBDIRS = gpgscm openpgp migrations gpgme pkits $(tpm2dtests) .",
        )
        gpg_defs = os.path.join(root, "source", "tests", "openpgp", "defs.scm")
        replace_in_file(self, gpg_defs, '"enable-ssh-support"\n', "")
        for name in ("libgpg-error", "libgcrypt", "libassuan", "npth", "libksba", "libiconv"):
            folder = self.dependencies[name].package_folder
            local.prepend_path("PATH", os.path.join(folder, "bin"))
            local.prepend_path("LD_LIBRARY_PATH", os.path.join(folder, "lib"))
        npth_prefix = os.path.join(root, "npth-prefix")
        npth_bin = os.path.join(npth_prefix, "bin")
        os.makedirs(npth_bin, exist_ok=True)
        npth_config = os.path.join(npth_bin, "npth-config")
        npth_pkg = self.dependencies["npth"].package_folder
        with open(npth_config, "w", encoding="utf-8") as handle:
            handle.write("#!/bin/sh\n")
            handle.write("case \"$1\" in\n")
            handle.write("  --version) printf \"1.8\\n\" ;;\n")
            handle.write("  --api-version) printf \"1\\n\" ;;\n")
            handle.write("  --cflags) printf \"-I%s/include\\n\" " + repr(npth_pkg) + " ;;\n")
            handle.write("  --libs) printf \"-L%s/lib -lnpth\\n\" " + repr(npth_pkg) + " ;;\n")
            handle.write("  *) exit 1 ;;\n")
            handle.write("esac\n")
        os.chmod(npth_config, 0o755)

        gpgrt = os.path.join(self.dependencies["libgpg-error"].package_folder, "bin", "gpgrt-config")
        if os.path.isfile(gpgrt):
            local.define("GPGRT_CONFIG", gpgrt)
        os.makedirs(os.path.join(root, "tmp"), exist_ok=True)
        env.compose_env(local)
        with env.vars(self).apply():
            yield
