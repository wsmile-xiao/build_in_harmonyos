# ola 0.10.9 适配笔记（HarmonyOS PC aarch64）

## 基本信息

- **上游**：https://github.com/OpenLightingProject/ola，tag 0.10.9
- **tarball**：https://github.com/OpenLightingProject/ola/archive/refs/tags/0.10.9.tar.gz（sha256 d2a80d90...47b5）
- **构建系统**：autotools（上游 GitHub tag tarball **不含**预生成 configure/Makefile.in，需 `autoreconf -i` bootstrap）
- **编译器**：clang 15（aarch64-unknown-linux-ohos 三元组，OHOS SDK 26.0.0.18 sysroot）
- **适配路径**：路径 A（基础适配）
- **产物**：28 个静态库 + olad/ola_trigger/usbpro_firmware/rdmpro_sniffer 4 个可执行 + 182 头文件
- **License**：LGPL-2.1-or-later（客户端库）+ GPL-2.0-or-later（守护进程/工具/插件）双许可

## 依赖（全部 ohpcd 制品仓已发布）

| 依赖 | 版本 | 角色 | 备注 |
|------|------|------|------|
| protobuf | 3.17.3 | 运行时+构建期 | 提供 libprotobuf/libprotoc/protoc 二进制/.pc 文件；configure 经 pkg-config 找到，`--with-protoc` 显式传 conan protoc（交叉编译惯例） |
| uuid | 2.40.1 | 运行时 | libuuid（静态），pkg_config_name=uuid，configure 的 PKG_CHECK_MODULES(base_uuid) 首选路径 |
| cppunit | 1.15.1 | 仅测试 | 上游 78 个 Tester 的框架，经 .pc 注入 |
| automake | 1.18 | tool_requires | CI Worker 无系统 aclocal（litecoin #45059 实锤），automake 包带全套；本地 autoreconf 也靠它装 config.guess/sub |
| libtool | 2.5.4.1 | tool_requires | autoreconf -i 需要 libtoolize |

## 构建流程（conanfile.py build()）

```
1. apply_conandata_patches()          # 0001 NetworkUtils + 0002 configure.ac
2. autoreconf -i                      # bootstrap 生成 configure/Makefile.in/config.guess/config.sub
3. 运行期修补 config.guess/config.sub  # E007: HarmonyOS 识别（2024-07-27 版仍不认）
4. 运行期修补 configure umask 077→022  # E011/E114: HMDFS + uid0 DAC
5. ./configure --build/--host=aarch64-unknown-linux-ohos ... --with-protoc=<conan protoc>
6. make -j1                           # HMDFS 无 mkfifo jobserver
7. make -j1 check                     # 上游测试实跑
8. make -j1 install (package())
```

## 遇到的问题与解决方案（完整踩坑日记）

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `autoreconf: error: libtoolize failed` | OHOS 无系统 libtoolize | conan tool_requires libtool/2.5.4.1，VirtualBuildEnv 自动注入 LIBTOOLIZE/ACLOCAL_PATH |
| 2 | `configure: error: cannot guess build type` | automake 1.18 的 config.guess（2024-07-27 版）仍不识别 HarmonyOS uname | conanfile.py 运行期给 config.guess 加 `*:HarmonyOS:*:*` 分支、config.sub 加 `linux-ohos*`（R6：生成文件运行期编辑） |
| 3 | `configure: error: cannot find 'protoc' program` | conan protobuf 包的 protoc 在包内 bin/，不在 PATH | `--with-protoc=$PREFIX/bin/protoc`（ola.m4 原生支持，交叉编译惯例） |
| 4 | `configure: error: Cannot find the protoc header files` | PKG_CHECK_MODULES(libprotobuf) 只影响 libprotobuf_CFLAGS，探针 AC_CHECK_HEADER 用裸 CXXFLAGS | CPPFLAGS 注入 -I$protobuf/include |
| 5 | `configure: error: cannot find libprotoc` | ola.m4 的 AC_LINK_IFELSE 只链 `-lprotoc`，但 libprotoc.a 引用大量 libprotobuf 符号（静态库无递归解析） | LIBS 预置 `-lprotobuf`，探针链接成功 |
| 6 | `common/network/NetworkUtils.cpp: error: use of undeclared identifier '_res'` | OHOS musl 不导出全局 `_res` resolver 符号（resolv.h 有 `struct __res_state` 类型与 res_init() 声明，但无 glibc 式 `extern struct __res_state _res;` 全局） | 补丁 0001：`#elif !defined(HAVE_DECL__RES)` 分支返回空列表（feature-detection）+ 补丁 0002：configure.ac 加 AC_CACHE_CHECK+AC_LINK_IFELSE 探针（探测全局 `_res` 符号，可链接则 AC_DEFINE HAVE_DECL__RES；OHOS 上探针失败不定义——本机实测 `checking for global _res resolver state symbol... no`，glibc 上通过） |
| 7 | `ld.lld: error: undefined reference due to --no-allow-shlib-undefined: uuid_*`（链接 olad） | 默认共享构建下 libolae131.so 引用 uuid 符号，但 uuid 只以静态库存在，共享库间符号检查失败 | `--disable-shared --enable-static` 全静态构建（与 R26 系统同名库静态化精神一致）；另在 LIBS 加 `-luuid` 保最终链接 |
| 8 | `common/testing/MockUDPSocket.cpp: fatal error: 'cppunit/extensions/HelperMacros.h' file not found` | 上游 common/testing/Makefile.mk 的 libolatesting 目标未挂 CPPUNIT_CXXFLAGS（上游构建系统缺口） | CPPFLAGS 全局注入 -I$cppunit/include（configure 时传入，全局生效） |
| 9 | `configure: error: C++ compiler cannot create executables`（静态轮） | 上一轮 LDFLAGS 只带了 protobuf 的 -L，LIBS 里 -luuid 找不到库 | LDFLAGS 同时注入 uuid 的 -L |
| 10 | configure 卡在 `config.status: Permission denied` | HMDFS + uid 0 不绕过 DAC，umask 077 建的临时目录 0700 不可写 | configure 生成后 sed 两处 umask 077→022（E011，锚定具体行） |
| 11 | CI #48238: `linux/socket.h:23: error: redefinition of 'sockaddr_storage'`（NetworkUtils.cpp:47 编译失败，CI Worker 独有——本地 include 链未先引 sys/socket.h 故未触发） | OHOS SDK sysroot 的 `linux/socket.h`（被 netlink.h 引入）与 `sys/socket.h`（被 resolv.h→netinet/in.h 传递引入）都定义 sockaddr_storage，无共同 guard；上游 AC_CHECK_HEADERS 只做孤立编译探测，测不出共存冲突 | 补丁 0002（第二处）：把 `AC_CHECK_HEADERS([linux/netlink.h linux/rtnetlink.h])` 换成 `AC_COMPILE_IFELSE` 共存探针（sys/socket.h + netlink.h + rtnetlink.h 一起编译）——OHOS 上探测失败，HAVE_LINUX_NETLINK_H 不定义，NetworkUtils.cpp 走 0001 的 /proc/net/route fallback；glibc/musl 上探测通过不受影响 |

