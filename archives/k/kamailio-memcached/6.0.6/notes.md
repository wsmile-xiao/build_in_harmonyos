# kamailio-memcached 6.0.6 适配笔记

## 编译环境

- 构建系统: makefile（kamailio 自有 Makefile 体系：`make cfg` + `make modules modules=modules/memcached`）
- 编译日期: 2026-10-02
- 编译器: clang 15.0.4（`/data/service/hnp/bin/clang`，默认目标 `aarch64-unknown-linux-ohos`）
- 状态: built（配方完成并经 `conan create` + `test_package` 验证；尚未 upload 到制品仓）
- 源码: https://www.kamailio.org/pub/kamailio/6.0.6/src/kamailio-6.0.6_src.tar.gz
- 源码 SHA256: 32e4290c6813c9d0289abe9ec2de9138e12e0381179218a7fed374ad813ecc48
- 本机: `uname -a` → `HarmonyOS localhost HongMeng Kernel 1.12.0 #1 SMP ... aarch64 Toybox`
- Conan: 2.29.1（OHOS 适配版），profile `ci/conan/profiles/ohos-aarch64`
- 工作区: `kamailio-memcached-6.0.6-wt`（worktree，分支 `feat/kamailio-memcached-6.0.6`）

## 定位

- 本包 = Kamailio 6.0.6 源包内 `src/modules/memcached/` 模块，产物 `memcached.so`。
  对应发行版子包：Alpine `kamailio-memcached`（`_mod_list_memcached="memcached"`）、
  Debian `kamailio-memcached-modules`、OBS/RHEL `%package memcached`。
- 模块源文件：`memcached.c`、`mcd_var.c`（纯 C）；入口 `struct module_exports exports`（name="memcached"）。
- 唯一强制第三方依赖：`libmemcached/1.0.18`（`Makefile:13-14` pkg-config；`memcached.h:28`
  `#include <libmemcached/memcached.h>`；`memcached.c:295` 代码级下限 `LIBMEMCACHED_VERSION_HEX >= 0x00038000`）。
- 模块**不链接 Kamailio core**：21 个 core ABI 符号保持未定义，由 kamailio 宿主在装载时提供。

## 编译步骤（探索阶段实跑）

```bash
cd <src>/src
export CC=/data/service/hnp/bin/clang
export PKG_CONFIG_PATH=<PkgConfigDeps 生成的 .pc 目录>     # 含 -lmemcached -lm -lc++
make cfg                                                    # 生成 config.mak / modules.lst
make -j1 modules modules=modules/memcached SHELL=/data/service/hnp/bin/bash
# → src/modules/memcached/memcached.so
```

配方内等价实现见 `conanfile.py`：`source()` 取官方 tarball；`generate()` 跑 `PkgConfigDeps`；
`build()` 在 `build_folder/worktree` 内以上述命令构建；`package()` 收取
`lib/kamailio/modules/memcached.so`。

## 遇到的问题与解决方案

| # | 问题（首个真实错误） | 根因 | 解决方案 |
|---|----------------------|------|----------|
| 1 | `conan create` 产物 `memcached.so` 中 `__gxx_personality_v0` / `_ZSt9terminatev` / `__cxa_begin_catch` 未解析（`llvm-nm -u` 可见）；运行时 `dlopen` 报 `symbol not found` | `libmemcached/1.0.18` 是**静态 C++ 实现**归档，其 `package_info` 声明 `system_libs=["m","c++"]`，但**包内自带 `.pc` 未声明** `-lm -lc++`；kamailio 模块 Makefile 正是用 `pkg-config --libs libmemcached` 取链接参数 → 共享库链接仍 rc=0，隐患静默 | `generate()` 用 Conan `PkgConfigDeps` 生成 `.pc`（自动带上声明过的 `system_libs` → `-lmemcached -lm -lc++`），并以 `PKG_CONFIG_PATH` 指向该目录。修复后 `DT_NEEDED = libc++_shared.so, libc.so`，`llvm-nm -u` 不再残留 C++ 运行时符号 |
| 2 | `make[1]: --libs: No such file or directory`（模块 Makefile 解析期噪声） | `src/modules/memcached/Makefile` 用 `BUILDER = $(shell which pkg-config)` 探测 pkg-config；在 make 默认 `/bin/sh`（toybox）下该探测不稳定 | 驱动 make 时显式传 `SHELL=/data/service/hnp/bin/bash`（可用时），消除噪声并使 pkg-config 探测确定化。无需改源码 |
| 3 | 裸进程 `dlopen(memcached.so, RTLD_LAZY)` 失败：`Error relocating ...: pv_get_null: symbol not found` | OHOS（musl）无延迟绑定 —— `dlopen` 返回前即完成全部重定位；模块依赖 Kamailio core ABI（宿主提供） | 非缺陷，属 Kamailio 模块装载模型的正确行为。test_package 以 `kamailio_host_stubs.c`（21 个 core ABI 桩，`-rdynamic` 导出）模拟宿主，与 kamailio 二进制 `-Wl,-export-dynamic` 同形 |
| 4 | `conan create` test_package 报 `CMakeToolchain is declared in the generators attribute, but was instantiated in the generate() method too` | test_package 既在 `generators` 声明 `CMakeToolchain`，又在 `generate()` 实例化（需注入 `MODULE_SO` cache 变量） | 从 `generators` 属性移除 `CMakeToolchain`，仅保留 `CMakeDeps`；`generate()` 中实例化并设 `MODULE_SO` |

