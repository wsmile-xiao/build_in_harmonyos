#!/usr/bin/env python3
"""Conan test_package for libecap 1.0.1 — consumer-side functional tests.

Builds two test programs against the packaged libecap and runs them:

1. test_version — libecap::Version value semantics + VersionString() linkage.
2. test_area — libecap::Name identity semantics + libecap::Area buffer API.
"""

import os

from conan import ConanFile


def _ensure_writable_tmpdir(build_folder=None):
    # Mirror of the main recipe probe: clang++ temp files must avoid
    # read-only /tmp. Prefer HMBS-injected dirs, fall back to build folder.
    candidates = [
        os.environ.get("HMBS_TMPDIR"),
        os.environ.get("TMPDIR"),
        os.environ.get("TMP"),
        os.environ.get("TEMP"),
    ]
    if build_folder:
        candidates.append(os.path.join(build_folder, ".tmp"))
    home = os.environ.get("HOME")
    if home:
        candidates.append(os.path.join(home, "tmp"))
    for cand in candidates:
        if not cand:
            continue
        try:
            os.makedirs(cand, exist_ok=True)
            probe = os.path.join(cand, ".tmp-write-probe")
            with open(probe, "w") as _pf:
                _pf.write("ok")
            os.unlink(probe)
            os.environ["TMPDIR"] = cand
            os.environ["TMP"] = cand
            os.environ["TEMP"] = cand
            return cand
        except OSError:
            continue
    return None


class LibecapTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        _ensure_writable_tmpdir(getattr(self, "build_folder", None))
        # Profile CXX may be as dead as CC; probe live candidates first.
        cxx = os.environ.get("CXX", "clang++")
        for cand in (cxx, "/storage/Users/currentUser/usr/local/bin/clang++",
                     "/storage/Users/currentUser/.harmonybrew/bin/clang++",
                     "clang++", "c++", "g++"):
            if not cand:
                continue
            try:
                self.run('"%s" --version' % cand)
                if cand != cxx:
                    self.output.info("hmbs_cc: test_package CXX %s -> %s" % (cxx, cand))
                cxx = cand
                break
            except Exception:
                continue
        # Direct compilation: link against libecap from the Conan package.
        # NOTE: upstream consumers are all autotools-based, so automake
        # passes -DHAVE_CONFIG_H (from AC_CONFIG_HEADERS) for free and
        # libecap/common/libecap.h then pulls the generated
        # libecap/common/autoconf.h that defines LIBECAP_VERSION (used as a
        # default argument in registry.h and by VersionString() in
        # registry.cc). A manual clang++ invocation must pass the same
        # flag, otherwise registry.h fails with "use of undeclared
        # identifier 'LIBECAP_VERSION'". The installed autoconf.h lives
        # under include/libecap/common/, already covered by inc_flags.
        dep = self.dependencies["libecap"]
        cpp = dep.cpp_info
        inc_flags = " ".join(f"-I{d}" for d in cpp.includedirs)
        lib_flags = " ".join(f"-L{d}" for d in cpp.libdirs)
        link_flags = " ".join(f"-l{l}" for l in cpp.libs)
        self.run(f"{cxx} -DHAVE_CONFIG_H test_version.cpp -o test_version {inc_flags} {lib_flags} {link_flags}")
        self.run(f"{cxx} -DHAVE_CONFIG_H test_area.cpp -o test_area {inc_flags} {lib_flags} {link_flags}")

    def test(self):
        _ensure_writable_tmpdir(getattr(self, "build_folder", None))
        # OHOS: /system/bin/sh (mksh) cannot execute ELF binaries.
        # Use the HMBS-provided shell to wrap binary execution. The old
        # default /data/service/hnp/bin/bash is inaccessible on the
        # current host, so prefer CONFIG_SHELL/SHELL and fall back to
        # /bin/sh instead of the dead hnp path.
        shell = os.environ.get("CONFIG_SHELL") or os.environ.get("SHELL")
        if not shell or shell == "/data/service/hnp/bin/bash":
            shell = "/bin/sh"
        bash = shell
        dep = self.dependencies["libecap"]
        cpp = dep.cpp_info
        lib_dirs = ":".join(str(d) for d in cpp.libdirs)
        # Test 1: Version API + library linkage (VersionString lives in libecap).
        self.run(f"{bash} -c 'export LD_LIBRARY_PATH={lib_dirs}:$LD_LIBRARY_PATH; ./test_version'", env="conanrun")
        # Test 2: Name + Area API.
        self.run(f"{bash} -c 'export LD_LIBRARY_PATH={lib_dirs}:$LD_LIBRARY_PATH; ./test_area'", env="conanrun")
        # HMBS machine-evidence gate: both test programs ran above (self.run
        # raises on non-zero exit, so reaching here means 2/2 passed).
        self.output.info(
            'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":true,'
            '"command":"./test_version + ./test_area",'
            '"discovered":2,"passedCount":2}')
