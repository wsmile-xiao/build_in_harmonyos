# vigor 0.016 适配笔记

## 编译环境
- 构建系统: autotools（autoconf 2.13，源码树 build/ 子目录含 configure.in）
- 编译日期: 2026-10-10
- 编译器: clang/clang++（OHOS 交叉工具链，aarch64-linux-ohos）
- 状态: built

## 软件简介

Vigor 0.016 是基于 nvi 1.79 的 vi 兼容编辑器，带 Tcl/Tk 图形界面（X11）。
产物为可执行文件 `vigor`（CLI 全屏编辑器，R38 声明 type=tool）。

## 编译步骤

1. `conan create` 前手工验证（build 目录外）：
   ```bash
   ./configure --prefix=$PREFIX --host=aarch64-linux-ohos --build=aarch64-linux-ohos \
       --enable-curses --enable-db --enable-re
   make -j1 && make install
   ```
2. 配方中（conanfile.py）等价复刻：
   - `AutotoolsDeps` 注入 tcl/tk/libx11/ncurses 的 -I/-L/-l；
   - `AutotoolsToolchain` 传 `--host=aarch64-linux-ohos --build=aarch64-linux-ohos
     --enable-curses --enable-db --enable-re`；
   - build() 将源码树 build/ 子目录 flatten 到根目录后 configure+make -j1；
   - package() 以 `prefix=$package_folder` + `strip=/system/bin/true` 直装
     （上游 Makefile 无 DESTDIR 支持，见问题表）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure `can not guess host type` | 2000 年版 config.guess 无法识别 HarmonyOS（E160） | 显式 `--host=aarch64-linux-ohos` + build() 里 replace config.sub 支持 aarch64/-ohos |
| 2 | `no writeable preserve directory found` | autoconf 2.13 探测 /var/preserve 等系统目录，conan 沙箱内均不可写；autoconf 2.13 无 `VAR=value` CLI | generate() 注入环境变量 `vi_cv_path_preserve`（指向 build_folder 私有目录）+ build() 预建该目录 |
| 3 | `X is required for Vigor`（probe 判 no_x） | autoconf 2.13 X 探测找固定系统目录的 X11/Intrinsic.h 与 -lXt（最终二进制只需 -lX11） | generate() 注入 `ac_cv_have_x=have_x=yes ac_x_includes=... ac_x_libraries=...`（libx11 依赖目录） |
| 4 | 类型探测全失败 → `no file truncation system call` | `$CC -E` 的 stderr 被 clang 注入的 `-Wl,--code-sign` 等 warning 污染 → AC_PROG_CPP 回落到 /lib/cpp → pid_t 等被误 #define | generate() 注入 `ac_cv_prog_CPP='clang -E -Qunused-arguments'` |
| 5 | conftest 运行期缺依赖 .so | 本机 aarch64 经 qemu binfmt 真实执行 conftest，需链接依赖共享库 | generate() 把全部依赖 libdir 追加进 LD_LIBRARY_PATH |
| 6 | `can not run config.sub` / `C compiler cannot create executables`（瞬态） | profile [buildenv]/toolchain 硬编码 CI worker 路径 /data/service/hnp/bin/bash|clang（shadow-CI 瞬态缺失，DRAFT-9639） | `_patch_buildenv_shells()`：生成的环境脚本中路径不存在时回退 PATH 解析工具 |
| 7 | 链接重复符号（tputs/tgetent 等） | ncurses 静态 libncursesw.a 与 nvi 内置 curses + termcap shim 全局状态冲突 | `libs=False` 引用 ncurses（仅头文件+TERMINFO），剥离 AutoolsDeps 注入的 -lncursew -lformw -lmenuw -lpanelw；自研 termcap(3) shim 编入 libtermlib.a（私有 prefix，R49） |
| 8 | Tcl/Tk 9 编译失败 | Tcl 9 将 Tcl_Interp 改为不透明结构，`interp->result` 直接访问编译失败 | 3 个补丁：0001 ex/ex_tcl.c、0002 vigor/vigor.c（Tcl_GetStringResult + mega_select 去 Tk 事件循环原语）、0003 tcl_api/tcl.c（Tcl_SetObjResult/Tcl_NewIntObj/Tcl_NewWideIntObj） |
| 9 | `make: No rule to make target 'Makefile.in'` | out-of-tree make 的 self-remake 规则引用的 Makefile.in/config.h.in/configure 在源码根而非 build_folder | 把三者 copy 到 build_folder（时间戳保证不重跑） |
| 10 | make install 写到 `/`（erofs 只读失败） | 上游 Makefile 无 DESTDIR，install 规则直写 $(prefix) | package() 用 `make install prefix=$package_folder`（make 变量覆盖优先）+ `strip=/system/bin/true`（configure 未找到 strip → strip=missing_strip 使 install 失败） |
| 11 | `[ -f VI.pm ]` 在 make cwd 找不到 | install_common 相对 make cwd 引用 VI.pm（不随 $(srcdir)） | package() 先把 source_folder/VI.pm copy 到 build_folder |

