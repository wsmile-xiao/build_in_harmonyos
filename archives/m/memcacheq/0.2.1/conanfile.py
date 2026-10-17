#!/usr/bin/env python3
"""Conan recipe — memcacheq 0.2.1 (simple queue service over memcache).

HarmonyOS PC (arm64, OS=OHOS) adaptation of Steve Chu's MemcacheQ, the
persistent memcache-protocol message queue built on libevent + BerkeleyDB.

Upstream facts that shape this recipe:

1. Autotools, single ``memcacheq`` executable, no tests.  configure locates
   libevent via ``--with-libevent=PATH`` and BerkeleyDB via ``--with-bdb=PATH``
   (its own AC_CACHE_CHECK/AC_SEARCH_LIBS loops, not pkg-config), so both
   dependencies are injected through those flags pointing at the Conan
   package folders (R49: build-folder private prefixes, never /usr/local).
2. The 2008-era configure has no ``AC_CANONICAL_HOST`` and ships no
   config.guess/config.sub, so there is no platform-guessing step to patch;
   but it *does* create its conftest temp dir with ``umask 077 && mktemp -d
   "./confXXXXXX"`` in the source/build directory.  The Conan build folder
   lives on an HMDFS volume where a 077-umask directory owned that way is not
   writable by the build user (E012 setgid quirk, same failure nylon 1.21
   hit).  The recipe therefore builds out of a private working directory and
   redirects the confstat tmpdir to $TMPDIR before invoking configure.
3. memcacheq is a daemon: the packaged executable is signed with the HNP
   ``binary-sign-tool -selfSign 1`` when present (seq-gen precedent) so it
   passes the OHOS loader's code-signature gate on the device.
4. Threads are enabled (``--enable-threads``): upstream's single-threaded
   build serialises all connections through one event loop; OHOS/musl
   pthreads work and the queue daemon is expected to use them.
"""

