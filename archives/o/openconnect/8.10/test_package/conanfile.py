import os

from conan import ConanFile
from conan.tools.env import Environment


class OpenconnectTestConan(ConanFile):
    """test_package for openconnect — executes the installed client binary.

    R34: the test must substantially depend on the tested package. It runs
    `openconnect --version` (prints the version banner, GnuTLS feature
    list and supported protocols) and asserts the banner contents.
    """
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _all_dependency_lib_dirs(self):
        """Collect lib/ dirs across the whole dependency graph.

        The ohpcd gnutls/nettle/gmp/libunistring binary packages do not
        export their shared-library libdirs through the default conanrun
        aggregation (only libtasn1/libgcrypt/libgpg-error/libxml2 do),
        so the conanrun LD_LIBRARY_PATH is incomplete and the openconnect
        binary fails with 'gnutls_strerror: symbol not found'. Walking
        the full requirements graph here (ocserv precedent) makes the
        runtime path deterministic.
        """
        lib_dirs = []
        seen = set()
        stack = [self.dependencies["openconnect"]]
        while stack:
            dep = stack.pop(0)
            key = str(dep.ref)
            if key in seen:
                continue
            seen.add(key)
            if not dep.package_folder:
                try:
                    stack.extend(dep.dependencies.values())
                except Exception:
                    pass
                continue
            lib_dir = os.path.join(dep.package_folder, "lib")
            if os.path.isdir(lib_dir):
                lib_dirs.append(lib_dir)
            try:
                stack.extend(dep.dependencies.values())
            except Exception:
                pass
        return lib_dirs

    def test(self):
        # OHOS: /system/bin/sh (mksh) cannot execute ELF binaries —
        # use bash to wrap binary execution (ocserv/openfortivpn
        # precedent). test.sh runs openconnect --version and asserts the
        # version banner (v8.10 / GnuTLS / anyconnect protocol line).
        lib_dirs = self._all_dependency_lib_dirs()
        if lib_dirs:
            existing = os.environ.get("LD_LIBRARY_PATH", "")
            combined = ":".join(lib_dirs)
            os.environ["LD_LIBRARY_PATH"] = (
                combined + ":" + existing if existing else combined
            )
            self.output.info(
                "test LD_LIBRARY_PATH: %s" % os.environ["LD_LIBRARY_PATH"]
            )
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        # env="conanrun" fully replaces the process environment, so PATH
        # injection (os.environ / Environment.vars) never reaches the
        # script. Pass the executable's absolute path through an env var
        # the script honours instead.
        dep = self.dependencies["openconnect"]
        bindir = dep.cpp_info.bindirs[0] if dep.cpp_info.bindirs else "bin"
        if not os.path.isabs(bindir):
            bindir = os.path.join(dep.package_folder, bindir)
        exe = os.path.join(bindir, "openconnect")
        env = Environment()
        env.define("OPENCONNECT_BIN", exe)
        with env.vars(self).apply():
            self.run(f"{bash} test.sh", env="conanrun")
