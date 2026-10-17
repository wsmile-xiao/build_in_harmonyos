# box64 0.4.4 适配笔记（HarmonyOS PC / aarch64）

## 交付形态

- **Conan 配方**：`archives/b/box64/0.4.4/`（cmake），源码 = 上游官方 tarball
  `v0.4.4`（sha256 `99c6de4f…c24029`），**10 个补丁**（`patches/`，全部由
  `refresh-patch --auto` 生成，见下「源码修改」）。
- **依赖**（ohpcd 制品仓，均有 OHOS binary）：`musl-fts/1.2.7`、`musl-obstack/1.2.3`。
- **可执行包**（R38）：`package_type=application` + `cpp_info.bindirs=["bin"]` +
  软件级 `archives/b/box64/commands.json`。
- **测试**：`test_package/`（R34 行为 6 断言 + R53 鸿蒙结构 14 断言；
  x86_64 ELF 由纯文本生成器 `make_x86_64_hello.py` 生成，不携带二进制资产）。

## 编译环境

- 构建系统：cmake 4.1.2（Conan 用 Unix Makefiles）+ GNU Make（hnp）
- 编译日期：2026-09-26
- 编译器：OHOS hnp clang 15（sysroot `ohos-sdk_26.0.0.18`，`--target=aarch64-linux-ohos`）
- 主机：HarmonyOS PC（aarch64，musl）；`/tmp` 只读 → 工作目录 `~/tmp`
- conan：2.29.1（OHOS 适配版）；profile `ci/conan/profiles/ohos-aarch64`

## 编译步骤

```bash
# 1) Conan 路径（CI/W3 同命令）
conan create archives/b/box64/0.4.4 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing --build="box64/*"

# 2) 裸参数本地构建（等价于配方 configure 参数；依赖由 find_library/find_path
#    或 BOX64_FTS_*/BOX64_OBSTACK_* 注入定位，无需任何手工链接 flag）
mkdir build && cd build
cmake -DARM64=ON -DARM_DYNAREC=ON -DNOGIT=ON -DCMAKE_BUILD_TYPE=Release \
      -DNOLOADADDR=OFF .. && make -j4
./box64 --version && ./box64 <最小 x86_64 ELF>
```

> 关键点：`-no-pie`、`.dynsym` 版本脚本（`{ local: *; }`）、`$ORIGIN/../lib`
> RUNPATH 均为 **CMakeLists 内的 OHOS 分支自动完成**（见下），配方不再需要
> `-DCMAKE_EXE_LINKER_FLAGS`，也不再依赖 `~/usr/local`（R49）。

## 遇到的问题与解决方案

### 编译期

| # | 问题 | 根因 | 解决方案（文件） |
|---|------|------|------------------|
| 1 | 缺 `M_ARENA_TEST`/`M_ARENA_MAX`/`M_MMAP_THRESHOLD` | glibc malloc 调优常量，musl 无 | 特征宏守卫（`src/os/os_linux.c`） |
| 2 | `PTHREAD_ERRORCHECK_MUTEX_INITIALIZER_NP` 未声明（signals.c 两处） | glibc-only 初始化宏 | `#ifdef` 守卫 + 回退 `PTHREAD_MUTEX_INITIALIZER`（`src/libtools/signals.c`） |
| 3 | `fts.h: No such file`（auxval.c/myalign.c/wrappedlibc.c） | OHOS libc 无 fts | Conan `musl-fts/1.2.7` + `find_path`/注入 `BOX64_FTS_INCLUDE_DIR` |
| 4 | `must use 'struct' tag to refer to type '__sigset_t'` | musl 只有 `typedef struct __sigset_t {...} sigset_t;` | `__OHOS__` 下 `typedef sigset_t __sigset_t;`（`src/include/mysignal.h`） |
| 5 | `_pthread_cleanup_push/pop` 声明冲突、`pthread_t`→`unsigned long` 类型错、9 个 GNU pthread 扩展在 sysroot 缺符号 | OHOS musl 签名差异；sysroot import 库不导出扩展 | `__OHOS__` 适配块 + `dlsym(RTLD_NEXT)` 懒加载（缺则 ENOSYS）+ NULL 守卫（`src/libtools/threads.c`） |
| 6 | `redefinition of 'sockaddr_storage'`（x86syscall.c） | `<linux/net.h>`→`<linux/socket.h>` 与 `<sys/socket.h>` 双定义（工具链不定义 `__MUSL__`） | `__OHOS__` 下跳过 `<linux/net.h>`（`src/emu/x86syscall.c`） |
| 7 | `obstack.h: No such file` | OHOS libc 无 GNU obstack | Conan `musl-obstack/1.2.3` + 注入 `BOX64_OBSTACK_*` |
| 8 | `error.h` 缺失；`error()/error_at_line()` 符号缺失 | glibc GNU error API，musl 无 | `__OHOS__` 守卫 + 最小 GNU 兼容实现（`src/wrapped/wrappedlibc.c`） |
| 9 | musl LFS64 宏（`stat64`→`stat` 等）重写 wrapper 结构体成员名；`__compar_d_fn_t` 未定义；TID 缓存私有布局 | OHOS musl 头文件差异 | `wrappercallback.h` 前后 `#undef/#define` 一批 *64 宏；`__compar_d_fn_t` 定义；TID 缓存走 ANDROID 同款 no-op（`src/wrapped/wrappedlibc.c`） |
| 10 | `RTLD_DL_SYMENT/RTLD_DL_LINKMAP` 未声明 | 原 fallback 仅 `#ifdef ANDROID` | 扩展为 `#if defined(ANDROID) || defined(__OHOS__)`（`src/wrapped/wrappedlibdl.c`） |

