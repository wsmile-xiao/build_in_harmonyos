# skia 2.88.9 — HarmonyOS PC 适配笔记

上游：`github.com/mono/skia` @ **`4bed689c9c9eb77a120c6a9d54af6a572c85d1c2`**（2024-10-11）
版本口径：skia 本体无语义版本号；`2.88.9` = SkiaSharp binding 版本（`mono/SkiaSharp` tag `v2.88.9`），
其 `externals/skia` submodule（分支 `xamarin-mobile-bindings`）pin 到上述 commit。
源码 tarball sha256：`4dee89bef1406efd0f0c35ef24ec801a8f18ad37d6033d4360c2120eb858da0e`
构建系统：**GN + Ninja**（上游 standalone），非 CMake/autotools。

---

## 1. 构建方式（gn args）

```gn
gn gen out/ohos --args='
  is_debug=false
  is_official_build=false          # dev/standalone 语义：third_party 全部从源码编（不用系统库）
  cc="clang" cxx="clang++" ar="ar"
  skia_enable_gpu=true
  skia_use_gl=true
  skia_use_egl=true                # OHOS 无 X11；EGL 是唯一可构建的 GL 原生接口
  skia_use_x11=false
  skia_use_fontconfig=false
  skia_pdf_subset_harfbuzz=true    # PDF 字体子集走 harfbuzz，避开 sfntly 的 ICU C++ 头依赖
  skia_use_system_freetype2=false  # Linux 上上游默认「用系统 freetype」，OHOS 无 → 显式关
  skia_use_system_zlib=false ; skia_use_system_libpng=false ; skia_use_system_libjpeg_turbo=false
  skia_use_system_libwebp=false ; skia_use_system_harfbuzz=false ; skia_use_system_expat=false
  skia_use_system_icu=true         # OHOS sysroot 自带 libicu.so（ICU 72.1），头由补丁补齐
  extra_cflags=["-D__WORDSIZE=64",
                "-DSK_FONT_FILE_PREFIX=\"/system/fonts/\""]  # 前者 musl 无 __WORDSIZE；后者 OHOS 字体目录（见 §4）
'
```

构建目标（CPU 光栅化核心面「零裁剪」+ 可选上游测试二进制）：

```sh
# 默认（CI / 发包）：产品件 —— libskia.a（complete static lib，含全部第三方目标对象）
ninja -C out/ohos skia

# -o "&:with_tests=True" 时追加：上游测试二进制
ninja -C out/ohos skia dm tests      # dm = skia 自带 DM 测试驱动（tests 是源码集，随 dm 链接）
```

> **为什么 dm/tests 默认不建**：CI 只跑 `conan create` + `test_package`，不运行上游单测；
> 而 dm 的编译+链接会显著拉长流水线（本地实测见 §6 时间预算）。本地复现：
> `conan create . -o "&:with_tests=True"`。

## 2. GN 工具链自举

- skia 的 `bin/fetch-gn` 从 `chrome-infra-packages.appspot.com` 抓 **x86/glibc 预编译 gn**
  （OHOS 不可达；即便拿到也不可执行），`bin/gn` 在 tarball 内不存在。
- **解法（复用 perfetto 先例）**：用 OHOS clang 从 **gn 源码**自举，
  pin `0725d7827575b239594fbc8fd5192873a1d62f44`（GitHub 镜像 `JiauZhang/gn`）：

  ```sh
  export CC=clang CXX=clang++
  python3 build/gen.py --no-last-commit-position    # 源码 tarball 无 .git，需跳过 git describe
  printf '…LAST_COMMIT_POSITION "0 (unknown)"…' > out/last_commit_position.h
  ninja -C out                                      # → out/gn（musl + .codesign），rc=0
  ```
- **skia 特有坑**：`//:skia.h` action（`gn/find_headers.py`）会执行 **源码树内的 `//bin/gn`**
  （`gn desc`）。必须把自举出的 `gn` 也拷到 `<src>/bin/gn`，否则 `gen/skia.h` 步骤报
  `FileNotFoundError: <src>/bin/gn`。
