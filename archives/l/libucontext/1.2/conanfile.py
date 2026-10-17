import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    rmdir,
)
from conan.tools.layout import basic_layout


def _sdk_llvm_libdir(compiler):
    """Return the active SDK llvm/lib containing lld's libxml2 runtime."""
    candidates = []
    if compiler:
        try:
            resource_dir = subprocess.check_output(
                [compiler, "-print-resource-dir"],
                stderr=subprocess.DEVNULL,
                text=True,
            ).strip()
            candidates.append(os.path.dirname(os.path.dirname(resource_dir)))
        except (OSError, subprocess.CalledProcessError):
            pass
        compiler = os.path.realpath(compiler)
        candidates.append(
            os.path.join(os.path.dirname(os.path.dirname(compiler)), "lib")
        )

    for candidate in dict.fromkeys(candidates):
        if os.path.isfile(os.path.join(candidate, "libxml2.so.16")):
            return candidate
    return ""


class LibucontextConan(ConanFile):
    name = "libucontext"
    version = "1.2"
    description = "ucontext implementation featuring glibc-compatible ABI"
    license = "ISC"
    homepage = "https://github.com/kaniini/libucontext"
    url = "https://github.com/kaniini/libucontext"
    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _make_arguments(self):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = compilers.get("c") or "clang"
        ar = compilers.get("ar") or "llvm-ar"
        ranlib = compilers.get("ranlib") or "llvm-ranlib"
        arch = "aarch64" if str(self.settings.arch) == "armv8" else str(self.settings.arch)
        if str(self.settings.os) == "OHOS":
            cc = f"{cc} --target={arch}-linux-ohos"
        return f'ARCH={arch} CC="{cc}" AR="{ar}" RANLIB="{ranlib}"'

    def _build_environment(self):
        environment = Environment()
        if str(self.settings.os) != "OHOS":
            return environment

        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        sdk_llvm_lib = _sdk_llvm_libdir(compilers.get("c") or "clang")
        if not sdk_llvm_lib:
            return environment

        lld = os.path.join(os.path.dirname(sdk_llvm_lib), "bin", "lld")
        probe_env = os.environ.copy()
        probe_env["LD_LIBRARY_PATH"] = os.pathsep.join(
            part
            for part in (sdk_llvm_lib, probe_env.get("LD_LIBRARY_PATH", ""))
            if part
        )
        try:
            probe = subprocess.run(
                [lld, "-flavor", "gnu", "--version"],
                env=probe_env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                text=True,
                timeout=10,
                check=False,
            )
        except (OSError, subprocess.SubprocessError) as error:
            raise ConanException(
                f"Cannot execute the active OHOS SDK linker {lld}: {error}"
            ) from error
        if probe.returncode != 0:
            raise ConanException(
                f"The active OHOS SDK linker failed its GNU-flavor probe: "
                f"{lld}; stderr={probe.stderr.strip()!r}"
            )

        self.output.info(
            f"Prepending OHOS SDK linker runtime path: {sdk_llvm_lib}"
        )
        environment.prepend_path("LD_LIBRARY_PATH", sdk_llvm_lib)
        return environment

    def build(self):
        apply_conandata_patches(self)
        os.chdir(self.source_folder)
        with self._build_environment().vars(self).apply():
            self.run(f"make {self._make_arguments()} -j1 all")
            if can_run(self):
                self.run(f"make {self._make_arguments()} -j1 check")

    def package(self):
        os.chdir(self.source_folder)
        staging_folder = os.path.join(self.source_folder, "package-staging")
        rmdir(self, staging_folder)
        with self._build_environment().vars(self).apply():
            self.run(
                f"make {self._make_arguments()} -j1 install "
                "DESTDIR=package-staging/ LIBDIR=lib "
                f"INCLUDEDIR=include PKGCONFIGDIR=lib/pkgconfig"
            )
        copy(self, "*", src=staging_folder, dst=self.package_folder)
        suffixes = (".a",) if self.options.shared else (".so", ".so.1")
        stems = ("libucontext", "libucontext_posix")
        for stem in stems:
            for suffix in suffixes:
                path = os.path.join(self.package_folder, "lib", stem + suffix)
                if os.path.isfile(path) or os.path.islink(path):
                    os.remove(path)
        if self.options.shared:
            posix_link = os.path.join(
                self.package_folder, "lib", "libucontext_posix.so"
            )
            if not os.path.lexists(posix_link):
                try:
                    os.symlink("libucontext_posix.so.1", posix_link)
                except OSError:
                    shutil.copy2(
                        os.path.join(
                            self.package_folder, "lib", "libucontext_posix.so.1"
                        ),
                        posix_link,
                    )

    def package_info(self):
        self.cpp_info.libs = ["ucontext_posix", "ucontext"]
