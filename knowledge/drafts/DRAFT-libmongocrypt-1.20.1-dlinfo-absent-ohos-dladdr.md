# OHOS 上取「已加载动态库的路径」：dlinfo 不存在，dlopen 句柄也不能和 dlpi_addr 比对

> Draft: DRAFT-LIBMONGOCRYPT-1201-OHOS-DLINFO-MISSING-DLADDR-PATH
> Stem: `libmongocrypt-1.20.1-dlinfo-absent-ohos-dladdr` — 与同 stem 的 `.kv` 成对
> 交付载体：`archives/l/libmongocrypt/1.20.1/patches/0002-mcr_dll-path-via-dladdr-on-ohos.patch`

## 基本信息

- **严重度**: 2（🟡 medium，会一路带到运行期语义）
- **类别**: libc, ohos, portability, headers, runtime
- **触发工具**: clang | cmake | make | ld | test | runtime
- **阶段**: compilation → testing → runtime
- **贡献者**: `iKalous_OscarP`（`draft: true`，未进图谱）

## 错误特征

```
src/os_posix/os_dll.c:112:14: error: call to undeclared function 'dlinfo';
    ISO C99 and later do not support implicit function declarations [-Werror,-Wimplicit-function-declaration]
```

或（改成走「平台不支持」分支后）运行期日志：

```
WARNING Cannot get path of loaded library on this platform. Skipping validation to ensure
        exactly one csfle library is loaded.
test error .../test-mongocrypt-csfle-lib.c:100 _test_csfle_load_twice_fail():
     _mongocrypt_init_for_test(crypt2) succeeded (but should have failed)
```

## 图谱检索反证（0 命中证据，统计基线 = main tip `dfbc6f31b`，2026-09-19）

检索范围：`knowledge/graph/E[0-9][0-9][0-9].kv` 540 条正式条目（graph 目录 .kv 共 542 个文件）、
`knowledge/doc/*.md` 540 篇、`knowledge/drafts/` 2378 个文件、`knowledge/` 根目录 md。

```sh
cd knowledge
grep -ril 'dli_fname'        graph/ doc/ drafts/ *.md   # → 无（0 命中：本条目的核心可执行动作）
grep -ril 'mcr_dll_path'     graph/ doc/ drafts/ *.md   # → 无
grep -ril 'crypt_shared'     graph/ doc/ drafts/ *.md   # → 无
grep -ril 'RTLD_DI_LINKMAP'  graph/ | wc -l             # → 0（正式条目里没有 dlinfo/link_map 家族）
grep -ril 'dlinfo'           graph/ | wc -l             # → 0
```

即：**540 条正式条目对 `dlinfo` / `RTLD_DI_LINKMAP` / `dli_fname` 全部 0 命中**。
`drafts/` 一侧确有 2 份相邻草稿（下表），`knowledge/` 根目录有 1 处 `dlinfo` 提及 ——
`knowledge/musl-glibc-full-comparison-iso-posix.md:2556` 的 `<dlfcn.h>` 对照表：

| 接口/宏 | glibc | musl | OHOS | 说明 |
|---------|:-----:|:----:|:----:|------|
| `dlinfo` | ✅ | ✅ | ✅ | |

**该 OHOS 列是错的**，本条目就是它的更正依据（下文实测三组数据）。同一表 2567 行的
`RTLD_DI_LINKMAP` 同样错标为 ✅。建议主编把这两格改成 ❌ 并把本条目 `similar_to` 挂到该对照文档。

### 与相邻内容的边界（不是同一件事，逐条给可执行反证）

| 相邻条目 | 它主张什么 | 与本条目的差别 | 可执行反证 |
|---|---|---|---|
| `knowledge/drafts/dylib-3.0.1-dlinfo-ohos.kv`（`DRAFT-dylib-dlinfo-ohos`） | 要**枚举已加载库的动态符号表**：用 `dl_iterate_phdr` 遍历，从 `PT_DYNAMIC` 手工解 `DT_SYMTAB/DT_STRTAB/DT_HASH/GNU_HASH` 求符号数 | 本条目要的是**已加载库的文件路径**（上游 `mcr_dll_path` 的语义），一次 `dladdr()` 即可，完全不需要解析 ELF 动态段。反过来 `dl_iterate_phdr` 在 OHOS 上**能**拿到名字（实测 19 个对象 18 个有 `dlpi_name`），但**无法从 `dlopen` 句柄反查是哪一项**——句柄是脱敏 token，与任何 `dlpi_addr` 都不相等（`MATCHES=0`），所以「遍历找句柄」这条路走不通，必须 `dlsym`+`dladdr` | `grep -c 'dli_fname' knowledge/drafts/dylib-3.0.1-dlinfo-ohos.kv` → 0；它的 `approach` 全篇是符号表枚举，没有任何取路径动作 |
| `knowledge/drafts/DRAFT-lief-1.0.0-ohos-runtime-linux-linkmap-sigsegv.*` | 把 `dlopen` 句柄当 `struct link_map*` 强转读会 SIGSEGV | 与本条目互补：它证明「句柄不可解释」，本条目给出「那到底怎么取路径」的可执行替代，并额外实测「`handle == dlpi_addr` 这一 musl 社区常见判等也不成立」（`MATCHES=0`），这是它没覆盖的坑 | `grep -c 'dladdr' .../DRAFT-lief-….md` > 0 但 `grep -c 'dli_fname'` → 0，即只提 dladdr 存在于 libc，未给出取路径配方 |
| `knowledge/graph/E462.kv` | gdb `ptrace Permission denied` / ASan 无报告段错误，`dladdr` 只是顺带出现在其排查手段里 | 阶段（testing/gdb）、错误面、结论都不同 | `grep -c 'ptrace' knowledge/graph/E462.kv` > 0，`grep -c 'mcr_dll_path\|dli_fname'` → 0 |
| `knowledge/musl-glibc-full-comparison-iso-posix.md` | ISO/POSIX 对照表，把 OHOS `dlinfo` 误标 ✅ | 它只是**记录面**（且记错），无可执行修法 | 见上表行号；本条目实测三组数据即它的勘误来源 |


