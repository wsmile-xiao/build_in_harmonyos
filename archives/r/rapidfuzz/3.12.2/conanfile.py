#!/usr/bin/env python3
"""Conan recipe for rapidfuzz 3.12.2 — Python C extension (CMake build).

rapidfuzz is a rapid fuzzy string matching library for Python. The C extensions
are built via CMake with Cython-generated .cxx sources (pre-generated in sdist).

Toolchain note (E-CI-locale-stub): OHOS has two clang-15 C++ environments and
they are NOT interchangeable.
  * The OHOS-native SDK clang (/data/service/hnp/bin/clang) resolves libc++
    itself — libcxx-ohos — whose __support/musl/xlocale.h *already defines*
    strtoll_l/strtoull_l unconditionally.
  * A DevEco Studio clang has no C++ headers on its default search path, and
    its libc++ 15 leaves strtoll_l/strtoull_l undeclared.
So build() probes the compiler instead of hardcoding either answer: forcing a
shim on the SDK clang fails with "error: redefinition of 'strtoll_l'", while a
hardcoded DevEco include path is meaningless on the CI worker.
"""
import glob
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get, copy, save
from conan.tools.layout import basic_layout


_BASE_CXX_FLAGS = "-stdlib=libc++ -D_LIBCPP_PROVIDES_DEFAULT_RUNE_TABLE"

_LOCALE_STUB = '''#ifndef RAPIDFUZZ_OHOS_LOCALE_STUB_H
#define RAPIDFUZZ_OHOS_LOCALE_STUB_H
#include <stdlib.h>
#include <locale.h>
static inline long long strtoll_l(const char *nptr, char **endptr, int base, locale_t loc) {
    (void)loc; return strtoll(nptr, endptr, base);
}
static inline unsigned long long strtoull_l(const char *nptr, char **endptr, int base, locale_t loc) {
    (void)loc; return strtoull(nptr, endptr, base);
}
#endif
'''


