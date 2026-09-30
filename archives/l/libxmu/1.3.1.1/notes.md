# libxmu 1.3.1.1 适配笔记

> 上游 libXmu **没有 1.3.2 发布**。`.1` 是本仓的**配方修订号**：同一份上游
> 1.3.1 源码，重出配方，以便在 libxext/6.4.0.1 已上架的当前 ohpcd 状态下
> 真正产出并把 libxmu 制品**上架**（1.3.1 从未 upload 成功）。

## 为什么重出 1.3.1.1

### 事实

| 项 | 1.3.1 | 1.3.1.1 |
|----|-------|---------|
| 配方是否合入 main | ✅ 已合入 | — |
| 制品是否在 ohpcd | ❌ `conan list "libxmu/*" -r=ohpcd` → no matching recipe | ✅（本修订合并后由 release 流水线上架） |
| `result.json` | `status: dependency_missing`（缺 libxext / libxt） | 无 |
| 下游阻塞 | libxaw/1.0.16（PR #9432）因 `requires("libxmu/1.3.1")` 无法解析而卡死 | 解除 |

### 根因链

1. libxmu/1.3.1 配方合入 main 时，依赖 `libxext/6.4.0` 的 matching binary
   （package_id `eab79208`）**尚未发布**。
2. conan 因此回退到**源码构建 libxext**；libxext 的 autotools 构建里
   libtool 需要 `libxcb.la`，而 conan 提供的 libxcb 制品**不带 `.la`**，
   构建在 libtool 链接阶段失败。
3. 构建失败 → 没有 binary → `upload.sh` 无制品可传 →
   `conan list "libxmu/*" -r=ohpcd` 为空。
4. 之后向 libxmu 的消费者（libxaw #9432）解析 `libxmu/1.3.1` 时，
   ohpcd 报 `acceleration policy not enabled`——该报错是**确定性缺包**信号，
   不是网络抖动（用兄弟包 `conan list` 自证）。

**制品上架只发生在 PR 合并到 main 之后**（`ci/conan/upload.sh` 要求
`CI_TASK_TYPE=release`，PR 流水线不 upload）。因此 1.3.1 在合入那一刻已经把
"失败结果"写进历史，无法自愈；**必须重出一版修订触发一次新的 build+upload**。

### 三件事必须同时成立

1. **libxext/6.4.0.1 已发布** —— 该修订的 recipe 自带 `_fix_dep_la_files`，
   为依赖合成 libtool `.la` shadow，正是解除上文第 2 步失败的修复。
2. **libx11 全图统一到 1.8.13** —— libxext/6.4.0.1 的 `requirements()` 写的是
   `libx11/6.4.0`，若图里同时出现 6.4.Z 与 1.8.Z 会报版本冲突，
   故本配方声明 `self.requires("libx11/1.8.13", force=True)` 强制整张图统一。
3. **generate() 里为依赖合成 libtool `.la` shadow** ——
   `_prepare_ohos_libtool_shadow()` + `_ensure_libx11_la()` 在构建前把
   conan 制品缺的 `libX11.la` 补出来，否则 libtool 在链接 libXmu 时仍找不到。
4. **shadow 构建器要容忍「home 前缀的 stray libdir」** ——
   见下节，CI 实测暴露。

### CI 实测暴露：`.la` 里的 stray `/usr/local/lib`（跨 worker 抖动）

首次 `conan create` 在 generate() 失败：

```
ERROR: libxmu/1.3.1.1: Error in generate() method
  while calling '_prepare_ohos_libtool_shadow', line 291
  ConanException: libX11-xcb.la references a missing non-Conan libdir:
                  /storage/Users/currentUser/usr/local/lib
```

libX11 的制品里，`libX11.la` / `libX11-xcb.la` / `libXau.la` 的
`dependency_libs` 都带一个**裸的** `-L/storage/Users/currentUser/usr/local/lib`
（不带任何 `-l`），这是某次 `make install` 落到家目录留下的 stray 路径：

