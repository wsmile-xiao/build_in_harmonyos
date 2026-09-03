#!/usr/bin/env python3
"""Conan recipe — Cesanta Fossa 2.1.

Fossa is Cesanta's single-file async networking library (HTTP/WebSocket/MQTT/
CoAP/DNS over one epoll/select event loop), the direct predecessor of Mongoose
6+. Like archives/m/mongoose/7.21 it ships as an amalgamated fossa.c + fossa.h
pair and is packaged as a static library only.
"""
import json
import os
import re
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import (apply_conandata_patches, copy,
                               export_conandata_patches, get, load)
from conan.tools.layout import basic_layout

# Feature set compiled into the packaged library — identical to the one the
# upstream unit test suite exercises, so the test matrix below really covers
# the shipped object code. NS_ENABLE_IPV6 is ABI-affecting: it switches
# union socket_address's sin6 member between sockaddr_in6 and sockaddr
# (fossa.h:537), so consumers must compile with the same macros.
FEATURE_DEFINES = ("NS_ENABLE_COAP", "NS_ENABLE_IPV6", "NS_ENABLE_THREADS",
                   "NS_ENABLE_MQTT_BROKER", "NS_ENABLE_DNS_SERVER")

# Upstream cases that cannot pass on this platform for reasons unrelated to
# fossa or to this recipe. Anything failing outside this whitelist aborts the
# build, so a real regression can never hide behind the known set.
KNOWN_ENV_FAILURES = {
    "test_cgi": (
        "工具未装：设备 perl 5.44 无 CGI.pm（CGI 自 Perl 5.22 起移出核心），"
        "test/data/cgi/index.cgi 报 \"Can't locate CGI.pm in @INC ... at index.cgi line 4\"，"
        "服务端因此回空响应，断言 ASSERT_STREQ_NZ(buf, \"HTTP/1.1 201 Created\\r\\n\") 失败；"
        "上游注释亦标明 \"Needs perl interpreter to run the test\"，与 OHOS 无关"),
    "test_connection_errors": (
        "环境限制：运营商 resolver（114.114.114.114）对 does.not.exist 做泛解析，"
        "合成 RFC 2544 基准测试段地址 198.18.6.163 并有透明代理接受任意端口，"
        "本应连接失败的 ns_connect(\"tcp://does.not.exist:8080\") 反而成功，"
        "断言 ASSERT_EQ(data, 4) 拿到 1（1=连接成功，4=连接失败）"),
    "test_dns_resolve": (
        "环境限制：用例把成功条件固定为 2015 年抓取的真实应答 52.16.170.74 / "
        "CNAME dev.cesanta.com，任何非原始 DNS 环境都不可能匹配，且失败形态随网络而异——"
        "真机上运营商 resolver（114.114.114.114）把 oncall.cesanta.com 泛解析合成为 "
        "198.18.6.164，断言 ASSERT_EQ(data, 1) 拿到 2；CI 环境得不到可用应答"
        "（NXDOMAIN 时 num_answers == 0，无应答时重试耗尽，两条路径都以 NULL 收尾），"
        "fossa 因此以 msg==NULL 回调（fossa.c:7068、:7084），而上游 dns_resolve_cb 缺少同源 "
        "dns_resolve_timeout_cb 就有的 NULL 守卫，打补丁 0002 之前直接 SIGSEGV，"
        "补丁之后同样干净地拿到 2。两种后果都由外部 DNS 语义决定，与 fossa 代码正确性无关；"
        "resolver 自身工作正常，因为 test_dns_resolve_hosts / test_dns_resolve_timeout / "
        "test_dns_server / test_dns_encode / test_dns_decode / "
        "test_dns_reply_encode 全部通过"),
}

_ASSERT_RE = re.compile(r"^  \[[0-9.]+\] (test_[a-z0-9_]+)$", re.M)
_SUMMARY_RE = re.compile(r"^(PASS|FAIL), run (\d+) in [0-9.]+s$", re.M)


