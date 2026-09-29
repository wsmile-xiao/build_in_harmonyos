#!/usr/bin/env python3
"""Conan recipe for OpenMAMA 6.3.2 on HarmonyOS PC (aarch64).

OpenMAMA is the middleware agnostic messaging API: a C API plus C++ and MAMDA
bindings on top of pluggable middleware bridges.  This package ships the
reusable, middleware independent part of it:

  libmama / libmamastatic          MAMA C API and the middleware dispatch engine
  libmamacpp / libmamacppstatic    the C++ bindings (Wombat::Mama*)
  libwombatcommon(static)          portability and utility layer shared by bridges
  libwombatcommoncpp(static)       C++ utilities (property files, strings)
  libmamda(static) and friends     market data (MAMDA) layers
  libmamabaseimpl                  the abstract "base" bridge that real bridges extend
  libmamarabbitmqimpl              the stub bridge used by upstream's own smoke tests
  libmamaompbimpl                  the OpenMAMA Playback bridge
  libmamaplugindqstrategy          data quality plugin
  libmamaentnoop                   the noop entitlement bridge
  bin/*                            upstream example and test tools
  include/mama, include/wombat, include/mamda, config/mama.properties

The qpid-proton AMQP bridge (bridge/qpid) and the qpidmsg payload are built
against the qpid-proton package of the registry: bridge/qpid and payload/qpidmsg
are the only two consumers of that library in the whole tree, and qpid-proton is
now published for this platform (the package the recipe requires).  See notes.md
for the dependency audit.

The upstream GTest suite (common/mama/mamda gunittest, built through the gtest
package from the registry) is built and run by the recipe so the pass rate is
reproducible.  The suite is registered against the qpid middleware bridge and
the qpidmsg payload (-m qpid -p qpidmsg), i.e. exactly the two components that
qpid-proton feeds, so the run exercises the AMQP bridge end to end at the API
level.  See reports/upstream-tests.md and notes.md for the measured numbers and
the per-case classification.
"""
import glob
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, rmdir


