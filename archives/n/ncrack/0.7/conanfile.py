#!/usr/bin/env python3
"""Conan recipe for Ncrack 0.7 (Nmap project).

High-speed network authentication cracking tool.  Hand-written autotools
build (configure.ac + a non-automake Makefile.in); the release tarball ships
a pre-generated `configure`, so no autoreconf is needed (the OHOS device has
no automake/libtoolize — probe-verified 2026-09-13).

OHOS machinery (device-verified 2026-09-13):

* **Shell**: autoconf's 2.69 `configure` saves stdin with `exec 7<&0`, which
  the system `/system/bin/sh` (toybox) rejects ("7<&0 : bad file descriptor")
  *and* which needs a valid fd 0.  Fix: run under `/usr/bin/zsh` (system image
  binary, same build batch as /system/bin/sh, zsh 5.9) with `CONFIG_SHELL`
  exported — configure self-re-execs into it (its re-exec block precedes the
  fd-7 line), and sub-directory recursion inherits the same shell.  stdin is
  redirected from /dev/null because the CI/worker job environment has fd 0
  closed ("0: bad file descriptor").  `bash` (PATH, from the hnp toolchain)
  is accepted as a fallback.
* **Triplets**: explicit `--build`/`--host` so config.guess never runs; this
  dist's 2019-vintage config.sub has no `ohos`/`harmonyos` entry, so the pair
  uses two config.sub-clean triplets that still differ (cross mode — the
  codebase branches nowhere on host_os; `NCRACK_PLATFORM` is a display
  string from `@host@`).
* **umask 077 -> 022 in all four configure scripts**: hmdfs mediates access
  through group bits, so the 2700 temp dir that `(umask 077 && mktemp -d)`
  creates (in both configure and the generated config.status, at top level
  and in every recursed sub-directory) is untraversable and aborts with
  "permission denied: ./confXXXXXX/subs1.awk".  See
  `_relax_umask_in_configures` for the full evidence chain.
* **In-tree build**: the hand-written Makefile.in is not VPATH-aware (SRCS
  are bare file names), so the source tree is copied into the build folder
  and configured/built there.

OpenSSL is a *hard* build requirement (not the optional feature the
configure script suggests): `ntlmssp.cc` includes <openssl/hmac.h>,
<openssl/md4.h>, <openssl/md5.h> unconditionally, while only `crypto.cc`
guards its includes with `#if HAVE_OPENSSL` (source-verified).  Without
`--with-openssl` the tree fails to compile, so openssl/1.1.1w is pinned —
era-matched to ncrack 0.7 (2019) and published on ohpcd (verified
2026-09-13).  The NTLM/RDP authentication path therefore stays enabled — no
capability is downgraded by this port.
"""

import os
import re
import shlex
import shutil
import subprocess
from pathlib import Path

# Minimal accept-and-hold peer standing in for ncat in the nsock
# regression suite: listens on the three ports run_tests.sh reads from
# test-common.h (55234/udp, 55235/tcp, 55236/tcp) and keeps every
# accepted connection open, which is all the suite's connect/cancel
# cases require.
_NSOCK_PEER_C = r"""
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <arpa/inet.h>
#include <sys/socket.h>
#include <sys/select.h>
#include <fcntl.h>
int main(void){
    int fds[3]; int cfg[3][2]={{55234,SOCK_DGRAM},{55235,SOCK_STREAM},{55236,SOCK_STREAM}};
    int maxfd=0; fd_set master; FD_ZERO(&master);
    for(int i=0;i<3;i++){
        int s=socket(AF_INET,cfg[i][1],0);
        struct sockaddr_in a; memset(&a,0,sizeof a);
        a.sin_family=AF_INET; a.sin_addr.s_addr=htonl(INADDR_ANY); a.sin_port=htons(cfg[i][0]);
        int one=1; setsockopt(s,SOL_SOCKET,SO_REUSEADDR,&one,sizeof one);
        if(bind(s,(struct sockaddr*)&a,sizeof a)<0){perror("bind");return 1;}
        if(cfg[i][1]==SOCK_STREAM) listen(s,16);
        int fl=fcntl(s,F_GETFL); fcntl(s,F_SETFL,fl|O_NONBLOCK);
        fds[i]=s; if(s>maxfd) maxfd=s; FD_SET(s,&master);
    }
    while(1){
        fd_set r=master; int rc=select(maxfd+1,&r,NULL,NULL,NULL);
        if(rc<=0) continue;
        for(int i=0;i<3;i++) if(FD_ISSET(fds[i],&r)){
            struct sockaddr_in a; socklen_t al=sizeof a;
            int c=accept(fds[i],(struct sockaddr*)&a,&al);
            if(c>=0){int fl=fcntl(c,F_GETFL); fcntl(c,F_SETFL,fl|O_NONBLOCK);
                if(c>maxfd) maxfd=c; FD_SET(c,&master);}
        }
    }
    return 0;
}
"""

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import (apply_conandata_patches, copy, download,
                               export_conandata_patches, unzip)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout

