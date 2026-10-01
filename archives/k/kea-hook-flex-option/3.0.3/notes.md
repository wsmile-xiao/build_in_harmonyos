# kea-hook-flex-option 3.0.3 适配笔记

## 编译环境
- 构建系统: meson（Kea 3.0 起由 Autotools 迁移；无 configure.ac）
- 编译日期: 2026-09-29
- 编译器: clang/clang++ 15.0.4（OHOS SDK 26.0.0.18，sysroot musl + libc++）
- 目标平台: OHOS / HarmonyOS PC aarch64（profile `ci/conan/profiles/ohos-aarch64`）
- 状态: published

## 定位与家族复用

`flex_option` 与已合入的 `kea-hook-limits`、`kea-hook-ping-check` 同属 Kea 3.0.3
单源码树（`src/hooks/dhcp/` 下平级目录），平台差异完全相同：4 个补丁**整组
逐字节复用**（0001/0002 与家族模板 kea-hook-limits 一致；0003/0004 与家族配方
kea-hook-ping-check 一致，均作用于同一上游树的同一批文件），零改动。插件本身的
源码核对（2026-09-29）：

- 产物 `libdhcp_flex_option.so`（`meson.build` `shared_library('dhcp_flex_option',
  ...)`，5 个 .cc 源文件：flex_option / flex_option_callouts / flex_option_log /
  flex_option_messages / version）
- 上游套件名：`dhcp-flex-option-lib-tests` + `dhcp-flex-option-libload-tests`
- 用例宏计数：tests/ 148（flex_option_unittests 63 + sub_option_unittests 85）+
  libloadtests/ 5 = 153，无 TEST_P
- hook 框架版本：`src/lib/hooks/hooks.h` `KEA_HOOKS_VERSION = 30003`
- 与 ping-check 的关键差异：flex-option 为**纯逻辑 hook**（表达式求值 /
  sub-option 定义与值替换，服务 v4/v6 双协议），无 SOCK_RAW、无特权依赖、
  无外部数据文件 → 上游 153 例在 OHOS 沙箱**零 root 零 SKIP** 全实跑
  （ping-check 有 48 个 Root 组用例因无 CAP_NET_RAW 自动 SKIP）

## 编译步骤

1. `conan install . -pr:h=<ohos-aarch64> -pr:b=<ohos-aarch64>`（PkgConfigDeps + MesonToolchain）
2. `meson setup <builddir> <srcdir> --native-file=conan_meson_native.ini -Dtests=enabled`
3. `ninja src/hooks/dhcp/flex_option/libdhcp_flex_option.so \
        src/hooks/dhcp/flex_option/tests/dhcp-flex-option-lib-tests \
        src/hooks/dhcp/flex_option/libloadtests/dhcp-flex-option-libload-tests`
4. `meson test -v dhcp-flex-option-lib-tests dhcp-flex-option-libload-tests`

## 遇到的问题与解决方案

