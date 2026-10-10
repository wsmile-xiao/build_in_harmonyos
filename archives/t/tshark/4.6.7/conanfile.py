#!/usr/bin/env python3
"""Conan recipe — tshark (Wireshark CLI dissector) 4.6.7.

tshark is the command-line packet analyzer from the Wireshark project.
This recipe builds ONLY the tshark executable (BUILD_tshark=ON, every other
Wireshark component OFF) so the package is a focused CLI tool.

Build system: CMake (>= 3.20). License: GPLv2.
Dependencies are all conan-sourced (the OHOS target has none of them
installed system-wide). Internal Wireshark libraries are built shared
(the upstream default) and shipped inside the package.
"""
import glob
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.gnu import PkgConfigDeps


class TsharkConan(ConanFile):
    name = "tshark"
    version = "4.6.7"
    description = "tshark - command-line network protocol analyzer (Wireshark CLI)"
    license = "GPL-2.0-only"
    homepage = "https://www.wireshark.org"
    url = ""  # CI fills this
    topics = ("network", "packet-analyzer", "cli", "wireshark", "dissector")

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # --- Core (REQUIRED by CMake find_package) ---
        self.requires("glib/2.84.0.1")
        self.requires("libgcrypt/1.11.0")
        self.requires("c-ares/1.34.5")
        self.requires("pcre2/10.45")
        self.requires("libxml2/2.15.3.1")
        # --- Decryption: OpenSSL >= 1.1.1 (ENABLE_GNUTLS defaults ON, which
        #     triggers find_package(OpenSSL REQUIRED); GnuTLS is then skipped) ---
        self.requires("openssl/3.5.7")
        # --- Live capture ---
        self.requires("libpcap/1.10.6")
        # --- Compression ---
        self.requires("zlib/1.3.1.1")
        self.requires("zstd/1.5.7.1")
        self.requires("lz4/1.10.0")
        self.requires("brotli/1.2.0.1")
        self.requires("snappy/1.1.10")
        # --- HTTP/2 + HTTP/3: intentionally excluded (see generate()).
        #     nghttp2/1.69.0 pins c-ares/1.34.6 + openssl/3.5.6.1.1 + zlib/1.3.2,
        #     which conflict with glib/2.84.0.1's zlib/1.3.1.1 in the ohpcd
        #     registry. Re-enable once the registry versions are aligned.
        # --- Lua dissectors: intentionally disabled (see generate()).
        #     conan's lua/5.4.8 is static-only and wireshark's FindLua.cmake
        #     (find_path/find_library) does not resolve it under conan
        #     config-mode; Lua is optional (Lua dissectors only). Re-enable
        #     with a FindLua-compatible lua package if Lua dissectors are needed.

    def build_requirements(self):
        # LEX (flex) is REQUIRED by CMake: find_package(LEX REQUIRED)
        self.tool_requires("flex/2.6.4.2")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        deps = CMakeDeps(self)
        deps.generate()
        # Wireshark's Find modules discover most deps via pkg-config
        # (pkg_search_module/pkg_check_modules: glib-2.0, gthread-2.0, ...).
        # Emit .pc files so they resolve to the conan packages.
        pcdeps = PkgConfigDeps(self)
        pcdeps.generate()
        tc = CMakeToolchain(self)
        # Upstream default: build the internal Wireshark libs as shared and
        # ship them in the package (most-tested configuration for this tree).
        tc.variables["BUILD_SHARED_LIBS"] = "ON"
        # Build ONLY tshark.
        tc.variables["BUILD_tshark"] = "ON"
        for comp in (
            "BUILD_wireshark", "BUILD_stratoshark", "BUILD_strato",
            "BUILD_tfshark", "BUILD_rawshark", "BUILD_dumpcap",
            "BUILD_text2pcap", "BUILD_mergecap", "BUILD_reordercap",
            "BUILD_editcap", "BUILD_capinfos", "BUILD_captype",
            "BUILD_randpkt", "BUILD_dftest", "BUILD_corbaidl2wrs",
            "BUILD_dcerpcidl2wrs", "BUILD_xxx2deb", "BUILD_androiddump",
            "BUILD_sshdump", "BUILD_ciscodump", "BUILD_dpauxmon",
            "BUILD_randpktdump", "BUILD_wifidump", "BUILD_etwdump",
            "BUILD_sdjournal", "BUILD_udpdump", "BUILD_falcodump",
            "BUILD_sshdig", "BUILD_sharkd", "BUILD_mmdbresolve",
            "BUILD_fuzzshark",
        ):
            tc.variables[comp] = "OFF"
        # Disable optional features whose deps are absent from the registry
        # (or out of scope for a tshark-only package).
        for feat in (
            "ENABLE_ZLIBNG", "ENABLE_XXHASH", "ENABLE_MINIZIP",
            "ENABLE_MINIZIPNG", "ENABLE_SMI", "ENABLE_KERBEROS",
            "ENABLE_SBC", "ENABLE_SPANDSP", "ENABLE_BCG729",
            "ENABLE_AMRNB", "ENABLE_ILBC", "ENABLE_OPUS", "ENABLE_SINSP",
            "ENABLE_CAP", "ENABLE_NETLINK",
            "ENABLE_NGHTTP2", "ENABLE_NGHTTP3",
        ):
            tc.variables[feat] = "OFF"
        # Make the OpenSSL decryption backend explicit.
        tc.variables["ENABLE_OPENSSL"] = "ON"
        # Lua dissectors disabled (see requirements() note).
        tc.variables["ENABLE_LUA"] = "OFF"
        # --- OHOS packaging: SONAME + relocatable RPATH ---
        # The OHOS clang/lld cross toolchain leaves CMake's
        # CMAKE_SHARED_LIBRARY_SONAME_*_FLAG undetected (empty), so the internal
        # shared libs get no SONAME and the tshark exe's DT_NEEDED records the
        # build-tree path (run/libwiretap.so) instead of a SONAME. The installed
        # package then cannot resolve its own libs at run time (L1 test fails:
        # "wtap_strerror: symbol not found"). Force the soname flag so CMake
        # embeds a proper SONAME in each internal lib. CMake concatenates the
        # flag with the computed soname with no separator, so the trailing comma
        # is mandatory (-Wl,-soname,libfoo.so.N); without it lld rejects the
        # fused token (-sonamelibfoo.so.N).
        tc.variables["CMAKE_SHARED_LIBRARY_SONAME_C_FLAG"] = "-Wl,-soname,"
        tc.variables["CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG"] = "-Wl,-soname,"
        # Force wireshark's $ORIGIN-based install RPATH. Its default gates on
        # CMAKE_SYSTEM_NAME being Linux/SunOS/FreeBSD; OHOS matches none, so it
        # would fall back to a non-relocatable absolute path (and the package
        # tshark ended up with no RPATH at all). $ORIGIN makes the package
        # self-contained: libs find each other via $ORIGIN, tshark finds them via
        # $ORIGIN/../lib.
        tc.variables["ENABLE_RPATH_ORIGIN"] = "ON"
        # --- OHOS platform fixes ---
        sysroot = self._ohos_sysroot()
        if sysroot:
            # FindM.cmake does find_path(math.h); the compiler sysroot is not in
            # CMake's search path for a native build, so pin it explicitly.
            tc.variables["M_INCLUDE_DIR"] = os.path.join(sysroot, "usr", "include")
        # Wireshark's custom Find modules add only the primary lib's include dir,
        # not conan's transitive deps (e.g. gcrypt.h -> gpg-error.h). Add every
        # host-dep include dir to the compile command so all headers resolve.
        inc = self._host_include_dirs()
        if inc:
            # No inner quotes: the ExtraFlagsBlock template already wraps the whole
            # value in one pair of CMake quotes, so embedded quotes nest and get
            # mangled (first -isystem path loses its opening quote -> dir not found).
            # Conan pkg paths carry no spaces, so unquoted is safe.
            isys = " ".join('-isystem {}'.format(p) for p in inc)
            # extra_*flags land in the toolchain file (CONAN_C_FLAGS -> CMAKE_C_FLAGS_INIT);
            # cache_variables would only reach the preset, not a toolchain-file configure.
            tc.extra_cflags.append(isys)
            tc.extra_cxxflags.append(isys)
        # Wireshark's find modules leave the legacy *_LIBRARIES vars empty under
        # conan config-mode, so several conan libs (libxml2, zstd, pcre2, openssl,
        # the compression set, the glib family) never reach the link line and lld's
        # --no-allow-shlib-undefined fails. Append every host dep's libs to the
        # exe/shared link flags; start/end-group makes static-lib order safe.
        # Inject into SHARED link flags only: the internal wireshark .so's get the
        # conan libs in DT_NEEDED, which satisfies lld --no-allow-shlib-undefined at
        # the tshark exe link. NOT into exe link flags — wireshark's ConfigureChecks
        # check_c_source_runs() links a trivial main() with CONAN_EXE_LINKER_FLAGS and
        # then RUNS it; the extra DT_NEEDED entries have no RPATH at run time and the
        # check aborts configure.
        lf = self._host_link_flags()
        if lf:
            tc.extra_sharedlinkflags.append(lf)
        # C++ runtime: the SDK's libc++.so is a 20-byte linker script
        # (INPUT(-lc++_shared)); the real runtime is libc++_shared.so. Bare clang++
        # auto-links it, but the CMake/ccache link drops it -> libwireshark.so ends up
        # with undefined _Znwm/_Zdl. Add the full path to the real .so explicitly. It
        # IS resolvable at run time (verified: a trivial exe linking it runs with no
        # LD_LIBRARY_PATH), so it is safe in exe link flags too (won't break
        # ConfigureChecks check_c_source_runs).
        cxx_rt = self._ohos_cxx_runtime()
        if cxx_rt:
            tc.extra_sharedlinkflags.append(cxx_rt)
            tc.extra_exelinkflags.append(cxx_rt)
        tc.generate()

    def _host_include_dirs(self):
        inc = []
        seen = set()
        for _name, dep in self.dependencies.host.items():
            for d in dep.cpp_info.aggregated_components().includedirs:
                if d and d not in seen:
                    seen.add(d)
                    inc.append(d)
        return inc

    def _host_link_flags(self):
        libdirs = []
        libs = []
        seen_d = set()
        seen_l = set()
        for _name, dep in self.dependencies.host.items():
            ci = dep.cpp_info.aggregated_components()
            for ld in ci.libdirs:
                if ld and ld not in seen_d:
                    seen_d.add(ld)
                    libdirs.append("-L{}".format(ld))
            for lib in ci.libs:
                if lib and lib not in seen_l:
                    seen_l.add(lib)
                    libs.append("-l{}".format(lib))
        if not libs:
            return ""
        return " ".join(libdirs) + " -Wl,--start-group " + " ".join(libs) + " -Wl,--end-group"

    def _ohos_sysroot(self):
        # Primary: the OHOS SDK layout on this platform.
        for cand in sorted(glob.glob("/data/service/hnp/ohos-sdk.org/ohos-sdk_*/ohos/native/sysroot")):
            if os.path.isdir(cand):
                return cand
        # Fallback: derive from the configured C compiler (a symlink into the SDK).
        try:
            cc = self.conf.get("tools.build:compiler_executables:c", "") or ""
        except Exception:
            cc = ""
        if cc and os.path.exists(cc):
            native = os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(cc))))
            cand = os.path.join(native, "sysroot")
            if os.path.isdir(cand):
                return cand
        return None

    def _ohos_cxx_runtime(self):
        # Full path to the OHOS C++ runtime (libc++_shared.so). The SDK ships
        # libc++.so as a 20-byte linker script (INPUT(-lc++_shared)) that the CMake
        # link does not resolve, so point at the real .so directly.
        try:
            sysroot = self._ohos_sysroot()
        except Exception:
            sysroot = None
        if not sysroot:
            return None
        llvm_lib = os.path.join(os.path.dirname(sysroot), "llvm", "lib", "aarch64-linux-ohos")
        cand = os.path.join(llvm_lib, "libc++_shared.so")
        return cand if os.path.isfile(cand) else None

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = ["lib"]