### 链接期

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 11 | 未定义符号：`__libc_malloc/free/calloc/realloc/memalign`、`dlinfo`、`glob64`、`qsort_r`、`scandirat(64)`、`obstack_vprintf`、`exp10/exp10f/exp10l`、`isnanf/isinff` | sysroot import libc 不导出（部分设备 runtime 有） | `wrappedlibc.c` OHOS 块：`__libc_*` 用 `dlsym(RTLD_NEXT)` 解析真实分配器；`dlinfo/glob64` 懒加载、缺则 ENOSYS；`qsort_r/scandirat/scandirat64` 本地实现；`exp10*`→`pow*`；`isnanf/isinff`→builtin；`libtools/obstack.c` 本地 `obstack_vprintf` |

### 运行期（关键）

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 12 | 任何参数启动都在 main 前 SIGSEGV（139） | box64 定义的 17 个宿主同名符号（`malloc/mmap/dlopen` 族）被导出进 `.dynsym` → OHOS musl libc 自身 PLT 解析命中**尚未初始化**的 wrapper → ld.so 阶段崩溃 | CMakeLists OHOS 分支在配置期生成版本脚本 `box64-ohos-hide.map`（`{ local: *; }`）并 `-Wl,--version-script=…`；同时 `-no-pie`（ET_EXEC）稳定化。**均已固化进源码**，不再依赖外部 map 文件/链接 flag |
| 13 | 隐藏后崩在 `init_malloc_hook()` 的 `dlsym(RTLD_NEXT,"malloc_usable_size")` | `GetNativeSymbolUnversioned()` 的 `dl_iterate_phdr_findsymbol` 只在对象有 `DT_VERDEF` 时搜索；**musl 无符号版本** → 恒 NULL → 调 NULL | `src/elfs/elfloader.c`：`__OHOS__` 下按名查找无版本符号 |

### 配方/工具链层（S2 新增，均是 conan 构建的坑）

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 14 | conan 构建产物无 Dynarec（`Box64 v0.4.4`，缺 arm64/nogit/with Dynarec） | box64 的 `option()` 链在 `project()` **之前**执行；Conan 工具链（`tc.variables` CACHE STRING）在 `project()` 才被读取 → 被 `option()` 默认值 `OFF` 覆盖（实测 `ARM64:BOOL=OFF`） | 配方 `cmake.configure(cli_args=["-DARM64=ON","-DARM_DYNAREC=ON","-DNOGIT=ON","-DNOLOADADDR=OFF"])`（与裸构建同形；实测 `C_DEFINES=-DARM64 -DDYNAREC -DNOGIT`） |
| 15 | 包内 `bin/box64` 有 `NEEDED libfts.so.0` 但无 RUNPATH，脱离 conan 环境无法启动 | CMake 无 `Platform/HarmonyOS` 模块 → `CMAKE_SHARED_LIBRARY_RUNTIME_C_FLAG` 为空 → `INSTALL_RPATH`/`BUILD_RPATH` 静默失效（`cmake_install.cmake` 无 RPATH 块） | OHOS 分支显式 `target_link_options(${BOX64} PRIVATE "LINKER:-rpath,\$ORIGIN/../lib")`；并随包携带 `libfts.so.0`/`libobstack.so.1` |
| 16 | `cmake --install` 写 `/usr/lib/...`、`/etc/...` 失败（Conan 包不可写系统路径） | 上游硬编码绝对安装路径，`--prefix` 不重定位绝对 DESTINATION | OHOS 分支：x64lib → `lib/box64-x86_64-linux-gnu`、`box64.conf`/`box64.box64rc` → `share/box64`（仍随包分发） |
| 17 | `cmake --install` 重写 RUNPATH 破坏 OHOS 代码签名 | OHOS 要求签名 ELF；安装期 `file(RPATH_CHANGE)` 改字节 | 配方 `package()` 安装后对 **aarch64** ELF（bin/ 与 lib/ 顶层）重签名；x86_64 guest payload 不签 |

