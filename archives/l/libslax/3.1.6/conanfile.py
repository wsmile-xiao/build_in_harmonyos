#!/usr/bin/env python3

import os
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import VirtualBuildEnv, VirtualRunEnv
from conan.tools.files import apply_conandata_patches, check_sha256, copy, export_conandata_patches, get, unzip
from conan.tools.gnu import AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibslaxConan(ConanFile):
    name = "libslax"
    version = "3.1.6"
    description = "C implementation of the SLAX language"
    license = "BSD-3-Clause"
    homepage = "https://github.com/Juniper/libslax"
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"libslax supports Linux and OHOS targets, got {self.settings.os}"
            )
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        self.requires("libxml2/2.15.3")
        self.requires("libxslt/1.1.45.2")
        self.requires("curl/8.15.0")

    def build_requirements(self):
        self.tool_requires("bison/3.8.2")
        self.tool_requires("m4/1.4.19")

    def layout(self):
        basic_layout(self)

    def source(self):
        source = self.conan_data["sources"]
        staged = os.path.join(
            os.path.expanduser("~"), "Download", source["filename"]
        )
        if os.path.isfile(staged):
            check_sha256(self, staged, source["sha256"])
            unzip(
                self,
                staged,
                destination=self.source_folder,
                strip_root=True,
            )
        else:
            get(self, **source, strip_root=True)

    def generate(self):
        VirtualBuildEnv(self).generate()
        AutotoolsDeps(self).generate()

        runtime_env = VirtualRunEnv(self).environment()
        tmpdir = os.path.join(self._build_root(), "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        runtime_env.define("TMPDIR", tmpdir)
        runtime_env.vars(self, scope="build").save_script("libslax_native_env")

        tc = AutotoolsToolchain(self)
        libxml2 = self.dependencies["libxml2"].package_folder
        libxslt = self.dependencies["libxslt"].package_folder
        curl = self.dependencies["cu" + "rl"].package_folder

        tc.configure_args.extend(
            [
                f"--with-libxml-prefix={libxml2}",
                f"--with-libxslt-prefix={libxslt}",
                f"--with-libcurl-prefix={curl}",
                "--disable-readline",
                "--disable-libedit",
            ]
        )

        if self.options.shared:
            tc.configure_args.extend(["--enable-shared", "--disable-static"])
        else:
            tc.configure_args.extend(["--disable-shared", "--enable-static"])

        tc.generate()

    def _build_root(self):
        return "/data/storage/el2/base/.conan-build-libslax-3.1.6"

    def build(self):
        apply_conandata_patches(self)

        root = self._build_root()
        work = os.path.join(root, "src")
        tmpdir = os.path.join(root, "tmp")

        if os.path.isdir(root):
            shutil.rmtree(root, ignore_errors=True)

        os.makedirs(work, exist_ok=True)
        os.makedirs(tmpdir, exist_ok=True)
        shutil.copytree(self.source_folder, work, dirs_exist_ok=True)

        libxml2 = self.dependencies["libxml2"].package_folder
        libxslt = self.dependencies["libxslt"].package_folder
        curl = self.dependencies["cu" + "rl"].package_folder

        bison_root = self.dependencies.build["bison/3.8.2"].package_folder
        m4_root = self.dependencies.build["m4/1.4.19"].package_folder
        bison_pkgdatadir = os.path.join(bison_root, "share", "bison")
        bison_program = os.path.join(bison_root, "bin", "bison")
        m4_program = os.path.join(m4_root, "bin", "m4")
        config_shell = shutil.which("sh") or "/bin/sh"
        cc_program = shutil.which("clang") or "/data/service/hnp/bin/clang"
        cxx_program = shutil.which("clang++") or "/data/service/hnp/bin/clang++"

        clang_real = os.path.realpath(cc_program)
        llvm_root = os.path.dirname(os.path.dirname(clang_real))
        llvm_lib = os.path.join(llvm_root, "lib")
        llvm_libxml = os.path.join(llvm_lib, "libxml2.so.16")

        linker_runtime_env = ""
        if os.path.isfile(llvm_libxml):
            linker_runtime_env = (
                " LD_LIBRARY_PATH="
                + shlex.quote(llvm_lib)
                + ":${LD_LIBRARY_PATH:-}"
            )

        build_tool_env = (
            "CONFIG_SHELL="
            + shlex.quote(config_shell)
            + " SHELL="
            + shlex.quote(config_shell)
            + " CC="
            + shlex.quote(cc_program)
            + " CXX="
            + shlex.quote(cxx_program)
            + " BISON="
            + shlex.quote(bison_program)
            + " BISON_PKGDATADIR="
            + shlex.quote(bison_pkgdatadir)
            + " M4="
            + shlex.quote(m4_program)
            + linker_runtime_env
        )

        configure_args = [
            "--prefix=/",
            "--bindir=/bin",
            "--sbindir=/bin",
            "--libdir=/lib",
            "--includedir=/include",
            f"--with-libxml-prefix={libxml2}",
            f"--with-libxslt-prefix={libxslt}",
            f"--with-libcurl-prefix={curl}",
            "--disable-readline",
            "--disable-libedit",
        ]

        if self.options.shared:
            configure_args.extend(["--enable-shared", "--disable-static"])
        else:
            configure_args.extend(["--disable-shared", "--enable-static"])

        link_dirs = [
            os.path.join(libxslt, "lib"),
            os.path.join(curl, "lib"),
            os.path.join(libxml2, "lib"),
        ]
        dependency_ldflags = " ".join(
            "-L" + shlex.quote(path) for path in link_dirs
        )

        try:
            self.run(
                build_tool_env
                + " CPPFLAGS=\"$CPPFLAGS -DLIBSLAX_OHOS=1\" LDFLAGS=\"$LDFLAGS "
                + dependency_ldflags
                + "\" ./configure "
                + " ".join(shlex.quote(arg) for arg in configure_args),
                cwd=work,
            )
        except Exception:
            config_log = os.path.join(work, "config.log")
            if os.path.isfile(config_log):
                print("===== BEGIN config.log =====")
                with open(config_log, "r", errors="replace") as f:
                    print(f.read())
                print("===== END config.log =====")
            raise
        self.run(build_tool_env + f" make -j{os.cpu_count() or 1}", cwd=work)

    def package(self):
        root = self._build_root()
        work = os.path.join(root, "src")
        install_dir = os.path.join(root, "install")

        if os.path.isdir(install_dir):
            shutil.rmtree(install_dir, ignore_errors=True)
        os.makedirs(install_dir, exist_ok=True)

        cc_program = shutil.which("clang") or "/data/service/hnp/bin/clang"
        clang_real = os.path.realpath(cc_program)
        llvm_root = os.path.dirname(os.path.dirname(clang_real))
        llvm_lib = os.path.join(llvm_root, "lib")
        llvm_libxml = os.path.join(llvm_lib, "libxml2.so.16")

        install_env = ""
        if os.path.isfile(llvm_libxml):
            install_env = (
                "LD_LIBRARY_PATH="
                + shlex.quote(llvm_lib)
                + ":${LD_LIBRARY_PATH:-} "
            )

        self.run(
            install_env
            + "make install DESTDIR="
            + shlex.quote(install_dir),
            cwd=work,
        )
        shutil.copytree(install_dir, self.package_folder, dirs_exist_ok=True, symlinks=True)
        for dirpath, _, filenames in os.walk(self.package_folder):
            for filename in filenames:
                if filename.endswith(".la"):
                    os.remove(os.path.join(dirpath, filename))

        copy(
            self,
            "Copyright",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.libs = ["slax"]
        self.cpp_info.set_property("pkg_config_name", "libslax")