## 上游测试（make check 实跑）

本配置形态（--disable-python-libs）下 TESTS = **79**：78 个 CppUnit Tester 二进制 + 1 个 FileValidateTest.sh。

```
# TOTAL: 79
# PASS:  77
# SKIP:  0
# XFAIL: 0
# FAIL:  2
# XPASS: 0
# ERROR: 0
```

**2 个 FAIL 均为 OHOS 环境限制（非代码缺陷）**：

1. `common/base/CredentialsTester`（6 用例中 1 失败）：
   - 报错：`Credentials.cpp:127: setuid(0): Operation not permitted` + `GetPasswdUID(uid, &passwd_entry)` 断言失败
   - 根因：OHOS 应用进程沙箱禁止 setuid/setgid 切换（无 root 权限模型）；且 OHOS 无 /etc/passwd 数据库，getpwuid 返回空
   - 定性：**环境限制**（测试需要 Unix 多用户权限模型，OHOS 单用户沙箱不提供）
2. `ola/OlaClientTester`（2 用例中 1 失败）：
   - 报错：`olad/OlaDaemon.cpp:111: Unable to determine home directory` → `StreamingClientTest::testSendDMX setUp() failed`
   - 根因：OlaDaemon::DefaultConfigDir() 走 SupportsUIDs() → GetPasswdUID(getpwuid) 路径取 home 目录；OHOS 无 passwd 数据库该路径返回空
   - 定性：**环境限制**（与 #1 同根因——无 passwd 数据库）
   - 注：同二进制中 OlaClientCoreTest 的 RPC 序列化用例通过

**python 系 12 个测试脚本未注册**：`--disable-python-libs` 下 BUILD_PYTHON_LIBS=false，tools/rdm 与 python/ola 的 .sh 系脚本不进 TESTS（需要 CPython + pybind11 绑定，路径 A 范围外）。

## OHOS bionic 差异清单（补丁层处理）

- `_res` 全局符号：bionic 不导出 → NameServers() 返回空列表（RDM DNS 发现降级为"无 DNS 通告"）
- netlink 头共存冲突：`linux/socket.h`（netlink.h 引入）与 `sys/socket.h` 双定义 sockaddr_storage，无共同 guard → configure.ac 换共存探针（AC_COMPILE_IFELSE），OHOS 上不定义 HAVE_LINUX_NETLINK_H，DefaultRoute() 走 /proc/net/route 解析（补丁 0001）
- setuid/setgid/getpwuid：应用沙箱禁止 → CredentialsTester/OlaClientTester 2 项环境限制豁免
- usb 插件：OHOS 无 /dev/bus/usb 直访（HDF 驱动框架管理），本配置 libusb 未找到 → usb 插件不构建（configure 自动跳过，非错误）。**编译期无需 libusb；运行期若需 USB DMX 硬件需走 OHOS USB API 层（后续工作）**

## smoke 验证

```
$ ./olad/olad --version
OLA ./olad/olad version: 0.10.9
```

## 版本号策略

0.10.9 = 上游正式版本号（首次适配，无修复后缀）。