## 源码修改（R2：补丁由 `refresh-patch --auto` 生成，禁止手写）

补丁总数 **10**；`conandata.yml` 每项均带 `strip: 1`（refresh-patch 产出
`--- a/…` / `+++ b/…` 路径，Conan `apply_conandata_patches` 默认 strip=0）。
`manifest.yaml` 的 `patch_classification` 已逐项标注 `guard`。

| 补丁 | 文件 | 修改内容 | guard |
|------|------|----------|-------|
| 0001 | `CMakeLists.txt` | OHOS 目标检测（Conan `CMAKE_SYSTEM_NAME=HarmonyOS` / `__OHOS__` 编译探测）；`BOX64_FTS_*`/`BOX64_OBSTACK_*` 注入接收 + `find_library/find_path` 回退；版本脚本生成 + `-no-pie` + 显式 `LINKER:-rpath,\$ORIGIN/../lib`；x64lib/conf 相对安装路径 | `CMAKE_SYSTEM_NAME=HarmonyOS / __OHOS__` |
| 0002 | `src/elfs/elfloader.c` | musl 无 `DT_VERDEF`：按名查找无版本符号 | `__OHOS__` |
| 0003 | `src/emu/x86syscall.c` | 跳过 `<linux/net.h>`（sockaddr_storage 重定义） | `__OHOS__` |
| 0004 | `src/include/mysignal.h` | `typedef sigset_t __sigset_t;` | `__OHOS__` |
| 0005 | `src/libtools/obstack.c` | 本地 `obstack_vprintf`（musl-obstack 未提供） | `__OHOS__` |
| 0006 | `src/libtools/signals.c` | `PTHREAD_ERRORCHECK_MUTEX_INITIALIZER_NP` 回退 | 特征宏 |
| 0007 | `src/libtools/threads.c` | 9 个 pthread 扩展 dlsym 懒加载；cleanup 适配；`iFli_t`→`pthread_t`；NULL 守卫 | `__OHOS__` |
| 0008 | `src/os/os_linux.c` | mallopt 常量守卫 | `M_ARENA_TEST` 等 |
| 0009 | `src/wrapped/wrappedlibc.c` | error() 兼容实现、*64 宏环绕、qsort_r/scandirat、ctype dlsym、TID no-op、链接兜底（__libc_*、dlinfo、glob64、exp10*、isnanf/isinff） | `__OHOS__` |
| 0010 | `src/wrapped/wrappedlibdl.c` | `RTLD_DL_*` fallback 扩展到 OHOS | `ANDROID \|\| __OHOS__` |

> **R8 例外说明**：本包是 musl 宿主适配，上游无 OHOS 支持；所有 `__OHOS__`
> 守卫均带实质逻辑（新增平台分支、按名查找、真实兼容实现，无空壳 stub），
> 非鸿蒙平台路径不受影响。按 R8 约定，提交 PR 时需在正文说明理由并使用
> `OHC_PREFLIGHT=0`（PF5 平台宏闸）。
>
> **诊断方法（已移除临时代码）**：首建崩溃期曾用 `BOX64_OHOS_TRACE` 环境变量
> 检查点 + `LD_PRELOAD` 信号探针定位（OHOS 禁 ptrace，gdb/lldb 不可用）；
> 定位完成后临时 trace 已全部移除，保持补丁最小化。

## Conan 配方要点

- **依赖注入（R49）**：`generate()` 由 `self.dependencies` 取
  `musl-fts`/`musl-obstack` 的精确路径注入 `BOX64_FTS_LIBRARY/INCLUDE_DIR`、
  `BOX64_OBSTACK_LIBRARY/INCLUDE_DIR`；不引用 `/usr/local`，不使用共享前缀。
- **配置参数**：`-DARM64=ON -DARM_DYNAREC=ON -DNOGIT=ON -DNOLOADADDR=OFF`
  经 `cmake.configure(cli_args=[…])` 传入（原因见问题 14）。
- **打包自包含**：把依赖的 `libfts.so.0`、`libobstack.so.1`（按 SONAME 命名，
  字节复制保留依赖包签名）复制进 `<pkg>/lib`，配合 `$ORIGIN/../lib` RUNPATH
  实现脱离 conan 环境直接运行（W3 L2 smoke 即直接执行包内 bin/box64）。
- **签名**：`package()` 用 `llvm-objcopy --remove-section .codesign` +
  `binary-sign-tool sign -selfSign 1` 重签 aarch64 ELF（bin/box64、lib 顶层
  compat 库）；x86_64 guest payload（x64lib、tests/box64-bash）跳过。
