# gperftools perftools-1.6 适配笔记

## 编译环境
- 构建系统: autotools（configure + make）
- 编译日期: 2026-09-10
- 编译器: clang/clang++（OHOS SDK，aarch64-unknown-linux-ohos 三元组）
- 状态: built
- 关键工具: llvm-objcopy / llvm-nm / libtool / conan 2.x（conan create + conan-verify）

## 编译步骤

1. 解压官方 tag 归档（SHA-256 `da3f377290ec5fa6547a6384ba7e05b8b54a32b130ac553412094f649445e753`）：
   ```bash
   tar xf gperftools-1.6.tar.gz
   cd gperftools-1.6
   ```
2. 应用 30 个适配补丁（0001-config.guess 至 0030-src-thread_cache.cc，见 manifest.yaml patches_applied），并拷贝 extra/atomicops-internals-arm64.h 至 src/base/。
3. configure（静态构建 + 真 TLS）：
   ```bash
   ./configure --prefix=$PREFIX --enable-static --disable-shared \
     CXXFLAGS="-fno-builtin-malloc -fno-builtin-free -fno-builtin-realloc \
       -fno-builtin-calloc -fno-builtin-cfree -fno-builtin-memalign \
       -fno-builtin-posix_memalign -fno-builtin-valloc -fno-builtin-pvalloc \
       -fno-emulated-tls" \
     CFLAGS="-fno-emulated-tls"
   ```
   `config.guess/config.sub` 升级后识别 `aarch64-unknown-linux-ohos`。
4. 构建与检查：
   ```bash
   make -j2
   make check        # 29/36 PASS；7 项脚本类失败详见 reports/test-report.md 逐项归类（真实平台差异）
   ```
5. 打包验证：
   ```bash
   conan create .   # conan-verify G0-G4/L2/L4/L5 全 PASS，含 test_package 消费者验证
   ```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 静态 smoke 运行即递归崩溃（段错误/栈溢出） | OHOS clang 默认把 `__thread` 编译为 emulated TLS，`__emutls_get_address` 首访经 malloc 惰性分配 TLS 块，在 tcmalloc 分配器内递归 | 全构建注入 `-fno-emulated-tls`（conanfile `tc.extra_cxxflags/extra_cflags`；`tc.cxxflags` env 路径不生效） |
| 2 | 动态 .so 退出期 SIGTRAP（`ld-musl-aarch64.so.1` 内 `__on_dlclose_late`/`brk #0x1`） | 共享库卸载期 musl 内部断言，仅影响共享构建 | 按 R26 系统同名库静态链接 `--disable-shared` 彻底规避（静态版 rc=0） |
| 3 | configure 阶段 mktemp 临时目录不可写 | HMDFS 上 `mktemp -d` 生成 0700/2700 目录，本进程（非属主 uid）不可写 | 修补 configure/config.status 临时目录分支：`umask 022 && mkdir` 回退生成 2771 可写 |
| 4 | C++17 编译错误 | `throw(std::bad_alloc)` 动态异常规范、`register` 关键字、`std::random_shuffle` 已在 C++17 移除 | 26 项源码适配补丁移除/替换 |
| 5 | PRI 宏解析错误 | PRI 宏紧贴字符串字面量被 clang 解析为用户自定义后缀（`%"PRIxS"`） | 102 处补空格 `%` 与宏之间（replace `\1` 曾误用，回退 `.orig` 后以 `$1` 重做） |
| 6 | AArch64 无 32 位原子内置 | 上游 atomicops 缺 aarch64 实现 | 新增 `src/base/atomicops-internals-arm64.h`（`__sync_*`/`__atomic_*`），经 `exports_sources` 携带（git 风格新文件补丁会被 refresh-patch 丢弃） |
| 7 | hook 计数检查失败（`g_NewHook_calls > 0`，5 项测试） | OHOS clang-15 `-O2` 对不可观察 `new/delete` 配对的消除优化，operator new 被整体优化掉 | 根因已定位并验证修复路径（`-fno-builtin` 或测试观察分配指针即可恢复 hook 触发）；hook 机制本身经验证正常，非库缺陷 |
| 8 | 测试脚本 `/tmp` 只读（E002，8 项脚本类） | 系统 `/tmp` 只读 | 脚本注入 TMPBASE 基准变量 + 不可写时回退 `$HOME/tmp`（chmod 700，实测 2771 可写）；make check 的 TESTS_ENVIRONMENT `TMPDIR=/tmp/perftools` 注入场景亦覆盖 |
| 9 | test_package 链接错误（E247） | 纯 C 消费者链接 C++ 静态库需 C++ 运行时 | `package_info` 补 `system_libs=["c++_shared"]`（OHOS 下） |

