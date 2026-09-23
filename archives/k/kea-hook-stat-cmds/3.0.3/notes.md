# kea-hook-stat-cmds 3.0.3 适配笔记

## 编译环境
- 构建系统: meson（=1.11.0，`tool_requires`）
- 编译日期: 2026-09-16
- 编译器: clang/clang++ 15.0.4（OHOS SDK 26.0.0.18 + `ci/conan/profiles/ohos-aarch64`）
- 状态: built（conan create / conan-verify / finish 本地门禁全通过；未 push、未 upload）

## 软件定位
- 上游：ISC Kea 3.0.3（MPL-2.0），本库源码目录 `src/hooks/dhcp/stat_cmds/`
- 产物：`libdhcp_stat_cmds.so`（hook 插件，安装到 `lib/kea/hooks/`，由 kea-dhcp4/kea-dhcp6 运行时 dlopen）
- 命令 callout：`stat-lease4-get` / `stat-lease6-get`（导出符号 `stat_lease4_get` / `stat_lease6_get`）
- 构建方式：Kea 3.0 起 Autotools → Meson，整棵源码树单工程构建；本配方构建上游树后只打包本插件 + 其 NEEDED 闭包中的 20 个 Kea 运行库

## 编译步骤

```bash
# 1) 生成构建环境（PkgConfigDeps + MesonToolchain，见 conanfile.py generate()）
conan install . --output-folder=<out> -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
# 2) 配置
meson setup <builddir> <srcdir> --native-file=<out>/conan_meson_native.ini -Dtests=enabled
# 3) 构建（本插件 + 两个测试 target）
ninja -C <builddir> -j6 \
  src/hooks/dhcp/stat_cmds/libdhcp_stat_cmds.so \
  src/hooks/dhcp/stat_cmds/tests/dhcp-stat-cmds-lib-tests \
  src/hooks/dhcp/stat_cmds/libloadtests/dhcp-stat-cmds-libload-tests
# 4) 上游测试
meson test -v -C <builddir> dhcp-stat-cmds-lib-tests dhcp-stat-cmds-libload-tests
```

## 遇到的问题与解决方案

| # | 问题（首个错误） | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `meson.build:17:0: ERROR: Unknown linker(s): [['llvm-ar']]`（exit 1） | meson 对 clang 默认用裸名 `llvm-ar` 探测静态链接器，Conan MesonToolchain 未写出 `ar/ranlib`，本环境（及 CI）裸名 exec 失败 | `generate()` 从 `tools.build:compiler_executables.c` 推导同目录 `llvm-ar`/`llvm-ranlib` 写入 `tc.binaries` |
| 2 | `meson.build:186:4: ERROR: Problem encountered: Unsupported system "harmonyos".`（exit 1） | OHOS 上 `build_machine.system()` 返回 `harmonyos`，Kea 平台白名单（`meson.build:163-186`）不含它 | 补丁 0001：顶层 `meson.build` 把 `harmonyos` 归一化为 `linux`（一处修改使所有子目录走 Linux 分支） |
| 3 | `meson.build:477:8: ERROR: Problem encountered: Boost TLS support broken.`，meson-log 首个编译错误 `boost/core/detail/sp_thread_sleep.hpp:73:5: error: use of undeclared identifier 'pthread_setcancelstate'`（exit 1） | OHOS musl `<pthread.h>` 不声明 `pthread_setcancelstate()`（实测出现次数 0），而 boost 1.85 在 `BOOST_HAS_PTHREADS && !__ANDROID__` 时无条件调用；`boost/asio/ssl.hpp` 头链必经 | `tc.extra_cxxflags.append("-DBOOST_SP_NO_PTHREAD_SETCANCELSTATE")`（boost 官方逃生宏） |
| 4 | `Checking if "LOG4CPLUS_INITIALIZER_H" with dependency log4cplus runs: NO (127)` → `meson.build:824:24: ERROR: Unknown variable "log4cplus".`（exit 1） | meson 特性探针是"编译并运行"，native 构建下真实执行；host 共享依赖 `liblog4cplus.so.9`（`shared=True`）不在配置期运行时 `LD_LIBRARY_PATH`（127 = 动态加载失败，meson-log：`Error loading shared library liblog4cplus.so.9`） | `generate()` 用 `Environment` 把各 host 依赖 `cpp_info.libdirs` 追加进 `LD_LIBRARY_PATH` 并 `save_script("conanbuildenv-kea-runtime")`（聚合进 conanbuild.sh） |
| 5 | `src/lib/dhcp/iface_mgr_linux.cc:40:10: error: redefinition of 'sockaddr_storage'`（exit 1，`ninja: build stopped`） | OHOS sysroot 的 `linux/socket.h`（bionic 派生）定义 `struct sockaddr_storage`，与 musl `sys/socket.h` 冲突；`linux/rtnetlink.h` 间接包含前者 | 补丁 0002：包含 netlink 头前 `#define sockaddr_storage __linux_uapi_sockaddr_storage`、include 后 `#undef`，守卫 `__linux__ && !__GLIBC__`（标准 libc 鉴别宏，不使用 `__OHOS__`） |