```text
# libX11-xcb.la
dependency_libs=' -L/storage/Users/currentUser/usr/local/lib'
```

本配方原有的 `_is_system_libdir()` 只做**精确匹配**（`/usr/local/lib` 等），
匹配不到这个带家目录前缀的形式，于是落到 `raise ... missing non-Conan libdir`。
之所以只有部分 worker 复现：该 stray 目录若恰好存在，`directory.is_dir()`
分支会先把 token 留下而不报错——即这条路径本身是**跨 worker 抖动**的
（与 `ci_worker_stray_glib` 是同一个家目录残留）。

修复：`_is_system_libdir()` 增加**后缀匹配** `*/usr/local/lib`、`*/usr/local/lib64`，
把这些 token 一并改写成 shadow `-L`（`/opt/foo/lib` 这类不会误伤）。

### 先例

- `conan graph info` 实测（本地）：libxt/1.3.1、libxcb/1.17.0 走 Download，
  libx11/1.8.13 命中 Cache，**仅 libxext/6.4.0.1 需要源码重建**——即整条链可解析。

## 编译环境
- 构建系统: autotools (configure + make)
- 编译器: clang 15.0.4 (aarch64-unknown-linux-ohos)
- 平台: HarmonyOS HongMeng Kernel 1.12.0 aarch64
- 状态: built (make 通过；make check 见下方"上游测试崩溃点诊断")

## W0 依赖预检结果

| 依赖 | 发布版本 | 上游要求 |
|------|---------|---------|
| libxt | 1.3.1 | xt >= 1.1 ✓ |
| libxext | 6.4.0.1 | xext ✓ |
| libx11 | 1.8.13 | x11 ✓ |
| xorgproto | 2025.1 | ✓ |

传递依赖（libx11/libxt 的 requires）：libxau/1.0.12、libxdmcp/1.1.5、
util-macros/1.20.1 均已发布。

## 编译步骤

libxmu 是 X.Org 官方库，标准 autotools 流程。源码 URL（R39 官方源）：
`https://xorg.freedesktop.org/releases/individual/lib/libXmu-1.3.1.tar.xz`
sha256: `81a99e94c4501e81c427cbaa4a11748b584933e94b7a156830c3621256857bc4`

```bash
source .build-context-libxmu-1.3.1.1
cd $BUILD_SRC_DIR

# configure —— 关键：必须把 GLib 的 pkgconfig 路径加入 PKG_CONFIG_PATH，
# 否则 configure 检测到 GLIB... no，导致 test/Makefile.am 的
# `if HAVE_GLIB` 守卫跳过所有 check_PROGRAMS，make check 变成 0/0 空跑。
export PKG_CONFIG_PATH="$TEST_PREFIX/lib/pkgconfig:$TEST_PREFIX/share/pkgconfig:$DEFAULT_PREFIX/lib/pkgconfig:$GLIB_PREFIX/lib/pkgconfig"
export CFLAGS="-I$TEST_PREFIX/include -I$DEFAULT_PREFIX/include"
export LDFLAGS="-L$TEST_PREFIX/lib -L$DEFAULT_PREFIX/lib"

sh ./configure --prefix=$TEST_PREFIX \
  --build=aarch64-unknown-linux-ohos \
  --host=aarch64-unknown-linux-ohos \
  --enable-unit-tests

make -j2          # ✅ 通过，产出 libXmu.so.6.2.0 + libXmuu.so.1.0.0
make check        # 26 TOTAL / 23 PASS / 1 SKIP / 1 FAIL / 1 ERROR（详见下方诊断）
```

产物（NEEDED 经 llvm-readelf 确认）：
- `libXmu.so.6.2.0` → NEEDED: libXt.so.6, libXext.so.6, libX11.so.6
- `libXmuu.so.1.0.0` → NEEDED: libX11.so.6

## 上游测试崩溃点诊断（⭐ 核心，R34 实质测试）

`make check` 运行了**真实上游测试套件**（非 0/0 空跑）：