## 根因（真机 + SDK 实测三组）

环境：`ohos-sdk@26.0.0.18`，clang 15，`--target=aarch64-unknown-linux-ohos`，真机 HarmonyOS PC（HongMeng Kernel 1.12.0）。

1. **头文件不声明**：`grep -c dlinfo $SDK/sysroot/usr/include/dlfcn.h` → `0`；`RTLD_DI_LINKMAP` 同样不存在。
   注意源文件顶部已按 `__has_include(<features.h>)` 定义了 `_GNU_SOURCE`（OHOS sysroot **有** `features.h`），所以不是特性宏没打开的问题。
2. **libc 不导出**：
   `llvm-nm -D --defined-only $SDK/sysroot/usr/lib/aarch64-linux-ohos/libc.so | grep -E 'dlinfo|dladdr|dl_iterate_phdr'`
   → 只有 `T dladdr`、`T dl_iterate_phdr`，**没有 `dlinfo`**。所以自己补一行声明也只是把错误从编译期推到运行期。
3. **句柄不能和 `dlpi_addr` 比对**（musl 社区常见替代写法，在 OHOS 上同样不成立）：
   在真机上 dlopen 一个 `libmongocrypt.so` 后打印——
   ```
   handle     = 0x906a8f02f29aa087        # 脱敏 token，不是地址
   dlpi_addr  = 0x5bb7000000              # 同一模块在 dl_iterate_phdr 里的基址
   MATCHES    = 0
   dladdr(sym)= rc=1 dli_fbase=0x5bb7000000 dli_fname=/storage/.../libmongocrypt.so
   ```
   复跑（`tools/probes/lmc_dlname.sh`，2026-09-19）再取一组，句柄值变了而基址不变，
   且 `dl_iterate_phdr` 遍历到的 19 个对象里 18 个 `dlpi_name` 非空（含 libmongocrypt 的完整路径）——
   即 **OHOS 上 `dlpi_name` 是可用的，缺的是「句柄 → 哪一项」这一环**：
   ```
   handle=0xf67234226ebb6148
   HIT name=/storage/.../build/Release/libmongocrypt.so addr=0x5bb20c0000
   phdr_total=19 named=18 empty=1
   dladdr rc=1 dli_fname=/storage/.../build/Release/libmongocrypt.so dli_fbase=0x5bb20c0000 eq_handle=NO
   ```
   所以可行链路只有一条：`dlsym(handle, <已知符号>)` 拿地址 → `dladdr()` 反查该地址所属模块的
   `dli_fname`（`dli_fbase` 恰好等于该项的 `dlpi_addr`，可与遍历结果互校）。
   即：句柄不可解释，但 **`dladdr()` 可用且能给出路径**。

## 解决方案

给 `mcr_dll_path()` 补一个 OHOS 分支，用「解析一个必然存在于目标库内的导出符号 → 把它的地址交给 `dladdr()` → 取 `Dl_info.dli_fname`」代替 `dlinfo(RTLD_DI_LINKMAP)`。

要点：

- 分支必须放在 `#elif defined(__linux__)` **之前**：OHOS 的 clang 同时预定义 `__linux__` 和 `__OHOS__`，顺序写反等于没写。
- 探测符号要按调用方语义挑：`mcr_dll_path` 只会作用在 crypt_shared(csfle) 句柄上，而任何被 libmongocrypt 接受的 csfle 库都必须导出 `MONGOC_CSFLE_FUNCTIONS_X` 里的全部函数（首项 `mongo_crypt_v1_status_create`）；再备一个 `mongocrypt_version` 覆盖「误把 libmongocrypt 自己当句柄」的场景。
- 命中后 `mcr_dll_path_supported()` 仍返回 `true`，让上游 `_validate_csfle_singleton()` 里那句 `assert(existing_path_.path.raw.data ...)` 成立。