## 源码修改

| 补丁文件 | 修改文件 | 改动 | 说明 |
|---|---|---|---|
| `patches/0001-meson.build.patch` | `meson.build` | +6/-0 | 平台名归一化（harmonyos → linux），无平台宏 |
| `patches/0002-src-lib-dhcp-iface_mgr_linux.cc.patch` | `src/lib/dhcp/iface_mgr_linux.cc` | +13/-0 | netlink 头前重命名 UAPI `sockaddr_storage`，守卫 `__linux__ && !__GLIBC__` |

## 依赖版本

| 依赖 | 版本 | 类型 |
|---|---|---|
| boost | 1.85.0 | 强制（`>=1.66`；1.90/1.91 制品仓包缺 Kea 实际使用的头文件） |
| log4cplus | 2.2.0.1 | 强制（经 kea-log 传递 + 顶层 fallback 声明） |
| openssl | 3.5.8.1 | 强制（`crypto` 默认后端，Mandatory） |
| gtest | 1.17.0.1 | test_requires（`-Dtests=enabled`） |
| meson | 1.11.0 | tool_requires（须 ≥1.10，boost 包头不含 `libboost_system`，靠 header-only 模块回退） |
| zlib | 1.3.1 | 传递（boost 依赖） |

可选后端 botan/krb5/mysql/postgresql/netconf 显式 `disabled`（制品仓无可消费依赖，默认亦不启用）。

## 知识图谱

| 平台问题 | 命中/新增 |
|---|---|
| `Unknown linker(s): [['llvm-ar']]` | E481（MesonToolchain 注入 llvm-ar/llvm-ranlib）、E012 |
| `Unsupported system "harmonyos"` | E090 |
| `pthread_setcancelstate` 未声明 | E085 / E127 / E507 |
| `sockaddr_storage` 重定义 | E091 / E119 |
| 配置期 compile-and-run 探针 `runs: NO (127)` | 未命中正式条目 → 新增草稿 `knowledge/drafts/E429-draft-C4CE.{kv,md}` |

## 验证结果

```bash
# 构建
ninja -C <builddir> -j6 <stat_cmds hook + 2 个测试 target>
# → exit_code=0，242/242 目标完成

# 上游测试
meson test -v -C <builddir> dhcp-stat-cmds-lib-tests dhcp-stat-cmds-libload-tests
# → Ok: 2  Fail: 0  (exit_code=0)
./dhcp-stat-cmds-lib-tests     → [==========] 10 tests from 1 test suite ran.  [  PASSED  ] 10 tests.
./dhcp-stat-cmds-libload-tests → [==========] 3 tests from 1 test suite ran.   [  PASSED  ] 3 tests.
# 共 13/13 通过，0 失败，0 跳过

# conan create（含 test_package dlopen 实测）
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
# → exit_code=0

# conan-verify
python3 $SKILL_ROOT/scripts/ohc-run.py conan-verify kea-hook-stat-cmds 3.0.3
# → G0-G4 全 PASS

# finish
python3 $SKILL_ROOT/scripts/ohc-run.py finish kea-hook-stat-cmds 3.0.3 built
# → exit_code=0，status=built
```

## 交付物

| 文件 | 说明 |
|------|------|
| `lib/kea/hooks/libdhcp_stat_cmds.so` | 本 hook 插件 |
| `lib/libkea-*.so*`（20 个库） | 插件运行时加载的 Kea 共享库（`readelf -dW` NEEDED 闭包），含 soname 符号链接 |
| `licenses/COPYING` | 上游 MPL-2.0 许可 |

## 注意事项

- 本包**不导出可链接的库/头**（`cpp_info.libs=[]`、`includedirs=[]`）：插件由 Kea 服务器运行时 `dlopen()`，不是被链接的目标；`libdirs=["lib"]` 仅供消费者运行时环境指向包内 Kea 库。
- 本包无 CLI 产物 → 不需要 `commands.json`（R38 不适用）。
- boost 必须固定 1.85.0：制品仓 `1.90.0.x` 缺 `boost/interprocess/sync/interprocess_upgradable_mutex.hpp`、`1.91.0.1.3` 缺 `boost/circular_buffer.hpp`（Kea `meson.build:198-215` 的 required 头检查）。
- 不运行整棵 Kea 测试套件（需要 root/网络夹具），只跑覆盖本插件的两个 Meson 注册套件。
---

**编译结束**: 2026-09-17 22:09
**最终状态**: built