import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class MemcacheqConan(ConanFile):
    name = "memcacheq"
    version = "0.2.1"
    description = (
        "MemcacheQ - simple, fast and reliable queue service over the "
        "memcache protocol, backed by BerkeleyDB (libevent + BDB)"
    )
    license = "BSD-3-Clause"
    homepage = "https://memcacheq.googlecode.com/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos.git"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def validate(self):
        # R32: OHOS must be accepted alongside Linux, never "== Linux".
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"memcacheq supports Linux and OHOS only, got {self.settings.os}"
            )

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libevent/2.1.12", transitive_headers=True, transitive_libs=True)
        self.requires("db/6.2.32")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True, verify=True)

    def _shell(self):
        # A real bash: the 2008-era configure uses $((...)), `local`, and
        # arrays in a few places where toybox /bin/sh is not enough, and the
        # profile's CONFIG_SHELL may point at a bash that only exists on the
        # CI worker (/data/service/hnp/bin/bash).  Validate candidates with
        # os.path.isfile before using them, falling back to /bin/sh.
        for cand in (
            os.environ.get("CONFIG_SHELL"),
            "/storage/Users/currentUser/usr/local/bin/bash",
            "/data/service/hnp/bin/bash",
            "/bin/bash",
        ):
            if cand and os.path.isfile(cand):
                try:
                    probe = subprocess.run(
                        [cand, "-c", "echo ok"], capture_output=True, text=True)
                    if probe.returncode == 0:
                        return cand
                except OSError:
                    continue
        return "/bin/sh"

    def _ohos_tool(self, name, default):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        return compilers.get(name, default)

    def generate(self):
        # Dependency prefixes are consumed in build() through the explicit
        # --with-libevent/--with-bdb configure flags; no generator needed.
        pass

    def build(self):
        apply_conandata_patches(self)

        libevent = self.dependencies["libevent"].package_folder
        db = self.dependencies["db"].package_folder

        # R49: private working prefix inside the build folder.  The HMDFS
        # setgid quirk (E012) breaks configure's `umask 077 && mktemp -d
        # ./confXXXXXX` when run directly inside the source tree: the created
        # confstat dir ends up 0270 root:file_manager and subsequent writes
        # fail with EACCES.  Building from a user-owned copy plus a TMPDIR
        # redirect keeps the conftest files off the affected directory.
        # NOTE: with basic_layout the build folder lives *inside* the source
        # export (b/build-release vs b/), so the copy must skip the build
        # folder itself or copytree recurses into its own output forever.
        build_root = os.path.join(self.build_folder, "work")
        if os.path.exists(build_root):
            shutil.rmtree(build_root)
        skip = os.path.basename(self.build_folder)          # e.g. build-release
        shutil.copytree(
            self.source_folder, build_root, symlinks=True,
            ignore=shutil.ignore_patterns(skip, "conan"),
        )

        configure = os.path.join(build_root, "configure")
        with open(configure, "r", encoding="utf-8") as fh:
            content = fh.read()
        # E012 (HMDFS setgid quirk): `umask 077 && mktemp -d` creates the
        # conftest dir as drwx--S--- with group file_manager; on HMDFS the
        # resulting dir is not writable even by its owner, so configure and
        # config.status die with "Permission denied" on every write.  Two
        # changes, following the nylon 1.21 precedent:
        #   * umask 077 -> 022 so the dir comes out group/other readable
        #     and, crucially, owner-writable on this filesystem;
        #   * mktemp/confstat paths redirected into the private work root
        #     under the build folder instead of ./ or $TMPDIR.
        work_tmp = os.path.join(build_root, "confstat")
        os.makedirs(work_tmp, exist_ok=True)
        content = content.replace(
            'tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null` &&',
            'tmp=`(umask 022 && mktemp -d "%s/XXXXXX") 2>/dev/null` &&'
            % work_tmp,
        )
        content = content.replace(
            "  tmp=./conf$$-$RANDOM",
            '  tmp="%s/conf$$-$RANDOM"' % work_tmp,
        )
        # config.status re-runs the same mktemp pattern through $tmp at the
        # top of its file; configure regenerates it, so patch it right after
        # configure finishes (below) rather than here.
        with open(configure, "w", encoding="utf-8") as fh:
            fh.write(content)
        os.chmod(configure, 0o755)

        pkg = self.package_folder
        cfg = [
            "--prefix=%s" % pkg,
            "--bindir=%s/bin" % pkg,
            "--with-libevent=%s" % libevent,
            "--with-bdb=%s" % db,
            # R26: this is an application, build the binary (no lib
            # installed anyway); keep static so the executable does not
            # depend on a libmemcacheq.so that does not exist.
            "--enable-static",
            "--disable-shared",
            "--enable-threads",
        ]

        tmpdir = os.environ.get("TMPDIR") or "/tmp"
        env = os.environ.copy()
        env["TMPDIR"] = tmpdir
        env["TMP"] = tmpdir
        # R33: the compiler must come from the Conan configuration, never
        # from a bare shell env var.  configure's AC_PROG_CC honours CC, so
        # export the conf-provided executable here explicitly.
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        if compilers.get("c"):
            env["CC"] = compilers["c"]
        # hashtable.h declares its iterator helpers as `extern inline` with
        # an out-of-line definition in hashtable.c: that is GNU89 inline
        # semantics, illegal to redefine under C99+ (clang error:
        # "redefinition of a 'extern inline' function is not supported in
        # C99 mode").  The profile's cppstd (gnu20) would otherwise select
        # the C99 semantics, so force the historical mode back on.
        cflags = "-fgnu89-inline"
        env["CFLAGS"] = (env.get("CFLAGS") or "") + " " + cflags

        build_sh = os.path.join(self.generators_folder, "conanbuild.sh")
        # conanbuildenv-*.sh hardcodes SHELL/CONFIG_SHELL to
        # /data/service/hnp/bin/bash (a CI-worker path that does not exist
        # on a dev box): configure honours $CONFIG_SHELL and would generate
        # a config.status with a dead interpreter.  Re-point both at the
        # bash this recipe actually runs the build with.
        shell = self._shell()

        def run_in_build(script):
            cmd = (
                "set -e\n"
                ". '%s'\n"
                "export SHELL='%s'\n"
                "export CONFIG_SHELL='%s'\n"
                "cd '%s'\n"
                "%s\n"
            ) % (build_sh, shell, shell, build_root, script)
            result = subprocess.run(
                [shell, "-c", cmd],
                cwd=build_root,
                env=env,
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                self.output.error("BUILD FAILED (rc=%d) on: %s"
                                  % (result.returncode, script.splitlines()[0]))
                self.output.error("STDOUT tail:\n%s" % result.stdout[-3000:])
                self.output.error("STDERR tail:\n%s" % result.stderr[-3000:])
                raise RuntimeError(
                    "memcacheq build failed (rc=%d)" % result.returncode)
            return result.stdout

        run_in_build("./configure %s" % " ".join(cfg))

        # Patch the freshly generated config.status: it embeds the same
        # `umask 077 && mktemp -d ./confXXXXXX` tmp-dir bootstrap (line 1
        # interpreter aside, $tmp is used for all its .sed/out writes) and
        # `make` re-runs config.status whenever configure/Makefile.in are
        # newer.  Same E012 fix as above.
        status = os.path.join(build_root, "config.status")
        if os.path.isfile(status):
            with open(status, "r", encoding="utf-8") as fh:
                sc = fh.read()
            sc = sc.replace(
                'tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null` &&',
                'tmp=`(umask 022 && mktemp -d "%s/XXXXXX") 2>/dev/null` &&'
                % work_tmp,
            )
            sc = sc.replace(
                "  tmp=./conf$$-$RANDOM",
                '  tmp="%s/conf$$-$RANDOM"' % work_tmp,
            )
            # config.status line 1 is `#! $SHELL` resolved to the env bash;
            # make it a plain /bin/sh-safe exec of the validated bash.
            sc = sc.replace(
                "#! /data/service/hnp/bin/bash",
                "#! %s" % shell,
                1,
            )
            with open(status, "w", encoding="utf-8") as fh:
                fh.write(sc)

        run_in_build("make -j1")
        run_in_build("make install")

    def package(self):
        binary = os.path.join(self.package_folder, "bin", "memcacheq")
        if not os.path.isfile(binary):
            raise ConanInvalidConfiguration(
                f"memcacheq executable was not produced by the build: {binary}"
            )

        # The HNP signing tools only exist on the HarmonyOS worker; a freshly
        # linked binary has no .codesign section, so on a host without them
        # this block is a no-op instead of a hard "command not found" error
        # (seq-gen precedent).
        if str(self.settings.os) == "OHOS":
            sign_tool = self._ohos_tool(
                "sign_tool", "/data/service/hnp/bin/binary-sign-tool"
            )
            objcopy = self._ohos_tool(
                "objcopy", "/data/service/hnp/bin/llvm-objcopy"
            )
            if objcopy and os.path.isfile(objcopy):
                self.run(
                    f'"{objcopy}" --remove-section .codesign "{binary}" '
                    "2>/dev/null || true",
                    cwd=self.package_folder,
                )
            if sign_tool and os.path.isfile(sign_tool):
                signed = binary + ".signed"
                self.run(
                    f'"{sign_tool}" sign -inFile "{binary}" '
                    f'-outFile "{signed}" -selfSign 1',
                    cwd=self.package_folder,
                    quiet=True,
                )
                os.replace(signed, binary)
        os.chmod(binary, 0o755)

    def package_info(self):
        # memcacheq is a daemon/application: no libraries, only bin/.
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        # The executable links libevent-2.1.so.7 / libdb-6.2.so from the
        # dependency packages, which the OHOS musl loader never finds on its
        # own (no default search entry for package folders).  Export their
        # lib dirs through runenv_info so any consumer's VirtualRunEnv (the
        # test_package in particular) gets a working LD_LIBRARY_PATH for
        # free.  This is the conan-native way to ship an application that
        # dlopens/links run-scope shared dependencies.
        try:
            deps = self.dependencies.host.topological_order
        except Exception:
            deps = []
        for _ref, dep in deps:
            if not dep.package_folder:
                continue
            try:
                libdirs = list(dep.cpp_info.aggregated_components().libdirs)
            except Exception:
                libdirs = []
            for ld in libdirs:
                if not ld:
                    continue
                if not os.path.isabs(ld):
                    ld = os.path.join(dep.package_folder, ld)
                if os.path.isdir(ld):
                    self.cpp_info.runenv_info.append("LD_LIBRARY_PATH", ld)