# Shells capable of autoconf 2.69's `exec 7<&0`: the OHOS system zsh first
# (fixed system path), then bash from PATH (hnp toolchain, device-verified
# at /data/service/hnp/bin/bash).
OHOS_SHELL_CANDIDATES = ("/usr/bin/zsh", "/data/service/hnp/bin/bash", "bash")


class NcrackConan(ConanFile):
    name = "ncrack"
    version = "0.7"
    description = "Network authentication cracking tool (Nmap project)"
    license = "NPSL (GPL-2.0 with Nmap exceptions)"
    homepage = "https://github.com/nmap/ncrack"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Hard build requirement: ntlmssp.cc includes openssl headers
        # unconditionally (see module docstring).
        self.requires("openssl/1.1.1w")

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"ncrack supports Linux and OHOS, not {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        """Fetch and unpack upstream, then delete the archive from the tree.

        get() is deliberately NOT used: conan's download() writes to a
        cwd-relative path while unzip() resolves against the source folder,
        and with cached/mirrored URLs the two disagree on this platform —
        device-verified failure with a perfectly standard recipe call:

            Calling source() in .../s
            Sources correctly downloaded from https://ghfast.top/...0.7.tar.gz
            Uncompressing 0.7.tar.gz to .
            FileNotFoundError: [Errno 2] No such file or directory: '0.7.tar.gz'

        (the mirror ghfast.top is injected by CI/conan-verify, so this is the
        exact path CI takes).  Downloading to an explicit absolute path and
        unpacking that same path removes the ambiguity entirely.
        """
        source = dict(self.conan_data["sources"])
        local_archive = os.getenv("NCRACK_SOURCE_ARCHIVE")
        if local_archive:
            provided = Path(local_archive).resolve()
            if not provided.is_file():
                raise ConanException(
                    f"NCRACK_SOURCE_ARCHIVE is not a regular file: {provided}"
                )
            archive = Path(self.source_folder, provided.name)
            copy(self, provided.name, src=str(provided.parent),
                 dst=self.source_folder, keep_path=False)
        else:
            archive = Path(self.source_folder, "ncrack-source.tar.gz")
            download(self, url=source["url"], filename=str(archive),
                     sha256=source["sha256"], retry=3, retry_wait=5)
        unzip(self, str(archive), destination=self.source_folder, strip_root=True)
        os.remove(str(archive))

    def generate(self):
        toolchain = AutotoolsToolchain(self)
        # ncrack 0.7 (2019) predates C++17's removal of the `register`
        # storage-class specifier: crypto.cc uses it 23 times, and the
        # ohos-aarch64 profile declares cppstd=17, so the build must pin the
        # era-appropriate standard.  ncrack is an application (nothing
        # consumes its C++ ABI), so this stays an internal build detail and
        # upstream sources are left untouched.  Appended after the
        # toolchain's own -std flag, which is what wins in the final
        # CXXFLAGS.
        toolchain.extra_cxxflags.append("-std=gnu++14")
        # The vendored opensshlib compiles umac128.o from umac.c itself (extra
        # -DUMAC_128), so both TUs define the global `umac_ctx`.  That is the
        # classic tentative-definition pattern: -fcommon merges them (GCC<=9
        # default), while clang 15's -fno-common default plus ld.lld makes it a
        # hard "duplicate symbol" error.  Restoring the era-appropriate
        # behaviour keeps upstream sources untouched.
        toolchain.extra_cflags.append("-fcommon")
        toolchain.generate()
        # R33: toolchain-provided env only — no bare shell CFLAGS anywhere.

    def build(self):
        apply_conandata_patches(self)
        if str(self.settings.os) == "OHOS":
            self._build_ohos()
        else:
            autotools = Autotools(self)
            autotools.configure()
            autotools.make()

    def package(self):
        if str(self.settings.os) == "OHOS":
            self._package_ohos()
            # E549: OHOS refuses to exec an unsigned ELF ("Operation not
            # permitted", exit 126), so the installed binary is self-signed
            # (cc-connect / clipnotify precedent).  Signing happens after
            # install, i.e. on the artifact that ships in the package.
            self._sign_elf(os.path.join(self.package_folder, "bin", "ncrack"))
        else:
            autotools = Autotools(self)
            autotools.install()
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        # Tool package (R38): commands.json at software level declares the
        # ncrack command; no libraries, no consumer linkage.
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []

    # ── OHOS build machinery ────────────────────────────────────────────

    def _build_ohos(self):
        shell = self._resolve_shell()
        # The hand-written Makefile.in is not VPATH-aware: build in a copy.
        copy(self, "*", src=self.source_folder, dst=self.build_folder)
        self._relax_umask_in_configures()
        with self._build_environment().vars(self).apply():
            self._run_ohos(f"{shlex.quote(shell)} ./configure {self._configure_args()}")
            self._run_ohos("make -j1")
            # R51/R34: upstream's regression suite lives in nsock (7 test
            # translation units + run_tests.sh).  Upstream CI only runs
            # ./configure && make, so running `make check` here is stronger
            # than upstream's own gate; a failure fails the build.
            self._run_ohos("make -j1 check",
                           cwd=os.path.join(self.build_folder, "nsock", "src"))
            # `make check` alone silently skips the suite: run_tests.sh
            # refuses to run without ncat ("You haven't built Ncat"),
            # which this tree does not ship — the suite then reports 0/7
            # executed.  A minimal accept-and-hold peer on the three
            # ports run_tests.sh reads from test-common.h (55234/udp,
            # 55235/tcp, 55236/tcp) stands in for ncat, and tests_main
            # runs for real.
            self._run_nsock_regression_suite()

    def _run_nsock_regression_suite(self):
        build = self.build_folder
        peer_c = os.path.join(build, "nsock_peer.c")
        with open(peer_c, "w", encoding="utf-8") as handle:
            handle.write(_NSOCK_PEER_C)
        self._run_ohos(f"$CC {shlex.quote(peer_c)} -o {shlex.quote(os.path.join(build, 'nsock_peer'))}")
        # One shell owns the peer's lifecycle: background it, run the
        # suite, then tear it down regardless of the test outcome.
        script = (
            f"./nsock_peer & peer=$!; sleep 1; "
            "cd nsock/tests && timeout 150 ./tests_main > tests_main.out 2>&1; "
            "rc=$?; kill $peer 2>/dev/null; cat tests_main.out; exit $rc"
        )
        self._run_ohos(script)
        out_path = os.path.join(build, "nsock", "tests", "tests_main.out")
        with open(out_path, encoding="utf-8", errors="replace") as handle:
            output = handle.read()
        passed = len(re.findall(r"OK\x1b\[0m", output))
        failed = output.count("FAILED")
        self.output.info(
            f"[nsock-suite] {passed} checks OK, {failed} FAILED "
            "(7 test translation units; SSL variants compiled out — "
            "--without-openssl)")
        if failed or passed < 10:
            raise ConanException(
                f"nsock regression suite failed: {passed} OK / {failed} FAILED "
                "(expected every check OK)")

    def _relax_umask_in_configures(self):
        """Rewrite `umask 077` -> `umask 022` in every generated configure.

        Device-verified root cause (2026-09-13): configure/config.status create
        their temp dir with `(umask 077 && mktemp -d "./confXXXXXX")`, which
        yields mode 2700 (`drwx--S---`).  hmdfs (the OHOS home filesystem)
        mediates access through the **group** bits — every hmdfs directory is
        `drwxrws--x` — so a group-untraversable 2700 dir makes every later
        read/write inside it fail with EACCES ("permission denied:
        ./confXXXXXX/subs1.awk", "could not setup config files machinery").
        chmod is a no-op on hmdfs (probe-verified), so the only lever is the
        umask used when the directory is created: 022 gives `drwxr-s--x`,
        which is group-traversable and works.

        All four configure scripts matter: the top level plus the nbase /
        nsock/src / opensshlib recursion — a sub-directory left at 077 fails
        with "configure: error: ./configure failed for nbase".
        """
        configures = [
            "configure",
            os.path.join("nbase", "configure"),
            os.path.join("nsock", "src", "configure"),
            os.path.join("opensshlib", "configure"),
        ]
        needle = "umask 077"
        for relative in configures:
            path = Path(self.build_folder, relative)
            if not path.is_file():
                raise ConanException(f"configure script is missing: {path}")
            content = path.read_text(encoding="utf-8")
            if content.count(needle) != 2:
                raise ConanException(
                    f"umask contract changed in {relative}: expected 2 "
                    f"occurrences of {needle!r}, found {content.count(needle)}"
                )
            path.write_text(content.replace(needle, "umask 022"),
                            encoding="utf-8", newline="\n")

    def _package_ohos(self):
        shell = self._resolve_shell()
        with self._build_environment().vars(self).apply():
            destination = shlex.quote(self.package_folder)
            self._run_ohos(f"make -j1 install DESTDIR={destination}")

    def _configure_args(self):
        openssl_folder = str(self.dependencies["openssl"].package_folder)
        arguments = [
            # build != host -> cross-compile mode: configure never EXECUTES
            # conftest binaries; both triplets explicit so config.guess never
            # runs.  This dist's 2019 config.sub knows neither `ohos` nor
            # `harmonyos`, hence two triplets it does know.
            "--build=aarch64-unknown-linux-musl",
            "--host=aarch64-unknown-linux-gnu",
            # prefix=/ + DESTDIR=<package_folder> lands bin/ and share/
            # directly in the package root (the autotools default
            # /usr/local would nest them under usr/local/).
            "--prefix=/",
            # ncrack's own --with-libpcap=no default is injected by
            # configure.ac; restated here so the intent is visible.
            "--with-libpcap=no",
            # Top level: ncrack's own option — sets its internal CPPFLAGS/
            # LDFLAGS and OPENSSL_LIBS=-lssl -lcrypto.
            f"--with-openssl={openssl_folder}",
            # Recursed sub-directories (opensshlib) run their own autoconf
            # with their own OpenSSL check, which the top-level option cannot
            # reach: the toolchain env carries no CPPFLAGS/LDFLAGS
            # (device-verified — conanautotoolstoolchain.sh/conanbuild.sh are
            # empty of them), and opensshlib ERRORS OUT hard on a missing
            # openssl/opensslv.h.  opensshlib declares `--with-ssl-dir=DIR`
            # (its help text misleadingly says --with-openssl=PATH), which
            # adds -I<dir>/include and -L<dir>/lib and lets its
            # `LIBS=-lcrypto` link probe succeed.  The top level only warns
            # about the unrecognized option and forwards it verbatim.
            f"--with-ssl-dir={openssl_folder}",
        ]
        return " ".join(shlex.quote(argument) for argument in arguments)

    def _build_environment(self):
        temporary = Path(self.build_folder, ".tmp")
        temporary.mkdir(parents=True, exist_ok=True)
        environment = Environment()
        environment.define_path("TMPDIR", str(temporary))
        return environment

    def _resolve_shell(self):
        for candidate in OHOS_SHELL_CANDIDATES:
            if os.path.sep in candidate:
                if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
                    return candidate
                continue
            for directory in os.environ.get("PATH", "").split(os.pathsep):
                path = os.path.join(directory, candidate)
                if os.path.isfile(path) and os.access(path, os.X_OK):
                    return path
        raise ConanInvalidConfiguration(
            "no autoconf-capable shell found on OHOS (need /usr/bin/zsh or bash; "
            "/system/bin/sh cannot run autoconf 2.69's `exec 7<&0`)"
        )

    def _find_tool(self, name):
        import glob as g
        candidates = [os.path.join(os.path.expanduser("~"), ".harmonybrew", "bin")]
        candidates += sorted(g.glob("/data/service/hnp/ohos-sdk.org/*/ohos/native/llvm/bin"))
        candidates.append("/data/service/hnp/bin")
        for directory in candidates:
            path = os.path.join(directory, name)
            if os.path.isfile(path):
                return path
        return shutil.which(name)

    def _sign_elf(self, binary_path):
        if not os.path.isfile(binary_path):
            raise ConanException(f"binary missing for signing: {binary_path}")
        objcopy = self._find_tool("llvm-objcopy")
        sign_tool = self._find_tool("binary-sign-tool")
        if not sign_tool or not objcopy:
            raise ConanException(
                "binary-sign-tool/llvm-objcopy not found on OHOS (E549: "
                "unsigned ELFs cannot be executed)"
            )
        subprocess.run([objcopy, "--remove-section", ".codesign", binary_path],
                       capture_output=True, timeout=60)
        temporary = binary_path + ".signed.tmp"
        for _ in range(3):
            result = subprocess.run(
                [sign_tool, "sign", "-inFile", binary_path, "-outFile", temporary,
                 "-selfSign", "1"],
                capture_output=True, text=True, timeout=120,
            )
            if result.returncode == 0 and os.path.isfile(temporary):
                shutil.move(temporary, binary_path)
                os.chmod(binary_path, 0o775)
                return
        if os.path.exists(temporary):
            os.remove(temporary)
        raise ConanException(f"ELF self-signing failed for {binary_path}")

    def _run_ohos(self, command, cwd=None):
        shell = self._resolve_shell()
        # SHELL/CONFIG_SHELL carry the shell into configure's own re-exec and
        # into the nbase/nsock/opensshlib recursion; `< /dev/null` supplies
        # the fd 0 that `exec 7<&0` saves (worker/CI jobs run with fd 0
        # closed — device-verified "0: bad file descriptor").
        prefix = (
            f"export SHELL={shlex.quote(shell)} CONFIG_SHELL={shlex.quote(shell)}; "
        )
        self.run(prefix + command + " < /dev/null", cwd=cwd or self.build_folder,
                 env="conanbuild")