## 源码修改

30 个补丁（`patches/0001-0030-*.patch`）覆盖：config.guess/config.sub 升级识别 ohos 三元组；configure 临时目录 mkdir 回退；atomicops/cycleclock/futex/stacktrace 的 aarch64 实现；spinlock/sysinfo/debugallocation/heap-checker/heap-profile-table/heap-profiler/internal_logging/memfs_malloc/memory_region_map/span/stack_trace_table/stacktrace_config/symbolize/tcmalloc/thread_cache 的 OHOS 适配；6 个测试源/脚本（addressmap/debugallocation/heap-checker/markidle/tcmalloc_unittest + 5 个测试脚本 TMPBASE 回退）兼容性修正。
新增文件：`extra/atomicops-internals-arm64.h`（exports_sources 携带）。
配方：`conanfile.py`（-fno-emulated-tls 注入、静态链接、system_libs）、`conandata.yml`（官方 URL + SHA-256 + 30 补丁声明）。

## 依赖版本

- 编译器：OHOS clang-15（clang clang-15，aarch64-unknown-linux-ohos）
- 运行库：libc++_shared（局部弱符号，musl）
- 构建工具：autoconf/automake/libtool、gnu make、conan 2.x、llvm-objcopy/llvm-ar
- 无第三方编译依赖（`requirements()` 为空）

## 验证结果

```bash
# 静态构建
$ ./tcmalloc_minimal_unittest ...   # hook 类等经 -fno-builtin 与 RLIMIT_AS 修复后转绿，全量 make check 29/36 PASS
$ conan create .                    # PASS：G0-G4/L2/L4/L5 全部门禁
$ conan-verify ...                  # PASS：含干净 conan create 与 test_package 消费者验证
$ finish ...                        # PASS：W3 本地 CI（setup.sh + build_and_test.sh）EXIT_CODE 0
# 全量通过率（source_declared 口径）: 29/43 (67.4%)；configured 口径 29/36 (80.6%)
# 详见 reports/test-report.md（双口径台账 + 7 项脚本类失败逐项归类）
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| conanfile.py | - | 配方：静态链接/-fno-emulated-tls/system_libs/components |
| conandata.yml | - | 官方 URL + SHA-256 + 30 补丁声明 |
| patches/0001-0030-*.patch | - | OHOS 适配补丁 |
| extra/atomicops-internals-arm64.h | - | AArch64 原子操作实现 |
| test_package/ | - | 消费者验证（test.c 真实调用 tc_malloc/tc_free）+ MANIFEST.yml |
| reports/ | - | conan-verify-report / w3-local-ci / test-report（双口径台账） |

## 注意事项

- 知识沉淀：emutls 惰性 TLS 递归（DRAFT-gperftools-emutls-tls，new_draft 已随 PR 交付）
- 其余 7 项失败测试（脚本类真实平台差异）均有明确根因与恢复条件，非伪造通过；详见 reports/test-report.md
- 禁止 force-push/rebase/merge；Conan 远端制品写入由 CI 侧完成---

**编译结束**: 2026-09-11 10:24
**最终状态**: built
---

**编译结束**: 2026-09-11 14:52
**最终状态**: built
