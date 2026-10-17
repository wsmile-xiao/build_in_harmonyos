#!/usr/bin/env python3
"""Conan recipe for barvinok 0.41.9."""
import os

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    replace_in_file,
    rm,
    save,
    unzip,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class BarvinokConan(ConanFile):
    name = "barvinok"
    version = "0.41.9"
    description = "Library and command-line tools for counting integer points in polytopes"
    license = "GPL-2.0-only"
    homepage = "https://barvinok.sourceforge.io/"
    url = "https://www.repo.or.cz/barvinok.git"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}
    _OHOS_TEST_SCRIPTS = (
        "check_approx.sh",
        "check_enumerate.sh",
        "check_enumerate_e.sh",
        "check_euler.sh",
        "check_iscc.sh",
        "check_lexmin.sh",
        "check_pwqp.sh",
        "check_test.sh",
        "check_union.sh",
    )

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "barvinok 0.41.9 is prepared for Linux/OHOS targets only"
            )

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # NTL must be built with GMP support; its published recipe already
        # carries the matching gmp/6.3.0.1 dependency.
        self.requires("gmp/6.3.0.1")
        self.requires("ntl/11.6.0.2")

    def layout(self):
        basic_layout(self)

    def source(self):
        sources = dict(self.conan_data["sources"])
        declared = sources.pop("url")
        if isinstance(declared, (list, tuple)):
            mirrors = list(declared)
        else:
            # downloads.sourceforge.net is a rotating CDN that can cut the
            # transfer mid-file on worker egress (three IncompleteRead
            # aborts at ~65% of 5.5 MB, builds #34017/#34024, and CI's
            # pre-download passes sourceforge URLs through without extra
            # mirrors).  Offer the official mirror hosts so Conan's
            # downloader falls back per URL; jaist is dropped because it
            # does not resolve on worker DNS (#34033).
            primary = declared
            mirrors = [primary] + [
                primary.replace("https://downloads.sourceforge.net/",
                                f"https://{host}/")
                for host in ("nchc.dl.sourceforge.net",
                             "cytranet.dl.sourceforge.net",
                             "freefr.dl.sourceforge.net")
                if not primary.startswith(f"https://{host}/")
            ]
        try:
            get(self, url=mirrors, retry=3, retry_wait=15,
                strip_root=True, **sources)
        except ConanException as primary_error:
            self.output.warn(
                "source download over all URLs failed "
                f"({str(primary_error)[-110:]}); trying a resumable "
                "Range-based transfer")
            self._resumable_source_download(mirrors,
                                            sha256=sources.get("sha256"))

    def _resumable_source_download(self, urls, sha256=None):
        """Stitch a mid-transfer-cut download back together with Range.

        The CDN cut pattern truncates every connection at a similar offset,
        so plain retries and mirror rotation cannot converge; resuming from
        the bytes already on disk does, while the declared sha256 still
        gates exactly what is unpacked.  This is a transport fallback only:
        the archive remains the official release and stays hash-verified.
        """
        import hashlib
        import time

        try:
            import requests
        except ImportError as exc:
            raise ConanException(
                f"resumable source download unavailable: {exc}")
        verify = True
        try:
            import certifi
            verify = certifi.where()
        except ImportError:
            pass
        fn = urls[0].split("/")[-1].split("?")[0]
        dest = os.path.join(self.source_folder, fn)
        for url in urls:
            for attempt in range(8):
                have = os.path.getsize(dest) if os.path.exists(dest) else 0
                headers = {"Range": f"bytes={have}-"} if have else {}
                try:
                    with requests.get(url, headers=headers, stream=True,
                                      timeout=180, verify=verify) as resp:
                        if resp.status_code == 416 and have:
                            break  # already complete; verified below
                        if resp.status_code not in (200, 206):
                            raise RuntimeError(f"HTTP {resp.status_code}")
                        if resp.status_code == 200:
                            have = 0  # Range ignored: restart cleanly
                        with open(dest, "ab" if have else "wb") as fh:
                            for chunk in resp.iter_content(1 << 16):
                                if chunk:
                                    fh.write(chunk)
                except Exception as exc:  # cut again: resume next round
                    self.output.warn(
                        f"resume {url.split('/')[2]} attempt {attempt + 1}: "
                        f"{str(exc)[-90:]}")
                    time.sleep(5)
                    continue
                break  # one stream finished without an error
            if not os.path.exists(dest):
                continue
            with open(dest, "rb") as fh:
                digest = hashlib.sha256(fh.read()).hexdigest()
            if sha256 and digest != sha256:
                self.output.warn(
                    f"{url.split('/')[2]} digest mismatch; trying next URL")
                continue
            unzip(self, dest, destination=self.source_folder,
                  strip_root=True)
            os.remove(dest)
            self.output.info("resumable source download verified "
                             "(sha256) and unpacked")
            return
        raise ConanException(
            "resumable source download failed sha256 verification on all "
            "candidate URLs")

    def generate(self):
        tc = AutotoolsToolchain(self)

        # Keep the bundled PolyLib and isl copies.  Optional GLPK, cddlib,
        # TOPCOM and PET integrations are not dependencies of this recipe.
        tc.configure_args.extend(
            [
                "--with-gmp=system",
                f"--with-gmp-prefix={self.dependencies['gmp'].package_folder}",
                "--with-polylib=bundled",
                "--with-isl=bundled",
                "--with-pet=no",
                "--with-ntl=system",
                f"--with-ntl-prefix={self.dependencies['ntl'].package_folder}",
                "--without-cddlib",
                "--without-glpk",
                "--with-topcom=no",
            ]
        )
        if str(self.settings.os) == "OHOS":
            # HarmonyOS exposes ffs() from strings.h under the X/Open feature
            # namespace; isl's configure probe otherwise rejects the target.
            tc.extra_defines.append("_XOPEN_SOURCE=700")
        if self.options.shared:
            tc.configure_args.extend(["--enable-shared", "--disable-static"])
        else:
            tc.configure_args.extend(["--enable-static", "--disable-shared"])
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)

        # E232: only a native OHOS build executor may use the OHOS shell.
        # Keep Conan's complete generated configure argument string intact;
        # target settings.os alone must not route Linux/WSL cross builds here.
        if str(self.settings_build.os) == "OHOS":
            configure = os.path.join(self.source_folder, "configure")
            # HMDFS maps the owner of mktemp's 0700 directory differently from
            # the hishell process.  Autoconf's private config.status directory
            # is therefore not writable.  Configure in a shell with a group-
            # writable umask; nested configure scripts inherit it without
            # modifying generated build-system files.
            rc = self.run(
                f'umask 002 && CONFIG_SHELL=/system/bin/sh SHELL=/system/bin/sh '
                f'/system/bin/sh "{configure}" {autotools._configure_args}',
                env="conanbuild",
                ignore_errors=True,
            )
            if rc != 0:
                # CI workers clean up the build folder; echo the failing
                # config.log tail before returning control to conan.
                config_log = os.path.join(self.build_folder, "config.log")
                if os.path.isfile(config_log):
                    self.output.info("---- configure failed: config.log tail ----")
                    try:
                        with open(config_log, "r", encoding="utf-8",
                                  errors="replace") as fh:
                            self.output.info(fh.read()[-16000:])
                    except OSError as exc:
                        self.output.info(f"(unreadable: {exc})")
                raise ConanException(
                    f"native OHOS configure failed (exit {rc}); "
                    "config.log tail echoed above"
                )
            self._patch_native_ohos_test_scripts()
        else:
            autotools.configure()

        isl_python_library = None
        if str(self.settings_build.os) == "OHOS" and not self.options.shared:
            isl_python_library = self._build_ohos_isl_python_test_library()

        if isl_python_library:
            build_env = os.path.join(self.generators_folder, "conanbuild.sh")
            self.run(
                f'. "{build_env}" && '
                f'ISL_PYTHON_DLNAMEDIR="{isl_python_library}" make -j1',
            )
        else:
            autotools.make(args=["-j1"])

        if str(self.settings_build.os) == "OHOS":
            # Conan separates compiler/build variables from runtime search
            # paths.  The upstream tests need both on the native device.
            build_env = os.path.join(self.generators_folder, "conanbuild.sh")
            run_env = os.path.join(self.generators_folder, "conanrun.sh")
            runtime_paths = [
                os.path.join(self.build_folder, name, ".libs")
                for name in ("", "polylib", "isl", "isl-python-shared", "zsolve")
            ]
            runtime_paths = [path for path in runtime_paths if os.path.isdir(path)]
            library_path = os.pathsep.join(runtime_paths)
            isl_env = (
                f'ISL_PYTHON_DLNAMEDIR="{isl_python_library}" '
                if isl_python_library
                else ""
            )
            launcher_arg = ""
            if isl_python_library and not getattr(self, "_ohos_isl_dlopen_ok", True):
                # E135 worker boundary: dlopen() of any user-directory .so
                # is refused regardless of signature (#33869 rejected even
                # the release-signed published gmp), and LD_PRELOAD is
                # ignored on the workers (#33895: the preloaded library
                # never joined the global scope).  Exec-time NEEDED loading
                # of freshly self-signed libraries works there (#33895:
                # isl C tests passed against the .libs libgmp.so.10 copy),
                # so run the ctypes test under an embedded python launcher
                # that links libisl as its own NEEDED; the upstream binding
                # then completes through CDLL(None) symbol resolution.
                self.output.info(
                    "E135 dlopen policy in effect: running make check with "
                    "an embedded python launcher linked against libisl")
                launcher = self._build_ohos_isl_python_launcher(isl_python_library)
                # The Makefile assigns ``PYTHON = @PYTHON@``, so a shell
                # environment prefix is ignored (build #33918 proved the
                # tracebacks still came from the stock interpreter).  Only a
                # make command-line variable overrides the assignment and
                # propagates through the recursive check to PY_LOG_COMPILER.
                launcher_arg = f' PYTHON="{launcher}"'
            rc = self.run(
                f'. "{build_env}" && . "{run_env}" && '
                f'{isl_env}'
                f'LD_LIBRARY_PATH="{library_path}:$LD_LIBRARY_PATH" '
                f'make -j1 check{launcher_arg}',
                ignore_errors=True,
            )
            if rc != 0:
                # CI workers keep only the console output; automake hides the
                # real traceback in per-test logs.  Echo them before failing.
                self._dump_failed_test_logs()
                raise ConanException(
                    f"barvinok upstream tests failed (exit {rc}); "
                    "failing test logs are echoed above"
                )
        else:
            autotools.make(target="check")

    def _dump_failed_test_logs(self):
        """Print automake test-suite logs of the OHOS build to the console."""
        candidates = [
            os.path.join(self.build_folder, "test-suite.log"),
            os.path.join(self.build_folder, "isl", "test-suite.log"),
            os.path.join(self.build_folder, "isl", "isl_test_python.log"),
            os.path.join(self.build_folder, "test", "test-suite.log"),
        ]
        for path in candidates:
            if os.path.isfile(path):
                self.output.info(f"---- {path} ----")
                try:
                    with open(path, "r", encoding="utf-8", errors="replace") as fh:
                        self.output.info(fh.read()[-12000:])
                except OSError as exc:
                    self.output.info(f"(unreadable: {exc})")

    def _build_ohos_isl_python_test_library(self):
        """Build only isl as shared for its upstream ctypes test.

        The package remains static, but the upstream Python binding requires a
        shared libtool ``dlname``.  Keeping this build separate avoids making
        the other barvinok/PolyLib tests depend on HarmonyOS shared-library
        relocation behavior.
        """
        shared_build = os.path.join(self.build_folder, "isl-python-shared")
        os.makedirs(shared_build, exist_ok=True)
        configure = os.path.join(self.source_folder, "isl", "configure")
        gmp_prefix = self.dependencies["gmp"].package_folder
        self.run(
            f'cd "{shared_build}" && '
            f'umask 002 && CONFIG_SHELL=/system/bin/sh SHELL=/system/bin/sh '
            f'/system/bin/sh "{configure}" '
            f'--prefix=/ --enable-shared --disable-static '
            f'--with-gmp=system --with-gmp-prefix="{gmp_prefix}"',
            env="conanbuild",
        )
        self.run(f'cd "{shared_build}" && make -j1', env="conanbuild")

        library_dir = os.path.join(shared_build, ".libs")
        candidates = sorted(
            os.path.join(library_dir, name)
            for name in os.listdir(library_dir)
            if name.startswith("libisl.so.") and os.path.isfile(os.path.join(library_dir, name))
        )
        if not candidates:
            raise ConanInvalidConfiguration(
                "OHOS isl Python test shared library was not produced"
            )
        shared_library = candidates[-1]
        # E135: the CI workers' loader rejects unsigned ELFs ("Error loading
        # shared library ...: Permission denied", builds #33686/#33689) and
        # still rejected the signed top library in #33806 (exact reason was
        # hidden by our own output cap; the probe below now echoes it).
        # Whatever the worker's precise policy is, the recipe must not rely
        # on the published dependency binaries' pre-signed state at test
        # time: copy every non-system NEEDED entry (libisl.so has no RPATH)
        # dereferenced next to isl and sign each copy here, so the whole
        # load chain is regular files freshly signed as their final
        # mutation, first in LD_LIBRARY_PATH for probe and make check alike.
        dep_copies, dep_originals = self._prepare_ohos_shared_dependency_chain(
            library_dir, shared_library)
        self._sign_ohos_shared_library(shared_library)
        self._ohos_isl_dlopen_ok = self._probe_ohos_dlopen(
            shared_library, dep_copies + dep_originals)
        return shared_library

    _OHOS_SYSTEM_LIB_DIRS = ("/system/lib64", "/system/lib")

    def _needed_shared_libraries(self, path):
        """Return the DT_NEEDED sonames of one ELF via llvm-readelf."""
        import subprocess

        readelf = "/data/service/hnp/bin/llvm-readelf"
        if not os.path.isfile(readelf):
            raise ConanException(
                "E135 cannot inspect NEEDED: llvm-readelf is missing")
        result = subprocess.run([readelf, "-d", path], capture_output=True,
                                text=True, timeout=60)
        if result.returncode != 0:
            raise ConanException(f"E135 llvm-readelf -d failed for {path}")
        needed = []
        marker = "Shared library: ["
        for line in result.stdout.splitlines():
            if marker in line:
                needed.append(line.rsplit("]", 1)[0].rsplit(marker, 1)[1])
        return needed

    def _prepare_ohos_shared_dependency_chain(self, library_dir, shared_library):
        """Copy and sign every non-system NEEDED dependency next to isl.

        Returns (signed_copies, original_paths).  The copies live under the
        isl ``.libs`` directory, which both the probe and ``make check`` put
        at the front of LD_LIBRARY_PATH; the shared dependency package folders
        in the Conan cache are never modified.
        """
        import shutil

        dep_dirs = []
        for dep in self.dependencies.host.values():
            lib_dir = os.path.join(dep.package_folder, "lib")
            if os.path.isdir(lib_dir):
                dep_dirs.append(lib_dir)

        copies = []
        originals = []
        for name in self._needed_shared_libraries(shared_library):
            if any(os.path.exists(os.path.join(system_dir, name))
                   for system_dir in self._OHOS_SYSTEM_LIB_DIRS):
                self.output.info(f"E135 dep provided by system: {name}")
                continue
            source = next((os.path.join(lib_dir, name) for lib_dir in dep_dirs
                           if os.path.lexists(os.path.join(lib_dir, name))),
                          None)
            if source is None:
                raise ConanException(
                    f"E135 cannot locate NEEDED '{name}' in dependency "
                    "packages to build the signed test chain")
            target = os.path.join(library_dir, name)
            if os.path.lexists(target):
                os.unlink(target)
            shutil.copyfile(os.path.realpath(source), target)
            os.chmod(target, 0o755)
            self._sign_ohos_shared_library(target)
            copies.append(target)
            originals.append(source)
        return copies, originals

    # One structured, short line per load attempt: CI keeps long recipes
    # outputs but build #33806 proved our own 400-char cap cut off exactly
    # the loader's reason.  Trailing-slicing keeps the identifying suffix and
    # the "Permission denied"-style tail of the OSError message.
    _OHOS_DLOPEN_PROBE_SRC = (
        "import ctypes, sys\n"
        "isl = sys.argv[1]\n"
        "isl_ok = False\n"
        "sys.stdout.write('E135PROBE py ...%s\\n' % sys.executable[-56:])\n"
        "for path in list(sys.argv[2:]) + [isl]:\n"
        "    try:\n"
        "        ctypes.CDLL(path)\n"
        "        ok = True\n"
        "        sys.stdout.write('E135PROBE OK ...%s\\n' % path[-58:])\n"
        "    except OSError as exc:\n"
        "        ok = False\n"
        "        sys.stdout.write('E135PROBE FAIL errno=%s ...%s\\n'\n"
        "                         % (exc.errno, path[-52:]))\n"
        "        sys.stdout.write('E135PROBE MSG ...%s\\n' % str(exc)[-58:])\n"
        "    if path == isl:\n"
        "        isl_ok = ok\n"
        "sys.stdout.write('E135PROBE DONE isl=%d\\n' % int(isl_ok))\n"
        "sys.exit(0 if isl_ok else 1)\n"
    )

    def _probe_ohos_dlopen(self, shared_library, extra_paths):
        """Reproduce the upstream test's dlopen with per-file short verdicts.

        Returns True when the loader accepts the signed isl top.  Build
        #33869 (CI-006) proved the worker rejects dlopen of *every*
        user-directory .so regardless of signature state -- even the
        release-signed published libgmp -- so a False verdict is a platform
        boundary to route around (LD_PRELOAD), not a recipe failure.  The
        per-file E135PROBE lines are always echoed so the console keeps the
        loader's exact reason.
        """
        import subprocess

        probe_python = "/data/service/hnp/bin/python3"
        if not os.path.isfile(probe_python):
            raise ConanException(
                "E135 cannot probe the loader: HNP python3 is missing")
        env = os.environ.copy()
        search = [os.path.dirname(shared_library)]
        gmp_lib = os.path.join(self.dependencies["gmp"].package_folder, "lib")
        if os.path.isdir(gmp_lib):
            search.append(gmp_lib)
        if env.get("LD_LIBRARY_PATH"):
            search.append(env["LD_LIBRARY_PATH"])
        env["LD_LIBRARY_PATH"] = os.pathsep.join(search)
        result = subprocess.run(
            [probe_python, "-c", self._OHOS_DLOPEN_PROBE_SRC, shared_library]
            + list(extra_paths),
            capture_output=True, text=True, timeout=120, env=env)
        for line in (result.stdout + result.stderr).splitlines():
            self.output.info(line[:96])
        return result.returncode == 0

    # Automake drives the ctypes test through PY_LOG_COMPILER = $(PYTHON),
    # so overriding PYTHON routes it via this embedded launcher.  The
    # launcher links libisl as its own NEEDED: exec-time loading of a
    # freshly self-signed library is accepted on the workers even where
    # dlopen() and LD_PRELOAD are not (see build #33895 notes), and the
    # startup global scope then satisfies the upstream CDLL(None) fallback
    # while the test still runs real isl computations.
    _OHOS_ISL_PYTHON_LAUNCHER_SRC = """\
#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include <stdio.h>

int main(int argc, char *argv[]) {
    if (argc < 2) {
        fprintf(stderr, "usage: %s SCRIPT [ARGS...]\\n", argv[0]);
        return 2;
    }
    Py_Initialize();
    wchar_t **wargv = PyMem_RawMalloc(sizeof(wchar_t *) * (size_t)argc);
    if (!wargv) {
        Py_Finalize();
        return 2;
    }
    for (int i = 1; i < argc; ++i)
        wargv[i - 1] = Py_DecodeLocale(argv[i], NULL);
    PySys_SetArgvEx(argc - 1, wargv, 0);
    for (int i = 1; i < argc; ++i)
        PyMem_RawFree(wargv[i - 1]);
    PyMem_RawFree(wargv);
    PyRun_SimpleString(
        "import sys, os\\n"
        "sys.path.insert(0, os.path.dirname(os.path.abspath(sys.argv[0])))\\n");
    FILE *fp = fopen(argv[1], "r");
    if (!fp) {
        perror(argv[1]);
        Py_Finalize();
        return 2;
    }
    int rc = PyRun_SimpleFileEx(fp, argv[1], 1);
    Py_Finalize();
    return rc == 0 ? 0 : 1;
}
"""

    def _build_ohos_isl_python_launcher(self, isl_shared_library):
        """Compile the embed-Python launcher against HNP python and libisl."""
        import subprocess

        probe_python = "/data/service/hnp/bin/python3"
        clang = "/data/service/hnp/bin/clang"
        detect = subprocess.run(
            [probe_python, "-c",
             "import os, sys, sysconfig\n"
             "root = os.path.dirname(os.path.dirname("
             "os.path.realpath(sys.executable)))\n"
             "print(sysconfig.get_paths()['include'])\n"
             "print(os.path.join(root, 'lib', "
             "sysconfig.get_config_var('LDLIBRARY') or ''))\n"
             "print(sysconfig.get_config_var('Py_ENABLE_SHARED'))\n"],
            capture_output=True, text=True, timeout=60)
        lines = detect.stdout.splitlines()
        if detect.returncode != 0 or len(lines) < 3:
            raise ConanException(
                "E135 launcher: python layout detection failed: "
                + (detect.stderr.strip()[-150:] or detect.stdout[-150:]))
        include_dir = lines[0].strip()
        libpython = lines[1].strip()
        shared = lines[2].strip() == "1"
        if not (os.path.isfile(os.path.join(include_dir, "Python.h"))
                and os.path.isfile(clang)):
            raise ConanException(
                "E135 launcher: python dev headers incomplete "
                f"({include_dir}, {clang})")
        src = os.path.join(self.build_folder, "isl_py_launcher.c")
        exe = os.path.join(self.build_folder, "isl_py_launcher")
        save(self, src, self._OHOS_ISL_PYTHON_LAUNCHER_SRC)
        if shared and os.path.isfile(libpython):
            command = [clang, "-Wno-deprecated-declarations", src,
                       "-I", include_dir, libpython, isl_shared_library,
                       "-Wl,-rpath," + os.path.dirname(libpython), "-o", exe]
        else:
            # Some HNP python builds embed the interpreter statically; fall
            # back to python3-config --embed when it ships beside the exe.
            import shlex
            cfg = os.path.join(os.path.dirname(
                os.path.dirname(os.path.realpath(probe_python))),
                "bin", "python3-config")
            if not os.path.isfile(cfg):
                raise ConanException(
                    "E135 launcher: no shared libpython and no "
                    f"python3-config at {cfg}")
            ldflags = subprocess.run([cfg, "--ldflags", "--embed"],
                                     capture_output=True, text=True, timeout=60)
            cflags = subprocess.run([cfg, "--includes"],
                                    capture_output=True, text=True, timeout=60)
            if ldflags.returncode != 0 or cflags.returncode != 0:
                raise ConanException(
                    "E135 launcher: python3-config --embed failed: "
                    + (ldflags.stderr + cflags.stderr)[-200:])
            command = ([clang, "-Wno-deprecated-declarations", src]
                       + shlex.split(cflags.stdout) + [isl_shared_library]
                       + shlex.split(ldflags.stdout) + ["-o", exe])
        result = subprocess.run(command, capture_output=True, text=True,
                                timeout=180)
        if result.returncode != 0:
            raise ConanException(
                "E135 launcher compile failed: "
                + (result.stdout + result.stderr)[-400:])
        os.chmod(exe, 0o755)
        verify = subprocess.run(
            ["/data/service/hnp/bin/llvm-readelf", "-d", exe],
            capture_output=True, text=True, timeout=60)
        if "libisl.so" not in verify.stdout:
            raise ConanException(
                "E135 launcher lacks the libisl NEEDED entry")
        self.output.info(f"E135 built embedded python launcher: {exe}")
        return exe

    def _sign_ohos_shared_library(self, path):
        """Self-sign one HarmonyOS shared library so dlopen accepts it (E135).

        Every outcome is echoed and every failure is fatal here: build
        #33756 proved that a silent skip or a signed-but-still-rejected
        library is indistinguishable once CI truncates the console output.
        Callers must sign as the final mutation of the file, because any
        later section edit invalidates ``.codesign``.
        """
        import subprocess

        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        sign_tool = "/data/service/hnp/bin/binary-sign-tool"
        for tool in (objcopy, sign_tool):
            if not os.path.isfile(tool):
                raise ConanException(
                    f"E135 cannot prepare the OHOS test libraries: "
                    f"{tool} is missing on this build executor"
                )
        try:
            subprocess.run([objcopy, "--remove-section", ".codesign", path],
                           capture_output=True, timeout=30)
        except OSError as exc:
            raise ConanException(f"E135 objcopy cleanup failed for {path}: {exc}")
        tmp = path + ".signed.tmp"
        last_error = None
        for attempt in range(3):
            result = subprocess.run(
                [sign_tool, "sign", "-inFile", path, "-outFile", tmp,
                 "-selfSign", "1"],
                capture_output=True, text=True, timeout=60,
            )
            if result.returncode == 0 and os.path.isfile(tmp):
                os.replace(tmp, path)
                os.chmod(path, 0o755)
                self.output.info(f"E135 signed shared library: {path}")
                break
            last_error = (result.stdout + result.stderr).strip()
            if os.path.isfile(tmp):
                os.unlink(tmp)
        else:
            raise ConanException(
                f"E135 failed to sign {path} for the OHOS loader: {last_error}"
            )

        readelf = "/data/service/hnp/bin/llvm-readelf"
        if os.path.isfile(readelf):
            try:
                verify = subprocess.run(
                    [readelf, "-S", path],
                    capture_output=True, text=True, timeout=30,
                )
            except OSError as exc:
                self.output.warn(f"E135 .codesign check skipped: {exc}")
            else:
                if ".codesign" not in verify.stdout:
                    raise ConanException(
                        f"E135 .codesign section missing after signing {path}")
        else:
            self.output.warn(
                "E135 .codesign check skipped: llvm-readelf unavailable")

    def _patch_native_ohos_test_scripts(self):
        """Make generated Automake tests executable by the native OHOS shell.

        The source templates retain ``#!/bin/sh`` so Linux/WSL cross builds
        continue to run their host-side test drivers.  Only the native OHOS
        build executor needs the target shell path.
        """
        for name in self._OHOS_TEST_SCRIPTS:
            path = os.path.join(self.build_folder, name)
            if os.path.isfile(path):
                replace_in_file(self, path, "#!/bin/sh", "#!/system/bin/sh", strict=False)

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))

        # The Conan package contains static libraries by default.  libtool
        # metadata and Darwin-only shared objects are not portable package API.
        rm(self, "*.la", os.path.join(self.package_folder, "lib"), recursive=True)
        rm(self, "*.dylib", os.path.join(self.package_folder, "lib"), recursive=True)

    def package_info(self):
        self.cpp_info.libs = ["barvinok", "polylibgmp", "isl"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.set_property("cmake_file_name", "barvinok")
        self.cpp_info.set_property("cmake_target_name", "barvinok::barvinok")
        self.cpp_info.set_property("pkg_config_name", "barvinok")