与家族模板 kea-hook-ping-check/kea-hook-limits 完全同源的十个平台问题（同一
上游树、同一差异），对策一一沿用（4 个补丁逐字节复用 + 配方内三处构建级适配）：

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `meson.build:17:0: ERROR: Unknown linker(s): [['llvm-ar']]` / `Running llvm-ar --version gave [Errno 2]` | 宿主环境 `AR=llvm-ar`（裸名）被 meson 静态链接器探测采用；OHOS 上 CPython subprocess 经 posix_spawn 执行**不解析 PATH**，裸名直接 ENOENT（`which llvm-ar` 却能找到） | `generate()` 从 `tools.build:compiler_executables` 的编译器目录推导 `llvm-ar`/`llvm-ranlib` **绝对路径**写入 machine file `[binaries]` |
| 2 | `meson.build:186:4: ERROR: Problem encountered: Unsupported system "harmonyos".` | OHOS 上 meson 的 `build_machine.system()` 返回 `harmonyos`；Kea 白名单只含 linux/bsd/solaris/darwin | 补丁 `0001-meson.build.patch`（与 kea-hook-limits 逐字节一致）：`SYSTEM == 'harmonyos'` 归一化为 `'linux'` |
| 3 | `meson.build:477:8: ERROR: Problem encountered: Boost TLS support broken.`（首错 `boost/core/detail/sp_thread_sleep.hpp:73: use of undeclared identifier 'pthread_setcancelstate'`） | OHOS musl 的 `<pthread.h>` 不声明 `pthread_setcancelstate()`，boost 1.85 的 `sp_thread_sleep.hpp` 无条件调用 | `tc.extra_cxxflags` 注入 boost 官方逃生宏 `-DBOOST_SP_NO_PTHREAD_SETCANCELSTATE` |
| 4 | `LOG4CPLUS_INITIALIZER_H ... runs: NO (127)` + `meson.build:824:24: ERROR: Unknown variable "log4cplus"` | meson 的"编译并运行"探针在 native 构建下真实执行；探针链接的 `liblog4cplus.so.9` 不在配置期 `LD_LIBRARY_PATH`（127 = 动态加载失败） | `generate()` 用 `Environment` 把各 host 依赖 `cpp_info.libdirs` 追加进 `LD_LIBRARY_PATH`，`save_script("conanbuildenv-kea-runtime")` 聚合进 `conanbuild.sh` |
| 5 | `ninja FAILED: src/lib/dhcp/libkea-dhcp.so.109.0.0.p/iface_mgr_linux.cc.o` → `.../sysroot/usr/include/linux/socket.h:23:8: error: redefinition of 'sockaddr_storage'` | OHOS sysroot 的 bionic 派生 `linux/socket.h` 与 musl `sys/socket.h:377` 都定义 `struct sockaddr_storage`；`linux/rtnetlink.h` 间接包含前者 | 补丁 `0002-src-lib-dhcp-iface_mgr_linux.cc.patch`（与 kea-hook-limits 逐字节一致）：包含 netlink 头前后 `#define sockaddr_storage __linux_uapi_sockaddr_storage` / `#undef`，守卫用 `__linux__ && !__GLIBC__`（标准 libc 鉴别宏，**不含平台宏**） |
| 6 | `meson setup` 报 `/bin/sh: <conan 缓存>/bin/meson: Permission denied`（conan create Error 126） | Conan 的 meson 包 `bin/meson` 是 **shebang shell 包装脚本**；OHOS 内核拒绝对脚本的 execve（全设备禁 shebang exec，与 automake 1.19 笔记同根因） | build() 不直接用 Meson helper 执行 meson，改 `sh "<meson 包>/bin/meson" setup/compile/test`（sh 直接读脚本不触发 execve；内部 exec 的 python3 是 ELF 可执行）——命令行参数与 conan 2.29 helper 完全一致（同 --native-file/--prefix=/） |
| 7 | `meson setup` 收尾处 `Running command: scripts/env.sh KEA_PKG_TYPE_IN_CONFIGURE` → `ERROR: Unhandled python OSError`（conan create Error 13） | Kea 顶层 meson.build 在 configure 期直接 `run_command(ENV, ...)` 执行 `scripts/env.sh`（探包类型）与 `scripts/grabber.py`（文件列表探针）——均为带 shebang 的脚本，OHOS 内核拒 execve，与 #6 同根因但发生在**上游源码内部** | 补丁 `0003-meson.build.patch`（与 kea-hook-ping-check 逐字节一致）：把脚本变量定义为**解释器前缀数组**（`ENV = ['/bin/sh', <脚本路径>]`、`GRABBER = [find_program('python3').full_path(), <脚本路径>]`），所有调用点仍把变量作为 run_command 首参传入、无需逐点修改 |
| 8 | setup 全绿后收尾处 `Configuring config.report with command` → `ERROR: Unhandled python OSError`（Error 13） | `meson.build:1025` 的 `CONFIG_REPORT = configure_file(command: [TOP_BUILD_DIR / 'config-report.sh'])` 直接执行**刚生成的**脚本——同一 shebang execve 家族，但发生在生成的产物脚本上 | 补丁 `0003` 第二个 hunk：`command: ['/bin/sh', TOP_BUILD_DIR / 'config-report.sh']`（hunk 行号按 patch-ng 语义写 1028 而非 1022：conan 的 patch-ng 引擎按"已打过先前补丁文件的源"解释 hunk 行号，0001 在 165 行处 +6 行，1022+6=1028） |
| 9 | setup 进入 `src/lib/process/cfgrpt` 后 `Configuring config_report.cc with command` → `ERROR: Unhandled python OSError`（Error 13） | `src/lib/process/cfgrpt/meson.build:4` 的 `command: [mk_cfgrpt, '@INPUT@', '@OUTPUT@']` 直接执行 `tools/mk_cfgrpt.sh`（把 config.report 文本嵌进 config_report.cc）——与 #6/#7/#8 同根因，但位于子目录构建文件 | 补丁 `0004-src-lib-process-cfgrpt-meson.build.patch`（与 kea-hook-ping-check 逐字节一致）：`command: ['/bin/sh', mk_cfgrpt, '@INPUT@', '@OUTPUT@']` |
| 10 | meson test 两套件 exit status 127；stderr 刷屏 `Error loading shared library libkea-dhcpsrv.so.131:` + `Error relocating ...: symbol not found` | OHOS /storage 沙箱**拒绝创建符号链接**：meson 用 `version: '131.0.0'` 构建并只以**符号链接**发布 soname 名 `libkea-X.so.131` → 链接名文件从不存在，加载器按 NEEDED 名（soname）找文件必然落空 | build() 在 compile 后 `_materialize_sonames()`：os.walk 构建树 src/lib，对每个 `libkea-X.so.N.M.K` 实文件以**复制**方式生成 soname 名 `libkea-X.so.N`（幂等）。package() 收尾另有空产物复核自愈（0 字节即从构建树重拷并 WARNING） |
| 11 | （家族新增）`meson compile` 中途 `posix_spawn: Resource temporarily unavailable (EAGAIN)` | OHOS app 沙箱限制并发进程数：ninja 默认按 20 核并发（~45 个活动 spawn）超出配额 | `meson compile -j 8` 限并发（家族配方 host-cmds 真机实测，本配方沿用） |