## 源码修改

无。未对 kamailio 源码施加任何补丁；平台适配完全由构建设置
（`SHELL`、`PKG_CONFIG_PATH`、Conan 生成的 `.pc`）完成，`patches/` 为空。

## 依赖版本

- `libmemcached/1.0.18`（ohpcd，`conan download --only-recipe` 与二进制 `73d9d7c4...` 双证 rc=0）
  - 传递第三方闭包为空（`conan graph info` → `requires=[]`）
- 系统运行时（不单独适配）：`libc.so`、`libc++_shared.so`
- 运行期服务（非构建期依赖）：memcached 服务端

## 上游测试（R51 三步法申报表）

| 步骤 | 内容 | 证据 |
|---|---|---|
| 1 清点 | 上游 6.0.6 **无自动化测试套件**：无顶层 `test/`·`tests/`；`src/modules/memcached/` 无测试文件；Makefile 层级无 `TESTS`/`check_PROGRAMS`/`check-local`；`src` 内无 ctest/pytest/gtest 注册；源码内 Alpine APKBUILD `options="!check" # no testsuite` | `reports/upstream-test-audit.md` 10 项；`test_package/MANIFEST.yml` 的 `upstream_test_audit` |
| 2 运行 | **真实上游入口 = 构建入口**，已实际执行：`make -C src cfg` + `make -C src modules modules=modules/memcached -j1 SHELL=<bash>` → 链接成功产出 `memcached.so` | `kamailio-memcached-6.0.6-evidence/logs/10-make-cfg.log`、`12-make-module-attempt2.log` |
| 3 回填 | 实测口径：**上游用例 0 / 通过 0 / 失败 0 / 跳过 0**（无套件，无"漏测"对象）；本包补全消费者用例 **10/10**（含鸿蒙 4/4） | 本文件"验证结果"节；`reports/test-report.md` |

> 补充清点（他模块/工具级，均未注册进任何构建/测试系统，与本模块无关）：
> `src/modules/tm/test/`、`src/modules/rtpproxy/test/`、`src/modules/janssonrpcc/test/`、
> `utils/kamctl/dbtextdb/tests/` —— 见 `reports/upstream-test-audit.md` 第 10 项。

## 验证结果

```bash
# 1) 真实构建（conan create）
$ conan create archives/k/kamailio-memcached/6.0.6 \
    -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
   rc=0
   包内: lib/kamailio/modules/memcached.so (1042944 B) + licenses/COPYING

# 2) test_package（消费者视角，10/10）
$ ./test_memcached_module
   CHECK-OK: module-dlopen-lazy
   CHECK-OK: module-exports-symbol
   CHECK-OK: module-exports-name-memcached      (name == "memcached")
   CHECK-OK: module-libmemcached-libversion-symbol
   CHECK-OK: module-libmemcached-version-string (1.0.18)
   CHECK-OK: module-libmemcached-api-callable
   CHECK-OK: ohos-elf64-aarch64-module
   CHECK-OK: ohos-dt-needed-only-system-runtime (libc++_shared.so, libc.so)
   CHECK-OK: ohos-no-build-path-rpath
   CHECK-OK: ohos-kamailio-host-abi-required
   RESULT 10/10
```

日志：`reports/`（本目录）与工作区证据目录
`kamailio-memcached-6.0.6-evidence/logs/`。
---

**编译结束**: 2026-10-02 14:18
**最终状态**: built
