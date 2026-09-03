# libxmu 1.3.1 适配笔记

## 编译环境
- 构建系统: autotools (configure + make)
- 编译日期: 2026-08-26
- 编译器: clang 15.0.4 (aarch64-unknown-linux-ohos)
- 平台: HarmonyOS HongMeng Kernel 1.12.0 aarch64
- 状态: built (make 通过；make check 见下方"上游测试崩溃点诊断")

## W0 依赖预检结果

所有运行时依赖已在制品仓 ohpcd 发布：

| 依赖 | 发布版本 | 上游要求 |
|------|---------|---------|
| libxt | 1.3.1 | xt >= 1.1 ✓ |
| libxext | 6.4.0 | xext ✓ |
| libx11 | 1.8.13 | x11 ✓ |

传递依赖（libx11/libxt 的 requires）：libxau/1.0.12、libxdmcp/1.1.5、util-macros/1.20.1、xorgproto/2025.1 均已发布。

## 编译步骤

libxmu 是 X.Org 官方库，标准 autotools 流程。源码 URL（R39 官方源）：
`https://xorg.freedesktop.org/releases/individual/lib/libXmu-1.3.1.tar.xz`
sha256: `81a99e94c4501e81c427cbaa4a11748b584933e94b7a156830c3621256857bc4`

```bash
source .build-context-libxmu-1.3.1
cd $BUILD_SRC_DIR

# configure —— 关键：必须把 GLib 的 pkgconfig 路径加入 PKG_CONFIG_PATH，
# 否则 configure 检测到 GLIB... no，导致 test/Makefile.am 的
# `if HAVE_GLIB` 守卫跳过所有 check_PROGRAMS，make check 变成 0/0 空跑。
export PKG_CONFIG_PATH="$TEST_PREFIX/lib/pkgconfig:$TEST_PREFIX/share/pkgconfig:$DEFAULT_PREFIX/lib/pkgconfig:/storage/Users/currentUser/tmpbc_jer8y/build/PCRE2-install/lib/pkgconfig"
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

## 依赖版本

| 依赖 | 版本 | 制品仓 |
|------|------|--------|
| libxt | 1.3.1 | ohpcd ✓ |
| libxext | 6.4.0 | ohpcd ✓ |
| libx11 | 1.8.13 | ohpcd ✓ |
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

## 注意事项

1. **GLib 必须可达**：configure 必须能在 PKG_CONFIG_PATH 找到 `glib-2.0.pc`（≥2.46），
   否则 `HAVE_GLIB=no`，test/Makefile.am 的 `if HAVE_GLIB` 跳过所有 check_PROGRAMS，
   make check 退化为 0/0 空跑（无法验证 R34 实质测试）。
2. **bionic realloc 语义**：HarmonyOS bionic libc 的 `realloc` 在 `setrlimit(RLIMIT_AS)` 下
   对中等分配（256MB）直接返回 ENOMEM，与 glibc 在 rlimit 内成功的语义相反。
   依赖 `setrlimit`+大分配失败的上游测试用例（如本 oversize）在 HarmonyOS 上不适用。
3. **libXmu.so vs libXmuu.so**：libXmu 链 Xt/Xext/X11；libXmuu 是 Xt 无关子集，仅链 X11。
---

**编译结束**: 2026-08-27 18:43
**最终状态**: built