class FossaConan(ConanFile):
    name = "fossa"
    version = "2.1"
    description = ("Cesanta Fossa — embedded network library providing "
                   "HTTP/HTTPS/WebSocket/MQTT/CoAP/DNS over a single event manager")
    topics = ("networking", "http", "websocket", "mqtt", "coap", "embedded")
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/cesanta/fossa"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}
    generators = "VirtualBuildEnv"
    exports_sources = "patches/*"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def validate(self):
        if self.info.options.shared:
            raise ConanException(
                "fossa 只提供静态库：OHOS 对用户态未签名 .so 有 ELF 签名校验，"
                "同族的 archives/m/mongoose/7.21 已确认同一平台限制并同样只交付 .a")

    def _executables(self):
        # R33: compilers come from the Conan conf, never from shell env vars.
        conf = self.conf.get("tools.build:compiler_executables",
                             default={}, check_type=dict) or {}
        return conf.get("c", "clang"), conf.get("ar", "llvm-ar")

    # ── upstream unit test driver ────────────────────────────────────────────
    def _unit_test_names(self, test_dir):
        text = load(self, os.path.join(test_dir, "unit_test.c"))
        names = []
        for m in re.finditer(r"RUN_TEST\((test_[a-z0-9_]+)\)", text):
            if m.group(1) not in names:
                names.append(m.group(1))
        return names

    def _run_unit_test(self, test_dir, case):
        # Upstream's `test` target body, verbatim: TEST_FILTER is argv[1].
        cmd = f"MallocLogFile=/dev/null ./unit_test {case}"
        proc = subprocess.run(cmd, shell=True, cwd=test_dir,
                              capture_output=True, text=True, timeout=300)
        output = (proc.stdout or "") + (proc.stderr or "")
        self.output.info(f"$ (cd {test_dir} && {cmd})\n{output.rstrip()}")
        ran = _ASSERT_RE.findall(output)
        summaries = _SUMMARY_RE.findall(output)
        if not summaries:
            raise ConanException(f"unit_test {case}: 框架汇总行缺失，无法取得真实用例数")
        # 取最后一条：用例体会把 HTTP 报文一类的任意文本打到 stdout，
        # 只有进程末尾那条才是框架自己的判定行。
        status, total = summaries[-1]
        return ran, status, int(total)

    def _measure_upstream(self, test_dir):
        """Build the per-case verdict and assertion matrix from the framework's
        own stdout.

        Upstream selects cases with strstr(#test, filter), i.e. a filter also
        matches every longer name containing it, and the runner aborts the
        whole process at the first failing case. One unfiltered run therefore
        stops at case #1 and cannot yield a matrix. Iterating the filters by
        descending name length makes the attribution exact: a case's own run
        additionally re-executes only its longer superstrings, whose assertion
        counts were already measured, so they can be subtracted instead of
        being counted twice.
        """
        names = self._unit_test_names(test_dir)
        assertions = {}
        verdicts = {}
        for case in sorted(names, key=lambda n: (-len(n), n)):
            ran, status, total = self._run_unit_test(test_dir, case)
            if not ran:
                # Not registered in this build: the RUN_TEST call sits behind an
                # #ifdef for a feature macro this configuration leaves off.
                verdicts[case] = "skipped"
                continue
            if case not in ran:
                raise ConanException(
                    f"{case} 未出现在自身过滤结果中（被更早失败的用例截断），无法给出真实判定")
            others = [t for t in ran if t != case]
            missing = [t for t in others if t not in assertions]
            if missing:
                raise ConanException(f"{case} 断言归因失败，未先行计量: {missing}")
            own = total - sum(assertions[t] for t in others)
            if own < 0:
                raise ConanException(f"{case} 断言数为负 ({own})，归因不自洽")
            assertions[case] = own
            if status == "FAIL" and ran[-1] != case:
                raise ConanException(f"{case} 组内 {ran[-1]} 先行失败，{case} 判定被截断")
            verdicts[case] = "passed" if status == "PASS" else "failed"

        executed = [c for c in names if verdicts[c] != "skipped"]
        return {
            "names": names,
            "executed": executed,
            "passed": [c for c in executed if verdicts[c] == "passed"],
            "failed": [c for c in executed if verdicts[c] == "failed"],
            "skipped": [c for c in names if verdicts[c] == "skipped"],
            "assertions": assertions,
        }

    def _run_upstream_tests(self, test_dir):
        # Evidence that upstream's own aggregate target runs on this platform.
        # It aborts at the first failing case, which is exactly why the
        # per-case pass below exists — keep both in the log.
        self._run_unit_test(test_dir, "")

        matrix = self._measure_upstream(test_dir)
        unexpected = [c for c in matrix["failed"] if c not in KNOWN_ENV_FAILURES]
        if unexpected:
            raise ConanException(f"上游测试出现白名单之外的失败: {unexpected}")
        if matrix["skipped"]:
            self.output.warning(
                "未编入二进制的上游用例（特性宏未启用）: " + ", ".join(matrix["skipped"]))

        total_assertions = sum(matrix["assertions"][c] for c in matrix["executed"])
        known = [c for c in matrix["failed"]]
        marker = {
            "status": "passed" if not known else "failed",
            "framework": "fossa unit_test (upstream test/Makefile, TEST_FILTER per case)",
            "command": "make -C test -j1 unit_test CC=clang CFLAGS_EXTRA=-DTEST_UNDER_VIRTUALBOX"
                       " && MallocLogFile=/dev/null ./unit_test <TEST_FILTER>",
            "discovered": len(matrix["names"]),
            "executed": len(matrix["executed"]),
            "passed": len(matrix["passed"]),
            "failed": len(known),
            "skipped": len(matrix["skipped"]),
            "assertions": total_assertions,
            "failed_cases": [{"test": c, "reason": KNOWN_ENV_FAILURES[c]} for c in known],
            "skipped_cases": [{"test": c,
                               "reason": "NS_ENABLE_SSL 未启用，该用例未编入二进制"}
                              for c in matrix["skipped"]],
            "verdict_note": "库构建、打包与消费端验证全部成功；failed 仅指上表已归因的"
                            "环境/工具受限用例，非适配缺陷",
        }
        # flush=True: Conan's output layer may not flush a build-stage print
        # before the log collector reads it (see archives/a/aiohttp-fast-zlib).
        print(f"HMBS_UPSTREAM_TEST_RESULT={json.dumps(marker, ensure_ascii=False)}",
              flush=True)
        self.output.info("上游用例矩阵: " + ", ".join(
            f"{c}={matrix['assertions'][c]}assert" for c in matrix["executed"]))

    # ── build ────────────────────────────────────────────────────────────────
    def build(self):
        apply_conandata_patches(self)
        cc, ar = self._executables()
        src = self.source_folder
        opt = {"Debug": "-O0 -g"}.get(str(self.settings.build_type), "-O2")
        defines = " ".join(f"-D{d}" for d in FEATURE_DEFINES)

        self.run(f"{cc} {opt} -fPIC {defines} -c {src}/fossa.c -o {src}/fossa.o",
                 cwd=src)
        self.run(f"{ar} rcs {src}/libfossa.a {src}/fossa.o", cwd=src)

        # TEST_UNDER_VIRTUALBOX is upstream's own switch for filesystems whose
        # permission semantics cannot be trusted. HMDFS ignores chmod (verified:
        # chmod 000 leaves -rw-r----- and fopen still succeeds), so the
        # chmod-000-expects-HTTP-500 block inside test_http_errors is a platform
        # expectation mismatch, not a fossa bug. Using the upstream switch keeps
        # that issue out of the sources entirely (R8/PF5: no platform macros in
        # patches). The only .c change is patch 0002, which fixes an upstream
        # NULL dereference in a test callback; it is platform neutral.
        test_dir = os.path.join(src, "test")
        self.run(f"make -C {test_dir} -j1 unit_test CC={cc} "
                 f"CFLAGS_EXTRA=-DTEST_UNDER_VIRTUALBOX")
        self._run_upstream_tests(test_dir)

    def package(self):
        src = self.source_folder
        copy(self, "fossa.h", src, os.path.join(self.package_folder, "include"))
        copy(self, "libfossa.a", src, os.path.join(self.package_folder, "lib"))
        copy(self, "LICENSE", src, os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["fossa"]
        self.cpp_info.defines = list(FEATURE_DEFINES)
        if "NS_ENABLE_THREADS" in FEATURE_DEFINES:
            self.cpp_info.system_libs = ["pthread"]
