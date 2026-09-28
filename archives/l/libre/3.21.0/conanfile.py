import glob
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import (apply_conandata_patches, copy,
                              export_conandata_patches, get, rm, rmdir)


def _abs(folder, rel):
    return rel if os.path.isabs(rel) else os.path.normpath(os.path.join(folder, rel))


def _find_lib(folder, basename):
    """在依赖包目录内定位 lib<basename>.{so,a}，优先返回 .so。"""
    hits = []
    for base, _dirs, files in os.walk(folder):
        for f in files:
            if not f.startswith("lib%s." % basename):
                continue
            if f.endswith(".so") or f.endswith(".a") or ".so." in f:
                hits.append(os.path.join(base, f))
    shared = [h for h in hits if h.endswith(".so")]
    if shared:
        return shared[0]
    return sorted(hits)[0] if hits else None


class LibreConan(ConanFile):
    name = "libre"
    version = "3.21.0"
    description = ("Libre (re) is a toolkit for real-time communications: RTP/RTCP, "
                   "SIP, SDP, STUN/TURN/ICE, DNS-SD, timers, memory pools and threads.")
    license = "BSD-3-Clause"
    homepage = "https://github.com/baresip/re"
    url = ""
    topics = ("sip", "rtp", "stun", "network", "voip")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # 上游 test/CMakeLists.txt 无条件把 ${OPENSSL_LIBRARIES} 放进 retest 的链接
        # 列表（其前提是构建机存在系统 OpenSSL），交叉环境下不声明就会 NOTFOUND。
        self.requires("openssl/3.5.8.1")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _openssl(self):
        dep = self.dependencies["openssl"]
        pkg = dep.package_folder
        inc = _abs(pkg, dep.cpp_info.includedirs[0])
        ssl = _find_lib(pkg, "ssl")
        crypto = _find_lib(pkg, "crypto")
        if not ssl or not crypto:
            raise ConanException("openssl 包内未找到 libssl/libcrypto")
        return pkg, inc, {"ssl": ssl, "crypto": crypto}

    def generate(self):
        CMakeDeps(self).generate()
        tc = CMakeToolchain(self)
        tc.user_presets_path = False
        if str(self.settings.os) == "OHOS":
            # E092：conan 把 OHOS 映射成 CMAKE_SYSTEM_NAME=HarmonyOS，而 CMake 既无
            # 对应 Platform 模块、也不会 set UNIX（实测 SYS=[HarmonyOS] UNIX=[]）。
            # 上游因此静默丢掉两类平台源文件：
            #   elseif(UNIX)        -> src/net/posix/pif.c、src/net/ifaddrs.c、src/mod/dl.c
            #   MATCHES "Linux"     -> src/net/linux/rt.c
            # 缺陷一路潜伏到链接期才以 undefined symbol（net_if_list /
            # net_if_getaddr4 / net_rt_list）暴露。改走 Linux 分支后 UNIX 自动为 1
            # （实测 SYS=[Linux] UNIX=[1]）。与 ableton-link/amqp-cpp/abcmidi 同法。
            tc.variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.variables["CMAKE_SYSTEM_PROCESSOR"] = (
                "aarch64" if str(self.settings.arch) == "armv8"
                else str(self.settings.arch))
            # 兜底：若工具链仍以 HarmonyOS 胜出，显式补上 UNIX（allegro4.4 同法）
            tc.variables["UNIX"] = "TRUE"
            # E091：走 Linux 分支后 src/net/linux/rt.c 经 <linux/netlink.h> 拉入
            # <linux/socket.h>，而 OHOS sysroot 的 linux/socket.h 无条件定义
            # struct sockaddr_storage、sys/socket.h 只在 #ifndef __MUSL__ 内定义它
            # → redefinition。工具链不自动定义 __MUSL__，按仓库 41 个配方同法补宏
            # （acpid/adns/agetty 先例）。
            tc.extra_cflags.append("-D__MUSL__")
            tc.extra_cxxflags.append("-D__MUSL__")
        for opt in ("USE_REM", "USE_BFCP", "USE_PCP", "USE_RTMP", "USE_SIP"):
            tc.cache_variables[opt] = "ON"
        # 上游 cmake/re-config.cmake 无条件 find_package(OpenSSL 1.1.1)，交叉环境无系统 OpenSSL，
        # 故显式喂 5 个 cache 变量让 FindOpenSSL 命中 conan 依赖包；USE_OPENSSL=ON 同时提供
        # HMAC/AES/TLS 后端（置 OFF 会在 src/hmac/hmac_sha1.c 触发 #error missing HMAC backend）。
        tc.cache_variables["USE_OPENSSL"] = "ON"
        root, inc, libs = self._openssl()
        tc.cache_variables["OPENSSL_ROOT_DIR"] = root
        tc.cache_variables["OPENSSL_INCLUDE_DIR"] = inc
        tc.cache_variables["OPENSSL_CRYPTO_LIBRARY"] = libs["crypto"]
        tc.cache_variables["OPENSSL_SSL_LIBRARY"] = libs["ssl"]
        tc.cache_variables["OPENSSL_LIBRARIES"] = "%s;%s" % (libs["ssl"], libs["crypto"])
        tc.cache_variables["LIBRE_BUILD_SHARED"] = "ON" if self.options.shared else "OFF"
        # 上游 test/CMakeLists.txt 链接的是名为 `re` 的静态目标，其 PUBLIC
        # $<BUILD_INTERFACE:include> 是 retest 拿到 re.h 的唯一来源；置 OFF 会让
        # CMake 退化成裸 -lre 且丢掉头目录（实测 fatal error: 're.h' file not found）。
        # 静态原件只服务于测试链接，shared 包不交付（见 package()）。
        tc.cache_variables["LIBRE_BUILD_STATIC"] = "ON"
        # cmake --install 会字节级改写 RPATH，musl 拒载（经验汇总 §12.38）
        tc.cache_variables["CMAKE_SKIP_INSTALL_RPATH"] = "ON"
        tc.generate()

    def _find_retest(self):
        for root, _dirs, files in os.walk(self.build_folder):
            if "retest" in files:
                return os.path.join(root, "retest")
        raise ConanException("上游测试目标 retest 未生成")

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        # test/ 以 EXCLUDE_FROM_ALL 加入，上游 `make test` 口径需显式构建 retest
        cmake.build(target="retest")
        if not can_run(self):
            self.output.info("retest 不可在本机执行，跳过运行")
            return
        # retest 以 "./test/data" 为相对数据目录（aulength 等用例读它），
        # 必须从源码根运行；在 build/ 下跑会报 "(No such file or directory [2])"。
        self.run('"%s" -rv' % self._find_retest(), cwd=self.source_folder)

    def _is_elf(self, path):
        try:
            with open(path, "rb") as handle:
                return handle.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _sign_installed_elfs(self):
        # E135：OHOS 动态链接器要求 .so 经过 ELF 签名，未签名的共享库即使
        # 路径正确也会被拒载（消费者 dlopen 报
        # "Error loading shared library libre.so.31: Permission denied"）。
        # 顺序与保护分支（E077/§12.14）：
        #   1) 先 llvm-objcopy --remove-section .codesign —— OHOS 工具链链接产物
        #      自带未签名占位段，直接签会报 ".codesign section already exists"；
        #   2) binary-sign-tool sign -selfSign 1；
        #   3) 调用签名器必须剔除 LD_LIBRARY_PATH —— SDK libc++ 会劫持它的
        #      St3__h 符号导致 exit 127；
        #   4) 工具缺失时降级直跑（不因环境差异让配方失败）。
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        if not (os.path.isfile(objcopy) and os.path.isfile(signer)):
            self.output.warning("binary-sign-tool/llvm-objcopy 缺失，跳过 ELF 签名（降级）")
            return
        targets = []
        for pattern in ("*.so", "*.so.*"):
            targets.extend(glob.glob(os.path.join(self.package_folder, "lib", pattern)))
        for target in targets:
            if os.path.islink(target) or not self._is_elf(target):
                continue
            self.run('env -u LD_LIBRARY_PATH "%s" --remove-section .codesign "%s"'
                     % (objcopy, target))
            self.run('env -u LD_LIBRARY_PATH "%s" sign -inFile "%s" -outFile "%s" -selfSign 1'
                     % (signer, target, target))
            os.chmod(target, 0o755)

    def package(self):
        cmake = CMake(self)
        cmake.install()
        if self.options.shared:
            # 静态原件仅为跑通上游 retest 而构建，不随 shared 包交付；
            # 一并去掉上游 export，避免消费者撞上缺失的 libre::re 导入目标
            rm(self, "*.a", os.path.join(self.package_folder, "lib"))
            rmdir(self, os.path.join(self.package_folder, "lib", "cmake", "libre"))
        # 上游把 re-config.cmake 原样装成 package config，但它不是 config 文件
        # （不含导入目标，还会二次 find_package），消费者一律用 conan 生成的 libre-config
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake", "re"))
        rmdir(self, os.path.join(self.package_folder, "share"))
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        self._sign_installed_elfs()

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "libre")
        self.cpp_info.set_property("cmake_target_name", "libre::libre")
        self.cpp_info.set_property("pkg_config_name", "libre")
        self.cpp_info.libs = ["re"]
        self.cpp_info.includedirs = ["include", os.path.join("include", "re")]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m", "pthread", "dl"]