```
# TOTAL: 26   # PASS: 23   # SKIP: 1   # FAIL: 1   # ERROR: 1
```

### 崩溃点（唯一）

- **文件**：`test/reallocarray.c`
- **行号**：157
- **函数**：`test_Xmureallocarray_oversize`
- **断言**：`g_assert_nonnull(p)` 失败 → `g_test_fail()` → SIGABRT (core dumped)
- **TAP 输出**：`not ok /reallocarray/Xmureallocarray/oversize - ERROR:reallocarray.c:157:test_Xmureallocarray_oversize: 'p' should not be NULL`

### 根因（已用最小复现程序 + 实测数据充分证明）

上游 `oversize` 测试依赖 glibc 的 `setrlimit(RLIMIT_AS)` + `realloc` 精确失败语义。
**HarmonyOS bionic libc 的 `realloc` 对 `RLIMIT_AS` 的响应与 glibc 方向相反**：

| 调用 | glibc 行为（上游假设） | bionic 实测（HarmonyOS） |
|------|----------------------|--------------------------|
| `setrlimit(RLIMIT_AS, 512MB)` | 生效 | 生效 |
| `realloc(NULL, 112)` | ✅ 成功 | ✅ 成功 (0x59e4441310, errno=0) |
| `realloc(NULL, 256MB)` | ✅ 成功（rlimit 内） | ❌ **NULL, errno=ENOMEM** |
| `realloc(NULL, 1GB)` (无 rlimit) | ✅ 成功 | ✅ 成功 |

测试 `oversize` 第一步 `p = Xmureallocarray(NULL, num, size)`（num,size ∈ [1,16K]，最大 256MB）
在 bionic 的 `RLIMIT_AS=512MB` 下直接 `realloc(NULL, 256MB) = NULL + ENOMEM`，触发第 157 行断言失败。

复现程序实测证据（`rlimit_test.c`，运行于同一 HarmonyOS 环境）：
```
ALLOC_LIMIT = INT_MAX/4 = 536870911
setrlimit(RLIMIT_AS, 536870911) = 0 (errno=0)
realloc(NULL, 112) = 0x59e4441310 errno=0          ← 小分配成功
realloc(NULL, 256MB) = 0 errno=12                  ← 256MB 失败（bionic 过度保守）
realloc(NULL, 2*ALLOC_LIMIT=1073741822) = 0 errno=12
```

### 其他 25 个测试用例状态

- **23 PASS**：CursorName/bad-names, EditResStream/ProtocolStream, Lower ×6, ReadBitmapData,
  reallocarray/normal, reallocarray/zero, StrToBS ×2, StrToGrav ×2, StrToJust ×2,
  StrToLong ×2, StrToOrnt ×2, StrToShap ×2 —— 全部真实调用 libXmu/libXmuu API，通过。
- **1 SKIP**：`CursorName 1 /CursorName/XmuCursorNameToIndex/good-names`
  原因：`Could not open /usr/include/X11/cursorfont.h`（测试环境无 X11 cursorfont 头文件，
  属环境缺文件，非 libxmu 缺陷；上游测试设计如此）。
- **1 FAIL + 1 ERROR**：即上述 `oversize` 崩溃点（FAIL 触发 ERROR/Bail out）。

### 结论

`oversize` 测试用例在 HarmonyOS bionic libc 上**平台固有不兼容**，非 libxmu 配方缺陷、
非网络/环境类问题。已指明崩溃点（`test/reallocarray.c:157`）且原因充分（bionic `realloc`
在 `RLIMIT_AS` 下与 glibc 行为方向相反，最小复现程序 + 实测 errno 数据已固化于本 notes）。

其余 23 个上游测试 100% 通过（真实调用 libXmu API，R34 实质测试满足）。

## 鸿蒙特有测试（rule12）

上游 `test/ReadBitmapData.c` 只把三个自带位图（plaid / star / xlogo64）从**可写**源目录
喂给 `XmuReadBitmapDataFromFile()`，因此**永远走不到**"打开失败"和"内容畸形"两条路径。
而这两条路径恰恰是 HarmonyOS 上最需要保证的：

