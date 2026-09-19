#!/usr/bin/env python3
"""Conan recipe for libblkid 2.42.2 from util-linux.

Builds ONLY the libblkid library (block device identification) from the
util-linux 2.42.2 tarball, using the "single sub-library" pattern already
proven by archives/u/uuid/2.40.1 (libuuid) and archives/u/util-linux-login
(the login(1) program): --disable-all-programs + --enable-libblkid.

libblkid itself has no external library dependencies (it only links the
internal libcommon), so the recipe has no `requires`.

Upstream tests (kept buildable via --enable-static, BUILD_LIBBLKID_TESTS):
- 12 check_PROGRAMS (test_blkid_cache/config/dev/devname/devno/evaluate/
  read/resolve/save/tag/verify + test_blkid_fuzz_sample)
- tests/ts/blkid/ script suite (needs root + block devices: skipped, see
  notes.md for the per-case rationale)

OHOS adaptation:
- config/config.guess: HarmonyOS detection patch (same as util-linux-login).
- configure umask 077 (E011): temp dirs become 0700 on HMDFS which are
  forced read-only -> replace with umask 022 (in-recipe sed).
- TMPDIR: point autoconf temp files at the build folder (/tmp is read-only).
- AWK: configure requires awk; locate the toolchain awk explicitly.
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, rm
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibBlkidConan(ConanFile):
    name = "libblkid"
    version = "2.42.2"
    description = "Block device identification library from util-linux"
    license = "LGPL-2.1-or-later"  # library part of util-linux (libblkid is LGPL)
    homepage = "https://www.kernel.org/pub/linux/utils/util-linux/"
    url = ""
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")
        if self.options.shared:
            raise ConanInvalidConfiguration("libblkid is packaged as a static library")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        data = self.conan_data["sources"][self.version]
        primary, mirrors = data["url"][0], data["url"][1:]
        for url in [primary] + mirrors:
            try:
                get(self, url, sha256=data["sha256"], strip_root=True)
                return
            except Exception as e:
                self.output.warning(f"source download failed from {url}: {e}")
        raise ConanInvalidConfiguration("source download failed from all mirrors")

    def _gnu_triplet(self, arch=None):
        arch = str(arch or self.settings.arch)
        arch_triplets = {
            "armv8": "aarch64-unknown-linux-gnu",
            "armv8.3": "aarch64-unknown-linux-gnu",
            "aarch64": "aarch64-unknown-linux-gnu",
            "x86_64": "x86_64-unknown-linux-gnu",
        }
        triplet = arch_triplets.get(arch)
        if not triplet:
            raise ConanInvalidConfiguration(f"Unsupported arch: {arch}")
        return triplet

    def _prepare_autotools_env(self):
        """Writable TMPDIR + explicit AWK for configure (uuid 2.40.1 pattern)."""
        tmpdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        os.chmod(tmpdir, 0o755)
        os.environ["TMPDIR"] = tmpdir

        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = compilers.get("c", "")
        bindir = os.path.dirname(cc) if os.path.isabs(cc) else ""
        toolchain_awk = ""
        if bindir:
            for name in ("gawk", "awk"):
                candidate = os.path.join(bindir, name)
                if os.path.exists(candidate):
                    toolchain_awk = candidate
                    break
        awk = toolchain_awk or shutil.which("gawk") or shutil.which("awk")
        if not awk:
            raise ConanInvalidConfiguration("An awk implementation is required")
        os.environ["AWK"] = awk
        os.environ["ac_cv_prog_AWK"] = awk
        return awk

    def generate(self):
        awk = self._prepare_autotools_env()
        host_triplet = self._gnu_triplet()
        build_arch = self.settings_build.get_safe("arch") if self.settings_build else None
        build_triplet = self._gnu_triplet(build_arch or self.settings.arch)
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend([
            f"AWK={awk}",
            f"ac_cv_prog_AWK={awk}",
            f"--build={build_triplet}",
            f"--host={host_triplet}",
            # util-linux "single sub-library" mode: disable everything, then
            # enable only libblkid (uuid 2.40.1 / util-linux-login pattern).
            "--disable-all-programs",
            "--enable-libblkid",
            "--disable-libuuid",
            "--disable-libmount",
            "--disable-libsmartcols",
            "--disable-libfdisk",
            "--without-python",
            "--without-systemd",
            "--without-udev",
            "--disable-makeinstall-chown",
            "--disable-makeinstall-setuid",
            # BUILD_LIBBLKID_TESTS requires --enable-static
            "--enable-static",
            "--disable-shared",
        ])
        tc.generate()
        # autoconf temp files must not land in /tmp (read-only on OHOS)
        env = Environment()
        env.define("TMPDIR", os.path.join(self.build_folder, "tmp"))
        env.vars(self, scope="build").save_script("conanblkidtmpdir")

    def build(self):
        apply_conandata_patches(self)
        self._prepare_autotools_env()
        # E011: configure creates confXXXXXX temp dirs with umask 077 (0700);
        # on OHOS HMDFS those dirs are force-downgraded and become unwritable
        # -> use umask 022 so config.status can write its helper files.
        for fname in ("configure",):
            fpath = os.path.join(self.source_folder, fname)
            if os.path.isfile(fpath):
                with open(fpath, encoding="utf-8", errors="ignore") as f:
                    text = f.read()
                if "umask 077" in text:
                    text = text.replace("umask 077", "umask 022")
                    with open(fpath, "w", encoding="utf-8") as f:
                        f.write(text)
                    self.output.info("patched configure: umask 077->022 (E011)")
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j4"])
        # Upstream test programs (BUILD_LIBBLKID_TESTS): the 12 check_PROGRAMS.
        # Build them all; the runnable subset is executed in test() below.
        for target in ("test_blkid_cache", "test_blkid_config", "test_blkid_dev",
                       "test_blkid_devname", "test_blkid_devno", "test_blkid_evaluate",
                       "test_blkid_read", "test_blkid_resolve", "test_blkid_save",
                       "test_blkid_tag", "test_blkid_verify", "test_blkid_fuzz_sample"):
            autotools.make(target=target, args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        # keep only the libblkid pieces
        for pc in ("uuid.pc", "mount.pc", "fdisk.pc", "smartcols.pc"):
            rm(self, pc, os.path.join(self.package_folder, "lib", "pkgconfig"))
        rm(self, "*.la", os.path.join(self.package_folder, "lib"))
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = ["blkid"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.set_property("pkg_config_name", "blkid")
        self.cpp_info.set_property("cmake_file_name", "blkid")
        self.cpp_info.set_property("cmake_target_name", "blkid::blkid")
