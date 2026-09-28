# fltk 1.4.5：CMake 选项整体改名导致的「配方假通过」+ 上游默认 ON 的后端开关地雷

## 场景一：大版本升级时「换个版本号」为什么必然踩坑

FLTK 1.4.x 相对 1.3.x 把**整套构建选项改了名**，而 CMake 对未知的 `-D`
变量**既不报错也不失败**——它只在 configure 末尾追加一段：

```
Manually-specified variables were not used by the project:
  OPTION_USE_XFT
  OPTION_USE_XINERAMA
  ...
```

于是配方"看起来把选项传进去了、实际上一个都没生效"。这类**静默退化**是最
危险的一种失败：构建成功、CI 全绿、产出的包却与配方声明完全不符（X 扩展
可能全开或全关，取决于上游默认值而不是配方里的 `OFF`）。

改名对照（1.3.x → 1.4.5）：

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
| （无） | `FLTK_BACKEND_X11` / `FLTK_BACKEND_WAYLAND`（新增大版本开关） |

**判据（写配方前在 source() 之后扫一遍）**：

```sh
grep -n "^ *option(" CMake/options.cmake      # 取当前版本的真实 option 名
grep -rn "Manually-specified variables" <configure 日志>   # 有这段 = 已被静默吞掉
```

同一大版本内的小版本可以沿用旧配方；**跨大版本必须逐个核对 `option()` 名**，
不能只改 `version =`。`FLTK_BUILD_GL` 更隐蔽一层：它只在
`HAVE_GL = LIB_GL OR LIB_MesaGL` 为真时才被 `option()` 声明，未声明时传值
只会多一条 unused 提示——所以"传了没生效"和"根本没声明"在这个选项上长得
一模一样。

## 场景二：上游默认 ON 的后端开关，是一条对适配极不友好的分支

1.4.x 新增 `FLTK_BACKEND_X11` / `FLTK_BACKEND_WAYLAND` 两个后端开关。
`CMake/options.cmake:277-306`：

```cmake
if(NOT APPLE)
  option(FLTK_BACKEND_WAYLAND "support the Wayland backend" ON)   # ← UNIX 上默认 ON
endif()
if(FLTK_BACKEND_WAYLAND)
  pkg_check_modules(WLDCLIENT  ... wayland-client>=1.18)
  pkg_check_modules(WLDCURSOR  ... wayland-cursor)
  pkg_check_modules(WLDPROTO   ... wayland-protocols>=1.15)
  pkg_check_modules(XKBCOMMON  ... xkbcommon)
  if(NOT(WLDCLIENT_FOUND AND WLDCURSOR_FOUND AND WLDPROTO_FOUND AND XKBCOMMON_FOUND))
    message(STATUS "... FLTK_BACKEND_WAYLAND is turned off.")
    unset(FLTK_BACKEND_WAYLAND CACHE)
    set(FLTK_BACKEND_WAYLAND 0)          # ← 静默自关，构建"成功"
  endif()
endif()
```

保持默认 ON 会走两条都很难受的分支：

* **探测不到 wayland 的 `.pc` 文件**（沙箱/大多数 worker 都没有）→ 上游把它
  自己悄悄置 0。构建成功，但"我传了后端选项"这件事**没有任何效果**，属于
  **假通过**：配方声明 X11 后端，实际生效的却取决于构建机上装了没有。
* **探测到了**（镜像里一旦带了 wayland 开发包）→ 紧接着强制
  `FLTK_GRAPHICS_CAIRO TRUE`，并要求 Xfixes / Xrender / Xft / Xcursor /
  Xinerama **全部存在**，缺一个就是
  `FATAL_ERROR "*** Terminating: one or more required software package(s) missing."`。
  适配时这几个 X 扩展库通常都没进依赖链，于是**换个 worker 就炸**。

⇒ 配方里**显式**写 `-DFLTK_BACKEND_WAYLAND=OFF`，把整条 `if` 分支绕开；
`-DFLTK_BACKEND_X11=ON` 虽然 UNIX 下已是默认，仍显式写出，防止上游改默认值
后行为漂移。

**推广**：凡是"上游自动探测 + 探测失败静默自降级"的开关，都不要依赖它的
默认值——把结论**钉死在显式 OFF/ON 上**，让配方声明的语义与实际构建一致。

## 场景三：1.4.x 恒建静态库，`BUILD_SHARED_LIBS` 是「额外」不是「二选一」

`src/CMakeLists.txt:824` 是无条件的 `fl_add_library(fltk STATIC ...)`；
`FLTK_BUILD_SHARED_LIBS` 的语义是"**额外再**建一份 shared"（输出名
`libfltk.so`），不是 static/shared 二选一。沿用 1.3.x 的
`OPTION_BUILD_SHARED_LIBS=OFF` 思路会让包同时含 `.a` 与 `.so`。

因此 `shared=False` 时 `package()` 里**不需要**任何"删多余静态库"的逻辑；
只有当显式 `--shared` 时才需要 `rm("*.a")` 把静态库清掉，让包语义单一。