- **CI 与本机的 python 差异（两处都要显式绕开，否则本地绿 / CI 红）**：

  | 症状 | 根因 | 处理 |
  |---|---|---|
  | `python3 build/gen.py` 抛 `KeyError: 'ohos'` | CI 的 `/data/app/bin/python3` 报 `sys.platform=='ohos'`，而 gn 的 `build/gen.py` 只识别 `linux/darwin/…` | 追加 `--platform=linux`（OHOS 宿主即 linux-like） |
  | `gn gen` 报 `//gn/BUILDCONFIG.gn:108 ... Command: python //gn/is_clang.py ... Returned 127` | gn 的 `exec_script` 默认执行**裸名 `python`**；CI worker 的 PATH 只有 `python3`，裸 `python` 不存在（rc=127） | `gn gen --script-executable=python3` |

- **ninja 并发上限（posix_spawn EAGAIN）**：CI（worker CI-030）实测 `ninja -C out gn`（gn 自举）报
  `ninja: fatal: posix_spawn: Resource temporarily unavailable` —— OHOS 上进程创建走 posix_spawn，
  并发过高即资源型 EAGAIN（本机 8 核、并发低，不复现）。处理：**两处 ninja 调用统一封顶**
  （gn 自举 `-j min(build_jobs,8)`；产品构建 `-j min(build_jobs,16)`），避免自造过载。

## 3. 第三方依赖供给（13 个包）

上游用 `DEPS` + depot_tools 的 `tools/git-sync-deps` 从 `*.googlesource.com` 抓源码（OHOS 全系不可达）。
改为 **GitHub 镜像 + 逐条核对同一 commit SHA**：

- `chromium.googlesource.com/external/github.com/<owner>/<repo>` 系 → GitHub 同名仓库（SHA 一致）。
- AOSP 专有仓（dng_sdk / piex / libjpeg_turbo / zlib）→ **`msft-mirror-aosp`**（同名 SHA 全部命中）。
- skia 自建仓 → 社区镜像（`libgifcodec` 用 `GoogleDepends/libgifcodec`）。
- **ICU 特殊处置**：chromium 的 ICU（`chromium/deps/icu@dbd3825b`）在 GitHub 无镜像命中
  （`unicode-org/icu` / `chromium/icu` / `msft-mirror-aosp/platform.external.icu` 全 404）→
  改用 **OHOS sysroot 系统 ICU**（`skia_use_system_icu=true`，`libicu.so` = ICU 72.1），
  并补齐与之一致的 **ICU 72.1 头**（`unicode-org/icu` tag `release-72-1`），见补丁 0002 与 §4-W2。

## 4. 移植/构建补丁（5 个）

| 补丁 | 根因 | 文件 |
|---|---|---|
| 0001 skia-pdf-harfbuzz-subset-modern-api | **harfbuzz 7.3 删除了旧 subset API**：`hb_subset_input_set_retain_gids` / `_set_drop_hints` / `hb_subset()` 已不存在（skia 这段代码自 2018 年起未随 HB 升级）→ 改用 flag API + `hb_subset_or_fail()` | `src/pdf/SkPDFSubsetFont.cpp` |
| 0002 icu-system-headers-ohos | OHOS sysroot 的 ICU 头是**公共 C API 子集**（`U_HIDE_INTERNAL_API`：`UText` 结构体与全部 C++ 头被裁掉），而 `modules/skshaper` 需要完整 `UText` → 补齐 ICU 72.1 头 + `U_DISABLE_RENAMING=1`（匹配系统库的 `u_*` 符号）+ 库名 `icuuc`→`icu` | `third_party/icu/BUILD.gn` |
| 0003 tests-ctest-duplicate-declaration | `tests/CTest.cpp` 中 `sk_paint_t* paint` **重复声明**（本快照的 bug，`tests` 目标编不过） → 删除重复行 | `tests/CTest.cpp` |
| 0004 harfbuzz-icu-script-bridge | fork 的 `SkShaper_harfbuzz.cpp` 调用 `hb_icu_script_to_script()`（实现于 `hb-icu.cc`，仅在 `HAVE_ICU` 下编译）→ 打开 `HAVE_ICU` 并加入 `hb-icu.cc` + 依赖 `//third_party/icu` | `third_party/harfbuzz/BUILD.gn` |
| 0005 gn-toolchain-python-path | skia 的 `gn/toolchain/BUILD.gn` 在 `copy`/`alink` 工具里**硬编码裸名 `python`**；CI worker 只有 `python3` → 链接首个静态库即 `python: command not found`（rc=127）。改用 gn 内置变量 **`$python_path`**（由 `gn gen --script-executable=python3` 驱动） | `gn/toolchain/BUILD.gn` |