class RapidfuzzConan(ConanFile):
    name = "rapidfuzz"
    version = "3.12.2"
    description = "rapid fuzzy string matching for Python"
    license = "MIT"
    homepage = "https://github.com/rapidfuzz/RapidFuzz"
    url = "https://pypi.org/project/rapidfuzz/"
    topics = ("fuzzy", "string-matching", "levenshtein", "python")

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        pass

    def requirements(self):
        self.requires("python/3.12.9")

    def layout(self):
        basic_layout(self)

    def source(self):
        # This sdist is 57.9MB — the largest PyPI source in this repo. The
        # worker link stalls mid-transfer ("Read timed out"), and conan's
        # defaults (retry=2, retry_wait=5) only allow 3 attempts, all of which
        # died at ~3.7MB in CI #62695. Widen the retry budget; same idiom as
        # openfast/5.0.0.
        #
        # The retry budget alone is NOT sufficient, and was not what actually
        # fixed CI #62819/#62860: with files.pythonhosted.org capped at ~10-15KB/s
        # from the workers, a clean run still needs ~4000s for the download, over
        # the 3600s cap, so builds died at 93% (54.3MB) twice on two different
        # workers. The real fix is the ordered mirror list in conandata.yml
        # (~2700x faster, byte-identical). retry/retry_wait stay as belt-and-braces
        # for the mirror path, which can still drop a connection.
        get(self, **self.conan_data["sources"], strip_root=True,
            retry=6, retry_wait=15)

    def generate(self):
        pass

    def _probe(self, cxx, flags, code, tag):
        """Try to compile `code` with `cxx`; True when it succeeds.

        Syntax-only on purpose: the question is whether the driver can find and
        parse the headers, which has nothing to do with linking. Linking would
        fail for unrelated reasons (no libc++abi on the search path yet) and
        push the recipe down the wrong branch.

        Used instead of assuming a toolchain layout. Runs with ignore_errors
        and records success in a marker file so a failing probe is a decision,
        not a build abort.
        """
        src = os.path.join(self.build_folder, f"_probe_{tag}.cpp")
        save(self, src, code)
        ok = os.path.join(self.build_folder, f"_probe_{tag}.ok")
        log = os.path.join(self.build_folder, f"_probe_{tag}.log")
        if os.path.isfile(ok):
            os.remove(ok)
        self.run(
            f'{cxx} {flags} -fsyntax-only "{src}" > "{log}" 2>&1 '
            f'&& echo ok > "{ok}" || true',
            ignore_errors=True,
        )
        return os.path.isfile(ok)

    def _libcxx_include_dir(self, cxx):
        """Locate <llvm>/include/c++/v1 from the driver's own resource dir.

        Returns "" when the driver already resolves the C++ headers itself
        (the OHOS-native SDK clang), which is the CI case. No host-specific
        path is hardcoded, so this also works for a DevEco Studio SDK.
        """
        proc = subprocess.run([cxx, "-print-resource-dir"],
                              capture_output=True, text=True)
        res_dir = proc.stdout.strip() if proc.returncode == 0 else ""
        # <llvm>/lib/clang/<ver> -> strip three levels to reach <llvm>
        llvm = os.path.dirname(os.path.dirname(os.path.dirname(res_dir)))
        cand = os.path.join(llvm, "include", "c++", "v1") if res_dir else ""
        return cand if cand and os.path.isdir(cand) else ""

    def _toolchain_cxx_flags(self, cxx):
        """Probe the C++ toolchain and return the CXXFLAGS to build with.

        Returns (cxxflags, probe_flags) where probe_flags is the shell-quoted
        form used for the probes themselves.
        """
        # Probe 1: does the driver find the C++ standard library on its own?
        inc_dir = ""
        if not self._probe(cxx, _BASE_CXX_FLAGS,
                           "#include <atomic>\nint main(){return 0;}\n", "hdr"):
            inc_dir = self._libcxx_include_dir(cxx)
            if not inc_dir:
                raise ConanException(
                    "C++ standard library headers are not on the driver's search "
                    f"path and no <llvm>/include/c++/v1 exists next to it "
                    f"(clang: {cxx})")
            self.output.info(f"libc++ not on default search path; adding {inc_dir}")

        probe_flags = _BASE_CXX_FLAGS + (f' -I"{inc_dir}"' if inc_dir else "")

        # Probe 2: does this C++ library already provide strtoll_l/strtoull_l?
        # libcxx-ohos does (musl xlocale.h); DevEco libc++ 15 does not.
        stub_path = ""
        locale_use = ('#include <cstdlib>\n#include <locale>\n'
                      'int main(){return (int)strtoll_l("1", (char**)0, 10, (locale_t)0);}\n')
        if not self._probe(cxx, probe_flags, locale_use, "locale"):
            stub_path = os.path.join(self.build_folder, "locale_stub.h")
            save(self, stub_path, _LOCALE_STUB)
            self.output.info(
                "libc++ leaves strtoll_l/strtoull_l undeclared; "
                "force-including locale_stub.h")
        else:
            self.output.info(
                "libc++ already provides strtoll_l/strtoull_l; no locale shim needed")

        # Passed via CXXFLAGS (not -DCMAKE_CXX_FLAGS) so CMake's own -D value
        # is never split on the spaces of a DevEco path.
        cxxflags = " ".join(x for x in (
            _BASE_CXX_FLAGS,
            "-I" + inc_dir.replace(" ", "\\ ") if inc_dir else "",
            f"-include {stub_path}" if stub_path else "",
        ) if x)
        return cxxflags, probe_flags

    def build(self):
        py = self.dependencies["python"]
        py_pkg = py.package_folder
        py_bin = os.path.join(py_pkg, "bin", "python3.12")
        py_lib = os.path.join(py_pkg, "lib")

        # Compiler paths from Conan profile (R33)
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cc = compilers.get("c", "/opt/ohos-toolchain/clang")
        cxx = compilers.get("cpp", "/opt/ohos-toolchain/clang++")

        cxx_flags, _ = self._toolchain_cxx_flags(cxx)
        self.output.info(f"CXXFLAGS: {cxx_flags}")

        # Collect all dependency lib dirs for LD_LIBRARY_PATH
        lib_dirs = [py_lib]
        for dep in self.dependencies.values():
            pf = dep.package_folder
            if pf:
                lib_dirs.append(os.path.join(pf, "lib"))
        ld_path = os.pathsep.join(lib_dirs)

        # CMake configuration
        # NOTE: Do NOT set CMAKE_SYSTEM_NAME — FindPython needs to run the
        # interpreter to detect version/SOABI, which works via qemu-aarch64 binfmt.
        # The clang shim already forces --target=aarch64-linux-ohos.
        #
        # CMAKE_MODULE_LINKER_FLAGS (E215): upstream asks FindPython for
        # `Development.Module` only, i.e. extension modules are linked with
        # libpython symbols left undefined, to be resolved from the *interpreter
        # process* (the usual Linux contract, the interpreter is linked with
        # -export-dynamic). The conan python/3.12.9 package does not export them,
        # so every generated .so failed to load with
        #   "ImportError: Error relocating .../fuzz_cpp...so:
        #    PyModuleDef_Init: symbol not found"
        # while `import rapidfuzz` still appeared to work because the package
        # silently falls back to its pure-Python implementation. Linking
        # libpython3.12.so into the modules (as CPython's own build does for
        # lib-dynload/*.so) records a DT_NEEDED entry, so loading no longer
        # depends on the interpreter exporting symbols.
        libpython = self._find_libpython(py_lib)
        cmake_args = [
            f"-DCMAKE_BUILD_TYPE=Release",
            f"-DCMAKE_C_COMPILER={cc}",
            f"-DCMAKE_CXX_COMPILER={cxx}",
            f"-DPython_ROOT_DIR={py_pkg}",
            f"-DPython_EXECUTABLE={py_bin}",
            f"-DCMAKE_MODULE_LINKER_FLAGS={libpython}",
        ]
        self.output.info(f"E215: extension modules will link libpython: {libpython}")

        # Run cmake configure
        self.run(
            f'export LD_LIBRARY_PATH="{ld_path}" && '
            f'export PYTHONHOME="{py_pkg}" && '
            f'export CXXFLAGS="{cxx_flags}" && '
            f'cmake -S "{self.source_folder}" -B "{self.build_folder}/build" '
            + " ".join(cmake_args),
        )

        # Run cmake build
        self.run(
            f'export LD_LIBRARY_PATH="{ld_path}" && '
            f'export PYTHONHOME="{py_pkg}" && '
            f'cmake --build "{self.build_folder}/build" -j{os.cpu_count()}',
        )

    def _find_libpython(self, py_lib):
        """Locate the libpython shared object shipped inside python/3.12.9.

        Preference order mirrors what the dynamic loader needs: the unversioned
        dev symlink first, then any libpython3.12.so* (e.g. libpython3.12.so.1.0).
        Failing loudly beats silently shipping modules that cannot be loaded.
        """
        candidates = [
            os.path.join(py_lib, "libpython3.12.so"),
            os.path.join(py_lib, "libpython3.12.so.1.0"),
        ]
        candidates += sorted(glob.glob(os.path.join(py_lib, "libpython3.12.so*")))
        for path in candidates:
            if os.path.isfile(path):
                return path
        raise ConanException(
            f"libpython3.12.so not found under {py_lib}: CPython extension "
            f"modules cannot be linked. Searched: {candidates}")

    def _find_ohos_tool(self, name):
        """Locate an OHOS SDK tool (llvm-objcopy, binary-sign-tool, ...)."""
        cc_conf = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        compiler_dir = os.path.dirname(cc_conf.get("cpp", "")) if cc_conf else ""
        candidates = [
            os.path.join(compiler_dir, name) if compiler_dir else "",
            os.path.join("/data/service/hnp/bin", name),
            shutil.which(name) or "",
        ]
        return next((p for p in candidates if p and os.path.isfile(p)), "")

    def _sign_shared_libraries(self):
        """Self-sign packaged .so files on OHOS, same as python/3.12.9 does.

        The interpreter's own lib-dynload/*.so are signed by the python recipe;
        without a .codesign section the loader may refuse extension modules
        from a user path (E212). Non-fatal: if the SDK tools are unavailable we
        only warn, matching the python recipe.
        """
        if self.settings.os != "OHOS":
            return
        objcopy = self._find_ohos_tool("llvm-objcopy")
        signer = self._find_ohos_tool("binary-sign-tool")
        if not objcopy or not signer:
            self.output.warning(
                "OHOS signing tools unavailable; .so left unsigned")
            return
        pattern = os.path.join(
            self.package_folder, "lib", "python3.12", "site-packages", "rapidfuzz", "**", "*.so")
        for path in glob.glob(pattern, recursive=True):
            if os.path.islink(path) or not os.path.isfile(path):
                continue
            with open(path, "rb") as fh:
                if fh.read(4) != b"\x7fELF":
                    continue
            original_mode = os.stat(path).st_mode
            temporary = f"{path}.signing"
            try:
                shutil.copy2(path, temporary)
                self.run(f'"{objcopy}" --remove-section .codesign "{temporary}" || true')
                self.run(
                    f'"{signer}" sign -inFile "{temporary}" '
                    f'-outFile "{temporary}" -selfSign 1'
                )
                os.chmod(temporary, original_mode)
                os.replace(temporary, path)
            finally:
                if os.path.exists(temporary):
                    os.remove(temporary)
            self.output.info(f"signed {os.path.basename(path)}")

    def package(self):
        src = self.source_folder
        build = os.path.join(self.build_folder, "build")
        dst = os.path.join(self.package_folder, "lib", "python3.12", "site-packages", "rapidfuzz")

        # Copy pure Python modules
        copy(self, "*.py", src=os.path.join(src, "src", "rapidfuzz"), dst=dst)
        copy(self, "*.pyi", src=os.path.join(src, "src", "rapidfuzz"), dst=dst)
        copy(self, "*.pxd", src=os.path.join(src, "src", "rapidfuzz"), dst=dst)
        copy(self, "*.h", src=os.path.join(src, "src", "rapidfuzz"), dst=dst)
        copy(self, "*.hpp", src=os.path.join(src, "src", "rapidfuzz"), dst=dst)

        # Copy distance subpackage
        copy(self, "*.py", src=os.path.join(src, "src", "rapidfuzz", "distance"), dst=os.path.join(dst, "distance"))
        copy(self, "*.pyi", src=os.path.join(src, "src", "rapidfuzz", "distance"), dst=os.path.join(dst, "distance"))
        copy(self, "*.pxd", src=os.path.join(src, "src", "rapidfuzz", "distance"), dst=os.path.join(dst, "distance"))
        copy(self, "*.h", src=os.path.join(src, "src", "rapidfuzz", "distance"), dst=os.path.join(dst, "distance"))
        copy(self, "*.hpp", src=os.path.join(src, "src", "rapidfuzz", "distance"), dst=os.path.join(dst, "distance"))

        # Copy built .so files
        copy(self, "*.so", src=os.path.join(build, "src", "rapidfuzz"), dst=dst)
        copy(self, "*.so", src=os.path.join(build, "src", "rapidfuzz", "distance"), dst=os.path.join(dst, "distance"))

        # Copy LICENSE
        copy(self, "LICENSE", src=src, dst=os.path.join(self.package_folder, "licenses"))

        # OHOS: sign the extension modules so dlopen from a user path is allowed
        self._sign_shared_libraries()

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.includedirs = ["include"]
