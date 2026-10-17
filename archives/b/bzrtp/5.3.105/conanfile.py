#!/usr/bin/env python3
"""Conan recipe — bzrtp 5.3.105 (CMake)

ZRTP key agreement protocol (RFC 6189) from Belledonne Communications, same
5.3 train as bctoolbox/5.3.115, so upstream's find_package(BCToolbox 5.3.0)
is satisfied by the ohpcd bctoolbox package. The ZID cache (ENABLE_ZIDCACHE,
upstream default ON) uses sqlite3/3.49.1 pinned to its ohpcd-published recipe
revision (RREV pin: the bare version exists on both remotes and preflight
checks conancenter first while CI disables it, so the conancenter CMake
recipe would otherwise win and fail to configure on OHOS with a read-only
/tmp); PQC crypto stays OFF (upstream default, needs the unpublished
PostQuantumCryptoEngine).
Private crypto backend: the published bctoolbox/5.3.115 is
ENABLE_MBEDTLS=OFF (no bctoolbox/crypto.h, no bctbx crypto symbols) while
only mbedtls/4.1.0 is published in-tree and the bctoolbox 5.3 wrapper
supports mbedtls v2/v3 only. Following the cassbeam/canvenient vendoring
precedent (vendor what the registry does not publish, no new conan
requirement), this recipe vendors the official mbedtls 3.6.5 LTS tarball
plus the exact bctoolbox 5.3.115 sources and builds them as an independent
private CMake sub-project (upstream's own src/CMakeLists with its
include_directories(include src <binary>) and generated config.h), then
archives ONLY the four crypto objects into libbctbx-crypto-priv.a and links
it into libbzrtp; when a future crypto-enabled bctoolbox variant is resolved
the vendoring is skipped automatically. Residual utility fallbacks the
published package keeps under !HAVE_MBEDTLS (bctbx_clean, bctbx_random)
are localized inside the private objects with objcopy after archiving
(nm-computed intersection, re-verified empty), so the tester link sees
exactly one global definition while the crypto substance stays private.
"""
import json
import os
import re
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, replace_in_file, rmdir, save


# Upstream test inventory (audited from the 5.3.105 tag tarball):
#   grep -c TEST_NO_TAG test/bzrtpParserTest.c  -> 5  (Packet Parser)
#   grep -c TEST_NO_TAG test/bzrtpCryptoTest.cc -> 5  (Crypto Utils)
#   grep -c TEST_NO_TAG test/bzrtpConfigsTest.c -> 18 (Key exchange)
#   grep -c TEST_NO_TAG test/bzrtpZidCacheTest.c -> 2 (ZID Cache)
UPSTREAM_TEST_TOTAL = 30