另有 **2 个编译期适配开关**（非补丁，走 gn args 的 `extra_cflags`，不写进 `patches/`）：

- `-D__WORDSIZE=64` —— **musl 无 `__WORDSIZE`**（glibc `<bits/wordsize.h>` 专有），而
  `dng_sdk/source/dng_safe_arithmetic.h:115` 与 `libjpeg-turbo/jconfigint.h:33` 用它做 64 位判定；
  不定义会取 0 → 类型/尺寸判定错误。
- `-DSK_FONT_FILE_PREFIX="/system/fonts/"` —— 上游默认字体目录 `/usr/share/fonts/` 在 OHOS 不存在，
  系统字体实际在 **`/system/fonts`**；`SkFontMgr_custom_directory_factory.cpp` 顶部本就有
  `#ifndef SK_FONT_FILE_PREFIX` 守卫（上游预留的构建期注入点），故直接用构建期 `-D` 注入，
  **不在补丁中引入 `__OHOS__` 平台宏**（R8）。实测该目标编译产物内含字符串 `/system/fonts/`。

## 5. 关键环境事实（跨库通用，含对 perfetto 结论的修正）

- **`.codesign` 与 strip（修正 perfetto 的过度保守结论）**：

  | 命令 | `.codesign` 段 | 可执行 |
  |---|---|---|
  | `clang t.c -o t_plain` | 有 | ✅ |
  | `clang -s t.c -o t_stripped`（**链接期 strip**） | **有** | ✅ |
  | `strip t_plain2`（**独立 strip 工具**） | 段在但内容被破坏 | ❌ Permission denied |

  ⇒ skia `//gn:optimize` 的 `-s` **安全**，无需像 perfetto 那样置 `strip=""`。
- **OHOS 无 X11**：skia 的 GL 原生接口只有 `EGL`（`skia_use_egl=true`）；`glx` 分支需要
  `<X11/Xlib.h>`，`gpu_tool_utils` 的 `CreatePlatformGLTestContext_glx.cpp` 会直接编不过。
- **OHOS sysroot 的 ICU 头是裁剪版**（仅公共 C API；`UText` 内部结构体不存在）。
- `*.googlesource.com` 全系不可达；`github.com` / `codeload.github.com` / `msft-mirror-aosp` 可达。
- OHOS `/tmp` 为只读 erofs；`/data/local/tmp` 对普通用户不可写。

## 6. 上游测试实测（宿主侧，dm = skia 自带 DM 测试驱动）

命令（cwd = skia 源码根）：

```sh
./out/ohos/dm --config 8888 --src tests --resourcePath resources
# → 0 srcs * 1 sinks + 1445 tests == 1445 tasks
# → 24 failures
```

| 项 | 数值 |
|---|---|
| 全量用例（dm `--src tests`，CPU 配置 8888） | **1445** |
| 失败用例（有≥1 断言失败的 test） | **5** |
| 失败断言数 | 24 |
| 通过率（按用例） | **1440 / 1445 = 99.65%** |

### 未通过项逐条归因

