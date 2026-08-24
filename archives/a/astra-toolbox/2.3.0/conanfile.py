#!/usr/bin/env python3
"""Conan recipe for astra-toolbox 2.3.0 — High-performance GPU tomography primitives.

Upstream build system: autotools under build/linux (configure.ac + Makefile.in).
OHOS: configure only the core C++ library (libastra) with --with-cuda=no,
--without-matlab, --without-python. No CUDA/MATLAB/Python dependencies.
Only portability patch for build/linux/config.sub to recognize aarch64-linux-ohos.
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class AstraToolboxConan(ConanFile):
    name = "astra-toolbox"
    version = "2.3.0"
    description = "High-performance GPU primitives for 2D/3D tomography (FBP, SIRT, SART, CGLS)"
    license = "GPL-3.0-only"
    homepage = "https://www.astra-toolbox.com/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def build_requirements(self):
        # SDK provides autoconf 2.72 / m4 / perl; only automake/libtool missing.
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def layout(self):
        basic_layout(self)

    def source(self):
        # conandata.yml stores sources/patches keyed by version (e.g. "2.3.0")
        src = self.conan_data["sources"]
        if isinstance(src, dict) and self.version in src:
            src = src[self.version]
        get(self, **src, strip_root=True)

    def _prepare_build_env(self):
        tmpdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        os.chmod(tmpdir, 0o755)
        os.environ["TMPDIR"] = tmpdir
        bash = shutil.which("bash") or "/bin/sh"
        os.environ.setdefault("CONFIG_SHELL", bash)
        os.environ.setdefault("SHELL", bash)
        # aclocal needs libtool + pkg-config pkg.m4 locations
        aclocal_dirs = []
        pkg_config = shutil.which("pkg-config")
        if pkg_config:
            import glob as _glob
            for cand in _glob.glob(os.path.join(
                    os.path.dirname(os.path.dirname(pkg_config)),
                    "pkg-config.org", "pkg-config_*", "share", "aclocal")):
                if os.path.isdir(cand):
                    aclocal_dirs.append(cand)
            cand = os.path.join(
                os.path.dirname(os.path.dirname(pkg_config)), "share", "aclocal")
            if os.path.isdir(cand):
                aclocal_dirs.append(cand)
        for dep in self.dependencies.build.values():
            if dep.ref.name == "libtool":
                cand = os.path.join(dep.package_folder, "share", "aclocal")
                if os.path.isdir(cand):
                    aclocal_dirs.append(cand)
        existing = os.environ.get("ACLOCAL_PATH", "")
        extra = ":".join(d for d in aclocal_dirs if d)
        os.environ["ACLOCAL_PATH"] = ":".join(
            [d for d in [extra, existing] if d])
        return bash

    def _gnu_triplet(self, arch=None):
        arch = str(arch or self.settings.arch)
        mapping = {
            "armv8": "aarch64-unknown-linux-gnu",
            "armv8.3": "aarch64-unknown-linux-gnu",
            "aarch64": "aarch64-unknown-linux-gnu",
            "x86_64": "x86_64-unknown-linux-gnu",
        }
        triplet = mapping.get(arch)
        if not triplet:
            raise ConanInvalidConfiguration(f"Unsupported arch: {arch}")
        return triplet

    def _create_mktemp_wrapper(self):
        wrapper_dir = os.path.join(self.build_folder, "mktemp-wrapper")
        os.makedirs(wrapper_dir, exist_ok=True)
        wrapper = os.path.join(wrapper_dir, "mktemp")
        if not os.path.exists(wrapper):
            with open(wrapper, "w", encoding="utf-8") as f:
                f.write("""#!/bin/sh
mode=""
for a in \"$@\"; do
  case \"$a\" in -d) mode=\"-d\" ;; esac
done
if [ \"$mode\" != \"-d\" ]; then
  exec /usr/bin/mktemp \"$@\"
fi
dir=\"\"
for a in \"$@\"; do
  case \"$a\" in -d) ;; *) dir=\"$a\" ;; esac
done
[ -n \"$dir\" ] || dir=\"./tmp.XXXXXX\"
base=$(dirname \"$dir\")
pat=$(basename \"$dir\")
out=\"\"
i=0
while [ -z \"$out\" ] && [ $i -lt 100 ]; do
  cand=\"$base/$(echo \"$pat\" | sed \"s/XXXXXX/$$-$RANDOM/\")\"
  if (umask 077 && mkdir -p \"$cand\" 2>/dev/null); then out=\"$cand\"; fi
  i=$((i+1))
done
if [ -n \"$out\" ]; then echo \"$out\"; exit 0; fi
exit 1
""")
            os.chmod(wrapper, 0o755)
        return wrapper_dir

    def generate(self):
        bash = self._prepare_build_env()
        _ = bash
        host_triplet = self._gnu_triplet()
        build_arch = self.settings_build.get_safe("arch") if self.settings_build else None
        build_triplet = self._gnu_triplet(build_arch or self.settings.arch)
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend([
            f"--build={build_triplet}",
            f"--host={host_triplet}",
            "--with-cuda=no",
        ])
        if not self.options.shared:
            tc.configure_args.extend(["--disable-shared", "--enable-static"])
        else:
            tc.configure_args.extend(["--enable-shared", "--disable-static"])
        # autoconf on OHOS needs writable tmp for config.status mktemp -d
        env = tc.environment()
        env.prepend_path("PATH", self._create_mktemp_wrapper())
        tc.generate(env=env)

    def build(self):
        bash = self._prepare_build_env()
        apply_conandata_patches(self)
        build_linux = os.path.join(self.source_folder, "build", "linux")
        # autogen.sh generates configure from configure.ac (tarball ships only configure.ac)
        if not os.path.exists(os.path.join(build_linux, "configure")):
            self.run(f"{bash} -e {os.path.join(build_linux, 'autogen.sh')}", cwd=build_linux, env="conanbuild")
        if not os.path.exists(os.path.join(build_linux, "configure")):
            raise ConanException("autogen.sh did not produce build/linux/configure")
        autotools = Autotools(self)
        autotools.configure(build_script_folder=build_linux)
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        # With --with-cuda=no etc the default `install` only runs
        # install-libraries (headers are under `install-headers` / `install-dev`).
        # Copy public headers + pkg-config manually so the package is usable.
        copy(self, "*.h", src=os.path.join(self.source_folder, "include"), dst=os.path.join(self.package_folder, "include"))
        copy(self, "*.inl", src=os.path.join(self.source_folder, "include"), dst=os.path.join(self.package_folder, "include"))
        # libastra.pc is generated in build/linux during configure
        for base in (self.build_folder, os.path.join(self.build_folder, "build", "linux"), os.path.join(self.source_folder, "build", "linux")):
            cand = os.path.join(base, "libastra.pc")
            if os.path.isfile(cand):
                copy(self, "libastra.pc", src=base, dst=os.path.join(self.package_folder, "lib", "pkgconfig"))
                break
        copy(self, "COPYING", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["astra"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.set_property("pkg_config_name", "libastra")
