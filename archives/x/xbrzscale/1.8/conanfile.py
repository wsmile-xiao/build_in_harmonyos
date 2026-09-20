#!/usr/bin/env python3
"""Conan recipe — xbrzscale 1.8 (plain Makefile, SDL2 tool + static lib).

xbrzscale is a command line image upscaling tool built on the xBRZ
"scale by rules" algorithm (bundled under xbrz/, version 1.8). Upstream
ships a minimal hand-written Makefile (no configure/CMake/Meson) that
produces libxbrzscale.a plus the xbrzscale CLI binary, linked against
SDL2 and SDL2_image.

Adaptation notes (HarmonyOS PC, aarch64):
    * W0: two published in-tree dependencies — sdl2/2.30.10.1 and
      sdl2_image/2.6.0.1 (the libpng-backed SDL2_image variant, so the
      tool's IMG_Load/IMG_SavePNG PNG path is guaranteed; the STB-only
      fallback of the default variant is not relied upon). The transitive
      closure (libpng/libjpeg-turbo/libwebp/zlib) is pinned to ohpcd RREVs
      plus repo-unique zlib/1.3.1.1 with override=True: preflight resolves
      conancenter first, where the same bare versions hit CCI recipes whose
      tool_requires("cmake") pulls CCI cmake/4.4.x with no OHOS sources
      entry (KeyError: 'OHOS'); the pins keep the graph on the hardened
      in-repo recipes (ayatana-ido/pycairo/libtiger/cataract precedents).
    * The upstream Makefile hardcodes `g++` and calls backtick
      `sdl2-config`, ignoring CC/CXX/CFLAGS/LDFLAGS, so plain `make`
      cannot carry Conan flags. build() therefore mirrors the upstream
      Makefile step-for-step with explicit commands (same sources, same
      -std=c++17, same -DNDEBUG on xbrz.cpp, same `ar qc` archive):
      compiler and ar come from tools.build:compiler_executables plus
      tools.build:cxxflags/defines/exelinkflags (R33: never a bare shell
      $CC), include/lib flags are aggregated from self.dependencies.
    * No patches: the upstream sources need no OHOS modification.
    * Upstream ships no test suite (no check/test target, no tests/
      directory — audited in test_package/MANIFEST.yml); build() guards
      this by failing if a check/test target ever appears, so the
      no_tests audit cannot silently go stale.
    * package() installs bin/xbrzscale (ELF-signed on OHOS, chmod 755),
      lib/libxbrzscale.a and headers (libxbrzscale.h + xbrz/*.h).
      Software-level commands.json declares the CLI tool (R38).

Artifacts: bin/xbrzscale + lib/libxbrzscale.a + include/*.h
License: GPL-3.0-only.
"""