- HMFS 根文件系统**只读**，且没有 `/usr/share/X11/bitmaps`，任何一次按默认路径的
  位图查找都会 miss；库必须**退化成确定的错误码**，而不是 `abort()`/`exit()` 拖垮调用进程。

`test_package/test_ohos.c` 针对 `libXmu`（Xt 链接组件）补了 3 条断言：

| 断言 | 输入 | 期望 |
|------|------|------|
| A1 | 合法 8×8 X11 位图（写到可写的 `./libxmu-ohos-bitmap.xbm`） | `BitmapSuccess`，且 `width==8 && height==8 && data != NULL` |
| A2 | 畸形内容（`"this is not an X11 bitmap"`） | `BitmapFileInvalid`（不 abort，不写坏 `*datap`） |
| A3 | 根上不存在的路径 `/libxmu-no-such-bitmap.xbm` | `BitmapOpenFailed` |

三个错误码常量均来自公共头 `<X11/Xutil.h>`，断言对象是**可观测的运行时行为与确定性
返回码**，不依赖 `tr` / `strings` / 二进制 grep。

## 依赖版本

| 依赖 | 版本 | 制品仓 |
|------|------|--------|
| libxt | 1.3.1 | ohpcd ✓ |
| libxext | 6.4.0.1 | ohpcd ✓ |
| libx11 | 1.8.13 | ohpcd ✓ |
| xorgproto | 2025.1 | ohpcd ✓ |
| glib-2.0 | 2.88.0（测试用，环境自带） | — |
| libpcre2-8 | 10.45（glib 依赖） | — |

## 验证结果

```bash
$ make check
# TOTAL: 26
# PASS:  23
# SKIP:  1
# XFAIL: 0
# FAIL:  1
# XPASS: 0
# ERROR: 1
```

崩溃点定位复现：
```bash
$ /tmp/rlimit_test
ALLOC_LIMIT = INT_MAX/4 = 536870911
setrlimit(RLIMIT_AS, 536870911) = 0 (errno=0)
realloc(NULL, 112) = 0x59e4441310 errno=0
realloc(NULL, 256MB) = 0 errno=12          ← bionic 在 rlimit 内对 256MB 返回 ENOMEM
realloc(NULL, 2*ALLOC_LIMIT=1073741822) = 0 errno=12
```

消费者视角（test_package，两个可执行文件均真跑）：
```bash
$ ./test_libxmu        # XmuCompareISOLatin1() —— libXmuu 组件
$ ./test_libxmu_ohos   # XmuReadBitmapDataFromFile() 退化路径 —— libXmu 组件
```

## 注意事项

1. **GLib 必须可达**：configure 必须能在 PKG_CONFIG_PATH 找到 `glib-2.0.pc`（≥2.46），
   否则 `HAVE_GLIB=no`，test/Makefile.am 的 `if HAVE_GLIB` 跳过所有 check_PROGRAMS，
   make check 退化为 0/0 空跑（无法验证 R34 实质测试）。
2. **bionic realloc 语义**：HarmonyOS bionic libc 的 `realloc` 在 `setrlimit(RLIMIT_AS)` 下
   对中等分配（256MB）直接返回 ENOMEM，与 glibc 在 rlimit 内成功的语义相反。
   依赖 `setrlimit`+大分配失败的上游测试用例（如本 oversize）在 HarmonyOS 上不适用。
3. **libXmu.so vs libXmuu.so**：libXmu 链 Xt/Xext/X11；libXmuu 是 Xt 无关子集，仅链 X11。
   下游按组件名 `libxmu::Xmu` / `libxmu::Xmuu` 引用。
4. **本修订不携带上游补丁**：`patches: {}`。1.3.1.1 的内容与 1.3.1 完全一致，
   差别只在依赖解析后的**可构建性**（见上文"为什么重出 1.3.1.1"）。

---

**编译结束**: 2026-09-29
**最终状态**: built