```c
#elif defined(__OHOS__)
mcr_dll_path_result mcr_dll_path(mcr_dll dll) {
    static const char *const probes[] = {"mongo_crypt_v1_status_create", "mongocrypt_version"};
    Dl_info info;
    for (size_t i = 0; i < sizeof(probes) / sizeof(probes[0]); i++) {
        void *sym = mcr_dll_sym(dll, probes[i]);
        if (sym != NULL && dladdr(sym, &info) && info.dli_fname != NULL) {
            return (mcr_dll_path_result){.path = mstr_copy_cstr(info.dli_fname)};
        }
    }
    return (mcr_dll_path_result){.error_string = mstr_copy_cstr("Failed to resolve ... via dladdr")};
}
bool mcr_dll_path_supported(void) { return true; }
```

## 证据（方案有效）

`conan create archives/l/libmongocrypt/1.20.1 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing`：
打了该补丁后，ctest 条目 `mongocrypt`（内含 347 个 `INSTALL_TEST`/`INSTALL_TEST_CRYPTO` 注册点、
本次配置实装 294 个用例，含 `_test_csfle_load_twice_fail` 这条依赖 `mcr_dll_path` 的用例）**Passed**，
`100% tests passed out of 8`、`CREATE_EXIT:0`。

## 通用性证据（验证语料不是自己写的 test_package）

- **上游自有的 csfle 用例组**就是本机制的裁判：`_test_csfle_no_paths` / `_test_csfle_not_found` /
  `_test_csfle_load` / `_test_csfle_load_twice` / `_test_csfle_load_twice_fail` 全部来自
  `test/test-mongocrypt-csfle-lib.c`（上游代码，未被本包修改，diff 里只有新增补丁）。
  补丁前 `_test_csfle_load_twice_fail` 以
  `_mongocrypt_init_for_test(crypt2) succeeded (but should have failed)` 失败并 abort 整个进程；
  补丁后同一条用例通过、294 个用例全部跑完（`begin`/`end` 唯一名配对 294/294，退出码 0）。
- **反证另一条路不成立**：用上游构建出的 `libmongocrypt.so` 做独立探针实验（`dlopen` →
  `dl_iterate_phdr` → `dladdr`），得到 `handle=0x906a8f02f29aa087` 与 `dlpi_addr=0x5bb7000000`
  不相等、`MATCHES=0`、`dladdr` 返回 `dli_fname` 正确——这三行数字与 libmongocrypt 的业务无关，
  换任何一个 OHOS 上的 .so 都成立。
- **符号层面的否证**：`llvm-nm -D --defined-only sysroot/.../libc.so` 里 `dlinfo` 不存在而
  `dladdr`/`dl_iterate_phdr` 存在，说明这不是"编译选项没打开"，而是运行库能力缺失。

## 为什么是「一类」而不是「一例」

任何「运行时反查已加载 so 的路径」的代码都会遇到：crypt_shared(csfle) 单例校验、插件按路径去重、
`dlopen` 多副本检测、热更新模块同名判定。它们在 glibc 上写 `dlinfo`，在 musl 上写
`handle == dlpi_addr`，两条路在 OHOS 上都不可用，统一改用 `dlsym + dladdr`。
`grep -rl "dlopen" knowledge/graph | wc -l` = 26 条条目涉及 dlopen，但没有一条讲"取路径"这件事，
本条目补的正是这一段。

## 回退方案

把 OHOS 归进上游自带的 `mcr_dll_path_supported() == false` 分支（`#elif (defined(__linux__) && !defined(__OHOS__)) || defined(__FreeBSD__)`）。改动最小、能编译过，但代价是跳过「全局只有一个 crypt_shared」的校验，于是 `_test_csfle_load_twice_fail` 必然断言失败——必须在 `test_package/MANIFEST.yml` 与 PR 的测试表里按用例记为未通过并写明系统能力原因，不能只写「未运行」。

## 禁止做法

| 做法 | 为什么禁止 | 后果 |
|---|---|---|
| 自己声明 `dlinfo` 继续用 | 符号在 libc.so 里根本不存在 | 编译期"通过"，运行期 undefined symbol 或崩溃 |
| 加 `-Wno-implicit-function-declaration` 压告警 | 只是消音 | `mcr_dll_path` 返回未初始化内容，csfle 单例校验静默误判 |
| 首选回退方案却不记录失败用例 | 掩盖了 1 个用例的真实状态 | 违反"通过率必须实跑数字"，审查 rule4 直接 FAIL |

## 适用性（为什么是「一类」而不是「一例」）

任何「运行时反查已加载 so 的路径」的代码都会遇到：crypt_shared/csfle 单例校验、插件按路径去重、
`dlopen` 多副本检测、热更新模块同名判定。它们在 glibc 上写 `dlinfo`，在 musl 上写
`handle == dlpi_addr`，两条路在 OHOS 上都不可用，统一改用 `dlsym + dladdr`。
