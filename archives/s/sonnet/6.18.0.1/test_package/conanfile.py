#!/usr/bin/env python3
import glob
import os
import shutil
import shlex
import stat

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class SonnetTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"

    def _resign_copied_libs(self):
        """Re-sign the shared objects copied into the runtime directory.

        A shared object copied out of a Conan package loses its effective code
        signing, so the OHOS loader refuses it: the run fails with
        "Error loading shared library libfontconfig.so.1: ..." followed by every
        Fc* symbol of libQt6Gui reported missing, even though the symbols are
        present in the file. The library loads fine straight from the package
        folder, and re-signing the copy in its new location makes the test
        executable run. Measured directly on an OHOS PC device:

            cache original            -> "Permission denied"
            plain copy, mode 0750     -> "Permission denied"
            plain copy, mode 0777     -> "Permission denied"
            re-signed copy, mode 0750 -> loaded

        So the mode bits are irrelevant and the signature is what matters.
        """
        import os as _os
        import stat as _stat
        import subprocess as _sp

        ELF_MAGIC = bytes([0x7F]) + b"ELF"

        def _find_signer():
            candidates = [
                _os.environ.get("OHOS_BINARY_SIGN_TOOL"),
                _os.environ.get("BINARY_SIGN_TOOL"),
            ]
            sdk = _os.environ.get("OHOS_SDK_ROOT")
            if sdk:
                candidates.append(_os.path.join(sdk, "bin", "binary-sign-tool"))
            candidates.extend(
                [
                    "/data/service/hnp/bin/binary-sign-tool",
                    _os.path.expanduser("~/usr/local/bin/binary-sign-tool"),
                ]
            )
            found = shutil.which("binary-sign-tool")
            if found:
                candidates.append(found)
            for c in candidates:
                if c and _os.path.isfile(c) and _os.access(c, _os.X_OK):
                    return c
            return None

        signer = _find_signer()
        if not signer:
            self.output.warning(
                "binary-sign-tool not found; copied libraries keep their broken "
                "signature and the test executable may fail to load them"
            )
            return

        roots = [self.cpp.build.bindirs[0], self.build_folder]
        candidates = []
        for root in roots:
            if not root or not _os.path.isdir(root):
                continue
            for cur, _dirs, files in _os.walk(root):
                for name in files:
                    if name.endswith(".so") or ".so." in name:
                        candidates.append(_os.path.join(cur, name))

        signed = 0
        inspected = 0
        seen = set()
        for p in candidates:
            ap = _os.path.abspath(p)
            if ap in seen:
                continue
            seen.add(ap)
            if not _os.path.isfile(p) or _os.path.islink(p):
                continue
            try:
                with open(p, "rb") as fh:
                    if fh.read(4) != ELF_MAGIC:
                        continue
            except OSError:
                continue
            inspected += 1
            tmp = p + ".resign"
            ok = False
            for args in (
                [signer, "sign", "-selfSign", "1", "-inFile", p, "-outFile", tmp],
                [signer, "sign", "-selfSign", "1", "-inFile", p, "-outFile", tmp,
                 "-profile", "ohos"],
            ):
                try:
                    r = _sp.run(args, capture_output=True)
                except OSError:
                    continue
                if r.returncode == 0 and _os.path.isfile(tmp) and _os.path.getsize(tmp) > 0:
                    _os.replace(tmp, p)
                    _os.chmod(
                        p,
                        _os.stat(p).st_mode | _stat.S_IXUSR | _stat.S_IXGRP | _stat.S_IXOTH,
                    )
                    signed += 1
                    ok = True
                    break
            if _os.path.isfile(tmp):
                _os.remove(tmp)
            if not ok:
                self.output.info("re-sign failed for {}".format(_os.path.basename(p)))
        self.output.info(
            "re-signed {}/{} copied ELF libraries before running tests".format(signed, inspected)
        )

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("qtbase/6.11.1.3")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        toolchain = CMakeToolchain(self)
        runtime_libs = []
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                runtime_libs.append(os.path.join(dep.package_folder, "lib"))
        # Embed dependency locations so the OHOS loader does not rely on
        # Conan cache symlink aliases at test runtime.
        if runtime_libs:
            toolchain.variables["CMAKE_BUILD_RPATH"] = ";".join(runtime_libs)
            toolchain.variables["CMAKE_INSTALL_RPATH"] = ";".join(runtime_libs)
        toolchain.generate()
        self._write_cmake_paths()

    def _write_cmake_paths(self):
        lines = ["set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)"]
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                lines.extend(
                    [
                        f'list(PREPEND CMAKE_PREFIX_PATH "{dep.package_folder}/lib/cmake")',
                        f'list(PREPEND CMAKE_LIBRARY_PATH "{dep.package_folder}/lib")',
                        f'list(PREPEND CMAKE_INCLUDE_PATH "{dep.package_folder}/include")',
                    ]
                )
        lines.extend(
            [
                'list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_LIST_DIR}")',
                'list(PREPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}")',
            ]
        )
        paths_file = os.path.join(self.generators_folder, "conan_cmakedeps_paths.cmake")
        with open(paths_file, "w") as f:
            f.write("\n".join(lines) + "\n")

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        runtime_dir = self._prepare_runtime_links()
        env = Environment()
        library_paths = [runtime_dir]
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                libdir = os.path.join(dep.package_folder, "lib")
                library_paths.append(libdir)
                env.prepend_path("QT_PLUGIN_PATH", os.path.join(dep.package_folder, "plugins"))
                env.prepend_path("QT_PLUGIN_PATH", os.path.join(dep.package_folder, "lib", "plugins"))
        env.define("QT_QPA_PLATFORM", "offscreen")
        test_exe = os.path.join(runtime_dir, "test_sonnet")
        # The Conan cache is non-executable to the OHOS app launcher. Libraries
        # were copied to runtime_dir above, beside the executable, so dlopen()
        # must use this allowed absolute directory instead.
        runtime_prefix = "SONNET_RUNTIME_DIR={} LD_LIBRARY_PATH={} QT_QPA_PLATFORM=offscreen".format(
            shlex.quote(runtime_dir), shlex.quote(os.pathsep.join(library_paths))
        )
        with env.vars(self).apply():
            self.run(
                '{} ctest --test-dir {} --output-on-failure --no-tests=error'.format(
                    runtime_prefix, shlex.quote(self.build_folder)
                ),
                env="",
            )
            self.run('{} {}'.format(runtime_prefix, shlex.quote(test_exe)), env="")

    def _prepare_runtime_links(self):
        runtime_dir = os.path.abspath(self.build_folder)
        os.makedirs(runtime_dir, exist_ok=True)
        for dep in self.dependencies.values():
            libdir = os.path.join(dep.package_folder, "lib") if dep.package_folder else None
            if not libdir or not os.path.isdir(libdir):
                continue
            for src in glob.glob(os.path.join(libdir, "lib*.so*")):
                dst = os.path.join(runtime_dir, os.path.basename(src))
                if os.path.abspath(src) == os.path.abspath(dst):
                    continue
                # Copy the target rather than retaining cache-relative symlinks.
                # OHOS requires execute permission when a shared object is
                # mapped by dlopen(), while Conan cache artifacts are 0644.
                shutil.copy2(src, dst, follow_symlinks=True)
                os.chmod(dst, os.stat(dst).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        # HMDFS may not resolve Conan's versioned symlink aliases. Materialize
        # the SONAME names required by the test executable.
        for stem in ("libKF6SonnetCore", "libKF6SonnetUi"):
            target = os.path.join(runtime_dir, stem + ".so.6")
            if not os.path.isfile(target):
                candidates = glob.glob(os.path.join(runtime_dir, stem + ".so.*"))
                candidates = [p for p in candidates if os.path.basename(p) != stem + ".so.6"]
                if candidates:
                    shutil.copy2(candidates[0], target)
                    os.chmod(target, os.stat(target).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
            if not os.path.isfile(target):
                raise RuntimeError("Missing consumer runtime library: {}".format(os.path.basename(target)))
        # The copies above are what the loader will actually open, so they must
        # carry a signature that is valid at their new location.
        self._resign_copied_libs()
        return runtime_dir