## 源码修改（补丁）

- `patches/0001-ex_tcl-tcl9-getstringresult.patch` — ex/ex_tcl.c 改 Tcl_GetStringResult（Tcl 9 不透明结构）
- `patches/0002-vigor-tcl9-result-megaselect.patch` — vigor/vigor.c 改 Tcl_GetStringResult；mega_select() 移除 HarmonyOS Tk 端口未暴露的 X11 事件循环原语，回退纯 select()
- `patches/0003-tcl-api-tcl9-setobjresult.patch` — tcl_api/tcl.c 改 Tcl_SetObjResult/Tcl_NewIntObj/Tcl_NewWideIntObj

## 依赖版本

- tcl/9.0.3.2（配置期硬依赖 Tcl_Init，链接 libtcl9.0.so）
- tk/9.0.3.2（配置期硬依赖 Tk_Init，链接 libtcl9tk9.0.so）
- libx11/1.8.13（X 探测 + 链接 -lX11）
- xorgproto/2025.1（提供 X11/Xosdefs.h，AutotoolsDeps 只喂直接依赖，故显式列出）
- ncurses/6.4（头文件 + TERMINFO，libs=False，不链接）

## 验证结果

```bash
# W3 本地 CI（finish step 5/10，阻塞门禁）
conan create 通过（exit_code=0，.ci-result.json 已写入）
# 上游测试清点（R51）：vigor 无 tests/ 目录
#   唯一上游自检 = catalog/Makefile 的 check 目标（消息目录校验，7 个目录）
#   实测：make -C catalog check 执行成功（exit=0），7/7 目录校验通过
# 鸿蒙特有测试（test_package/vigor_test.py，9 项断言全过）：
#   ① 真实执行 vigor -e -r（rc=0 + 有输出）
#   ② 二进制内嵌版本戳 "Version 1.79"
#   ③ ELF magic + ELF64 class
#   ④ e_machine=0xB7（AArch64）
#   ⑤ DT_NEEDED 全部动态链接可解析（含 OHOS sysroot 系统库）
# L2 --version/--help 为 skip：nvi 家族无 --version 选项（返回 1 + usage），
#   非阻塞，已在 test_package 用 vigor -e -r 真实执行代替
```

## 交付物

| 文件 | 说明 |
|------|------|
| bin/vigor | 可执行文件（aarch64 ELF，动态链接 tcl/tk/X11 链） |
| share/... | 帮助/文档数据（make install prefix 直装） |

## 注意事项

- 上游 2000 年版 autotools 脚本 + Tcl/Tk 9 + OHOS 平台需大量配置期环境注入，见问题表 1-7 与 conanfile.py 注释。
- 产物为 CLI 编辑器，需终端驱动；Tk GUI 事件循环在 HarmonyOS Tk 端口下裁剪（补丁 0002），不影响 CLI 核心编辑功能。
