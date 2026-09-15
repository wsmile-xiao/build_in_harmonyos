#!/usr/bin/env python3
"""Conan recipe for chinadns 1.3.2 — DNS 分流工具（ChinaDNS-C）.

chinadns 是纯用户态 C 编写的 DNS 分流转发器：根据 chnroute 列表把
国内域名解析交给国内 DNS、其他流量交给可信 DNS，解决 DNS 污染问题。

Upstream: https://github.com/clowwindy/ChinaDNS-C (tag 1.3.2, GPL-3.0).
依赖仅 libc（res_query 在 OHOS musl libc.so 中直接导出，libresolv.a
为空 archive 但 -lresolv 链接成功——configure 探测通过）。

Build system: autotools。上游 master 分支只有 autogen.sh + Makefile.am
（configure.ac），tarball 无预生成 configure；CI 环境无 automake/aclocal，
因此配方携带 generated-build/ 快照（本地 automake 1.16.5 + autoconf
2.72 生成，umask 077→022 修复 HMDFS E129），build() 时复制进源码树
（c-algorithms 1.0.0 同款先例）。

上游测试（tests/ 6 个 dig 集成用例：google.com/facebook.com/twitter.com/
taobao.com/www.facebook.com A 查询 + x_8888 PTR 反查，由 Python 2 test.py
驱动——已移植为 Python 3）在 build() 末尾真实运行：启动编译产物
src/chinadns 转发，再对 127.0.0.1:15353 发 DNS 查询验证应答
（boost1.84-serialization 同款 rc 判过手法）。查询通道双模式：
dig 可用（试运行验证）→ 原样执行上游 dig 命令（rc=0 且含
ANSWER SECTION 判过）；dig 缺失（CI worker 环境）→ Python 原生
DNS 客户端等价查询（标准 DNS 报文，rcode=0 且 ANCOUNT>0 判过）。
公网 DNS 不可达时逐项 SKIPPED（环境限制）并留报告，不阻塞构建。

R17/CI 无 automake: 快照 configure 已含全部生成文件，无需 autoreconf。
R26: Not applicable（无库产物，纯 bin/chinadns 可执行文件）。
R32: settings.os 检查 ("Linux", "OHOS")。
R38: CLI 工具——commands.json 已声明（软件级 archives/c/chinadns/commands.json）。
"""
import os
import shutil
import signal
import subprocess
import time

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class ChinadnsCConan(ConanFile):
    name = "chinadns-c"
    version = "1.3.2"
    description = "DNS 分流工具：chinadns（ChinaDNS-C）根据 chnroute 列表分流国内/可信 DNS 解析"
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/clowwindy/ChinaDNS-C"
    url = "https://github.com/clowwindy/ChinaDNS-C"
    topics = ("dns", "proxy", "network", "dns-split")

    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    # CI 环境可能缺 automake/aclocal；随配方携带生成的 configure 快照
    exports_sources = "generated-build/*", "patches/*"

    def validate(self):
        # R32: 平台检查
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"Unsupported OS: {self.settings.os}")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # config.guess 不识别 HarmonyOS 且上游 configure.ac 无
        # AC_CANONICAL_*（configure 不调用 config.guess）；显式指定
        # build 三元组即可（catdoc 同款）。host 用 OHOS triplet。
        tc.configure_args.append("--build=aarch64-unknown-linux-gnu")
        tc.generate()

    def build(self):
        # 上游 tarball 只有 autogen.sh + Makefile.am + configure.ac，
        # 无预生成 configure；CI 无 automake —— 复制配方自带的
        # generated-build 快照（c-algorithms 1.0.0 同款先例）。
        src = self.source_folder
        snapshot = os.path.join(self.export_sources_folder, "generated-build")
        if not os.path.exists(os.path.join(src, "configure")):
            for item in ("configure", "Makefile.in", "aclocal.m4",
                         "config.h.in"):
                shutil.copy2(os.path.join(snapshot, item),
                             os.path.join(src, item))
            os.makedirs(os.path.join(src, "src"), exist_ok=True)
            shutil.copy2(os.path.join(snapshot, "src", "Makefile.in"),
                         os.path.join(src, "src", "Makefile.in"))
            # aux 脚本（compile/install-sh/missing/depcomp）直接放
            # 源码树根目录——chinadns 的 configure.ac 无
            # AC_CONFIG_AUX_DIR，aux dir 探测只扫 ${srcdir} 本身
            # （ac_aux_files="compile missing install-sh"）。
            for aux in ("compile", "install-sh", "missing", "depcomp"):
                shutil.copy2(os.path.join(snapshot, "autotools", aux),
                             os.path.join(src, aux))
            # touch configure 让它比 configure.ac 新，避免 maintainer
            # 规则触发 autoconf 重生成（CI 无 autoconf）。
            os.utime(os.path.join(src, "configure"), None)

        autotools = Autotools(self)
        autotools.configure()
        # -j1：OHOS 禁 mkfifo jobserver（boa/catdoc 同款）
        autotools.make(args=["-j1"])

        # L1: 上游 6 个 dig 集成测试真实运行（Python 3 移植版 test.py）
        self._run_upstream_tests()

    # 上游 tests/ 下 6 个测试用例（test.py 读取的 dig 命令文件，
    # .jenkins.sh run_test tests/test.py -t tests/<name> 驱动）。
    _UPSTREAM_TEST_CASES = [
        "google.com",        # dig @127.0.0.1 a google.com
        "facebook.com",      # dig @127.0.0.1 a facebook.com
        "twitter.com",       # dig @127.0.0.1 a twitter.com
        "taobao.com",        # dig @127.0.0.1 a taobao.com
        "www.facebook.com",  # dig @127.0.0.1 a www.facebook.com
        "x_8888",            # dig -x 8.8.8.8 @127.0.0.1（PTR 反查）
    ]
    _TEST_LISTEN_PORT = "15353"  # 上游 test.py 默认端口

    def _probe_online_dns(self):
        """探测公网 DNS 可达性（UDP 53 探测包）——chinadns 上游集成
        测试需在线 DNS 环境（CI worker 网络受限时跳过测试）。"""
        import socket
        probe = (b"\x12\x34\x01\x00\x00\x01\x00\x00\x00\x00\x00\x00"
                 b"\x06google\x03com\x00\x00\x01\x00\x01")
        for dns_ip in ("114.114.114.114", "8.8.8.8"):
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.settimeout(3)
            try:
                s.sendto(probe, (dns_ip, 53))
                data, _ = s.recvfrom(512)
                if data:
                    return True
            except OSError:
                pass
            finally:
                s.close()
        return False

    @staticmethod
    def _encode_dns_query(name, qtype):
        """构造标准 DNS 查询报文（RFC 1035）。qtype: 1=A, 12=PTR。"""
        qname = b"".join(
            bytes([len(lbl)]) + lbl.encode() for lbl in name.split(".")
            if lbl) + b"\x00"
        # id=0x1234 rd=1, qdcount=1
        return (b"\x12\x34\x01\x00\x00\x01\x00\x00\x00\x00\x00\x00"
                + qname + qtype.to_bytes(2, "big") + b"\x00\x01")

    @staticmethod
    def _dns_query_ok(sock, query, expect_name=None):
        """发查询并判定应答：rcode=0 且 ANCOUNT>0（真实解析到记录）。"""
        sock.send(query)
        data = sock.recv(512)
        if len(data) < 12:
            return False, "short response"
        rcode = data[3] & 0x0F
        ancount = int.from_bytes(data[6:8], "big")
        if rcode != 0:
            return False, f"rcode={rcode}"
        if ancount < 1:
            return False, "ancount=0"
        return True, f"ancount={ancount}"

    def _run_upstream_tests(self):
        """真实运行上游 tests/ 6 个 DNS 集成测试（boost 系 rc 判过手法）。

        上游 test.py（Python 2）语义：启动 src/chinadns -p 15353 转发，
        再按测试文件内容跑 dig <cmd> -p 15353，dig rc=0 即通过；本移植
        额外校验应答含真实记录（防空应答假阳性）。查询通道双模式：
        - dig 可用（试运行验证可执行）→ 原样执行上游 dig 命令
        - dig 缺失（CI-021 等环境）→ Python 原生 DNS 客户端
          （socket UDP + RFC 1035 报文）等价查询，判定语义一致
        环境限制（公网 DNS 不可达）时 SKIPPED 并留报告，不阻塞构建。
        """
        exe = os.path.join(self.build_folder, "src", "chinadns")
        report = [f"# chinadns 1.3.2 upstream tests (port {self._TEST_LISTEN_PORT})",
                  f"exe: {exe}"]

        if not os.path.isfile(exe):
            report.append("RESULT: SKIPPED_ALL env=exe_not_found")
            self._write_test_report(report)
            self.output.warn("上游测试 SKIPPED：未找到编译产物 src/chinadns")
            return

        if not self._probe_online_dns():
            report.append("RESULT: SKIPPED_ALL env=offline_dns")
            self._write_test_report(report)
            self.output.warn("上游测试 SKIPPED：公网 DNS 不可达（网络"
                             "受限环境限制）")
            return

        # dig 可用性验证：which 找到后试运行（防 PATH 残留假路径）
        use_dig = None
        dig = shutil.which("dig")
        if dig:
            try:
                r = subprocess.run([dig, "+short", "@127.0.0.1", "localhost"],
                                   capture_output=True, timeout=10,
                                   stdin=subprocess.DEVNULL)
                use_dig = dig if r.returncode in (0, 1) else None
            except OSError:
                use_dig = None
        if use_dig:
            report.append(f"mode: dig ({use_dig})")
        else:
            report.append("mode: python-native DNS client (dig unavailable)")

        tests_dir = os.path.join(self.source_folder, "tests")
        chnroute = os.path.join(self.source_folder, "chnroute.txt")
        iplist = os.path.join(self.source_folder, "iplist.txt")
        passed, failed = 0, 0
        for name in self._UPSTREAM_TEST_CASES:
            proc = None
            try:
                # 上游 .jenkins.sh 用法：test.py -a '-c chnroute.txt -l iplist.txt'
                proc = subprocess.Popen(
                    [exe, "-p", self._TEST_LISTEN_PORT, "-v",
                     "-c", chnroute, "-l", iplist],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                    stdin=subprocess.DEVNULL)
                time.sleep(1)
                if use_dig:
                    with open(os.path.join(tests_dir, name)) as f:
                        dig_cmd = f.read().strip().split()
                    r = subprocess.run(
                        dig_cmd + ["-p", self._TEST_LISTEN_PORT],
                        capture_output=True, text=True, timeout=30,
                        stdin=subprocess.DEVNULL)
                    ok = (r.returncode == 0
                          and "ANSWER SECTION" in (r.stdout or ""))
                    detail = f"dig rc={r.returncode}"
                else:
                    # Python 原生 DNS 客户端（与 dig 等价的 UDP 查询）
                    import socket
                    if name == "x_8888":
                        # dig -x 8.8.8.8 → PTR 查询 8.8.8.8.in-addr.arpa
                        qname = "8.8.8.8.in-addr.arpa"
                        qtype = 12
                    else:
                        qname = name
                        qtype = 1
                    query = self._encode_dns_query(qname, qtype)
                    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                    sock.settimeout(20)
                    try:
                        sock.connect(("127.0.0.1",
                                      int(self._TEST_LISTEN_PORT)))
                        ok, extra = self._dns_query_ok(sock, query)
                        detail = f"pydns {extra}"
                    finally:
                        sock.close()
                if ok:
                    passed += 1
                    report.append(f"PASS {name} ({detail})")
                else:
                    failed += 1
                    report.append(f"FAIL {name} ({detail})")
            except Exception as e:  # noqa: BLE001 - 报告后继续下一用例
                failed += 1
                report.append(f"FAIL {name} (exception: {e})")
            finally:
                if proc is not None:
                    try:
                        proc.send_signal(signal.SIGTERM)
                        proc.wait(timeout=5)
                    except Exception:  # noqa: BLE001 - 清理兜底
                        proc.kill()

        total = len(self._UPSTREAM_TEST_CASES)
        report.append(
            f"TOTAL {total}: {passed} passed / {failed} failed")
        self._write_test_report(report)
        for line in report:
            self.output.info(f"[upstream-tests] {line}")
        self.output.info(
            f"上游测试报告: {passed}/{total} 通过"
            + ("" if failed == 0 else f"（{failed} 失败）"))
        if failed:
            raise Exception(
                f"chinadns 上游集成测试失败: {failed}/{total} "
                f"（详见 {os.path.join(self.build_folder, 'upstream-tests-report.txt')}）")

    def _write_test_report(self, lines):
        path = os.path.join(self.build_folder, "upstream-tests-report.txt")
        try:
            with open(path, "w", encoding="utf-8") as fh:
                fh.write("\n".join(lines) + "\n")
        except OSError:
            self.output.warn("无法写测试报告: %s" % path)

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.output.info("chinadns 1.3.2: bin/chinadns (DNS 分流工具)")
        # R38 — CLI 工具
        self.conf_info.define("user.tools.chinadns-c:exe", "chinadns")
