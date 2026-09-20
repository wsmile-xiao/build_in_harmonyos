#!/usr/bin/env python3
"""Conan recipe for tevent 0.17.1 on HarmonyOS.

tevent is the Samba event-loop library.  Its standalone tarball ships its own
waf build system, an in-tree copy of lib/replace and lib/talloc, and the
third_party/cmocka sources used by the two upstream unit tests.  Rather than
port the waf machinery (whose configure probes assume /tmp is writable and a
fully populated lib/replace build), this recipe drives the compiler directly
and links against the already-published talloc/2.4.4 package.
"""

import glob
import json
import os
import shlex
import sys

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout

# Upstream wscript `build()` SRC list.  tevent_epoll.c is appended there when
# HAVE_EPOLL is set; OHOS exposes sys/epoll.h so the backend must be built or
# the loop falls back to the poll() backend.
TEVENT_SOURCES = [
    "tevent.c",
    "tevent_debug.c",
    "tevent_fd.c",
    "tevent_immediate.c",
    "tevent_queue.c",
    "tevent_req.c",
    "tevent_wrapper.c",
    "tevent_poll.c",
    "tevent_threads.c",
    "tevent_signal.c",
    "tevent_standard.c",
    "tevent_timed.c",
    "tevent_util.c",
    "tevent_wakeup.c",
    "tevent_epoll.c",
]

# tevent's in-tree lib/replace normally supplies rep_memset_s(), reachable from
# tevent_signal.o / tevent_epoll.o through the ZERO_STRUCT / BURN_DATA macros in
# replace.h.  replace.c itself cannot be compiled standalone because it expects
# waf's full autoconf feature matrix, so files/tevent_ohos_compat.c provides
# that one symbol with the same semantics.
COMMON_DEFINES = (
    "-D_GNU_SOURCE -DNO_CONFIG_H -D__STDC_WANT_LIB_EXT1__=1 "
    "-include sys/types.h -include limits.h "
    "-DHAVE_STDINT_H -DHAVE_INTTYPES_H -DHAVE_UNISTD_H -DHAVE_STRING_H "
    "-DHAVE_STRINGS_H -DHAVE_VA_COPY -DHAVE_MEMMOVE -DHAVE_STRNLEN "
    "-DHAVE_VSNPRINTF -DHAVE_C99_VSNPRINTF "
    "-DHAVE_STDBOOL_H -DHAVE_BOOL -DHAVE_INTPTR_T -DHAVE_UINTPTR_T "
    "-DHAVE_PTRDIFF_T -DHAVE_SIZE_T "
    "-DHAVE_USLEEP -DHAVE_COPY_FILE_RANGE -DHAVE_POLL "
    "-DHAVE_CONSTRUCTOR_ATTRIBUTE "
    "-DHAVE_EPOLL -DHAVE_SYS_EPOLL_H -DHAVE_EVENTFD -DHAVE_SYS_EVENTFD_H "
    "-DHAVE_SYS_SELECT_H -DHAVE_SYS_TIMERFD_H "
    "-DHAVE_PTHREAD -DHAVE_PTHREAD_H -DHAVE___THREAD -DHAVE___SYNC_FETCH_AND_ADD "
    "-DHAVE_STRUCT_TIMESPEC -DHAVE_SYS_TIME_H -DHAVE_SIGNAL_H "
    "-DHAVE_DLFCN_H -DHAVE_STRERROR -DHAVE_ERRNO_DECL "
    # replace.h remaps strerror_r -> rep_strerror_r unless BOTH HAVE_STRERROR_R
    # and STRERROR_R_XSI_NOT_GNU are set; declaring the shim without defining it
    # would leave an unresolved symbol for any future caller.
    "-DHAVE_STRERROR_R -DSTRERROR_R_XSI_NOT_GNU "
    "-DHAVE_SNPRINTF -DHAVE_STRDUP -DHAVE_SETLINEBUF "
    "-DHAVE_ATFORK -DHAVE_GETEUID -D_UINTPTR_T "
    # waf computes TEVENT_NUM_SIGNALS as max(64, NSIG, _NSIG, SIGRTMAX,
    # SIGRTMIN * 2).  On OHOS _NSIG is 65 and SIGRTMIN/SIGRTMAX are runtime
    # functions (__libc_current_sigrtmin/max), which CHECK_VALUEOF cannot fold
    # into a constant, so waf settles on 65.
    "-DTEVENT_NUM_SIGNALS=65"
)