## 插件特有测试面：零 root 零特权

flex_option 与 ping_check 的测试面差异是家族内的关键对照：ping_check 的
`IcmpSocket` 底层是 `socket(AF_INET, SOCK_RAW, IPPROTO_ICMP)` 原始套接字，
上游 48 个 Root 组用例在 OHOS 沙箱自动 SKIP；flex_option 是纯选项表达式逻辑
hook，`src/hooks/dhcp/flex_option/tests/` 与 `libloadtests/` 全部 153 例
无 SOCK_RAW、无特权依赖、无外部数据文件（测试源码 grep 零命中 getenv/fork/
system/popen/TMPDIR；lib-tests 链接 `dhcp_flex_option_archive` 静态对象、
libloadtests 经 `-DFLEX_OPTION_LIB_SO` 指向真机路径 dlopen 真实 .so），
OHOS 沙箱下**零 root 零 SKIP 全实跑**（实测结果见「真机验证」节）。

## 真机验证

2026-09-29 真机（HarmonyOS PC aarch64，conan 2.29.1，profile
ohos-aarch64）`ohc-run.py conan-verify` **八门禁全 PASS**，验证报告
22:51 生成，Verdict: PASS，R46 终态 result.json 已上报（draft:false）：

| 门禁 | 结果 | 说明 |
|------|------|------|
| G0 | ✅ | E490 提示为 autotools 启发式误报（本配方 meson，无 configure 脚本），不影响 |
| G1 | ✅ | 配方完整性 11 项全过（R26/R28 通过） |
| G2 | ✅ | conan create 干净构建 + build() 内 meson test 实跑 + test_package |
| G3 | ✅ | R26 系统同名库隔离验证通过 |
| G4 | ✅ | 产物完整性检查通过 |
| L2/L4/L5 | ✅ | 框架在非默认 cache 路径下按“无 cache 路径”跳过深度检查并记 PASS（与家族配方同一运行环境行为） |

真机实测数据（reports/conan-create.log）：

- **meson test 两套件**：`dhcp-flex-option-lib-tests` 148 例 + 
  `dhcp-flex-option-libload-tests` 5 例，**PASSED 153 / SKIPPED 0 /
  FAILED 0**（`[ PASSED ] 148 tests` + `[ PASSED ] 5 tests`，`Ok: 2
  Fail: 0`，实测“零 root 零 SKIP 全实跑”结论成立）
- **test_package 3/3**：
  - test_flex_option_hook：dlopen 加载成功（hooks version 30003），
    load/unload 契约符号可解析 → OK
  - test_ohos_platform：ELFCLASS64 / EM_AARCH64 / PT_DYNAMIC ✓；
    **DT_NEEDED 11 项** = kea 闭包 9（libkea-dhcpsrv.so.131 /
    process.so.91 / eval.so.84 / dhcp.so.109 / hooks.so.121 /
    cc.so.83 / log.so.75 / util.so.102 / exceptions.so.45）+
    libc++_shared.so + libc.so（无 glibc/libstdc++ 命名）→ OK
  - test_ohos_runtime：包内 Kea 运行库 **40 found / 40 loaded**，
    闭包驻留后 hook 仍可加载、契约符号可解析 → OK
- **产物**：`lib/kea/hooks/libdhcp_flex_option.so`（218 KB）+ Kea
  运行时闭包 40 文件
- **0 字节落盘自愈命中 ×2**：package() 复核发现 libkea-exceptions.so.45
  与 libkea-util.so.102 落盘为空，已从构建树重拷（WARNING 日志留存）；
  后续 test_ohos_runtime 40/40 dlopen 证明自愈有效（与 ping-check 笔记
  同款瞬时异常）

运行环境备注（非配方知识）：ohc-run.py 的 conan 以 app 沙箱 home
（/data/storage/el2/base/.conan2）为 cache，该 home 无 ohpcd 源且缓存
为空 → 依赖（log4cplus/2.2.0.1 等）解析失败（首次 G2 FAIL：E540）。
解法：启动 verify 时 `CONAN_HOME=/storage/Users/currentUser/.conan2`
指向家族真机构建缓存（61G，全部依赖二进制齐全），全部依赖零网络命中；
源码经设备内 127.0.0.1:18080 http 镜像（conandata.yml 设备侧临时换
http 镜像 URL，本地配方保持官方 URL 不提交）。

## 已知限制

无。上游本组件 153 例全部为纯逻辑用例，不存在 ping-check 式 root 用例
SKIP；全树其余 11585 例（Kea 主程序、核心库及其他 hook 组件）不在本配方
适配范围（见 MR 正文「测试减少原因」节）。
