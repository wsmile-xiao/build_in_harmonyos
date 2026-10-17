# DRAFT-20006: 图形/文本栈（skia 类）在 OHOS 的适配模式（ICU 裁剪头 / EGL / /system/fonts / `__WORDSIZE`）

> 适用：把依赖 **ICU + freetype + harfbuzz + libpng/jpeg/webp** 的 2D 图形库（skia 及其下游、cairo、
> Qt 图形栈等）适配到 OHOS。四条独立事实，按命中项取用。

## A. sysroot 的 ICU 头是「公共 C API 子集」

### 症状

```text
modules/skshaper/src/SkUnicode_icu.cpp:144: error: variable has incomplete type 'UText'
modules/skshaper/src/SkUnicode_icu.cpp:144: error: use of undeclared identifier 'UTEXT_INITIALIZER'
third_party/externals/sfntly/.../subsetter_impl.cc: fatal error: 'unicode/unistr.h' file not found
```

### 根因

OHOS sysroot 的 `unicode/*.h` 只有 **公共 C API**（38 个头）：`utext.h` 里 `UText` **只有前向声明**
（内部结构体与 `UTEXT_INITIALIZER` 被裁），且**没有任何 C++ 头**（`unistr.h`/`normalizer2.h` 等）。
所以任何需要 `UText` 内部结构（harfbuzz 的 hb-unicode/hb-icu、SkShaper）或 ICU C++ API（sfntly）的代码都编不过。

### 修法

1. 取**与 sysroot `libicu.so` 同版本**的完整 ICU 头：`unicode-org/icu` 的 `release-<M>-<m>` tag，
   只要 `icu4c/source/{common,i18n}/unicode`（skia 用 72.1，与 sysroot `uvernum.h` 的
   `U_ICU_VERSION_MAJOR_NUM 72 / MINOR 1` 对齐），随配方附带并加 include 路径。
2. 定义 **`U_DISABLE_RENAMING=1`**：sysroot 的 `unicode/uconfig.h` 就是 `U_DISABLE_RENAMING 1`
   → 系统 `libicu.so` 导出的是**无后缀**的 `u_*` 符号（`nm -D` 可见 `T u_strlen`）。
   不关重命名，头会把 `u_strlen` 宏映射到 `u_strlen_72`，链接期全部找不到。
3. 系统库名是 **`libicu.so`**（不是 `libicuuc.so`）→ 上游构建脚本里的 `-licuuc` 要改成 `-licu`。

> 自检命令：`nm -D $SYSROOT/usr/lib/aarch64-linux-ohos/libicu.so | grep -c ' T u_'`；
> `grep -n U_DISABLE_RENAMING $SYSROOT/usr/include/unicode/uconfig.h`。

## B. 无 X11 → GL 原生接口只有 EGL

### 症状

```text
tools/gpu/gl/glx/CreatePlatformGLTestContext_glx.cpp:11: fatal error: 'X11/Xlib.h' file not found
```

### 根因

图形库在 Linux 上默认的 GL 原生接口是 **glx**。**只关 `skia_use_x11` 不够**：skia 的
`tools/gpu/gl/{glx,egl}/CreatePlatformGLTestContext_*.cpp` 选择逻辑是
`if (is_android || skia_use_egl) → egl; else if (is_linux) → glx` —— `is_linux` 在 OHOS 上仍为真。

### 修法

`skia_use_egl=true`。OHOS sysroot 提供 `EGL/`、`GLES2/`、`GLES3/` 头与 `libEGL.so`，
且其 `eglplatform.h` 用 `USE_X11` 守卫（而非上游 registry 版的 `__unix__`），不会去拉 X11。

## C. 系统字体在 `/system/fonts`

### 症状

dm 的首轮里字体相关用例大面积失败（105 条断言），如 `FontMgr_Font`、`TextBlob_iter`、
`LegacyMakeTypeface`、`DrawText_dashout`、`Skottie_Shaper_*`。

### 根因

`SkFontMgr_custom_directory_factory.cpp` 的默认目录是 `/usr/share/fonts/`（OHOS 不存在）。
OHOS 的系统字体在 **`/system/fonts`**。

### 修法

该文件有 `#ifndef SK_FONT_FILE_PREFIX` 守卫 → 加 OHOS 分支（或 `-DSK_FONT_FILE_PREFIX`）：

```c
#  elif defined(__OHOS__)
#    define SK_FONT_FILE_PREFIX "/system/fonts/"
```

> 实测效果：skia `dm --config 8888 --src tests` 的失败断言数 **105 → 24**（1445 用例）。

## D. musl 无 `__WORDSIZE`

### 症状

```text
third_party/externals/dng_sdk/source/dng_safe_arithmetic.h:118:45:
error: cannot initialize a parameter of type 'long long *' with an rvalue of type 'std::int64_t *' (aka 'long *')
```

### 根因

`__WORDSIZE` 是 glibc `<bits/wordsize.h>` 专有；musl 没有 → 第三方代码
`#if __WORDSIZE == 64` 取 0 → 走 32 位分支 → 类型/尺寸判定错误。
（本例：`__builtin_smulll_overflow` 要 `long long*`，而 `int64_t` 在 LP64 下是 `long`。）

### 修法

`extra_cflags = ["-D__WORDSIZE=64"]`。musl 自身不使用该宏（sysroot 仅
`bits/{reg,user}.h` 引用且不参与这类构建），全局定义安全。
自检：`clang -dM -E -x c /dev/null | grep __SIZEOF_LONG__`（= 8 即 LP64）。

## 附：两个连带项（fork/版本漂移）

- **`hb_icu_script_to_script` undefined symbol**：fork 的 SkShaper 调用了实现于
  `hb-icu.cc` 的函数，而上游 harfbuzz 目标未开 `HAVE_ICU`（该文件在 `unused_sources` 里）
  → 链接期未定义。修法：`defines += ["HAVE_ICU"]` + 把 `hb-icu.cc` 加进 sources
  + `deps += ["//third_party/icu"]`（其只用 ICU C API，A 的头即可满足）。
- **harfbuzz ≥8 删除旧 subset API**：`hb_subset_input_set_retain_gids` /
  `hb_subset_input_set_drop_hints` / `hb_subset()` 已不存在 → 旧图形库代码改用
  flag API：`hb_subset_input_set_flags(..., hb_subset_input_get_flags(...) | HB_SUBSET_FLAGS_RETAIN_GIDS)`、
  `... & ~HB_SUBSET_FLAGS_NO_HINTING`、`hb_subset_or_fail(face, input)`。

## 适用边界

- **适用**：OHOS(aarch64, musl) + 依赖 ICU/freetype/harfbuzz/图形编解码的库。
- **不适用**：不依赖 ICU 的纯 2D 库（A 不触发）；使用 GLES-only 且本就带 EGL 接口的库（B 不触发）。
- **注意**：A 的「补齐 ICU 头」是**替代源**（与 sysroot 系统库同版本），不是逐字节 pin，
  需在交付说明里显式标注为待确认项。