class TeventConan(ConanFile):
    name = "tevent"
    version = "0.17.1"
    description = "Samba's event loop / asynchronous request library"
    license = "LGPL-3.0-or-later"
    homepage = "https://tevent.samba.org"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "static-library"
    exports_sources = "files/*"

    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def requirements(self):
        # tevent.h includes <talloc.h> in its public interface, so the header
        # and the library are both propagated to consumers.
        self.requires("talloc/2.4.4", transitive_headers=True, transitive_libs=True)

    def generate(self):
        VirtualBuildEnv(self).generate()

    def _toolchain(self):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cc = compilers.get("c", "clang")
        ar = compilers.get("ar")
        if not ar:
            compiler_dir = os.path.dirname(cc) if os.path.sep in cc else ""
            candidate = os.path.join(compiler_dir, "llvm-ar") if compiler_dir else ""
            ar = candidate if candidate and os.path.isfile(candidate) else "llvm-ar"
        return cc, ar

    def _optimization_flags(self):
        build_type_flags = {
            "Debug": "-O0 -g",
            "Release": "-O2 -DNDEBUG",
            "RelWithDebInfo": "-O2 -g -DNDEBUG",
            "MinSizeRel": "-Os -DNDEBUG",
        }
        return build_type_flags.get(str(self.settings.build_type), "-O2")

    def _dependency_includes(self):
        """-I flags for the talloc dependency.

        Direct-cc recipes do not get dependency paths injected the way the
        CMake/Meson generators do, so tevent.h's `#include <talloc.h>` has to
        be satisfied by passing talloc's includedirs explicitly.
        """
        talloc = self.dependencies["talloc"]
        return " ".join(
            '-I"{}"'.format(os.path.join(talloc.package_folder, d))
            for d in talloc.cpp_info.includedirs
        )

    def _dependency_libdirs(self):
        talloc = self.dependencies["talloc"]
        return [
            os.path.join(talloc.package_folder, d) for d in talloc.cpp_info.libdirs
        ]

    def build(self):
        cc, ar = self._toolchain()
        optimization_flags = self._optimization_flags()
        flags = f"{optimization_flags} -fPIC -std=gnu11 {COMMON_DEFINES}"
        includes = (
            f'-I"{self.source_folder}" '
            f'-I"{os.path.join(self.source_folder, "lib", "replace")}" '
            f"{self._dependency_includes()}"
        )

        objects = []
        for name in TEVENT_SOURCES:
            obj = os.path.join(self.build_folder, name.replace(".c", ".o"))
            self.run(
                '"{}" {} {} -c "{}" -o "{}"'.format(
                    cc,
                    flags,
                    includes,
                    os.path.join(self.source_folder, name),
                    obj,
                )
            )
            objects.append(obj)

        compat_obj = os.path.join(self.build_folder, "tevent_ohos_compat.o")
        self.run(
            '"{}" {} {} -c "{}" -o "{}"'.format(
                cc,
                flags,
                includes,
                os.path.join(self.source_folder, "files", "tevent_ohos_compat.c"),
                compat_obj,
            )
        )
        objects.append(compat_obj)

        archive = os.path.join(self.build_folder, "libtevent.a")
        self.run(
            '"{}" rcs "{}" {}'.format(
                ar,
                archive,
                " ".join('"{}"'.format(o) for o in objects),
            )
        )

        self._run_upstream_tests(cc, ar, optimization_flags)

    def _run_upstream_tests(self, cc, ar, optimization_flags):
        """Build and run the upstream cmocka unit tests.

        wscript's test() target runs exactly three tests: test_tevent_tag,
        test_tevent_trace and the Python bindings (bindings.py).  The two C
        tests are built here against libtevent.a and the cmocka sources
        vendored in third_party/cmocka.  bindings.py exercises the pytevent
        CPython extension, which this pure-C recipe does not build (no Python
        development headers on the OHOS build worker), so it is declared as an
        excluded upstream test rather than silently dropped.

        Both binaries are handed a stdin that is a genuinely writable, pollable
        fd (the write end of a pipe this recipe opens): the two fd-trace cases
        inside test_tevent_trace hard-code fd 0 as a TEVENT_FD_WRITE event, so
        the handler only runs when fd 0 actually reports EPOLLOUT.  Redirecting
        /dev/null -- read-only or even O_RDWR -- does not provide that on the
        OHOS worker.  See _run_with_writable_stdin() for the full analysis and
        _stdin_probe() for the on-host evidence emitted with the summary below.
        """
        cmocka_inc = os.path.join(self.source_folder, "third_party", "cmocka")
        cmocka_obj = os.path.join(self.build_folder, "cmocka.o")
        cmocka_archive = os.path.join(self.build_folder, "libcmocka.a")
        common = (
            f"{optimization_flags} -fPIC -std=gnu11 {COMMON_DEFINES} "
            f'-I"{self.source_folder}" '
            f'-I"{os.path.join(self.source_folder, "lib", "replace")}" '
            f"{self._dependency_includes()} "
            f'-I"{cmocka_inc}"'
        )

        self.run(
            '"{}" {} -c "{}" -o "{}"'.format(
                cc,
                common,
                os.path.join(cmocka_inc, "cmocka.c"),
                cmocka_obj,
            ),
            env="conanbuild",
        )
        self.run(
            '"{}" rcs "{}" "{}"'.format(ar, cmocka_archive, cmocka_obj),
            env="conanbuild",
        )

        archive = os.path.join(self.build_folder, "libtevent.a")
        talloc_libdirs = " ".join(
            '-L"{}"'.format(d) for d in self._dependency_libdirs()
        )
        results = []
        for test in ("test_tevent_tag", "test_tevent_trace"):
            binary = os.path.join(self.build_folder, test)
            self.run(
                '"{}" {} "{}" "{}" "{}" {} -ltalloc -lpthread -o "{}"'.format(
                    cc,
                    common,
                    os.path.join(self.source_folder, "tests", f"{test}.c"),
                    cmocka_archive,
                    archive,
                    talloc_libdirs,
                    binary,
                ),
                env="conanbuild",
            )
            if can_run(self):
                rc = self._run_with_writable_stdin(binary)
                results.append((test, rc))
                self.output.info(f"upstream {test}: exit {rc}")
            else:
                self.output.info(
                    f"upstream {test} skipped: cannot run target binaries on the "
                    "build host (cross build)"
                )

        self.output.info(
            "upstream bindings.py excluded: pytevent CPython extension is not "
            "built by this pure-C recipe (no Python development headers)"
        )

        # 先把所有用例跑完再一次性汇报、最后才失败：只报第一条失败的写法会让
        # 后面用例的结论被 conan 的报错尾部掩盖（CI 侧只能取到日志末尾 4000 字符）。
        failed = [name for name, rc in results if rc != 0]
        self.output.info(
            "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(
                {"executed": len(results), "failed": len(failed),
                 "failed_tests": failed,
                 "stdin_probe": self._stdin_probe()},
                ensure_ascii=False))
        if failed:
            raise ConanException(
                "upstream tests failed: " + ", ".join(failed))

    def _run_with_writable_stdin(self, binary):
        """Run a test binary with a stdin that really is a writable, pollable fd.

        test_tevent_trace.c 的两处用例（test_trace_event_fd__loop:436 与
        test_trace_event_fd__free_in_handler:529）把 **fd 0 本身** 注册成一个
        TEVENT_FD_WRITE 事件：

            fde = tevent_add_fd(ev, tctx, 0, TEVENT_FD_WRITE, ...);
            TEVENT_FD_WRITEABLE(fde);
            tevent_loop_once(ev);
            assert_true(tctx->before_handler);   /* 必须真的派发过 */

        tevent 的 epoll 后端只有在 fd 0 上报 EPOLLOUT 时才调用 handler；上游
        CI 里 stdin 是控制终端（永远可写），所以上游一直绿。无 tty 的构建
        worker 上 stdin 的可写性完全取决于运行环境：

        * `< /dev/null`（O_RDONLY）：POSIX 规定 POLLOUT 只对"打开时带写权限"
          的 fd 上报，epoll_wait 只带回 EPOLLIN；
        * `0<>/dev/null`（O_RDWR）：fd 0 的 poll 掩码取决于 /dev/null 是不是
          一个真正可 poll 的字符设备 —— 实测 OHOS worker 上仍然不满足，
          epoll_ctl(EPOLL_CTL_ADD, 0, {EPOLLOUT}) 直接 EPERM，而 tevent 0.17.1
          的 epoll 后端对该 errno 没有任何 fallback（tevent_epoll.c 的
          epoll_add_event() 只在成功后打 HAS_EVENT 标记，失败即静默丢弃），
          于是 handler 永不被调用、epoll_wait 一路阻塞到 wait_timeout(30 s)，
          两处 assert_true(before_handler) 失败（cmocka 退出码 2）。

        这里改为由配方自己开一根 pipe，把它的**写端**交给子进程当 fd 0：写端
        永远报 POLLOUT（只要读端还在父进程里开着），与上游的 tty 前置条件等价，
        而且不依赖 /dev 下任何设备节点的类型、也不用假设 shell 支持 `<>`。用例
        仍然是原样编译、原样执行、断言一条不改。
        """
        script = (
            "import os, subprocess, sys;"
            "r, w = os.pipe();"
            "sys.exit(subprocess.run(sys.argv[1:], stdin=w).returncode)"
        )
        return self.run(
            '"{}" -c {} "{}"'.format(sys.executable, shlex.quote(script),
                                     binary),
            env="conanbuild", ignore_errors=True)

    @staticmethod
    def _stdin_probe():
        """Report why an ordinary stdin redirection is not enough on this host.

        Kept in the recipe so the claim above stays checkable from the CI log
        itself: the result is emitted with the final upstream-test summary.
        """
        import stat as stat_mod
        try:
            import select as select_mod
        except ImportError as exc:          # pragma: no cover - non-POSIX host
            return {"error": "import select failed: %s" % exc}
        if not hasattr(select_mod, "poll"):
            return {"error": "select.poll unavailable on this host"}

        probe = {}

        def _pollout(fd):
            poller = select_mod.poll()
            poller.register(fd, select_mod.POLLOUT)
            return bool(poller.poll(0))

        try:
            st = os.stat("/dev/null")
            probe["dev_null_type"] = (
                "chr" if stat_mod.S_ISCHR(st.st_mode) else
                "reg" if stat_mod.S_ISREG(st.st_mode) else "other")
        except OSError as exc:
            probe["dev_null_type"] = "stat failed: %s" % exc

        fd = None
        try:
            fd = os.open("/dev/null", os.O_RDWR)
            probe["dev_null_O_RDWR_pollout"] = _pollout(fd)
        except Exception as exc:
            probe["dev_null_O_RDWR_pollout"] = "failed: %s" % exc
        finally:
            if fd is not None:
                os.close(fd)

        rfd = wfd = None
        try:
            rfd, wfd = os.pipe()
            probe["pipe_write_end_pollout"] = _pollout(wfd)
        except Exception as exc:
            probe["pipe_write_end_pollout"] = "failed: %s" % exc
        finally:
            for fd in (rfd, wfd):
                if fd is not None:
                    os.close(fd)
        return probe

    def package(self):
        copy(
            self,
            "tevent.h",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "include"),
        )
        copy(
            self,
            "libtevent.a",
            src=self.build_folder,
            dst=os.path.join(self.package_folder, "lib"),
        )
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.libs = ["tevent"]
        self.cpp_info.set_property("cmake_file_name", "tevent")
        self.cpp_info.set_property("cmake_target_name", "tevent::tevent")
        self.cpp_info.set_property("pkg_config_name", "tevent")