## 场景四：内置图像库是三个独立静态库，`libs` 少写一个就链接期报错

`FLTK_USE_SYSTEM_{LIBJPEG,LIBPNG,ZLIB}=OFF` 的语义是"用**随包源码**"，而上游
是**分别编译**成独立静态库再安装的：

```
lib/libfltk.a  lib/libfltk_images.a  lib/libfltk_forms.a
lib/libfltk_png.a  lib/libfltk_jpeg.a  lib/libfltk_z.a
```

依赖关系（`src/CMakeLists.txt:846,905-907`、`png/CMakeLists.txt:101`）：

```
fltk_images ──PUBLIC──> fltk, fltk_png, fltk_jpeg
fltk_png    ──PUBLIC──> fltk_z
```

所以 `package_info()` 必须写
`libs = ["fltk_images", "fltk_png", "fltk_jpeg", "fltk_z", "fltk"]`（顺序即
链接顺序）。只写 `["fltk_images","fltk"]` 的包，消费者一旦用到
`Fl_PNG_Image` / `Fl_JPEG_Image` 就会在链接期拿到未定义符号。内置库的头文件
装在 `include/FL/images/`，也要作为 include 根一并暴露。

## 场景五：上游无 CTest——`test/` 是 demo 集合，「构建期」就是「测试期」

1.4.5 源码树内没有 `enable_testing()` / `add_test()`，
`cmake --build . --target test` **直接失败**（1.3.x 时期的档案不是这样，不能
照抄）。上游的 `test/` 是一组独立 demo，由 `test/CMakeLists.txt` 的
`fl_create_example()` 生成，并挂到默认的 `all` 目标下。

⇒ `FLTK_BUILD_TEST=ON` 时，`cmake.build()`（即 `cmake --build .`）本身
就是上游的校验动作：**96 个 demo 全部编译+链接成功**才算过。沙箱没有 X
display，这些 demo 只能构建、不能运行，这一点必须在 PR 正文的"未执行说明"
里逐项交代。

用本包选项集（GL/Cairo/X 扩展全关、shared OFF）实测：
`fl_create_example()` 共 121 次调用，**启用 96 / 禁用 25**。禁用 25 个 =
1 个 `extra_tests` 占位 + 7 个 OpenGL demo（CubeView / cube / fractals /
glut_test / glpuzzle / gl_overlay / shape）+ 17 个 shared 变体（MSVC 与非
MSVC 两个分支下的同名 shared 目标）。

## 场景六：消费者链接只需要 `-lX11`，不需要 `-lXext`

`src/drivers/X11/Fl_X11_Window_Driver.cxx:280-306` 对 XShape 系列符号走的是
`dlopen`/`dlsym` **动态解析**，而不是直接调用。所以在本包（Xrender/Xft/
Xinerama 等全关）的配置下，静态消费者补齐 `-lX11 -ldl` 即可，不需要
`-lXext`。多写 `-lXext` 会在未适配该库时直接把消费者链接搞挂。

## 场景七：两个文档与实现不一致的运行时陷阱（测试里按真实行为钉死）

* `Fl_System_Driver::filename_ext()`（`src/filename_ext.cxx:50`）**文档写
  "无扩展名返回 NULL"，实现返回指向结尾 `'\0'` 的指针**（Unix 驱动不覆写，
  只有 WinAPI 覆写）。按文档判空会写出永远为假的判断。
* Unix/OHOS 上 `fl_filename_name()` 只认 `'/'` 作分隔符
  （`src/drivers/Unix/Fl_Unix_System_Driver.cxx:696`），Windows 风格的
  `C:\Users\a\b.txt` 会被**原样返回**。跨平台搬运路径时这是个静默错误源。

## 场景八：`fl_utf8locale()` 是纯 getenv 启发式，且结果进程内不可差分

`Fl_Unix_System_Driver::utf8locale()`（同文件 :680）：

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
OHOS/musl 上根本没有被生成）判为 UTF-8。

关键在 `static int ret` —— **同一进程内无法做差分**，第一次调用的结果会被
永久缓存。所以平台特有测试必须用**多个独立进程**、各设一种 `LC_ALL` 来断言，
不能在同一个进程里连续 setenv 后重测。

## 场景九：`fl_filename_*` / utf8 / `Fl_Text_Buffer` 全不碰 X display

这一族 API（版本宏、`fl_utf8len`/`fl_utf8decode`/`fl_utf8test`、
`fl_filename_name`/`fl_filename_ext`/`fl_filename_match`、`Fl_Text_Buffer`）
的代码路径都不经过窗口/屏幕驱动，所以 test_package 可以在**无 X display 的
沙箱里真实编译 + 真实运行**，而不只是"构建成功"。G0 要求 test_package 有
literal 的 `self.run()`，这一点是可以满足的——不要因为"GUI 库跑不起来"就
退化成只编译。
