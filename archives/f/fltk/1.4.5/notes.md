# fltk 1.4.5 — HarmonyOS PC 适配笔记

## 1. 概览

| 项 | 值 |
|----|----|
| 上游 | https://www.fltk.org （源码 https://github.com/fltk/fltk） |
| 版本 | 1.4.5 |
| 源码 | `https://github.com/fltk/fltk/releases/download/release-1.4.5/fltk-1.4.5-source.tar.gz` |
| SHA256 | `eede1fb2b8e9c2e581e77082e15252145855c79aad30070ee3b24aabe2f926f1` |
| 构建 | cmake（上游 CMake 直接构建） |
| 包名 | `fltk/1.4.5`（同软件另有 `archives/l/libfltk` 提供 1.3.11，包名 `libfltk`） |
| 依赖 | `libx11/1.8.13` + `xorgproto/2025.1` |
| 后端 | X11（Wayland 后端显式关闭） |
| 补丁 | 无（`patches_applied: []`，上游源码零改动） |

## 2. 为什么不是「把 libfltk/1.3.11 的配方换个版本号」

1.4.x 对 1.3.x 做了**构建选项的整体改名**，而 CMake 对未知的 `-D` 变量
**既不报错也不失败**——它只在 configure 末尾输出一行

```
Manually-specified variables were not used by the project:
  OPTION_USE_XFT
  ...
```

于是"配方看起来把选项传进去了、实际上一个都没生效"。沿用旧名会得到一份
**静默退化**的包（X 扩展全开或全关都与配方声明不符）。改名对照：

| 1.3.x | 1.4.5 |
|-------|-------|
| `OPTION_USE_XINERAMA` | `FLTK_USE_XINERAMA` |
| `OPTION_USE_XFIXES` | `FLTK_USE_XFIXES` |
| `OPTION_USE_XCURSOR` | `FLTK_USE_XCURSOR` |
| `OPTION_USE_XFT` | `FLTK_USE_XFT` |
| `OPTION_USE_XRENDER` | `FLTK_USE_XRENDER` |
| `OPTION_USE_GL` | `FLTK_BUILD_GL` |
| `OPTION_CAIRO` | `FLTK_GRAPHICS_CAIRO` |
| `FLTK_USE_SYSTEM_JPEG` | `FLTK_USE_SYSTEM_LIBJPEG` |
| `FLTK_USE_SYSTEM_PNG` | `FLTK_USE_SYSTEM_LIBPNG` |
| （无） | `FLTK_BACKEND_X11` / `FLTK_BACKEND_WAYLAND`（新增） |

另外还有三处结构性差异，见下。

## 3. `FLTK_BACKEND_WAYLAND` 默认 ON —— 本适配里最危险的一个默认值

`CMake/options.cmake:277-306`：

```cmake
if(NOT APPLE)
  option(FLTK_BACKEND_WAYLAND "support the Wayland backend" ON)   # ← UNIX 上默认 ON
endif()
if(FLTK_BACKEND_WAYLAND)
  pkg_check_modules(WLDCLIENT ... wayland-client>=1.18)
  pkg_check_modules(WLDCURSOR ... wayland-cursor)
  pkg_check_modules(WLDPROTO  ... wayland-protocols>=1.15)
  pkg_check_modules(XKBCOMMON ... xkbcommon)
  if(NOT(WLDCLIENT_FOUND AND WLDCURSOR_FOUND AND WLDPROTO_FOUND AND XKBCOMMON_FOUND))
    message(STATUS "... FLTK_BACKEND_WAYLAND is turned off.")
    unset(FLTK_BACKEND_WAYLAND CACHE)
    set(FLTK_BACKEND_WAYLAND 0)          # ← 静默自关，构建"成功"
  endif()
```

两条分支都很难受：

* **探测不到 wayland 的 .pc 文件**（本地沙箱/大多数 worker）→ 它把自己悄悄置 0。
  构建成功，但"我传了后端选项"这件事**没有任何效果**，出问题极难定位。
* **探测到了**（一旦镜像里装了 wayland 开发包）→ 紧接着
  `set(FLTK_GRAPHICS_CAIRO TRUE CACHE BOOL ...)`，并要求 Xfixes / Xrender /
  Xft / Xcursor / Xinerama **全部存在**，缺一个就是
  `FATAL_ERROR "*** Terminating: one or more required software package(s) missing."`。
  而本仓并未适配这几个 X 扩展库。

因此配方里显式写 `-DFLTK_BACKEND_WAYLAND=OFF`，把整条分支绕开；
`-DFLTK_BACKEND_X11=ON` 虽然 UNIX 下已是默认，仍显式写出以防上游改默认值。

## 4. 1.4.x 恒建静态库

`src/CMakeLists.txt:824` 是无条件的 `fl_add_library(fltk STATIC ...)`；
`FLTK_BUILD_SHARED_LIBS` 的语义是"**额外再**建一份 shared"（输出名
`libfltk.so`），不是二选一。所以本包默认 `shared=False`，且 `package()` 里
不再需要处理"删掉多余静态库"的 1.3.x 式逻辑（只有显式 `--shared` 时才删）。

