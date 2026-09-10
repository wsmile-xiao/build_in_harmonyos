#!/usr/bin/env python3
"""Conan recipe -- clamav-libunrar 1.4.5 (direct compile, standalone libclamunrar subdir).

ClamAV RAR archive unpacking library. Upstream ships libclamunrar inside the
monolithic ClamAV source tree; only that subdirectory is built here, so the
heavyweight ClamAV requirements (Rust toolchain, Libcheck, python pytest)
are not needed. Builds the clamunrar shared/static library and installs the
public UnRAR C API headers (dll.hpp plus raros.hpp which defines _UNIX).

Build approach: direct compile with the Conan-configured compiler
(boost1.84-coroutine precedent). No CMake project() is executed at all, so
the preflight failure mode "compiler identification is unknown" (conan
CMakeToolchain mapping to an unknown system name on os=OHOS, ohos.toolchain
file absent on this machine) cannot occur. Upstream libclamunrar is a flat
list of ~48 C++ files with two defines (RARDLL, _FILE_OFFSET_BITS=64),
C++11, one include dir and warning flags; all replicated below.
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


# Exact source list from upstream libclamunrar/CMakeLists.txt (non-Windows;
# isnt.cpp is WIN32-only and excluded). Kept in upstream order.
_UNRAR_SOURCES = [
    "archive.cpp",
    "arcread.cpp",
    "blake2s.cpp",
    "cmddata.cpp",
    "consio.cpp",
    "crc.cpp",
    "crypt.cpp",
    "dll.cpp",
    "encname.cpp",
    "errhnd.cpp",
    "extinfo.cpp",
    "extract.cpp",
    "filcreat.cpp",
    "file.cpp",
    "filefn.cpp",
    "filestr.cpp",
    "find.cpp",
    "getbits.cpp",
    "global.cpp",
    "hash.cpp",
    "headers.cpp",
    "list.cpp",
    "match.cpp",
    "options.cpp",
    "pathfn.cpp",
    "qopen.cpp",
    "rar.cpp",
    "rarvm.cpp",
    "rawread.cpp",
    "rdwrfn.cpp",
    "recvol.cpp",
    "resource.cpp",
    "rijndael.cpp",
    "rs.cpp",
    "rs16.cpp",
    "scantree.cpp",
    "secpassword.cpp",
    "sha1.cpp",
    "sha256.cpp",
    "smallfn.cpp",
    "strfn.cpp",
    "strlist.cpp",
    "system.cpp",
    "threadpool.cpp",
    "timefn.cpp",
    "ui.cpp",
    "unicode.cpp",
    "unpack.cpp",
    "volume.cpp",
]


class ClamavLibunrarConan(ConanFile):
    name = "clamav-libunrar"
    version = "1.4.5"
    description = "ClamAV RAR archive unpacking library (UnRAR decoder used by ClamAV)"
    license = "GPL-2.0-only"
    homepage = "https://www.clamav.net/"
    url = "https://github.com/Cisco-Talos/clamav"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}
    exports_sources = "CMakeLists.txt"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # No external dependencies — libclamunrar is self-contained C++
        # (libc/libc++ only); it links no third-party libraries.
        pass

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # Direct compile needs no CMakeToolchain/CMakeDeps (no deps, no
        # CMake invocation). Compiler/flags come from the profile conf and
        # environment in build().
        pass

    def _writable_tmpdir(self):
        # E002: OHOS /tmp is an erofs read-only mount. Reuse the HMBS-injected
        # task temp dir (TMPDIR/TMP/TEMP first — these are what HMBS injects;
        # HMBS_TMPDIR kept as compat fallback), then
        # HMBS_AUTOCONF_MKTEMP_FALLBACK, else a build_folder subdir. The
        # "/tmp" and "0" sentinels mean "no writable dir".
        for var in ("TMPDIR", "TMP", "TEMP", "HMBS_TMPDIR"):
            value = os.environ.get(var)
            if value and value != "0" and value != "/tmp":
                try:
                    os.makedirs(value, exist_ok=True)
                except OSError:
                    pass
                if os.path.isdir(value):
                    return value
                return value
        fallback = os.environ.get("HMBS_AUTOCONF_MKTEMP_FALLBACK")
        if fallback and fallback != "0" and fallback != "/tmp":
            try:
                os.makedirs(fallback, exist_ok=True)
            except OSError:
                pass
            return fallback
        cand = os.path.join(self.build_folder, "tmp_hmbs")
        try:
            os.makedirs(cand, exist_ok=True)
        except OSError:
            return self.build_folder
        return cand

    def _cxx(self):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        path = compilers.get("cpp")
        if path and os.path.isfile(path):
            return path
        if path:
            return shutil.which(os.path.basename(path)) or path
        for key in ("CXX", "CC"):
            env_val = os.environ.get(key, "")
            if env_val:
                first = env_val.split()[0]
                if os.path.isfile(first):
                    return env_val
                resolved = shutil.which(os.path.basename(first))
                if resolved:
                    return env_val.replace(first, resolved, 1)
        return shutil.which("clang++") or "clang++"

    def _ar(self):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        for key in ("ar",):
            path = compilers.get(key, "")
            if path and os.path.isfile(path):
                return path
        for cand in ("llvm-ar", "ar"):
            resolved = shutil.which(cand)
            if resolved:
                return resolved
        return "llvm-ar"

    def build(self):
        apply_conandata_patches(self)
        # E002: export the writable tmpdir before any child process (clang)
        # is spawned so no temp file falls back to read-only /tmp.
        writable_tmp = self._writable_tmpdir()
        try:
            os.makedirs(writable_tmp, exist_ok=True)
        except OSError:
            pass
        for key in ("TMPDIR", "TMP", "TEMP"):
            os.environ[key] = writable_tmp
        self.output.info("[HMBS tmp] build TMPDIR={0}".format(writable_tmp))

        src_dir = os.path.join(self.source_folder, "libclamunrar")
        probe = os.path.join(src_dir, "dll.cpp")
        if not os.path.isfile(probe):
            raise ConanException(
                "libclamunrar sources not found at {0} (expected dll.cpp)".format(src_dir))
        missing = [s for s in _UNRAR_SOURCES if not os.path.isfile(os.path.join(src_dir, s))]
        if missing:
            raise ConanException(
                "libclamunrar sources missing: {0}".format(", ".join(missing)))

        cxx = self._cxx()
        self.output.info("direct compile with cxx={0}".format(cxx))
        obj_dir = os.path.join(self.build_folder, "obj")
        try:
            os.makedirs(obj_dir, exist_ok=True)
        except OSError:
            pass

        opt = "-O0 -g" if str(self.settings.build_type) == "Debug" else "-O2 -DNDEBUG"
        # Upstream: CXX_STANDARD 11, defines RARDLL + _FILE_OFFSET_BITS=64,
        # PRIVATE include = binary dir (generated headers; none at 1.4.5 but
        # keep obj dir for -I parity), PUBLIC include = source dir, plus
        # -Wno-logical-op-parentheses -Wno-switch -Wno-dangling-else.
        base_flags = (
            "-std=c++11 -stdlib=libc++ -fPIC {opt} "
            "-DRARDLL -D_FILE_OFFSET_BITS=64 "
            '-I"{obj}" -I"{src}" '
            "-Wno-logical-op-parentheses -Wno-switch -Wno-dangling-else"
        ).format(opt=opt, obj=obj_dir, src=src_dir)

        objects = []
        for src_file in _UNRAR_SOURCES:
            src_path = os.path.join(src_dir, src_file)
            obj_path = os.path.join(obj_dir, src_file.replace(".cpp", ".o"))
            self.run('"{0}" {1} -c "{2}" -o "{3}"'.format(cxx, base_flags, src_path, obj_path))
            objects.append('"{0}"'.format(obj_path))

        if self.options.shared:
            out_lib = os.path.join(self.build_folder, "libclamunrar.so.12.0.3")
            link_flags = "-shared -stdlib=libc++ -Wl,-soname,libclamunrar.so.12"
            map_file = os.path.join(src_dir, "libclamunrar.map")
            if os.path.isfile(map_file):
                link_flags += ' -Wl,--version-script="{0}"'.format(map_file)
            self.run('"{0}" {1} {2} -o "{3}"'.format(cxx, link_flags, " ".join(objects), out_lib))
        else:
            out_lib = os.path.join(self.build_folder, "libclamunrar_static.a")
            ar = self._ar()
            self.output.info("archiving with ar={0}".format(ar))
            self.run('"{0}" rcs "{1}" {2}'.format(ar, out_lib, " ".join(objects)))

    def package(self):
        if self.options.shared:
            for built in ("libclamunrar.so.12.0.3", "libclamunrar.so"):
                src = os.path.join(self.build_folder, built)
                if os.path.isfile(src):
                    copy(self, built, self.build_folder, os.path.join(self.package_folder, "lib"))
            # Provide the SONAME/SOVERSION symlink set expected of a versioned
            # shared lib when the filesystem supports symlinks; fall back to
            # copies where it does not (HMBS_CAP_SYMLINK diagnostics).
            try:
                self._make_version_links()
            except OSError as exc:
                self.output.warning("versioned .so links skipped: {0}".format(exc))
            self._sign_shared_libs()
        else:
            copy(self, "libclamunrar_static.a", self.build_folder,
                 os.path.join(self.package_folder, "lib"))
        # Upstream installs only the library targets; install the public
        # UnRAR C API headers (dll.hpp needs the _UNIX macro from raros.hpp).
        unrar_dir = os.path.join(self.source_folder, "libclamunrar")
        for header in ("dll.hpp", "raros.hpp"):
            copy(self, header, unrar_dir, os.path.join(self.package_folder, "include"))
        for lic in ("license.txt", "COPYING", "LICENSE"):
            lic_path = os.path.join(unrar_dir, lic)
            if os.path.isfile(lic_path):
                copy(self, lic, unrar_dir, os.path.join(self.package_folder, "licenses"))
                break

    def _make_version_links(self):
        import os as _os
        libdir = _os.path.join(self.package_folder, "lib")
        real = _os.path.join(libdir, "libclamunrar.so.12.0.3")
        if not _os.path.isfile(real):
            return
        for link in ("libclamunrar.so.12", "libclamunrar.so"):
            link_path = _os.path.join(libdir, link)
            try:
                if _os.path.islink(link_path) or _os.path.isfile(link_path):
                    _os.unlink(link_path)
            except OSError:
                pass
            try:
                _os.symlink("libclamunrar.so.12.0.3", link_path)
            except OSError:
                copy(self, "libclamunrar.so.12.0.3", libdir, libdir)

    def _sign_shared_libs(self):
        # HarmonyOS PC requires code signing for .so loaded via dlopen
        # (zstd/expat precedent). Tolerant when the signing tools are absent
        # (e.g. Linux dev machine).
        import glob
        libdir = os.path.join(self.package_folder, "lib")
        targets = glob.glob(os.path.join(libdir, "**", "*.so*"), recursive=True)
        if not targets:
            return
        objcopy = os.environ.get("LLVM_OBJCOPY", "/data/service/hnp/bin/llvm-objcopy")
        signer = os.environ.get("BINARY_SIGN_TOOL", "/data/service/hnp/bin/binary-sign-tool")
        if not os.path.isfile(signer) and not shutil.which("binary-sign-tool"):
            self.output.warning("binary-sign-tool not found, skipping code signing")
            return
        if not os.path.isfile(objcopy) and not shutil.which("llvm-objcopy"):
            objcopy = "llvm-objcopy"
        for target in targets:
            if os.path.islink(target):
                continue
            self.run('{0} --remove-section .codesign "{1}" 2>/dev/null || true'.format(objcopy, target))
            self.run('{0} sign -inFile "{1}" -outFile "{1}" -selfSign 1'.format(signer, target))

    def package_info(self):
        # Upstream target names differ: SHARED -> clamunrar, STATIC ->
        # clamunrar_static. Default options.shared=False builds static.
        self.cpp_info.libs = ["clamunrar" if self.options.shared else "clamunrar_static"]
        self.cpp_info.set_property("cmake_file_name", "clamav-libunrar")
        self.cpp_info.set_property("cmake_target_name", "clamav-libunrar::clamunrar")