import os
import shutil
import stat
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class XbrzscaleConan(ConanFile):
    name = "xbrzscale"
    version = "1.8"
    description = "Image upscaling command line tool using the xBRZ algorithm"
    license = "GPL-3.0-only"
    homepage = "https://github.com/atheros/xbrzscale"
    url = "https://github.com/atheros/xbrzscale"
    topics = ("image", "upscaling", "xbrz", "sdl2", "cli")
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("sdl2/2.30.10.1")
        self.requires("sdl2_image/2.6.0.1")
        # CCI-competition closure (preflight resolves conancenter first while
        # CI disables it): bare libpng/libjpeg-turbo/libwebp collide with CCI
        # recipes whose tool_requires("cmake") pulls CCI cmake/4.4.x, whose
        # conandata has no OHOS sources entry (KeyError: 'OHOS' at build()
        # line 35). Pin version-preserving ohpcd RREVs so the transitive
        # closure stays on the hardened in-repo recipes (bare cmake +
        # ohos.toolchain / autotools, zero tool_requires); same versions keep
        # sdl2_image's package_id untouched. RREVs are ohpcd-API-verified
        # single revisions (ayatana-ido/0.10.4-v2, pycairo/1.29.0,
        # python3-cairo/1.29.1, libtiger/0.3.4 precedents). zlib uses the
        # repo-unique 1.3.1.1 (what the published libpng/1.6.58 binary was
        # built against; vips/8.18.4.1 precedent).
        self.requires(
            "libpng/1.6.58#d25df07aba0399181f60ee377e83d701",
            override=True,
        )
        self.requires(
            "libjpeg-turbo/3.2.0#5ed08e7ff848da8fdf6b7bca74354560",
            override=True,
        )
        self.requires(
            "libwebp/1.6.0#8b273a5128ee70c508671933b61288ec",
            override=True,
        )
        self.requires("zlib/1.3.1.1", override=True)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # No toolchain file needed: build() resolves the compiler and all
        # dependency flags directly from Conan conf and self.dependencies
        # (R33), so there is nothing to generate here.
        pass

    def _resolve_tool(self, configured, names):
        # The profile conf tools.build:compiler_executables may point at an
        # SDK path that is inaccessible on the executing worker
        # ("/bin/sh: .../clang++: inaccessible or not found", Error 127).
        # Prefer the configured absolute path only when the file exists;
        # otherwise fall back to PATH lookup (hmbs/profile prepend the
        # worker's tool directories). libcoverart/fceux precedent.
        if configured and os.path.isfile(configured):
            return configured
        for name in names:
            found = shutil.which(name)
            if found:
                self.output.info(
                    "xbrzscale: conf tool path unusable ({}), "
                    "fall back to PATH: {}".format(configured, found)
                )
                return found
        self.output.warning(
            "xbrzscale: no PATH fallback for {}, keep conf value: {}".format(
                names, configured
            )
        )
        return configured or names[0]

    def _compilers(self):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cxx = self._resolve_tool(
            compilers.get("cpp") or compilers.get("c"), ("clang++",)
        )
        cc = self._resolve_tool(compilers.get("c"), ("clang",))
        ar = self._resolve_tool(compilers.get("ar"), ("llvm-ar", "ar"))
        return cxx, cc, ar

    def _conf_flags(self, key):
        value = self.conf.get(key, default="", check_type=str) or ""
        return value.split()

    def _dep_abs_dirs(self, attr):
        seen = set()
        ordered = []
        for dep in self.dependencies.values():
            if not dep.package_folder:
                # Override-only / unresolved node (an override no other
                # recipe in the closure requires): it contributes no paths.
                # Logged so the next preflight shows which node it was.
                self.output.info(
                    "xbrzscale: skip dep without package folder: {}".format(
                        dep.ref
                    )
                )
                continue
            candidates = []
            candidates.extend(getattr(dep.cpp_info, attr, []) or [])
            for component in getattr(dep.cpp_info, "components", {}).values():
                candidates.extend(getattr(component, attr, []) or [])
            for entry in candidates:
                if not isinstance(entry, str) or not entry:
                    continue
                path = entry
                if not os.path.isabs(path):
                    path = os.path.normpath(
                        os.path.join(dep.package_folder, entry)
                    )
                if path not in seen and os.path.isdir(path):
                    seen.add(path)
                    ordered.append(path)
        return ordered

    def _sdl_cflags(self):
        flags = []
        for inc in self._dep_abs_dirs("includedirs"):
            flags.append("-I{}".format(inc))
        flags.append("-D_REENTRANT")
        flags.extend(self._conf_flags("tools.build:cxxflags"))
        for define in self._conf_flags("tools.build:defines"):
            flags.append("-D{}".format(define))
        return flags

    def _link_libs(self):
        """Link libraries in dependency order (dependents first).

        sdl2_image references SDL symbols, so SDL2_image precedes SDL2;
        the remaining (shared) transitive libraries are order-insensitive
        and appended in deterministic name order; system libraries last.
        SDL2main/SDL2test components are excluded: upstream links neither
        (it defines its own main and uses no test framework).
        """
        image_libs = []
        sdl_libs = []
        other_libs = []
        system_libs = []
        for dep in self.dependencies.values():
            top_libs = list(getattr(dep.cpp_info, "libs", []) or [])
            top_system = list(getattr(dep.cpp_info, "system_libs", []) or [])
            comp_libs = []
            comp_system = []
            for comp_name, component in getattr(
                dep.cpp_info, "components", {}
            ).items():
                if dep.ref.name == "sdl2" and comp_name != "SDL2":
                    continue
                comp_libs.extend(getattr(component, "libs", []) or [])
                comp_system.extend(getattr(component, "system_libs", []) or [])
            libs = top_libs + comp_libs
            system = top_system + comp_system
            if dep.ref.name == "sdl2_image":
                image_libs.extend(libs)
            elif dep.ref.name == "sdl2":
                sdl_libs.extend(libs)
            else:
                other_libs.extend(libs)
            system_libs.extend(system)
        other_libs = sorted(set(other_libs))
        ordered = image_libs + other_libs + sdl_libs
        seen = set()
        libs = [lib for lib in ordered if not (lib in seen or seen.add(lib))]
        seen_sys = set()
        systems = [
            lib for lib in system_libs if not (lib in seen_sys or seen_sys.add(lib))
        ]
        return libs, systems

    def _link_flags(self):
        flags = []
        for libdir in self._dep_abs_dirs("libdirs"):
            flags.append("-L{}".format(libdir))
        libs, systems = self._link_libs()
        for lib in libs:
            flags.append("-l{}".format(lib))
        for lib in systems:
            flags.append("-l{}".format(lib))
        flags.extend(self._conf_flags("tools.build:exelinkflags"))
        return flags

    def _assert_no_upstream_tests(self):
        makefile = os.path.join(self.source_folder, "Makefile")
        targets = set()
        if os.path.isfile(makefile):
            with open(makefile, "r", encoding="utf-8", errors="replace") as handle:
                for line in handle:
                    if line and not line[0].isspace() and ":" in line:
                        targets.add(line.split(":", 1)[0].strip())
        for forbidden in ("check", "test"):
            if forbidden in targets:
                raise ConanException(
                    "xbrzscale upstream gained a '{}' target — the no_tests "
                    "audit in test_package/MANIFEST.yml must be revisited "
                    "instead of silently skipping it".format(forbidden)
                )

    def build(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanException("xbrzscale requires a POSIX host (Linux or OHOS)")
        apply_conandata_patches(self)
        self._assert_no_upstream_tests()
        cxx, _cc, ar = self._compilers()
        cflags = self._sdl_cflags()
        ldflags = self._link_flags()
        self.output.info("xbrzscale cxx: {}".format(cxx))
        self.output.info("xbrzscale cflags: {}".format(" ".join(cflags)))
        self.output.info("xbrzscale ldflags: {}".format(" ".join(ldflags)))

        def run(cmd):
            self.run(cmd, cwd=self.source_folder, env="conanbuild")

        # Mirror of the upstream Makefile (same files, same -std=c++17,
        # same -DNDEBUG on xbrz.cpp, same `ar qc` archive), with the
        # compiler and flags injected from Conan instead of hardcoded g++.
        run(
            "{cxx} -std=c++17 -DNDEBUG -c xbrz/xbrz.cpp -o xbrz/xbrz.o {flags}".format(
                cxx=cxx, flags=" ".join(cflags)
            )
        )
        run(
            "{cxx} -std=c++17 -c libxbrzscale.cpp -o libxbrzscale.o {flags}".format(
                cxx=cxx, flags=" ".join(cflags)
            )
        )
        run(
            "{cxx} -std=c++17 -c xbrzscale.cpp -o xbrzscale.o {flags}".format(
                cxx=cxx, flags=" ".join(cflags)
            )
        )
        run("{ar} qc libxbrzscale.a libxbrzscale.o xbrz/xbrz.o".format(ar=ar))
        run(
            "{cxx} -o xbrzscale xbrzscale.o libxbrzscale.a {flags}".format(
                cxx=cxx, flags=" ".join(ldflags)
            )
        )

    def _sign_elf(self, path):
        if str(self.settings.os) != "OHOS":
            return
        signer = shutil.which("binary-sign-tool") or "/data/service/hnp/bin/binary-sign-tool"
        objcopy = shutil.which("llvm-objcopy") or "/data/service/hnp/bin/llvm-objcopy"
        if not os.path.isfile(signer):
            raise ConanException(
                "OHOS ELF signing requires binary-sign-tool: {}".format(path)
            )
        self.run(
            '{} --remove-section .codesign "{}"'.format(objcopy, path),
            ignore_errors=True,
        )
        tmp = path + ".signed"
        self.run(
            '{} sign -inFile "{}" -outFile "{}" -selfSign 1'.format(signer, path, tmp)
        )
        if os.path.isfile(tmp):
            os.replace(tmp, path)
        os.chmod(
            path,
            stat.S_IMODE(os.stat(path).st_mode)
            | stat.S_IXUSR
            | stat.S_IXGRP
            | stat.S_IXOTH,
        )

    def package(self):
        bindir = os.path.join(self.package_folder, "bin")
        libdir = os.path.join(self.package_folder, "lib")
        os.makedirs(bindir, exist_ok=True)
        os.makedirs(libdir, exist_ok=True)
        copy(self, "xbrzscale", src=self.source_folder, dst=bindir, keep_path=False)
        copy(self, "libxbrzscale.a", src=self.source_folder, dst=libdir, keep_path=False)
        copy(self, "libxbrzscale.h", src=self.source_folder, dst=os.path.join(self.package_folder, "include"), keep_path=False)
        copy(self, "*.h", src=self.source_folder, dst=os.path.join(self.package_folder, "include"), keep_path=True)
        copy(self, "License.txt", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
        binary = os.path.join(bindir, "xbrzscale")
        if os.path.isfile(binary):
            os.chmod(binary, 0o755)
            self._sign_elf(binary)

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "xbrzscale")
        self.cpp_info.set_property("cmake_target_name", "xbrzscale::xbrzscale")
        self.cpp_info.set_property("pkg_config_name", "xbrzscale")
        self.cpp_info.libs = ["xbrzscale"]
        self.cpp_info.requires = ["sdl2_image::sdl2_image", "sdl2::sdl2"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = ["lib"]
        self.runenv_info.prepend_path(
            "PATH", os.path.join(self.package_folder, "bin")
        )