## 5. 上游没有 CTest

源码树内没有 `enable_testing()` / `add_test()`，`cmake --build . --target test`
会直接失败。上游的 `test/` 是一组独立 demo，由 `test/CMakeLists.txt` 的
`fl_create_example()` 生成，并挂到默认的 `all` 目标下。

所以本包 `FLTK_BUILD_TEST=ON` 时，`cmake.build()` 本身就是上游的校验动作：
**96 个 demo 程序全部编译+链接成功**才算过。沙箱没有 X display，这些 demo
只能构建、不能运行，这一点在 PR 正文的"未执行说明"里逐项交代。

## 6. 静态库不止 `libfltk.a` 与 `libfltk_images.a`

`FLTK_USE_SYSTEM_{LIBJPEG,LIBPNG,ZLIB}=OFF` 的语义是"用**随包源码**"，
而上游是**分别编译**成三个独立静态库再安装的：

```
lib/libfltk.a  lib/libfltk_images.a  lib/libfltk_forms.a
lib/libfltk_png.a  lib/libfltk_jpeg.a  lib/libfltk_z.a
```

依赖关系（`src/CMakeLists.txt:846,905-907`、`png/CMakeLists.txt:101`）：

```
fltk_images ──PUBLIC──> fltk, fltk_png, fltk_jpeg
fltk_png    ──PUBLIC──> fltk_z
```

`package_info()` 因此声明 `libs = ["fltk_images", "fltk_png", "fltk_jpeg",
"fltk_z", "fltk"]`（顺序即依赖顺序）。只写 `["fltk_images","fltk"]` 的包
在消费者用到 `Fl_PNG_Image` / `Fl_JPEG_Image` 时会在链接期报未定义符号。
内置库的头文件装在 `include/FL/images/`，也作为 include 根一并暴露。

`libfltk_forms.a`（Forms 兼容层，仅 `FL/forms.H` 一族 API 需要）**不**列进
`libs`：它不在任何其它静态库的 PUBLIC 依赖里，是消费者按需显式链接的可选
组件——与同软件 1.3.11 包（`archives/l/libfltk`）的处理一致。库本身随包
安装（`lib/libfltk_forms.a` + `include/FL/forms.H`），只是不进默认链接行。

## 7. 消费者链接：只需要 `-lX11`，不需要 `-lXext`

`src/drivers/X11/Fl_X11_Window_Driver.cxx:280-306` 对 XShape 系列符号走的是
`dlopen`/`dlsym` 动态解析，而不是直接调用，所以在本包（Xrender/Xft/Xinerama
等全关）的配置下，静态消费者补齐 `-lX11 -ldl` 即可，无需 `-lXext`。

## 8. 运行时行为的两个"陷阱"（已写进 test_package 断言）

* `Fl_System_Driver::filename_ext()`（`src/filename_ext.cxx:50`）**文档写
  "无扩展名返回 NULL"，实现返回指向结尾 `'\0'` 的指针**。按文档判空会
  写出永远为假的判断。测试里按真实实现钉住。
* Unix/OHOS 上 `fl_filename_name()` 只认 `'/'` 作分隔符
  （`src/drivers/Unix/Fl_Unix_System_Driver.cxx:696`），Windows 风格的
  `C:\Users\a\b.txt` 会被**原样返回**。跨平台搬运路径时这是个静默错误源。

## 9. 平台特有行为：`fl_utf8locale()` 是纯 getenv 启发式

`Fl_Unix_System_Driver::utf8locale()`（同文件 :680）的实现是：

```c
static int ret = 2;
if (ret == 2) {
  ret = 1;                       /* 没有 locale 变量时假定 UTF-8 */
  if (((s=getenv("LC_CTYPE")) && *s) || ((s=getenv("LC_ALL")) && *s) ||
      ((s=getenv("LANG")) && *s))
    ret = (strstr(s,"utf") || strstr(s,"UTF"));   /* 只看字符串里有没有 utf/UTF */
}
return ret;
```

即：**它不查询真实的 C locale，只看环境变量字符串里有没有 `utf`/`UTF`**。
后果是 `LC_ALL=C` 判为非 UTF-8，而 `LC_ALL=C.UTF-8`（哪怕该 locale 在
OHOS/musl 上根本没有被生成）判为 UTF-8。此外结果缓存在函数内 `static` 里，
**同一进程内无法做差分**——所以 test_package 用三个独立进程、三种 `LC_ALL`
来断言。

## 10. 验证

* `archives/f/fltk/1.4.5/test_package/test_fltk.cxx`：45 条断言（版本标识 6 /
  UTF-8 编解码 17 / 文件名 Unix 语义 9 / Fl_Text_Buffer 13），真实编译 + **真实运行**。
* 平台特有差分：`LC_ALL=C` → `fl_utf8locale()==0`；`LC_ALL=C.UTF-8` 与
  `LC_ALL=en_US.UTF-8` → `==1`（3 次独立进程调用）。
* 产物可用性：包内 `bin/fltk-config --version` 可执行。