| 测试 | 断言数 | 根因类 | 说明与证据 |
|---|---|---|---|
| `Geometry` | 8 | 编译器优化敏感（非适配引入） | `SkClassifyCubic` 三次曲线分类。**对照实验**：仅把 `SkGeometry.cpp` 换成 `-O1`（或 `-O3 -fno-strict-aliasing`）→ **8 个失败全部消失**；`-ffp-contract=off` 无效。⇒ OHOS clang 15 在 aarch64 `-O3` 下的代码生成/别名假设敏感性，与 OHOS 适配改动无关（适配改动仅涉 PDF/ICU/字体路径） |
| `OffsetSimplePoly` | 10 | 编译器优化敏感（非适配引入） | `SkOffsetSimplePolygon` 数值边界。**对照实验**：`SkPolyUtils.cpp` 换 `-O1` → **10 个失败全部消失**（`-fno-strict-aliasing` 无效）。同上 |
| `PathOpsSimplify` | 1 | 路径布尔运算结果差异 | `ExpectMatch::kNo` 的用例「**现在反而成功了**」（`failing test now succeeds`）——即结果比上游更"正确"，非崩溃/异常 |
| `LegacyMakeTypeface` | 4 | 字体环境 | 断言 `typeface{1,2,3}->isItalic()/isBold()`：需要系统字体提供 Italic/Bold **变体**，OHOS `/system/fonts` 内无对应族变体 |
| `Skottie_Shaper_ExplicitFontMgr` | 1 | 字体环境 | `fontmgr->fallbackCount() == 1ul`：期望字体管理器带 1 个 fallback；OHOS 自定义目录字体管理器无 fallback 配置 |

> 说明：判据为「有 ≥1 条断言失败的 test 记 1 个失败用例」。字体类失败在字体目录切到
> `/system/fonts`（构建期 `-DSK_FONT_FILE_PREFIX`，见 §4）后已从 105 条断言失败降到 24 条
> —— 这是本适配最有效的功能性改进之一。

### 时间预算（CI 3600 s 风险）

- 本地 `conan create`（默认只建 `libskia.a`）实测 wall = **3306 s（≈55 min）**：含源码解压、
  gn 自举（只建 `gn` 目标）、`gn gen`、`libskia.a`（1225 步）、打包、`test_package` 全流程。
  与 CI 默认 3600 s 预算相比余量约 294 s —— **已在 PR「需要评审委员会确认的问题」中标注为风险**。
- 上游测试二进制（dm/tests）**不默认构建**（见 §1），故不进 CI 路径。

## 7. 消费者验证（conan test_package，`conan create` 内自动执行）

- `test_package/consumer.cpp`（消费者测试）：编译并链接 `libskia.a` 的最小程序 ——
  光栅 surface 创建 / 立即模式绘制（矩形+路径描边+抗锯齿）/ 像素回读 / `SkPngEncoder` 编码 /
  `SkCodec` 解码
- `test_package/test.sh`（消费者用例）：10 条断言（见文件）
- `test_package/test_ohos.sh`（鸿蒙平台特有）：5 条断言（AArch64 ELF / `.codesign` / musl 解释器 / TMPDIR）

## 8. 打包要点（conan）

- `package_type = "static-library"`；产物 = `lib/libskia.a`（**complete static lib**，已含
  freetype/harfbuzz/libpng/libjpeg-turbo/libwebp/zlib/expat/dng_sdk/piex/libgifcodec 等目标对象）
  + `include/`（公共头，保持 skia 源码根相对布局，因 skia 头内部以 `include/core/...` 互相引用）。
- `package_info`：`includedirs=["include"]`（= 类 skia 源码根）、`libs=["skia"]`、
  `system_libs=["pthread","dl","m"]`。
- `with_tests` 选项默认关（见 §1）。

## 9. conan create 本地验证

```sh
cd archives/s/skia/2.88.9
conan create . -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing
# → CONAN_RC=0（wall = 3306 s）
#   test_package：consumer 运行通过；test.sh 10/10 PASS；test_ohos.sh 5/5 PASS
```
