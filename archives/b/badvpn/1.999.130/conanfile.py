#!/usr/bin/env python3
"""Conan recipe for badvpn 1.999.130 on HarmonyOS PC.

BadVPN is a VPN tool suite (NCD scripting language, tun2socks
proxifier, udpgw, P2P VPN). Built with CMake; we build the tun2socks
+ udpgw tools only (-DBUILD_NOTHING_BY_DEFAULT=1 -DBUILD_TUN2SOCKS=1
-DBUILD_UDPGW=1) — they need only the bundled lwIP (zero external
deps), keeping the OHOS build minimal (full VPN would need OpenSSL/
NSS, also published on ohpcd).

Runtime needs a TUN/TAP device (absent on OHOS) — real tunnel
operation is not verifiable; test degrades to binary presence +
executable + ELF (honest, environment limitation).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain
from conan.tools.files import copy, get


class BadvpnConan(ConanFile):
    name = "badvpn"
    version = "1.999.130"
    package_type = "application"
    license = "BSD-3-Clause"
    homepage = "https://github.com/ambrop72/badvpn"
    url = "https://github.com/ambrop72/badvpn"
    description = ("BadVPN — NCD scripting, tun2socks proxifier, "
                   "udpgw, P2P VPN (tun2socks/udpgw tools)")
    settings = "os", "arch", "compiler", "build_type"

    def source(self):
        get(self, **self.conan_data["sources"][self.version],
            strip_root=True)
        # CMakeLists:1 cmake_minimum_required(VERSION 2.8) 被新 CMake 拒绝
        # （'Compatibility with CMake < 3.5 has been removed'——
        # CMAKE_POLICY_VERSION_MINIMUM 在此 CMake 组合下不生效，capnproto
        # 同款）——内联 python 替换为 3.5（awardeco main 签名同款方案）
        cf = os.path.join(self.source_folder, "CMakeLists.txt")
        s = open(cf).read()
        s = s.replace("cmake_minimum_required(VERSION 2.8)",
                      "cmake_minimum_required(VERSION 3.5)")
        open(cf, "w").write(s)
        # udpgw.c: glibc 的 _res 全局（resolv.h）在 OHOS musl libc 不存在
        # （use of undeclared identifier '_res' 实测）——DNS 获取改读
        # /etc/resolv.conf（标准方式，musl 兼容）
        uf = os.path.join(self.source_folder, "udpgw", "udpgw.c")
        us = open(uf).read()
        old_res = '''    if (res_init() != 0) {
        BLog(BLOG_ERROR, "res_init failed");
        goto fail;
    }
    
    if (_res.nscount == 0) {
        BLog(BLOG_ERROR, "no name servers available");
        goto fail;
    }
    
    BAddr addr;
    BAddr_InitIPv4(&addr, _res.nsaddr_list[0].sin_addr.s_addr, hton16(53));'''
        new_res = '''    // OHOS musl libc lacks glibc's _res global — read /etc/resolv.conf
    FILE *rf = fopen("/etc/resolv.conf", "r");
    char rline[256];
    uint32_t ns_ip = 0;
    if (rf) {
        while (fgets(rline, sizeof(rline), rf)) {
            unsigned a, b, c, d;
            if (sscanf(rline, "nameserver %u.%u.%u.%u", &a, &b, &c, &d) == 4) {
                ns_ip = (a << 24) | (b << 16) | (c << 8) | d;
                break;
            }
        }
        fclose(rf);
    }
    if (ns_ip == 0) {
        BLog(BLOG_ERROR, "no name servers available");
        goto fail;
    }
    
    BAddr addr;
    BAddr_InitIPv4(&addr, hton32(ns_ip), hton16(53));'''
        if old_res in us:
            us = us.replace(old_res, new_res, 1)
        open(uf, "w").write(us)

    def generate(self):
        tc = CMakeToolchain(self)
        # 只构建 tun2socks/udpgw（内置 lwIP，无外部依赖）
        tc.variables["BUILD_NOTHING_BY_DEFAULT"] = "1"
        tc.variables["BUILD_TUN2SOCKS"] = "1"
        tc.variables["BUILD_UDPGW"] = "1"
        tc.variables["CMAKE_INSTALL_PREFIX"] = self.package_folder
        # badvpn CMakeLists:1 cmake_minimum_required 旧值被新 CMake 拒绝
        # （'Compatibility with CMake < 3.5 has been removed'，capnproto
        # 同款）——按报错提示加 CMAKE_POLICY_VERSION_MINIMUM=3.5
        tc.variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        # 平台/事件/信号/TAP 后端：CMake 的 Linux 分支（CMAKE_SYSTEM_NAME
        # STREQUAL "Linux"）在 OHOS 上不执行（系统名 OHOS）→ BADVPN_LINUX/
        # epoll/signalfd 全未定义 → BReactor_badvpn.h:14 / BUnixSignal.h:38
        # / BTap.h:38 'Unknown backend'。OHOS 内核基于 Linux——统一强制
        # -DBADVPN_LINUX -DBADVPN_USE_EPOLL -DBADVPN_USE_SIGNALFD。
        tc.variables["CMAKE_C_FLAGS"] = ("-DBADVPN_LINUX "
                                         "-DBADVPN_USE_EPOLL "
                                         "-DBADVPN_USE_SIGNALFD")
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        # CMake 可执行名是 badvpn-tun2socks/badvpn-udpgw——复制并改名为
        # 预期工具名 tun2socks/udpgw（test_badvpn.py 检查这俩）
        import shutil
        bin_dir = os.path.join(self.package_folder, "bin")
        os.makedirs(bin_dir, exist_ok=True)
        shutil.copy2(
            os.path.join(self.build_folder, "tun2socks", "badvpn-tun2socks"),
            os.path.join(bin_dir, "tun2socks"))
        shutil.copy2(
            os.path.join(self.build_folder, "udpgw", "badvpn-udpgw"),
            os.path.join(bin_dir, "udpgw"))

    def package_info(self):
        self.conf_info.define("user.badvpn:exe", os.path.join(
            self.package_folder, "bin", "tun2socks"))