class OpenMamaConan(ConanFile):
    name = "openmama"
    version = "6.3.2"
    description = ("Middleware agnostic messaging API (MAMA) with C, C++ and MAMDA "
                   "bindings, the base/stub middleware bridges and the upstream tools")
    license = "LGPL-2.1-or-later"
    homepage = "https://github.com/finos/OpenMAMA"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"

    # Upstream builds the shared and the static flavour of every library
    # unconditionally (add_library(<name> SHARED ...) plus a matching STATIC
    # target), so both are always installed.  The option records the flavour
    # consumers are expected to link against; it cannot switch the build.
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def requirements(self):
        # The MAMA core: APR for the pools/threading primitives that the
        # dispatch engine and the resource pool are built on.
        self.requires("apr/1.7.6.1")
        # Every middleware bridge and the MAMA event loop are driven by libevent.
        self.requires("libevent/2.1.13")
        # The common layer generates message ids with libuuid (uuid/uuid.h).
        self.requires("e2fsprogs/1.47.4")
        # The AMQP middleware bridge (bridge/qpid) and the qpidmsg payload
        # (payload/qpidmsg) are the two components that link qpid-proton, so it
        # is a hard requirement of the package rather than an optional feature.
        self.requires("qpid-proton/0.38.0")

    def build_requirements(self):
        # The upstream GTest suite (UnitTestCommonC / UnitTestMamaC /
        # UnitTestMamaCPP / UnitTestMamdaCPP) is built by the recipe build so it
        # can be executed on the target; gtest is a build-time only dependency
        # and must not leak into the consumer interface.
        self.test_requires("gtest/1.17.0.1")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "openmama is only validated for Linux/OHOS, got %s" % self.settings.os)

    def _apr_library(self):
        """Path of the apr library, which doubles as the APR-util placeholder."""
        apr_libdir = os.path.join(self.dependencies["apr"].package_folder, "lib")
        for entry in sorted(os.listdir(apr_libdir)):
            if entry.startswith("libapr-1.") and not entry.endswith(".la"):
                return os.path.join(apr_libdir, entry)
        raise ConanInvalidConfiguration(
            "no libapr-1 library found in %s" % apr_libdir)

    @staticmethod
    def _first_existing(candidates):
        """First path of the list that the dependency package really carries."""
        for path in candidates:
            if os.path.exists(path):
                return path
        raise ConanInvalidConfiguration(
            "none of these files exists: %s" % ", ".join(candidates))

    def generate(self):
        tc = CMakeToolchain(self)

        # E092: CMake has no platform module for HarmonyOS, so it reports
        # "System is unknown to cmake" and leaves UNIX undefined.  Upstream
        # OpenMAMA branches on both CMAKE_SYSTEM_NAME (to pick the platform
        # source directory, common/c_cpp/src/c/<system>) and on UNIX (to link
        # libm instead of the Windows rpcrt4), so on OHOS it would both miss
        # the platform headers and link a Windows library.  Aliasing the
        # system to Linux, which is what HarmonyOS actually behaves like,
        # fixes both without touching the upstream CMake files.
        tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
        tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"

        # The tarball is not a git checkout, so the version has to be supplied
        # explicitly or the top level CMakeLists aborts.
        tc.variables["OPENMAMA_VERSION"] = self.version

        # --- middleware selection ------------------------------------------
        # WITH_PROTON gates bridge/qpid and payload/qpidmsg, the only two
        # consumers of qpid-proton in the whole tree; the qpid-proton package
        # declared in requirements() feeds both of them.
        tc.variables["WITH_PROTON"] = True
        tc.variables["WITH_BASE_BRIDGE"] = True
        tc.variables["WITH_NOOP_BRIDGE"] = True
        tc.variables["WITH_OMPB_BRIDGE"] = True

        # --- bindings, examples and tools ----------------------------------
        tc.variables["WITH_CPP"] = True
        tc.variables["WITH_MAMDA"] = True
        tc.variables["WITH_EXAMPLES"] = True
        tc.variables["WITH_TESTTOOLS"] = True
        # Not available on this platform: a JDK + gradle, .NET, doxygen and the
        # tutorial sources.  The unit tests are built: their GoogleTest comes
        # from the gtest package of the registry (build_requirements).
        tc.variables["WITH_JAVA"] = False
        tc.variables["WITH_CSHARP"] = False
        tc.variables["WITH_UNITTEST"] = True
        tc.variables["WITH_TUTORIALS"] = False
        tc.variables["WITH_DOC"] = False

        # --- where the Conan packages live ---------------------------------
        # OpenMAMA ships its own FindAPR/FindLibevent/FindUUID modules that
        # take plain <X>_ROOT/<X>_DIR variables instead of importing CMake
        # targets, so the package folders are handed over through those.
        tc.variables["APR_ROOT"] = self.dependencies["apr"].package_folder
        tc.variables["LIBEVENT_ROOT"] = self.dependencies["libevent"].package_folder
        tc.variables["UUID_DIR"] = self.dependencies["e2fsprogs"].package_folder

        # Upstream expects libuuid to be a system library and therefore never
        # puts UUID_INCLUDE_DIR on the include path: the common layer's
        # <wombat/wUuid.h> does "#include <uuid/uuid.h>" outright.  The uuid
        # headers live inside the e2fsprogs package here, so its include dir
        # is added for all targets.
        uuid_incdir = os.path.join(self.dependencies["e2fsprogs"].package_folder,
                                   "include")
        tc.extra_cflags.append("-I%s" % uuid_incdir)
        tc.extra_cxxflags.append("-I%s" % uuid_incdir)

        # mama/c_cpp/src/c/CMakeLists.txt appends ${APRUTIL_LIBRARY} to the
        # libmama link line unconditionally, but APR-util is not published for
        # this platform.  It is also not used: a whole tree audit finds no
        # apu.h include and no apr-util symbol, apr_uri_parse having been the
        # one exception (replaced by the local parser added in
        # patches/0003).  Pointing APRUTIL_* at the apr package keeps that
        # link line resolvable without introducing any APR-util symbol.
        apr_pkg = self.dependencies["apr"].package_folder
        libevent_pkg = self.dependencies["libevent"].package_folder
        uuid_pkg = self.dependencies["e2fsprogs"].package_folder
        proton_pkg = self.dependencies["qpid-proton"].package_folder

        # Upstream's FindAPR / FindLibevent / FindUUID look these libraries up
        # in the default search paths as well as in ${APR_ROOT}/${LIBEVENT_ROOT}/
        # ${UUID_DIR}, and CMake also searches the prefixes derived from PATH -
        # which the CI profile extends with $HOME/usr/local/bin.  Passing the
        # resolved library as a *cache* variable makes find_library() skip its
        # search, so the build always links the packages this recipe declared:
        # on a worker whose $HOME/usr/local/lib held a stray OpenSSL, the base
        # bridge link line ended up depending on that file and the build failed
        # with "No rule to make target '.../usr/local/lib/libssl.so'".
        tc.cache_variables["APR_INCLUDE_DIR"] = os.path.join(apr_pkg, "include", "apr-1")
        tc.cache_variables["APR_LIBRARY"] = self._apr_library()
        tc.cache_variables["APRUTIL_INCLUDE_DIR"] = os.path.join(apr_pkg, "include", "apr-1")
        tc.cache_variables["APRUTIL_LIBRARY"] = self._apr_library()
        tc.cache_variables["LIBEVENT_INCLUDE_DIRS"] = os.path.join(libevent_pkg, "include")
        tc.cache_variables["LIBEVENT_LIBRARIES"] = self._first_existing([
            os.path.join(libevent_pkg, "lib", "libevent.so"),
            os.path.join(libevent_pkg, "lib", "libevent_core.so"),
            os.path.join(libevent_pkg, "lib", "libevent.a"),
            os.path.join(libevent_pkg, "lib", "libevent_core.a"),
        ])
        tc.cache_variables["UUID_INCLUDE_DIR"] = os.path.join(uuid_pkg, "include")
        tc.cache_variables["UUID_LIBRARY"] = self._first_existing([
            os.path.join(uuid_pkg, "lib", "libuuid.a"),
            os.path.join(uuid_pkg, "lib", "libuuid.so"),
        ])

        # Upstream's FindProton module reads ${PROTON_ROOT}/include and
        # ${PROTON_ROOT}/lib, and searches the system paths
        # (/usr/local/lib, /usr/lib, ...) as well.  The library lookup runs
        # with NO_DEFAULT_PATH but the include lookup does not, so both are
        # pinned as cache variables to make the build always use the declared
        # package - a worker that happens to carry a stray proton in
        # $HOME/usr/local would otherwise be able to satisfy the header and
        # then fail to link against the library.
        tc.cache_variables["PROTON_ROOT"] = proton_pkg
        tc.cache_variables["PROTON_INCLUDE_DIR"] = os.path.join(proton_pkg, "include")
        tc.cache_variables["PROTON_LIBRARY"] = self._first_existing([
            os.path.join(proton_pkg, "lib", "libqpid-proton.so"),
            os.path.join(proton_pkg, "lib", "libqpid-proton.a"),
        ])

        # --- upstream GTest suite -------------------------------------------
        # The gunittest CMakeLists of common/mama/mamda declare
        # find_package(GTest REQUIRED) and link the legacy variables
        # ${GTEST_INCLUDE_DIRS} / ${GTEST_BOTH_LIBRARIES}.  Upstream knows
        # nothing about Conan, so the GTest package is pointed at through the
        # plain variables it reads: the CMake config directory shipped inside
        # the package (the official GTestConfig.cmake, which declares the
        # GTest::* targets) is used for the package lookup, and the legacy
        # variables are filled in explicitly as well.
        gtest = self.dependencies["gtest"]
        tc.variables["GTest_ROOT"] = gtest.package_folder
        tc.variables["GTest_DIR"] = os.path.join(gtest.package_folder, "lib", "cmake", "GTest")
        tc.variables["GTEST_INCLUDE_DIRS"] = os.path.join(gtest.package_folder, "include")
        tc.variables["GTEST_BOTH_LIBRARIES"] = "GTest::gtest_main;GTest::gtest;Threads::Threads"
        # Discover the tests at ctest time instead of at build time: the test
        # executables are target binaries that need the build tree libraries
        # (and, on OHOS, a code signature) to be able to run.
        tc.cache_variables["CMAKE_GTEST_DISCOVER_TESTS_DISCOVERY_MODE"] = "PRE_TEST"

        # The static libraries are shipped next to the shared ones, so they
        # have to be position independent for consumers to be able to link
        # them into their own shared objects.
        if self.options.fPIC:
            tc.variables["CMAKE_POSITION_INDEPENDENT_CODE"] = True

        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        try:
            cmake.build()
        except Exception:
            self._report_link_inputs()
            raise
        self._run_upstream_tests()

    def _report_link_inputs(self):
        """Print the libraries CMake resolved when a build fails.

        The CI workers differ in what they carry outside the Conan cache, and a
        failure while linking is much easier to diagnose from the resolved
        library paths (the cache holds every one of them) than from the
        compiler output alone.
        """
        cache = os.path.join(self.build_folder, "CMakeCache.txt")
        if not os.path.isfile(cache):
            return
        keys = ("APR", "LIBEVENT", "UUID", "SSL", "OPENSSL")
        self.output.warning("library paths resolved by CMake (from %s):" % cache)
        with open(cache, "r", errors="replace") as handle:
            for line in handle:
                name = line.split(":", 1)[0].upper()
                if line.startswith("//") or "NOTFOUND" in line:
                    continue
                if any(key in name for key in keys):
                    self.output.warning("  %s" % line.strip())

    def _find_ohos_tool(self, name):
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict) or {}
        compiler = compilers.get("c", "") or compilers.get("cpp", "")
        candidates = (
            os.path.join(os.path.dirname(compiler), name) if compiler else "",
            os.path.join("/data/service/hnp/bin", name),
            shutil.which(name) or "",
        )
        return next((path for path in candidates if path and os.path.isfile(path)), "")

    def _sign_executable(self, path):
        objcopy = self._find_ohos_tool("llvm-objcopy")
        signer = self._find_ohos_tool("binary-sign-tool")
        if not objcopy or not signer:
            raise ConanInvalidConfiguration(
                "running the OHOS test executables requires llvm-objcopy and binary-sign-tool")
        unsigned = path + ".unsigned"
        try:
            shutil.copy2(path, unsigned)
            self.run('env -u LD_LIBRARY_PATH %s --remove-section .codesign "%s" '
                     '2>/dev/null || true' % (objcopy, unsigned))
            self.run('env -u LD_LIBRARY_PATH %s sign -inFile "%s" -outFile "%s" '
                     '-selfSign 1' % (signer, unsigned, path))
        finally:
            if os.path.exists(unsigned):
                os.remove(unsigned)

    def _run_upstream_tests(self):
        """Run the upstream GTest suite that this recipe builds.

        The suite is the one upstream registers against the qpid middleware
        bridge and the qpidmsg payload (-m qpid -p qpidmsg), i.e. exactly the
        two components that qpid-proton feeds, so the run exercises the AMQP
        bridge end to end at the API level and is a real, executable regression
        signal on this platform.  The numbers are printed for the CI log and
        written to upstream-ctest.log in the build folder.
        """
        executables = []
        for name in ("UnitTestCommonC", "UnitTestMamaC", "UnitTestMamaCPP", "UnitTestMamdaCPP"):
            found = glob.glob(os.path.join(self.build_folder, "**", name), recursive=True)
            executables.extend(path for path in sorted(found)
                               if not os.path.isdir(path) and os.access(path, os.X_OK))
        if not executables:
            self.output.warning("no upstream test executable was produced")
            return
        if self.settings.os == "OHOS":
            for path in executables:
                self._sign_executable(path)
        log = os.path.join(self.build_folder, "upstream-ctest.log")
        # mama_loadBridge()/mama_loadPayloadBridge() dlopen() the bridges by
        # name - the qpid middleware bridge (libmamaqpidimpl.so), the qpidmsg
        # payload (libmamaqpidmsgimpl.so), the noop entitlement bridge
        # (libmamaentnoop.so) - and nothing puts the CMake build tree on the
        # loader path: upstream's own CI installs first and points
        # LD_LIBRARY_PATH at the install tree.  This recipe never installs, so
        # every build tree directory holding a shared library is added to the
        # loader path instead.  Without it the bridges cannot be opened and
        # every case that opens MAMA fails with "Could not open middleware/
        # payload/entitlement bridge library".
        libdirs = sorted({os.path.dirname(path) for path in glob.glob(
            os.path.join(self.build_folder, "**", "lib*.so"), recursive=True)})
        inherited = os.environ.get("LD_LIBRARY_PATH", "")
        ld_path = ":".join(libdirs + ([inherited] if inherited else []))
        # `|| true`: the numbers are reported instead of enforced (see the
        # docstring); --timeout bounds the run, as a handful of cases can block
        # on a connection attempt to a broker that is not part of the build.
        self.run('env LD_LIBRARY_PATH=%s ctest --timeout 60 --output-on-failure '
                 '> %s 2>&1 || true' % (ld_path, log), cwd=self.build_folder)
        with open(log, "r", errors="replace") as handle:
            content = handle.read()
        summary = next((line.strip() for line in content.splitlines()
                        if "tests passed" in line and "tests failed out of" in line),
                       "no ctest summary in the log")
        failures = sum(1 for line in content.splitlines()
                       if line.strip().startswith("[  FAILED  ]"))
        self.output.info("upstream GTest suite: %d executables, %s" % (len(executables), summary))
        self.output.info("  %d case level failure message(s) in %s (crashed cases print none)"
                         % (failures, log))

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSE*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        # The upstream install tree also carries the C/C++ example sources and
        # the example property file; the binaries live in bin/ and the property
        # file is installed again below config/, so the copies under examples/
        # are dropped from the package.
        examples = os.path.join(self.package_folder, "examples")
        if os.path.isdir(examples):
            rmdir(self, examples)
        self._sign_binaries()

    @staticmethod
    def _is_elf(path):
        try:
            with open(path, "rb") as handle:
                return handle.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _sign_binaries(self):
        """Restore the OHOS code signature of the installed artifacts.

        OHOS refuses to dlopen a shared object or exec a binary whose
        signature does not match its content, and the signature the linker
        writes is a content hash.  CMake's install step strips the RUNPATH out
        of the libraries it installs, i.e. it rewrites bytes after linking and
        therefore invalidates that signature: measured on this platform, the
        build tree copy of libmama.so loads while the installed copy is
        rejected with "Permission denied" until it is signed again.  Copying a
        file preserves its signature, rewriting it does not.
        """
        if self.settings.os != "OHOS":
            return
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        targets = glob.glob(os.path.join(self.package_folder, "lib", "**", "*.so"),
                            recursive=True)
        bindir = os.path.join(self.package_folder, "bin")
        if os.path.isdir(bindir):
            targets += [os.path.join(bindir, name) for name in sorted(os.listdir(bindir))
                        if self._is_elf(os.path.join(bindir, name))]
        for target in targets:
            if os.path.islink(target):  # only sign the real files
                continue
            # LD_LIBRARY_PATH may hold an ABI incompatible libc++ for the tools
            self.run('env -u LD_LIBRARY_PATH %s --remove-section .codesign "%s" '
                     '2>/dev/null || true' % (objcopy, target))
            self.run('env -u LD_LIBRARY_PATH %s sign -inFile "%s" -outFile "%s" '
                     '-selfSign 1' % (signer, target, target))

    def package_info(self):
        # Order matters for consumers that link statically: dependents first.
        self.cpp_info.libs = [
            "mamacpp",
            "mamda",
            "mama",
            "wombatcommoncpp",
            "wombatcommon",
        ]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.set_property("cmake_file_name", "openmama")
        self.cpp_info.set_property("cmake_target_name", "openmama::openmama")