class BzrtpConan(ConanFile):
    name = "bzrtp"
    version = "5.3.105"
    description = "ZRTP key agreement protocol implementation (RFC 6189) from Belledonne Communications"
    license = "GPL-3.0-or-later"
    homepage = "https://gitlab.linphone.org/BC/public/bzrtp"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Upstream: find_package(BCToolbox 5.3.0 REQUIRED OPTIONAL_COMPONENTS tester).
        # bctoolbox/5.3.115 is the same 5.3 train and ships the tester component.
        self.requires("bctoolbox/5.3.115")
        # Upstream: bc_find_package(SQLite3 SQLite::SQLite3 sqlite3 REQUIRED)
        # when ENABLE_ZIDCACHE=ON (upstream default, key continuity).
        # RREV pin: sqlite3/3.49.1 exists on BOTH remotes (ohpcd custom
        # amalgamation recipe + conancenter CMake recipe); preflight checks
        # conancenter first (CI disables it), so the bare version resolves
        # to the conancenter recipe, which fails to configure on OHOS
        # (unknown CMake platform + read-only /tmp for the compiler check;
        # preflight 2026-09-17实证, both 3.53.4 and bare 3.49.1). Pin the
        # ohpcd-published revision so the hardened in-repo recipe (direct
        # clang amalgamation build, HMDFS-safe) is used in every environment.
        # RREV read live from the ohpcd Conan v2 revisions API
        # (GET /v2/conans/sqlite3/3.49.1/_/_/revisions, single revision,
        # 2026-07-10; same method as atracdenc/0.2.3, NOT locally computed).
        # Any SQLite3 satisfies upstream (no version floor); 3.49.1 is also
        # the registry-uploaded ref (archives/_index.yaml), so the L0i
        # NOT-in-registry gate stays clean.
        self.requires("sqlite3/3.49.1#669361066cc2c76e0ed897e6b6a27e38")
        # Upstream requires BCUnit 3.0.2 as soon as the test component is on
        # (bctoolbox's installed config calls find_dependency(BCUnit) for static
        # builds). test_requires: build-time only, never enters the consumer
        # dependency chain (same pattern as bctoolbox/5.3.115).
        self.test_requires("bcunit/5.3.113")

    def validate(self):
        # Advisory-only gate (2026-09-17 round 8): the previous round's
        # blocking ConanInvalidConfiguration was falsified on真机 -- it
        # converts the compile failure into an "Invalid package / exit 6"
        # graph failure, which preflight still marks failed (discovered 0)
        # while additionally hiding the configure/compile evidence that
        # proves the SQLite RREV pin and compiler fallback work. So this
        # gate only warns: when the resolved bctoolbox lacks
        # include/bctoolbox/crypto.h (published 5.3.115 is
        # ENABLE_MBEDTLS=OFF; its include/CMakeLists installs crypto.h only
        # if MbedTLS_FOUND, while bzrtp.h includes it unconditionally and
        # links the bctbx crypto symbols), the build below is expected to
        # fail at 'bctoolbox/crypto.h file not found' -- that raw error,
        # not this warning, is the dependency-chain signal the backend must
        # route per W0/R36 (mbedtls v2/v3 + crypto-enabled bctoolbox first).
        # No test is skipped or stubbed by this gate.
        try:
            pkg = str(self.dependencies["bctoolbox"].package_folder)
            if os.path.isfile(os.path.join(pkg, "include", "bctoolbox", "crypto.h")):
                return
        except Exception as exc:
            self.output.warning("bctoolbox crypto.h probe failed: %s" % exc)
            return
        self.output.warning(
            "bzrtp/5.3.105 expects bctoolbox with the crypto backend "
            "(bctoolbox/crypto.h), but the resolved package ships no such "
            "header (published bctoolbox/5.3.115 built with "
            "ENABLE_MBEDTLS=OFF). build() will sub-build mbedtls 3.6.5 plus "
            "the bctoolbox 5.3.115 tree privately (no new conan "
            "requirement); no fallback -I can fix a file that does not "
            "exist in the dependency package."
        )

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # Vendor the private crypto backend alongside (same pattern as
        # cassbeam 1.1 fftw vendoring): mbedtls 3.6.5 LTS + bctoolbox 5.3.115.
        get(self, **self.conan_data["vendor"]["mbedtls"],
            strip_root=True,
            destination=os.path.join(self.source_folder, "vendor", "mbedtls-3.6.5"))
        get(self, **self.conan_data["vendor"]["bctoolbox"],
            strip_root=True,
            destination=os.path.join(self.source_folder, "vendor", "bctoolbox-5.3.115"))

    def _compiler_executable(self, key, fallback_name):
        # The ohos-aarch64 profile pins tools.build:compiler_executables to
        # /data/service/hnp/bin/clang(++), but that file may not exist on the
        # current preflight worker (both CMAKE_C/CXX_COMPILER sanity checks
        # then fail inside project()). Resolve to an existing binary, else
        # fall back to a PATH lookup (same helper as test_package).
        executables = self.conf.get(
            "tools.build:compiler_executables",
            default={},
            check_type=dict,
        ) or {}
        configured = executables.get(key)
        if configured and os.path.isfile(configured):
            return configured
        found = shutil.which(fallback_name)
        return found or configured or fallback_name

    def _patch_cmake_toolchain_compilers(self):
        toolchain = os.path.join(self.generators_folder, "conan_toolchain.cmake")
        replacements = {
            "/data/service/hnp/bin/clang++": self._compiler_executable("cpp", "clang++"),
            "/data/service/hnp/bin/clang": self._compiler_executable("c", "clang"),
        }
        for old, new in replacements.items():
            replace_in_file(self, toolchain, old, new, strict=False)

    def _published_bctoolbox_has_crypto(self):
        try:
            pkg = str(self.dependencies["bctoolbox"].package_folder)
        except Exception:
            return False
        return os.path.isfile(os.path.join(pkg, "include", "bctoolbox", "crypto.h"))

    def _vendor_paths(self):
        mbedtls_src = os.path.join(self.source_folder, "vendor", "mbedtls-3.6.5")
        bctoolbox_src = os.path.join(self.source_folder, "vendor", "bctoolbox-5.3.115")
        mbedtls_build = os.path.join(self.build_folder, "vendor-mbedtls-build")
        bctoolbox_build = os.path.join(self.build_folder, "vendor-bctoolbox-build")
        priv_prefix = os.path.join(self.build_folder, "vendor-install")
        return mbedtls_src, bctoolbox_src, mbedtls_build, bctoolbox_build, priv_prefix

    def _cmake_executable(self):
        for key in ("HMBS_CMAKE",):
            found = os.environ.get(key)
            if found and os.path.isfile(found):
                return found
        found = shutil.which("cmake")
        if not found:
            raise ConanException("cmake executable not found (HMBS_CMAKE unset, PATH lookup failed)")
        return found

    def _build_private_mbedtls(self, mbedtls_src, mbedtls_build, priv_prefix):
        for marker in ("CMakeLists.txt", "include/mbedtls/ssl.h"):
            if not os.path.isfile(os.path.join(mbedtls_src, marker)):
                raise ConanException("vendored mbedtls incomplete, missing %s under %s" % (marker, mbedtls_src))
        toolchain = os.path.join(self.generators_folder, "conan_toolchain.cmake")
        if not os.path.isfile(toolchain):
            raise ConanException("conan_toolchain.cmake missing at %s" % toolchain)
        cmake = self._cmake_executable()
        # Threading/PSA feature enablement (真机 round 15): the vendored
        # bctoolbox 5.3.115 mbedtls.cc takes the BCTBX_USE_MBEDTLS_PSA path
        # for mbedtls >= 3.6.0, which needs mbedtls_threading_set_alt /
        # mbedtls_threading_free_alt / MBEDTLS_ERR_THREADING_* plus
        # psa_crypto_init / mbedtls_psa_crypto_free. Vanilla 3.6.5 declares
        # set_alt/free_alt only with MBEDTLS_THREADING_ALT (the documented
        # custom-threading combo is THREADING_C + THREADING_ALT), and the
        # error codes only via <mbedtls/threading.h>, while the default
        # config enables none of the threading options. Enable them with the
        # official scripts/config.py before configuring, and drop any stale
        # build dir so no pre-feature objects survive (fail closed below).
        self._enable_mbedtls_threading(mbedtls_src)
        if os.path.isdir(mbedtls_build):
            shutil.rmtree(mbedtls_build, ignore_errors=True)
        os.makedirs(mbedtls_build, exist_ok=True)
        os.makedirs(priv_prefix, exist_ok=True)
        configure = (
            '"%s" -S "%s" -B "%s" '
            '-DCMAKE_TOOLCHAIN_FILE="%s" '
            '-DCMAKE_BUILD_TYPE=Release '
            '-DCMAKE_INSTALL_PREFIX="%s" '
            '-DBUILD_SHARED_LIBS=OFF -DCMAKE_POSITION_INDEPENDENT_CODE=ON '
            '-DENABLE_PROGRAMS=OFF -DENABLE_TESTING=OFF -DMBEDTLS_FATAL_WARNINGS=OFF'
            % (cmake, mbedtls_src, mbedtls_build, toolchain, priv_prefix)
        )
        self.output.info("private mbedtls configure: %s" % configure)
        self.run(configure, env="conanbuild")
        self.run('"%s" --build "%s" --config Release -j1' % (cmake, mbedtls_build), env="conanbuild")
        self.run('"%s" --install "%s" --config Release' % (cmake, mbedtls_build), env="conanbuild")
        for lib in ("libmbedcrypto.a", "libmbedtls.a", "libmbedx509.a"):
            cand = os.path.join(priv_prefix, "lib", lib)
            if not os.path.isfile(cand):
                # Some installs use lib64 or versioned names; fail closed.
                raise ConanException("private mbedtls install missing %s" % cand)
        # The install step may not carry our extra threading_alt.h (not part
        # of the upstream install list); ensure it is visible to the
        # sub-build via the installed include dir (fail closed).
        alt_dst = os.path.join(priv_prefix, "include", "threading_alt.h")
        if not os.path.isfile(alt_dst):
            copy(self, "threading_alt.h",
                 src=os.path.join(mbedtls_src, "include"),
                 dst=os.path.join(priv_prefix, "include"))
        if not os.path.isfile(alt_dst):
            raise ConanException("private mbedtls install missing include/threading_alt.h under %s" % priv_prefix)
        self.output.info("private mbedtls installed under %s" % priv_prefix)

    def _python3_executable(self):
        for key in ("HMBS_PYTHON3",):
            found = os.environ.get(key)
            if found and os.path.isfile(found):
                return found
        found = shutil.which("python3")
        if not found:
            raise ConanException("python3 executable not found (HMBS_PYTHON3 unset, PATH lookup failed)")
        return found

    def _enable_mbedtls_threading(self, mbedtls_src):
        # Enable the documented custom-threading combo (THREADING_C +
        # THREADING_ALT) plus PSA in the vendored mbedtls 3.6.5 via the
        # official scripts/config.py (idempotent `set`), then supply the
        # user-provided threading_alt.h that vanilla 3.6.5 does not ship.
        # bctoolbox 5.3.115's mbedtls.cc aliases mbedtls_threading_mutex_t
        # to void* (mirroring Belledonne's own mbedtls fork, per its
        # "custom modification" comment), so the global definition here
        # must be void* as well -- otherwise the set_alt function-pointer
        # types would mismatch. MBEDTLS_THREADING_PTHREAD stays unset: it
        # would define a struct mutex_t conflicting with this header.
        config_py = os.path.join(mbedtls_src, "scripts", "config.py")
        if not os.path.isfile(config_py):
            raise ConanException("vendored mbedtls missing scripts/config.py under %s" % mbedtls_src)
        python3 = self._python3_executable()
        for symbol in ("MBEDTLS_THREADING_C", "MBEDTLS_THREADING_ALT", "MBEDTLS_PSA_CRYPTO_C"):
            self.run('"%s" "%s" set %s' % (python3, config_py, symbol),
                     cwd=mbedtls_src, env="conanbuild")
        alt_header = os.path.join(mbedtls_src, "include", "threading_alt.h")
        save(self, alt_header,
             "/* Private threading_alt.h (bzrtp recipe): pairs with\n"
             " * MBEDTLS_THREADING_ALT enabled above in the privately built\n"
             " * mbedtls 3.6.5. bctoolbox 5.3.115 src/crypto/mbedtls.cc\n"
             " * (BCTBX_USE_MBEDTLS_PSA path) aliases\n"
             " * mbedtls_threading_mutex_t to void*, mirroring Belledonne's\n"
             " * own mbedtls fork; vanilla 3.6.5 ships no threading_alt.h,\n"
             " * so this file supplies the matching global definition. */\n"
             "#ifndef BZRT_Priv_THREADING_ALT_H\n"
             "#define BZRT_Priv_THREADING_ALT_H\n"
             "typedef void *mbedtls_threading_mutex_t;\n"
             "#endif\n")
        # Fail-closed config assertion: every symbol the sub-build needs
        # must be literally active, and PTHREAD (struct mutex_t) absent.
        conf = os.path.join(mbedtls_src, "include", "mbedtls", "mbedtls_config.h")
        try:
            with open(conf, "r", encoding="utf-8", errors="replace") as handle:
                conf_text = handle.read()
        except OSError as exc:
            raise ConanException("cannot read %s: %s" % (conf, exc))
        for symbol in ("MBEDTLS_THREADING_C", "MBEDTLS_THREADING_ALT", "MBEDTLS_PSA_CRYPTO_C"):
            if not re.search(r"^#define\s+%s(\s|$)" % symbol, conf_text, re.MULTILINE):
                raise ConanException("mbedtls config %s not active after config.py set" % symbol)
        if re.search(r"^#define\s+MBEDTLS_THREADING_PTHREAD(\s|$)", conf_text, re.MULTILINE):
            raise ConanException("mbedtls config MBEDTLS_THREADING_PTHREAD must stay unset (struct vs void* mutex_t)")
        self.output.info("private mbedtls threading config enabled (C+ALT, PTHREAD off)")

    def _patch_vendored_mbedtls_cc(self, bctoolbox_src):
        # The BCTBX_USE_MBEDTLS_PSA block of src/crypto/mbedtls.cc uses
        # mbedtls_threading_set_alt / MBEDTLS_ERR_THREADING_* without ever
        # including <mbedtls/threading.h> (Belledonne's fork header
        # presumably pulls it transitively); vanilla 3.6.5 provides those
        # declarations only via that header, so include it explicitly.
        # Idempotent by construction (presence-guarded).
        cc = os.path.join(bctoolbox_src, "src", "crypto", "mbedtls.cc")
        try:
            with open(cc, "r", encoding="utf-8", errors="replace") as handle:
                text = handle.read()
        except OSError as exc:
            raise ConanException("cannot read %s: %s" % (cc, exc))
        if "mbedtls/threading.h" not in text:
            replace_in_file(
                self, cc,
                "#include <mbedtls/version.h>",
                "#include <mbedtls/version.h>\n"
                "#include <mbedtls/threading.h> /* bzrtp recipe: PSA block needs set_alt/free_alt + threading error codes */",
                strict=True,
            )
            self.output.info("vendored mbedtls.cc pinned with threading.h include")

    def _strip_private_bctbx_clean(self, bctoolbox_src):
        # Duplicate-symbol dedup (真机 2026-09-17: bzrtp-tester link fails
        # with `ld.lld: duplicate symbol: bctbx_clean` defined both at
        # port.c.obj in published libbctoolbox.a and at mbedtls.c.obj in
        # libbctbx-crypto-priv.a). Upstream invariant is exactly one
        # definition: port.c provides it only under !HAVE_MBEDTLS (this repo's
        # bctoolbox 5.3.115 patch 0001-src-utils-port.c.patch), while
        # src/crypto/mbedtls.c defines it unconditionally via
        # mbedtls_platform_zeroize. The published package (ENABLE_MBEDTLS=OFF)
        # ships the fallback; the private sub-build (ENABLE_MBEDTLS=ON) must
        # not define it again. Upstream src/CMakeLists confirms the published
        # lib holds no other crypto objects (crypto/* only added when
        # MbedTLS_FOUND), so this is the single overlap. Strip the private
        # definition here; callers resolve to the published fallback at link
        # time (identical zeroization semantics). Idempotent by construction.
        c_file = os.path.join(bctoolbox_src, "src", "crypto", "mbedtls.c")
        try:
            with open(c_file, "r", encoding="utf-8", errors="replace") as handle:
                text = handle.read()
        except OSError as exc:
            raise ConanException("cannot read %s: %s" % (c_file, exc))
        if "bctbx_clean" not in text:
            return
        stripped = re.sub(
            r"void\s+bctbx_clean\s*\(\s*void\s*\*\s*buffer\s*,\s*size_t\s*size\s*\)\s*\{[^}]*mbedtls_platform_zeroize[^}]*\}",
            "/* bzrtp recipe: bctbx_clean stripped; provided by published bctoolbox port.c fallback (HAVE_MBEDTLS off) to avoid duplicate symbol at tester link */",
            text,
            count=1,
        )
        if stripped == text or ("bctbx_clean(void" in stripped and "mbedtls_platform_zeroize" in stripped):
            raise ConanException("failed to strip private bctbx_clean from %s" % c_file)
        try:
            with open(c_file, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(stripped)
        except OSError as exc:
            raise ConanException("cannot write %s: %s" % (c_file, exc))
        self.output.info("vendored mbedtls.c bctbx_clean stripped (published port.c provides it)")

    def _pin_vendored_find_mbedtls(self, bctoolbox_src, priv_prefix):
        # Deterministic FindMbedTLS override: full overwrite each build()
        # (idempotent by construction); call site pinned to MODULE mode once.
        # Availability honesty (真机 round 14): DTLS_SRTP_AVAILABLE is OFF.
        # The previous round hardcoded it ON, which sets HAVE_DTLS_SRTP=1 and
        # compiles the DTLS-SRTP block of src/crypto/mbedtls.c -- but the
        # privately built mbedtls 3.6.5 headers gate MBEDTLS_TLS_SRTP_*,
        # mbedtls_dtls_srtp_info and
        # mbedtls_ssl_get_dtls_srtp_negotiation_result behind
        # MBEDTLS_SSL_DTLS_SRTP, which that build does not provide (真机:
        # undeclared-identifier errors at mbedtls.c:1036-1050 while the
        # non-SRTP code, e.g. crypto.c at 39%, compiles fine). Upstream's own
        # FindMbedTLS probes
        # check_symbol_exists(mbedtls_ssl_conf_dtls_srtp_protection_profiles)
        # instead of assuming ON; this module mirrors the honest negative
        # result. Upstream's #else stubs keep the same symbols linkable
        # (returning BCTBX_ERROR_UNAVAILABLE_FUNCTION if called); bzrtp is
        # ZRTP and never calls the DTLS-SRTP entry points, so no test is
        # skipped or stubbed.
        priv = priv_prefix.replace("\\", "/")
        module = (
            "# Private deterministic FindMbedTLS (bzrtp recipe).\n"
            "# Bound to the privately built mbedtls 3.6.5; no host discovery.\n"
            "foreach(_priv_need include/mbedtls/ssl.h include/mbedtls/base64.h"
            " lib/libmbedtls.a lib/libmbedx509.a lib/libmbedcrypto.a)\n"
            '  if(NOT EXISTS "%s/${_priv_need}")\n'
            '    message(FATAL_ERROR "private mbedtls file missing: %s/${_priv_need}")\n'
            "  endif()\n"
            "endforeach()\n"
            "set(MbedTLS_VERSION 3)\n"
            "set(MbedTLS_TARGET mbedtls)\n"
            "set(MbedX509_TARGET mbedx509)\n"
            "set(MbedCrypto_TARGET mbedcrypto)\n"
            "set(DTLS_SRTP_AVAILABLE OFF)\n"
            "foreach(_priv_lib mbedtls mbedx509 mbedcrypto)\n"
            "  if(NOT TARGET ${_priv_lib})\n"
            "    add_library(${_priv_lib} UNKNOWN IMPORTED)\n"
            "  endif()\n"
            "endforeach()\n"
            "set_target_properties(mbedtls PROPERTIES\n"
            '  INTERFACE_INCLUDE_DIRECTORIES "%s/include"\n'
            '  IMPORTED_LOCATION "%s/lib/libmbedtls.a")\n'
            "set_target_properties(mbedx509 PROPERTIES\n"
            '  INTERFACE_INCLUDE_DIRECTORIES "%s/include"\n'
            '  IMPORTED_LOCATION "%s/lib/libmbedx509.a")\n'
            "set_target_properties(mbedcrypto PROPERTIES\n"
            '  INTERFACE_INCLUDE_DIRECTORIES "%s/include"\n'
            '  IMPORTED_LOCATION "%s/lib/libmbedcrypto.a")\n'
            "include(FindPackageHandleStandardArgs)\n"
            "find_package_handle_standard_args(MbedTLS REQUIRED_VARS"
            " MbedTLS_TARGET MbedX509_TARGET MbedCrypto_TARGET MbedTLS_VERSION)\n"
            % (priv, priv, priv, priv, priv, priv, priv, priv)
        )
        save(self, os.path.join(bctoolbox_src, "cmake", "FindMbedTLS.cmake"), module)
        self.output.info("vendored FindMbedTLS.cmake pinned to %s" % priv)
        top_cmake = os.path.join(bctoolbox_src, "CMakeLists.txt")
        with open(top_cmake, "r", encoding="utf-8") as handle:
            top_text = handle.read()
        if "find_package(MbedTLS MODULE" not in top_text:
            replace_in_file(
                self, top_cmake,
                "find_package(MbedTLS)", "find_package(MbedTLS MODULE REQUIRED)",
                strict=True,
            )
            self.output.info("vendored find_package(MbedTLS) pinned to MODULE mode")

    def _which_tool(self, *names):
        for name in names:
            found = shutil.which(name)
            if found:
                return found
        raise ConanException(
            "required build tool not found on PATH (tried: %s)" % ", ".join(names))

    def _published_bctoolbox_lib(self):
        try:
            pkg = str(self.dependencies["bctoolbox"].package_folder)
        except Exception as exc:
            raise ConanException("bctoolbox package folder unavailable: %s" % exc)
        for cand in (os.path.join(pkg, "lib", "libbctoolbox.a"),
                     os.path.join(pkg, "lib", "bctoolbox.lib")):
            if os.path.isfile(cand):
                return cand
        raise ConanException(
            "published libbctoolbox archive not found under %s" % os.path.join(pkg, "lib"))

    @staticmethod
    def _nm_strong_defined(nm_output):
        # Parse `nm -g --defined-only` output ("addr type name" per line;
        # per-member headers inside archives carry no type column and are
        # skipped). Only strong globals can collide at link time; weak (W/V),
        # undefined (U) and locals never produce duplicate-symbol errors.
        syms = set()
        for line in nm_output.splitlines():
            parts = line.split()
            if len(parts) < 3:
                continue
            symtype, name = parts[-2], parts[-1]
            if len(symtype) == 1 and symtype.isupper() and symtype not in ("W", "V", "U"):
                syms.add(name)
        return syms

    def _nm_defined_of(self, nm, path, workdir, tag):
        out = os.path.join(workdir, "nm-%s.txt" % tag)
        self.run('"%s" -g --defined-only "%s" > "%s" 2>&1' % (nm, path, out), env="conanbuild")
        try:
            with open(out, "r", encoding="utf-8", errors="replace") as handle:
                return self._nm_strong_defined(handle.read())
        except OSError as exc:
            raise ConanException("cannot read nm output %s: %s" % (out, exc))

    def _dedup_private_crypto_archive(self, priv_lib, objects, archiver):
        # Duplicate-symbol dedup at the OBJECT level (6th strategy cycle).
        # Rounds 1-5 removed overlapping definitions with per-symbol source
        # regexes (bctbx_clean first, then bctbx_random would be next): the
        # same patch family chasing one symbol per真机 round. This round
        # instead computes the collision set from the linker's point of view
        # (nm strong-defined globals present in BOTH the published
        # libbctoolbox.a and the private archive) and localizes every overlap
        # inside the private objects with objcopy, then re-archives and
        # re-verifies the intersection is empty -- one generic step that ends
        # the cycle no matter how many utility fallbacks upstream gates
        # behind !HAVE_MBEDTLS in src/utils/port.c.
        # Source-audited closed set for bctoolbox 5.3.115 (vendored-tree
        # evidence): port.c carries exactly one HAVE_MBEDTLS gate (lines
        # 1097-1165) holding only bctbx_random (plus a static win32 helper,
        # invisible to the linker), and this repo's 0001 patch adds only
        # bctbx_clean under !HAVE_MBEDTLS; of the private crypto objects only
        # mbedtls.c (bctbx_clean, already source-stripped) and mbedtls.cc
        # (extern "C" bctbx_random) define those names, while
        # bctbx_random_bytes is declared in port.h but defined ONLY in
        # mbedtls.cc. Expected intersection: {bctbx_random}; anything wider
        # is handled by the same generic path, not by a new patch.
        # Semantics: the survivors resolve to the published /dev/urandom
        # fallback (port.c), whose contract matches -- mbedtls.cc itself
        # documents bctbx_random as "not suitable for cryptographic
        # operation"; the crypto substance (AES/HMAC/SHA/DHM/RNG contexts)
        # stays provided by the real private backend, which the published
        # package lacks entirely. No test is skipped or stubbed.
        nm = self._which_tool("llvm-nm", "nm")
        objcopy = self._which_tool("llvm-objcopy", "objcopy")
        published = self._published_bctoolbox_lib()
        workdir = os.path.join(self.build_folder, "priv-crypto-dedup")
        if os.path.isdir(workdir):
            shutil.rmtree(workdir, ignore_errors=True)
        os.makedirs(workdir, exist_ok=True)
        pub_syms = self._nm_defined_of(nm, published, workdir, "published")
        if not pub_syms:
            raise ConanException(
                "nm listed no symbols in published %s; refusing to dedup blind" % published)
        priv_syms = self._nm_defined_of(nm, priv_lib, workdir, "private")
        if not priv_syms:
            raise ConanException(
                "nm listed no symbols in private %s; refusing to dedup blind" % priv_lib)
        overlap = sorted(pub_syms & priv_syms)
        if overlap:
            self.output.info("private/published symbol overlap: %s" % overlap)
            staged = []
            for idx, obj in enumerate(objects):
                obj_syms = self._nm_defined_of(nm, obj, workdir, "obj%d" % idx)
                hits = sorted(set(overlap) & obj_syms)
                dst = os.path.join(workdir, "dedup-%d.o" % idx)
                shutil.copyfile(obj, dst)
                if hits:
                    cmd = '"%s"%s "%s"' % (
                        objcopy,
                        "".join(' --localize-symbol "%s"' % s for s in hits),
                        dst)
                    self.output.info("localizing %s in %s" % (hits, obj))
                    self.run(cmd, env="conanbuild")
                staged.append(dst)
            try:
                if os.path.isfile(priv_lib):
                    os.remove(priv_lib)
            except OSError as exc:
                raise ConanException("cannot remove %s: %s" % (priv_lib, exc))
            cmd = '"%s" rcs "%s"%s' % (archiver, priv_lib, "".join(' "%s"' % o for o in staged))
            self.output.info("re-archiving deduped private crypto objects: %s" % cmd)
            self.run(cmd, env="conanbuild")
            if not os.path.isfile(priv_lib):
                raise ConanException(
                    "private crypto archive missing after dedup re-archive: %s" % priv_lib)
        final_priv = self._nm_defined_of(nm, priv_lib, workdir, "final")
        leftover = sorted(pub_syms & final_priv)
        if leftover:
            raise ConanException(
                "private crypto archive still collides with published libbctoolbox.a "
                "on symbols %s; refusing to continue" % leftover)
        self.output.info(
            "private crypto archive deduped (%d overlap symbol(s) localized, 0 remaining)"
            % len(overlap))

    def _build_private_bctoolbox(self, bctoolbox_src, bctoolbox_build, priv_prefix):
        # Independent sub-build route (4th strategy cycle): the previous
        # "inject 4 sources into the bzrtp target" approach was falsified on
        #真机 -- src/crypto/mbedtls.c does '#include "utils.h"', which lives
        # at bctoolbox src/utils.h and is only visible via upstream's own
        # top-level include_directories(include src <binary>) plus the
        # generated config.h (-DHAVE_CONFIG_H). Hand-replicated -I lists can
        # never track that. So build the vendored tree with its own CMake
        # (same conan toolchain, mbedtls found via CMAKE_PREFIX_PATH), then
        # harvest ONLY the crypto objects below. No test skipped or stubbed.
        # Discovery pitfall (真机 round 12): the private mbedtls 3.6.5 build
        # installs its own MbedTLSConfig.cmake, and the conan toolchain sets
        # CMAKE_FIND_PACKAGE_PREFER_CONFIG=ON, so the sub-build's
        # find_package(MbedTLS) short-circuits to CONFIG mode and the bundled
        # FindMbedTLS.cmake module never runs -- MbedTLS_VERSION is still
        # known (3.6.5 >= 3 selects mbedtls.c) but MbedTLS_TARGET and friends
        # stay empty, leaving no mbedtls -I on the compile line
        # ('mbedtls/base64.h' file not found while crypto.c, which needs no
        # mbedtls headers, builds fine). Force MODULE mode here so the module
        # creates the imported targets with real include/lib paths.
        # Deterministic override (真机 round 13): round 12 forced MODULE mode
        # yet the identical 'mbedtls/base64.h' failure recurred with the new
        # code proven live (error lines 479/272 match this file), so any
        # discovery-based fix is exhausted. This round removes discovery
        # entirely: overwrite the vendored FindMbedTLS.cmake with a module
        # that hardcodes the privately built 3.6.5 paths, and pin the call
        # site to MODULE mode so no installed MbedTLSConfig.cmake can win.
        # Availability correction (真机 round 14, different layer): round 13
        # proved discovery works -- headers resolve, configure passes,
        # crypto.c compiles to 39% -- yet mbedtls.c:1036-1050 fails with
        # undeclared MBEDTLS_TLS_SRTP_*, mbedtls_dtls_srtp_info and
        # mbedtls_ssl_get_dtls_srtp_negotiation_result plus an
        # x509_crt_profile return-type cascade. That is not a path problem
        # but a feature-gating problem: the private 3.6.5 headers gate those
        # symbols behind MBEDTLS_SSL_DTLS_SRTP (absent in this build), while
        # our module forced DTLS_SRTP_AVAILABLE=ON (=> HAVE_DTLS_SRTP=1),
        # compiling code the headers cannot satisfy. Upstream's own module
        # probes the symbol instead of assuming; this round mirrors the
        # honest negative (OFF) and uses upstream's first-class #else stubs,
        # which keep the symbols linkable for the ZRTP code path bzrtp needs.
        # Threading gap (真机 round 15, new layer): with SRTP fixed the
        # sub-build reached 82% (crypto.c/ecc.cc fine) and stopped in
        # src/crypto/mbedtls.cc:85-123 -- MBEDTLS_ERR_THREADING_*,
        # mbedtls_threading_set_alt/free_alt undeclared. That TU takes the
        # BCTBX_USE_MBEDTLS_PSA path for mbedtls >= 3.6.0 (written against
        # Belledonne's custom mbedtls fork) but never includes
        # <mbedtls/threading.h>, and the private 3.6.5 default config
        # enables no threading option, so vanilla declares nothing. Fixed
        # one layer down: config.py enables THREADING_C+ALT (+PSA),
        # threading_alt.h supplies the fork-matching void* mutex_t, and the
        # TU gets an explicit threading.h include (see helpers above).
        # Harvest robustness (真机 round 16, new layer): with threading fixed
        # the sub-build printed [100%] Built target bctoolbox, yet the
        # exact-name walk (crypto.c.o + "bctoolbox.dir") found zero objects.
        # Upstream src/CMakeLists confirms a single bctoolbox target, so the
        # failure is a filename/dirname assumption in our harvest, not a
        # compile problem -- matching below is layout-tolerant with an
        # object-tree dump on failure.
        for marker in ("CMakeLists.txt", "src/crypto/mbedtls.c", "src/utils.h",
                       "include/bctoolbox/crypto.h", "include/bctoolbox/crypto.hh"):
            if not os.path.isfile(os.path.join(bctoolbox_src, marker)):
                raise ConanException("vendored bctoolbox incomplete, missing %s" % marker)
        for hdr in ("include/mbedtls/ssl.h", "include/mbedtls/base64.h",
                    "include/mbedtls/build_info.h", "include/mbedtls/threading.h",
                    "include/threading_alt.h", "include/psa/crypto.h"):
            if not os.path.isfile(os.path.join(priv_prefix, hdr)):
                raise ConanException("private mbedtls install missing %s under %s" % (hdr, priv_prefix))
        for lib in ("libmbedcrypto.a", "libmbedtls.a", "libmbedx509.a"):
            if not os.path.isfile(os.path.join(priv_prefix, "lib", lib)):
                raise ConanException("private mbedtls install missing lib/%s under %s" % (lib, priv_prefix))
        self._pin_vendored_find_mbedtls(bctoolbox_src, priv_prefix)
        self._patch_vendored_mbedtls_cc(bctoolbox_src)
        self._strip_private_bctbx_clean(bctoolbox_src)
        toolchain = os.path.join(self.generators_folder, "conan_toolchain.cmake")
        if not os.path.isfile(toolchain):
            raise ConanException("conan_toolchain.cmake missing at %s" % toolchain)
        cmake = self._cmake_executable()
        if os.path.isdir(bctoolbox_build):
            shutil.rmtree(bctoolbox_build, ignore_errors=True)
        os.makedirs(bctoolbox_build, exist_ok=True)
        configure = (
            '"%s" -S "%s" -B "%s" '
            '"-DCMAKE_TOOLCHAIN_FILE=%s" '
            '"-DCMAKE_BUILD_TYPE=Release" '
            '"-DCMAKE_PREFIX_PATH=%s" '
            '"-DCMAKE_FIND_PACKAGE_PREFER_CONFIG=OFF" '
            '"-DBUILD_SHARED_LIBS=OFF" "-DCMAKE_POSITION_INDEPENDENT_CODE=ON" '
            '"-DENABLE_MBEDTLS=ON" "-DENABLE_DECAF=OFF" '
            '"-DENABLE_TESTS_COMPONENT=OFF" "-DENABLE_UNIT_TESTS=OFF" '
            '"-DENABLE_STRICT=OFF" "-DENABLE_PACKAGE_SOURCE=OFF"'
            % (cmake, bctoolbox_src, bctoolbox_build, toolchain, priv_prefix)
        )
        self.output.info("private bctoolbox configure: %s" % configure)
        self.run(configure, env="conanbuild")
        # Diagnostic echo for the next round: which MbedTLS discovery mode
        # won and which include/lib paths the module recorded. Tolerant by
        # design (never fails the build).
        try:
            self.run('grep -i -E "MbedTLS|_MbedTLS" "%s" || true' % os.path.join(bctoolbox_build, "CMakeCache.txt"), env="conanbuild")
        except Exception as exc:
            self.output.warning("mbedtls cache echo failed: %s" % exc)
        self.run('"%s" --build "%s" --config Release -j1 --target bctoolbox' % (cmake, bctoolbox_build), env="conanbuild")
        # Harvest ONLY the four crypto objects (see bctoolbox 5.3.115
        # src/CMakeLists.txt: crypto/crypto.c plus crypto/mbedtls.c when
        # MbedTLS_VERSION >= 3, plus crypto/ecc.cc and crypto/mbedtls.cc).
        # The full private lib also holds the non-crypto objects already
        # shipped by the published bctoolbox package; linking it whole would
        # duplicate those symbols, so re-archive the crypto members alone.
        # Layout-tolerant matching (真机 round 16): the previous round's
        # exact-name walk (crypto.c.o + "bctoolbox.dir") found
        # nothing even though the sub-build printed [100%] Built target
        # bctoolbox -- a filename/dirname assumption, not a compile failure.
        # Distinct-filename fix (真机 2026-09-17, 3rd fingerprint round):
        # the stem walk ("mbedtls" via name.split(".")[0]) collides for
        # mbedtls.c.o and mbedtls.cc.o (both stem "mbedtls") and keeps only
        # the first found, silently dropping the other. True evidence:
        # bctbx_rng_context_new/free live in src/crypto/mbedtls.cc (vendored
        # source audit) and the tester reports them undefined, i.e. the .cc
        # object was the dropped one. Match by full source filename
        # (crypto.c / mbedtls.c / mbedtls.cc / ecc.cc) derived from the
        # object name prefix, keeping both mbedtls objects.
        wanted_files = ("crypto.c", "mbedtls.c", "mbedtls.cc", "ecc.cc")
        found = {}
        all_objects = []
        for root, _, files in os.walk(bctoolbox_build):
            for name in files:
                if not name.endswith((".o", ".obj")):
                    continue
                full = os.path.join(root, name)
                all_objects.append(full)
                if os.path.basename(root) != "crypto":
                    continue
                # Derive the source filename from make-style object names
                # (e.g. "mbedtls.cc.o" -> "mbedtls.cc", "crypto.c.obj" ->
                # "crypto.c"); match distinct files so both mbedtls.c and
                # mbedtls.cc are kept.
                src_name = None
                for cand in wanted_files:
                    if name == cand + ".o" or name == cand + ".obj" or name.startswith(cand + "."):
                        src_name = cand
                        break
                if src_name is not None and src_name not in found:
                    found[src_name] = full
        missing = [f for f in wanted_files if f not in found]
        if missing:
            dump = "\n".join(sorted(all_objects)[:100])
            raise ConanException(
                "private bctoolbox build produced no crypto objects for %s under %s; objects seen:\n%s"
                % (missing, bctoolbox_build, dump if dump else "<no .o/.obj files at all>"))
        objects = [found[f] for f in wanted_files]
        self.output.info("harvested private crypto objects: %s" % objects)
        archiver = shutil.which("ar") or shutil.which("llvm-ar")
        if not archiver:
            raise ConanException("no 'ar'/'llvm-ar' on PATH to archive private crypto objects")
        libdir = os.path.join(priv_prefix, "lib")
        os.makedirs(libdir, exist_ok=True)
        priv_lib = os.path.join(libdir, "libbctbx-crypto-priv.a")
        try:
            if os.path.isfile(priv_lib):
                os.remove(priv_lib)
        except OSError as exc:
            raise ConanException("cannot remove stale %s: %s" % (priv_lib, exc))
        cmd = '"%s" rcs "%s"%s' % (archiver, priv_lib, "".join(' "%s"' % o for o in objects))
        self.output.info("archiving private crypto objects: %s" % cmd)
        self.run(cmd, env="conanbuild")
        if not os.path.isfile(priv_lib):
            raise ConanException("private crypto archive missing after ar: %s" % priv_lib)
        self._dedup_private_crypto_archive(priv_lib, objects, archiver)
        self.output.info("private bctoolbox crypto archive ready: %s" % priv_lib)
        return priv_lib

    def _embed_private_crypto(self, bctoolbox_src, priv_prefix, priv_crypto_lib):
        # bzrtp sources include <bctoolbox/crypto.h> unconditionally, so the
        # vendored header pair must be visible; the crypto OBJECTS come from
        # the sub-built archive (correct -I/-D already baked in at compile
        # time), linked here together with the private mbedtls archives.
        for hdr in ("include/bctoolbox/crypto.h", "include/bctoolbox/crypto.hh"):
            if not os.path.isfile(os.path.join(bctoolbox_src, hdr)):
                raise ConanException("vendored bctoolbox missing %s" % hdr)
        vendor_include = os.path.join(bctoolbox_src, "include")
        mbedtls_libdir = os.path.join(priv_prefix, "lib")
        if not os.path.isdir(vendor_include):
            raise ConanException("private crypto include dir missing: %s" % vendor_include)
        for lib in ("libmbedcrypto.a", "libmbedtls.a", "libmbedx509.a", "libbctbx-crypto-priv.a"):
            if not os.path.isfile(os.path.join(mbedtls_libdir, lib)):
                raise ConanException("private crypto lib missing: %s" % os.path.join(mbedtls_libdir, lib))
        src_cmake = os.path.join(self.source_folder, "src", "CMakeLists.txt")
        # 1) expose the vendored crypto headers to the bzrtp compile AND to
        # any in-build consumer of the public bzrtp/bzrtp.h (notably the
        # upstream bzrtp-tester, which failed at 57% with
        # 'bctoolbox/crypto.h file not found' because PRIVATE does not
        # propagate). Bare PUBLIC was falsified on真机: CMake rejects an
        # INTERFACE path inside the source tree without a generator
        # expression. $<BUILD_INTERFACE:...> propagates at build time only
        # and keeps the installed INTERFACE clean.
        old_lib = "add_library(bzrtp ${BZRTP_SOURCE_FILES})"
        new_lib = (
            "add_library(bzrtp ${BZRTP_SOURCE_FILES})\n"
            'target_include_directories(bzrtp PUBLIC "$<BUILD_INTERFACE:%s>")'
            % vendor_include.replace("\\", "/")
        )
        replace_in_file(self, src_cmake, old_lib, new_lib, strict=True)
        # 2) link the sub-built crypto archive plus the private mbedtls
        # static archives into libbzrtp (order: crypto-priv before mbedtls).
        # Transitivity fix (真机 2026-09-17: duplicate-symbol round passed,
        # tester link now reports undefined sqlite3_* and bctbx_rng_*):
        # libbzrtp is STATIC, so its PRIVATE link libs are not propagated to
        # the in-build bzrtp-tester executable (which links only
        # ${BCToolbox_tester_TARGET} + bzrtp upstream). Publish the private
        # archives as PUBLIC behind $<BUILD_INTERFACE:...> so the tester
        # inherits them at build time while the installed INTERFACE stays
        # clean (same hygiene as the include fix above, which was falsified
        # bare-PUBLIC). SQLite stays upstream-PUBLIC (${SQLite3_TARGET}).
        old_link = "target_link_libraries(bzrtp PRIVATE ${BCToolbox_TARGET})"
        new_link = (
            "target_link_libraries(bzrtp PRIVATE ${BCToolbox_TARGET})\n"
            'target_link_libraries(bzrtp PUBLIC\n'
            '  \"$<BUILD_INTERFACE:%s>\"\n  \"$<BUILD_INTERFACE:%s>\"\n  \"$<BUILD_INTERFACE:%s>\"\n  \"$<BUILD_INTERFACE:%s>\")'
            % (
                os.path.join(mbedtls_libdir, "libbctbx-crypto-priv.a").replace("\\", "/"),
                os.path.join(mbedtls_libdir, "libmbedtls.a").replace("\\", "/"),
                os.path.join(mbedtls_libdir, "libmbedx509.a").replace("\\", "/"),
                os.path.join(mbedtls_libdir, "libmbedcrypto.a").replace("\\", "/"),
            )
        )
        replace_in_file(self, src_cmake, old_link, new_link, strict=True)
        self.output.info("linked sub-built private crypto archive into libbzrtp")
        self._fix_tester_linkage(priv_prefix)

    def _sqlite_lib_file(self):
        # Resolve the real sqlite archive from the Conan package (fail
        # closed). Depending only on ${SQLite3_TARGET} was falsified: the
        # tester still reports undefined sqlite3_* even with the target on
        # its link line, so link the file absolutely as well.
        try:
            pkg = str(self.dependencies["sqlite3"].package_folder)
        except Exception as exc:
            raise ConanException("sqlite3 package folder unavailable: %s" % exc)
        for cand in (os.path.join(pkg, "lib", "libsqlite3.a"),
                     os.path.join(pkg, "lib", "sqlite3.lib")):
            if os.path.isfile(cand):
                return cand.replace("\\", "/")
        libdir = os.path.join(pkg, "lib")
        try:
            names = sorted(os.listdir(libdir))
        except OSError as exc:
            raise ConanException("cannot list sqlite3 libdir %s: %s" % (libdir, exc))
        for name in names:
            if name.endswith(".a") and "sqlite" in name.lower():
                return os.path.join(libdir, name).replace("\\", "/")
        raise ConanException("no sqlite archive found under %s (seen: %s)" % (libdir, names))

    def _fix_tester_linkage(self, priv_prefix):
        # Belt-and-suspenders for the in-build tester: even with the PUBLIC
        # BUILD_INTERFACE above, make the tester link explicit so a static
        # libbzrtp never leaves sqlite/priv symbols unresolved (the observed
        # undefined sqlite3_open_v2/bctbx_rng_context_new come from tester
        # objects + zidCache/bzrtp objects inside libbzrtp.a). Upstream test
        # links only ${BCToolbox_tester_TARGET} + bzrtp; append the absolute
        # sqlite archive (resolved from the Conan package, not only the
        # ${SQLite3_TARGET} variable which proved insufficient on真机) plus
        # the four private archives by absolute path (executable: no
        # install-INTERFACE pollution). Idempotent by marker comment.
        test_cmake = os.path.join(self.source_folder, "test", "CMakeLists.txt")
        try:
            with open(test_cmake, "r", encoding="utf-8", errors="replace") as handle:
                text = handle.read()
        except OSError as exc:
            raise ConanException("cannot read %s: %s" % (test_cmake, exc))
        if "bzrtp recipe: tester explicit sqlite+priv link" in text:
            return
        old = "target_link_libraries(bzrtp-tester PRIVATE ${BCToolbox_tester_TARGET} bzrtp)"
        libdir = os.path.join(priv_prefix, "lib").replace("\\", "/")
        sqlite_lib = self._sqlite_lib_file()
        new = (
            "target_link_libraries(bzrtp-tester PRIVATE ${BCToolbox_tester_TARGET} bzrtp)\n"
            "# bzrtp recipe: tester explicit sqlite+priv link (static libbzrtp PRIVATE deps do not propagate)\n"
            "target_link_libraries(bzrtp-tester PRIVATE ${SQLite3_TARGET}\n"
            '  "%s"\n  "%s/libbctbx-crypto-priv.a"\n  "%s/libmbedtls.a"\n  "%s/libmbedx509.a"\n  "%s/libmbedcrypto.a")'
            % (sqlite_lib, libdir, libdir, libdir, libdir)
        )
        replace_in_file(self, test_cmake, old, new, strict=True)
        self.output.info("tester link patched with explicit sqlite+priv libs: %s" % sqlite_lib)

    def _ensure_sqlite_include(self):
        # Upstream typedef.h includes "sqlite3.h" under ZIDCACHE_ENABLED and
        # the target propagation (SQLite::SQLite3 via CONFIG) proved unable
        # to place it on the compile line on真机 (configure passes, 5%
        # compile fails). Add the resolved sqlite3 package include dir
        # explicitly: minimal, additive, no test skipped.
        try:
            pkg = str(self.dependencies["sqlite3"].package_folder)
        except Exception as exc:
            raise ConanException("sqlite3 package folder unavailable: %s" % exc)
        inc = os.path.join(pkg, "include")
        if not os.path.isfile(os.path.join(inc, "sqlite3.h")):
            raise ConanException("resolved sqlite3 lacks include/sqlite3.h under %s" % pkg)
        src_cmake = os.path.join(self.source_folder, "src", "CMakeLists.txt")
        old = "if(SQLite3_FOUND)"
        new = (
            'target_include_directories(bzrtp PUBLIC "$<BUILD_INTERFACE:%s>")\n'
            "if(SQLite3_FOUND)" % inc.replace("\\", "/")
        )
        replace_in_file(self, src_cmake, old, new, strict=True)
        self.output.info("sqlite3 include pinned: %s" % inc)

    def generate(self):
        deps = CMakeDeps(self)
        # bc_find_package(SQLite3 SQLite::SQLite3 sqlite3 REQUIRED) short-circuits
        # only when TARGET SQLite::SQLite3 already exists; otherwise it stamps the
        # non-existent SQLite::SQLite3 name into the link line and configure fails.
        # Generate exactly that file/target name from the sqlite3 package.
        deps.set_property("sqlite3", "cmake_file_name", "SQLite3")
        deps.set_property("sqlite3", "cmake_target_name", "SQLite3")
        deps.set_property("sqlite3", "cmake_target_namespace", "SQLite")
        deps.generate()
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        # Resolve find_package(BCToolbox) to upstream's own installed config
        # (<pkg>/share/BCToolbox/cmake/BCToolboxConfig.cmake) instead of the
        # CMakeDeps one: only the upstream config ships the bc_* CMake macros,
        # the BCToolbox_TARGET variable and the tester component target.
        # A <PackageName>_DIR cache entry wins over prefix-path search.
        try:
            bctoolbox_pkg = str(self.dependencies["bctoolbox"].package_folder)
        except Exception as exc:
            raise ConanException("bctoolbox package folder unavailable: %s" % exc)
        config_dir = os.path.join(bctoolbox_pkg, "share", "BCToolbox", "cmake")
        if not os.path.isfile(os.path.join(config_dir, "BCToolboxConfig.cmake")):
            raise ConanException(
                "upstream BCToolboxConfig.cmake not found under %s" % config_dir
            )
        tc.variables["BCToolbox_DIR"] = config_dir
        # Build and run the upstream non-regression suite (bzrtp-tester) in
        # build(); its run output is the upstream test evidence of this recipe.
        tc.variables["ENABLE_UNIT_TESTS"] = True
        # Upstream default ON (key continuity via sqlite); sqlite3/3.49.1 is a
        # regular require above, so the cache stays genuinely enabled.
        tc.variables["ENABLE_ZIDCACHE"] = True
        if str(self.settings.get_safe("os")) == "OHOS":
            # Force the probed compilers through cache variables as well: the
            # generated toolchain file otherwise bakes the profile-pinned
            # absolute paths verbatim (missing file on some workers).
            tc.cache_variables["CMAKE_C_COMPILER"] = self._compiler_executable("c", "clang")
            tc.cache_variables["CMAKE_CXX_COMPILER"] = self._compiler_executable(
                "cpp", "clang++"
            )
        tc.generate()
        if str(self.settings.get_safe("os")) == "OHOS":
            self._patch_cmake_toolchain_compilers()

    def build(self):
        apply_conandata_patches(self)
        # Private crypto backend (4th strategy cycle: independent sub-build).
        # Rounds 9-11 injected the four bctoolbox backend sources directly
        # into the bzrtp target and were falsified on真机 at
        # "src/crypto/mbedtls.c:23:10: fatal error: 'utils.h' file not found":
        # that header lives at bctoolbox src/utils.h, visible only through
        # upstream's own top-level include_directories(include src <binary>)
        # plus the generated config.h (-DHAVE_CONFIG_H), which a hand-written
        # -I list cannot reproduce. This round instead configures+builds the
        # vendored bctoolbox tree with its own CMake (mbedtls found via
        # CMAKE_PREFIX_PATH) and links ONLY the four crypto objects
        # (re-archived, so the non-crypto symbols already shipped by the
        # published bctoolbox are not duplicated) into libbzrtp, so the 30
        # upstream tests run for real. No test is skipped or stubbed.
        # SQLite3 discovery (preflight 2026-09-17): upstream
        # bc_find_package(SQLite3 SQLite::SQLite3 sqlite3 REQUIRED) stamps the
        # legacy SQLite::SQLite3 name into SQLite3_TARGET even when the finder
        # behind it provides the modern SQLite3::SQLite3 target (CMake >= 3.14
        # module, CMake 4.4 on preflight), so src/ links a non-existent target
        # (CMake Error: Target "bzrtp" links to SQLite::SQLite3 but the target
        # was not found, with if(SQLite3_FOUND) true). Bypass it: prefer the
        # Conan CONFIG (CMakeDeps generates SQLite3Config providing
        # SQLite::SQLite3), alias either direction, and set the two variables
        # src/CMakeLists.txt actually consumes (SQLite3_FOUND/SQLite3_TARGET).
        replace_in_file(
            self,
            os.path.join(self.source_folder, "CMakeLists.txt"),
            "bc_find_package(SQLite3 SQLite::SQLite3 sqlite3 REQUIRED)",
            "find_package(SQLite3 REQUIRED CONFIG)\n"
            "if(NOT TARGET SQLite::SQLite3 AND TARGET SQLite3::SQLite3)\n"
            "  add_library(SQLite::SQLite3 ALIAS SQLite3::SQLite3)\n"
            "endif()\n"
            "if(NOT TARGET SQLite3::SQLite3 AND TARGET SQLite::SQLite3)\n"
            "  add_library(SQLite3::SQLite3 ALIAS SQLite::SQLite3)\n"
            "endif()\n"
            "set(SQLite3_FOUND TRUE)\n"
            "if(TARGET SQLite::SQLite3)\n"
            "  set(SQLite3_TARGET SQLite::SQLite3)\n"
            "elseif(TARGET SQLite3::SQLite3)\n"
            "  set(SQLite3_TARGET SQLite3::SQLite3)\n"
            "endif()",
            strict=True,
        )
        # E002/readonly_tmp: every child process inherits a writable temp dir
        # even if the buildenv sourcing misses it; prefer the hmbs-injected value.
        tmpdir = (
            os.environ.get("TMPDIR")
            or os.environ.get("TMP")
            or os.environ.get("TEMP")
            or self.build_folder
        )
        try:
            os.makedirs(tmpdir, exist_ok=True)
        except Exception:
            tmpdir = self.build_folder
        os.environ["TMPDIR"] = tmpdir
        os.environ["TMP"] = tmpdir
        os.environ["TEMP"] = tmpdir
        if self._published_bctoolbox_has_crypto():
            self.output.info("resolved bctoolbox ships crypto.h; skipping private backend")
        else:
            self.output.info("resolved bctoolbox lacks crypto.h; building private mbedtls + crypto backend")
            mbedtls_src, bctoolbox_src, mbedtls_build, bctoolbox_build, priv_prefix = self._vendor_paths()
            self._build_private_mbedtls(mbedtls_src, mbedtls_build, priv_prefix)
            priv_crypto_lib = self._build_private_bctoolbox(bctoolbox_src, bctoolbox_build, priv_prefix)
            self._embed_private_crypto(bctoolbox_src, priv_prefix, priv_crypto_lib)
        # Always applicable: explicit sqlite3 include (target propagation
        # alone left sqlite3.h off the compile line on真机).
        self._ensure_sqlite_include()
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        self._run_upstream_tester()

    def _run_upstream_tester(self):
        tester_dir = os.path.join(self.build_folder, "test")
        tester = os.path.join(tester_dir, "bzrtp-tester")
        if not os.path.isfile(tester):
            raise ConanException("upstream tester was not built at %s" % tester)
        resource_dir = os.path.join(self.source_folder, "test")
        if not os.path.isfile(os.path.join(resource_dir, "patternZIDAlice.sqlite")):
            raise ConanException(
                "upstream resource patternZIDAlice.sqlite missing under %s" % resource_dir
            )
        # Capture combined stdout+stderr to a log file inside build_folder
        # (never /tmp): evidence parsing must not depend on Conan's stdout
        # return value. Run from the tester's own directory: the ZID cache
        # tests create their working database next to the current directory,
        # and a shared build records relative DT_NEEDED entries resolved
        # against it (same cwd rule as bctoolbox/5.3.115 knowledge #13).
        log_path = os.path.join(self.build_folder, "bzrtp_tester.log")
        command = '"%s" --resource-dir "%s" > "%s" 2>&1' % (tester, resource_dir, log_path)
        try:
            self.run(command, cwd=tester_dir)
        except ConanException as exc:
            # Non-zero exit: the captured log below still holds the evidence
            # _save_upstream_result() parses. Fall through to parse.
            self.output.warning("bzrtp-tester exited non-zero: %s" % exc)
        log = ""
        try:
            with open(log_path, "r", encoding="utf-8", errors="replace") as handle:
                log = handle.read()
        except OSError as exc:
            raise ConanException("cannot read tester log %s: %s" % (log_path, exc))
        self.output.info("upstream bzrtp-tester output:\n" + log)
        self._save_upstream_result(log, command)

    def _save_upstream_result(self, log, command):
        # CUnit "Run Summary" table (bc_tester framework):
        #   Run Summary:    Type  Total    Ran Passed Failed Inactive
        #                  suites      4      4    n/a      0        0
        #                   tests     30     30     30      0        0
        #                  asserts   ... (assert counts are informational only)
        if "Run Summary:" not in log:
            raise ConanException(
                "upstream tester produced no Run Summary (crashed or skipped); "
                "refusing to continue. log tail:\n%s" % log[-2000:]
            )
        match = re.search(
            r"^\s*tests\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)",
            log,
            re.MULTILINE,
        )
        if not match:
            raise ConanException(
                "cannot parse Run Summary tests row; refusing to continue. "
                "log tail:\n%s" % log[-2000:]
            )
        total, ran, passed, failed, inactive = (int(match.group(i)) for i in range(1, 6))
        # Falsifiability cross-checks (exit-0-alone is not proof):
        # every registered test must print a "started" line and a "passed" line.
        started = len(re.findall(r" Test \[.*?\] started", log))
        passed_lines = len(re.findall(r" Test \[.*?\] passed", log))
        zidcache_disabled = "Test skipped as ZID cache is disabled" in log
        self.output.info(
            "upstream summary: total=%d ran=%d passed=%d failed=%d inactive=%d "
            "started_lines=%d passed_lines=%d zidcache_disabled=%s"
            % (total, ran, passed, failed, inactive, started, passed_lines, zidcache_disabled)
        )
        if total != UPSTREAM_TEST_TOTAL:
            raise ConanException(
                "upstream test total changed (got %d, audited %d); refusing to "
                "continue with an unverified denominator." % (total, UPSTREAM_TEST_TOTAL)
            )
        if zidcache_disabled:
            raise ConanException(
                "ZID cache tests silently skipped (ZIDCACHE_ENABLED off); the 2 "
                "zidcache cases would pass vacuously. Refusing to continue."
            )
        if started != total or passed_lines != passed:
            raise ConanException(
                "per-test evidence lines do not match the summary "
                "(started=%d passed_lines=%d summary_total=%d summary_passed=%d); "
                "refusing to continue." % (started, passed_lines, total, passed)
            )
        if ran != total or failed != 0 or inactive != 0 or passed != total:
            raise ConanException(
                "upstream suite not fully green "
                "(ran=%d passed=%d failed=%d inactive=%d of %d); refusing to continue."
                % (ran, passed, failed, inactive, total)
            )
        upstream = {
            "status": "passed",
            "framework": "bcunit",
            "command": command,
            "discovered": total,
            "executed": ran,
            "passed": passed,
            "failed": failed,
            "skipped": inactive,
        }
        marker = "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream, ensure_ascii=False)
        print(marker, flush=True)
        self.output.info(marker)
        try:
            with open(
                os.path.join(self.build_folder, "hmbs_upstream.json"),
                "w",
                encoding="utf-8",
                newline="\n",
            ) as handle:
                json.dump(upstream, handle, ensure_ascii=False, indent=2)
        except OSError as exc:
            self.output.warning("write hmbs_upstream.json failed: %s" % exc)

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # bzrtp-tester is a build-time verification artifact (already executed
        # in build()), not a deliverable of this library package: drop it and
        # its resource database so the package ships the library, its headers
        # and its CMake config alone (R38: pure library, no commands.json).
        rmdir(self, os.path.join(self.package_folder, "bin"))
        rmdir(self, os.path.join(self.package_folder, "share", "bzrtp-tester"))
        # Private backend deliverables: consumers include bzrtp/bzrtp.h, which
        # includes bctoolbox/crypto.h, so ship the vendored header pair when
        # the resolved bctoolbox did not provide them. The bctbx crypto
        # objects live in the sub-built libbctbx-crypto-priv.a (NOT merged
        # into libbzrtp.a for static builds); the private mbedtls static
        # archives are shipped for static consumers (shared libbzrtp already
        # carries them via PRIVATE link).
        # Self-containment (2026-09-18 round 2, different layer from the
        # test_package explicit-link fix): the shipped crypto.h itself does
        # '#include "bctoolbox/list.h"' + '#include "bctoolbox/port.h"'
        # (verified against upstream bctoolbox 5.3.115 sources), which live
        # in the bctoolbox dependency package. The consumer-side explicit
        # find/link did not put that -I on the test_package compile line on
        #真机 (same 'bctoolbox/list.h file not found' fingerprint), so ship
        # the full vendored include/bctoolbox header set alongside: the
        # consumer then resolves list.h/port.h via bzrtp's own -I with zero
        # dependence on bctoolbox include propagation or -I ordering.
        # Version-lock safety: the copies come from the exact vendored
        # 5.3.115 tree (same conandata vendor entry as the crypto objects),
        # and this repo's bctoolbox/5.3.115 patches touch .c files only, so
        # the non-crypto headers are content-identical to the dependency
        # package's; when a crypto-enabled bctoolbox is resolved the whole
        # block (including these copies) is skipped automatically.
        try:
            _, bctoolbox_src, _, _, priv_prefix = self._vendor_paths()
            if not self._published_bctoolbox_has_crypto():
                for pattern in ("*.h", "*.hh"):
                    copy(
                        self,
                        pattern,
                        src=os.path.join(bctoolbox_src, "include", "bctoolbox"),
                        dst=os.path.join(self.package_folder, "include", "bctoolbox"),
                    )
                for hdr in ("crypto.h", "crypto.hh", "list.h", "port.h"):
                    if not os.path.isfile(os.path.join(self.package_folder, "include", "bctoolbox", hdr)):
                        raise ConanException("private backend packaging missing include/bctoolbox/%s" % hdr)
                for lib in ("libbctbx-crypto-priv.a", "libmbedtls.a", "libmbedx509.a", "libmbedcrypto.a"):
                    copy(
                        self,
                        lib,
                        src=os.path.join(priv_prefix, "lib"),
                        dst=os.path.join(self.package_folder, "lib"),
                    )
        except Exception as exc:
            self.output.warning("private backend packaging failed: %s" % exc)
        # Persist upstream evidence for cache-hit re-emit via test_package.
        try:
            copy(
                self,
                "hmbs_upstream.json",
                src=self.build_folder,
                dst=os.path.join(self.package_folder, "res"),
            )
        except Exception:
            pass

    def package_info(self):
        self.cpp_info.libs = ["bzrtp"]
        # Private backend link closure: when the vendored archives were
        # shipped (published bctoolbox lacks crypto), static consumers need
        # them after libbzrtp (crypto-priv first, then mbedtls); shared
        # libbzrtp already embeds them.
        try:
            libdir = os.path.join(self.package_folder, "lib")
            priv = [lib for lib in ("bctbx-crypto-priv", "mbedtls", "mbedx509", "mbedcrypto")
                    if os.path.isfile(os.path.join(libdir, "lib%s.a" % lib))]
            if priv:
                self.cpp_info.libs.extend(priv)
        except Exception:
            pass
        self.cpp_info.requires = ["bctoolbox::bctoolbox", "sqlite3::sqlite3"]
        self.cpp_info.set_property("cmake_file_name", "bzrtp")
        self.cpp_info.set_property("cmake_target_name", "bzrtp::bzrtp")
        # The library is built from C++ objects (cryptoUtils.cc) behind a
        # C-compatible API. When packaged as a static archive a pure C consumer
        # must also link the C++ runtime or the link fails on the C++ symbols
        # (same E247 pattern as bctoolbox/5.3.115). With shared=True the .so
        # already carries DT_NEEDED libc++_shared.so.
        if not self.options.shared:
            self.cpp_info.system_libs = ["c++"]
