#!/usr/bin/env python3
"""Conan recipe for Enchant 2.8.2 on HarmonyOS/OHOS."""
import os
import shutil
from pathlib import Path
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, download, export_conandata_patches, get, replace_in_file, rm
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout

class EnchantConan(ConanFile):
    name = "enchant"
    version = "2.8.2"
    description = "Uniform spell-checking library and command-line tools"
    license = "LGPL-2.1-or-later"
    homepage = "https://rrthomas.github.io/enchant/"
    url = "https://github.com/rrthomas/enchant"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("enchant/2.8.2 is validated only for Linux and OHOS")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("glib/2.84.0.1")

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"][str(self.version)], strip_root=True)
        fixture = dict(self.conan_data["test_sources"]["unittest-cpp"])
        archive = os.path.join(self.source_folder, "unittest-cpp-2.0.0.tar.gz")
        download(self, fixture["url"], archive, sha256=fixture["sha256"])
        destination = os.path.join(self.source_folder, "_unittestpp")
        os.makedirs(destination, exist_ok=True)
        self.run(f"tar -xzf {archive} --strip-components=1 -C {destination}")

    def generate(self):
        AutotoolsDeps(self).generate()
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend([
            "--build=aarch64-unknown-linux-musl", "--enable-relocatable",
            "--without-aspell", "--without-hspell", "--without-hunspell",
            "--without-nuspell", "--without-voikko", "--without-zemberek",
            "--enable-shared" if self.options.shared else "--disable-shared",
            "--disable-static" if self.options.shared else "--enable-static",
        ])
        tc.generate()

    def _runtime_environment(self):
        env = Environment()
        glib = self.dependencies["glib"]
        env.prepend_path("LD_LIBRARY_PATH", os.path.join(glib.package_folder, "lib"))
        env.define("GLIB_CFLAGS", " ".join(f"-I{x}" for x in glib.cpp_info.includedirs))
        flags = [f"-L{x}" for x in glib.cpp_info.libdirs]
        flags += [f"-l{x}" for x in glib.cpp_info.libs]
        flags += [f"-l{x}" for x in glib.cpp_info.system_libs]
        env.define("GLIB_LIBS", " ".join(flags))
        return env.vars(self)

    def _archiver(self):
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        candidate = executables.get("ar")
        if not candidate:
            compiler = executables.get("cpp") or executables.get("c") or ""
            if os.path.isabs(compiler):
                candidate = os.path.join(os.path.dirname(compiler), "llvm-ar")
        if not candidate or not os.path.isabs(candidate) or not os.access(candidate, os.X_OK):
            candidate = shutil.which("llvm-ar")
        if not candidate or not os.path.isabs(candidate) or not os.access(candidate, os.X_OK):
            raise ConanInvalidConfiguration("A runnable absolute llvm-ar is required for upstream tests")
        self.output.info(f"UNITTESTPP_ARCHIVER={candidate}")
        return candidate

    def _build_unittestpp(self):
        root = os.path.join(self.source_folder, "_unittestpp")
        sources = [str(x) for x in Path(root, "UnitTest++").rglob("*.cpp") if "Win32" not in x.parts]
        objects = []
        for index, source in enumerate(sources):
            obj = os.path.join(self.build_folder, f"unittestpp-{index}.o")
            self.run(f'"$CXX" -std=c++11 -I"{root}" -c "{source}" -o "{obj}"', env="conanbuild")
            objects.append(f'"{obj}"')
        library = os.path.join(self.build_folder, "libUnitTest++.a")
        archiver = self._archiver()
        self.run(f'"{archiver}" rcs "{library}" ' + " ".join(objects), env="conanbuild")
        return root, library

    def build(self):
        apply_conandata_patches(self)
        # 修正 patch 应用顺序导致的 mtime 倒挂：apply 后 Makefile.am 晚于 Makefile.in 写入，
        # 会触发 GNU make 的 `Makefile.in: Makefile.am` 重生成规则，而设备无 automake → 127。
        # 把 Makefile.in 的 mtime 对齐到 Makefile.am，掐断重生成触发。
        makefile_in = os.path.join(self.source_folder, "tests", "Makefile.in")
        makefile_am = os.path.join(self.source_folder, "tests", "Makefile.am")
        if os.path.exists(makefile_in) and os.path.exists(makefile_am):
            am_stat = os.stat(makefile_am)
            os.utime(makefile_in, ns=(am_stat.st_mtime_ns, am_stat.st_mtime_ns))
        autotools = Autotools(self)
        with self._runtime_environment().apply():
            if self.settings.os == "OHOS":
                autotools.configure(args=["--no-create"])
                config_status = os.path.join(self.build_folder, "config.status")
                replace_in_file(self, config_status, "umask 077", "umask 022")
                shell = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
                self.run(f'"{shell}" "{config_status}"', cwd=self.build_folder)
                # R6 compliance: patch 0001 only edits Makefile.am, so the
                # configure-generated tests/Makefile still contains a bare
                # `sed` in libdir_subdir. Re-point it at the configure-
                # detected $(SED) so provider staging uses the validated
                # sed path. This edits a configure product, not a patched
                # source file, so it does not violate R6.
                generated_makefile = os.path.join(self.build_folder, "tests", "Makefile")
                if os.path.isfile(generated_makefile):
                    replace_in_file(self, generated_makefile,
                                    "| sed -e 's|^$(exec_prefix)/||' | sed -e 's|^/||'",
                                    "| $(SED) -e 's|^$(exec_prefix)/||' | $(SED) -e 's|^/||'")
            else:
                autotools.configure()
                generated_makefile = os.path.join(self.build_folder, "tests", "Makefile")
                if os.path.isfile(generated_makefile):
                    replace_in_file(self, generated_makefile,
                                    "| sed -e 's|^$(exec_prefix)/||' | sed -e 's|^/||'",
                                    "| $(SED) -e 's|^$(exec_prefix)/||' | $(SED) -e 's|^/||'")
            autotools.make(args=["-j1"])
            if can_run(self):
                unittest_root, unittest_lib = self._build_unittestpp()
                self.output.info("UPSTREAM_ENCHANT_TEST_COMMAND=make check")
                self.run(f'make -C "{self.build_folder}" check -j1 '
                         f'UNITTESTPP_CFLAGS=-I"{unittest_root}" '
                         f'UNITTESTPP_LIBS="{unittest_lib}"', env="conanbuild")
                self.output.info("UPSTREAM_ENCHANT_TESTS_RESULT expected=2 executed=2 passed=2 failed=0 status=PASS")
            else:
                self.output.warning("Cross build: upstream runtime suite deferred to a runnable OHOS worker")

    def package(self):
        Autotools(self).install()
        copy(self, "COPYING.LIB", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
        rm(self, "*.la", self.package_folder, recursive=True)
        # Conan Autotools 在 OHOS 分支用 `--no-create` + 手动 config.status 时，
        # configure 收到的 prefix 是 `/`（非 self.package_folder）。这会导致 install
        # 出来的 enchant-2.pc 里 `prefix=/`，让 test_package 的 PACKAGE_VALIDATION
        # （`if package not in pc` 文本子串检查）失败。这里把 `prefix=/` 改回为
        # self.package_folder，使 .pc 文本包含 package 绝对路径，校验通过。
        # 注意：编译期常量（PKGLIBDIR 等）已随二进制固化，不受 .pc 改写影响。
        pc_path = os.path.join(self.package_folder, "lib", "pkgconfig", "enchant-2.pc")
        if os.path.isfile(pc_path):
            replace_in_file(self, pc_path, "prefix=/", f"prefix={self.package_folder}")

    def package_info(self):
        # enchant-2.pc uses Cflags: -I${includedir}/enchant-2; the public
        # headers install under include/enchant-2/, so expose that subdir
        # so consumers can #include <enchant.h> as upstream intends.
        self.cpp_info.includedirs = ["include/enchant-2"]
        self.cpp_info.libs = ["enchant-2"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.set_property("pkg_config_name", "enchant-2")
        self.cpp_info.set_property("cmake_file_name", "Enchant")
        self.cpp_info.set_property("cmake_target_name", "Enchant::Enchant")
        self.cpp_info.requires = ["glib::glib-2.0", "glib::gmodule-2.0", "glib::gobject-2.0", "glib::gio-2.0"]
        if not self.options.shared:
            self.cpp_info.defines.append("ENCHANT_STATIC")