- **并行度**：`cmake.build(build_tool_args=["-j4"])`（设备与他人重编译并行，
  统一 -j4）。
- **package_info**：`package_type="application"`、`cpp_info.bindirs=["bin"]`、
  `cpp_info.libs=[]`（R38 CLI 包）。

## 验证结果

```bash
# M1 裸参数构建（Unix Makefiles + make -j4）
$ file build/box64
ELF 64-bit LSB executable, ARM aarch64, interpreter /lib/ld-musl-aarch64.so.1
Type: EXEC (ET_EXEC); NEEDED=libc.so; sha256=28ab0df3…caac5（裸构建，静态 fts）

# M2/M3
$ ./box64 --version
Box64 arm64 v0.4.4 nogit with Dynarec built on Sep 26 2026 14:38:54   # rc=0
$ ./box64 hello_x86_64
hello from x86_64                                                      # rc=0

# conan create（含 test_package：R34 6 断言 + R53 14/14）
$ conan create archives/b/box64/0.4.4 -pr:h=… -pr:b=… --build=missing --build="box64/*"
 → CREATE_RC=0
包内 bin/box64：ET_EXEC，RUNPATH=$ORIGIN/../lib，
NEEDED=libc.so/libfts.so.0/libobstack.so.1，.codesign 存在，
sha256=f19fc74a…84881（36MB 包）

# 独立运行（清空 LD_LIBRARY_PATH）
$ env -u LD_LIBRARY_PATH ~/.conan2/p/…/p/bin/box64 --version   # rc=0
$ env -u LD_LIBRARY_PATH ~/.conan2/p/…/p/bin/box64 hello_x86_64  # hello from x86_64, rc=0

# conan-verify：G0/G1/G2/G3/G4 PASS（L2/L4/L5 因框架缺陷 #13 跳过，
#   手工 L4 证据 reports/l4-manual-evidence.txt：NX/GNU_RELRO/BIND_NOW/canary 正常，
#   PIE=disabled（ET_EXEC，属 OHOS 稳定化预期，L4 仅非阻断警告））
# 全新 CONAN_HOME=~/tmp/ci-sim-box64 复现：CREATE_RC=0（依赖从 ohpcd 重新下载）
# W3 本地 CI（finish）：exit_code=0，.ci-result.json + reports/w3-local-ci.log
```

### R51 上游测试三步法（如实申报）

- **清点**：`ctest -N` = **34** 项（tests/ CMakeLists；test01–test35，14 号用例
  上游注释；BOX32=OFF/ANDROID=OFF）。guest = 预编译动态 glibc x86_64 ELF。
- **实跑**：`ctest --output-on-failure --timeout 60` → **N=34 / N′=34 / 通过 0**。
- **不可跑根因**（34 项统一，平台限制非本包缺陷）：musl 宿主无法 wrap glibc
  guest（`libresolv.so.2` 缺失、`__libc_start_main` 解析失败 → SIGSEGV）；设备
  无 x86_64 glibc 运行库；上游本就未支持 musl 宿主（#1027/#2012）。
- **替代真实验证**：test_package 内生成 177B 静态 x86_64 ELF 并实跑（R34），
  外加 R53 结构断言 14 项。详见 `reports/test-report.md`。

## 依赖版本

- OHOS SDK 26.0.0.18（hnp clang 15）；cmake 4.1.2；conan 2.29.1
- musl-fts/1.2.7、musl-obstack/1.2.3（ohpcd，OHOS binary，2026-07-30）

## 注意事项与残留风险

1. **R8/PF5**：补丁含 `__OHOS__` 守卫（musl 宿主适配必需）→ submit 需按 R8
   例外处理（PR 正文说明 + `OHC_PREFLIGHT=0`）；`manifest.yaml` 已留痕。
2. **PF8/R38 ⟷ PF9 已知矛盾**：CLI 包在 `archives/b/box64/commands.json`
   （4 段路径）会被 PF9（要求 ≥5 段）拦截 —— 与 leave/kcoreaddons5/kconfig5/
   libnfs-tools 同因，属框架缺陷 #7/#24，提交期用 `OHC_PREFLIGHT=0` 留痕。
3. glibc/musl 动态 guest、图形 guest 不在本阶段验证范围；如需扩展属独立立项。
4. `~/usr/local` 仅为探索期依赖，**配方不引用**（R49 已遵守）；裸构建的依赖
   定位依赖 CMake `find_library/find_path` 或配方注入变量。
5. 诊断用 `BOX64_OHOS_TRACE` 临时代码已移除（方法见「源码修改」说明）。
---

**编译结束**: 2026-09-26 15:37
**最终状态**: published
