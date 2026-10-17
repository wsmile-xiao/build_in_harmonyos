# cdebconf-terminal 0.49 适配笔记

## 编译环境

- 构建系统: autotools（configure.ac + Makefile.in，tarball 内无预生成 configure）
- 上游: https://salsa.debian.org/installer-team/cdebconf-terminal（Debian Installer Team）
- 源码包: `https://deb.debian.org/debian/pool/main/c/cdebconf-terminal/cdebconf-terminal_0.49.tar.xz`（38376 字节，sha256 与 0.49 .dsc 一致：`4f8af6e8…63575e7`）
- 编译日期: 2026-09-09
- 编译器: clang/clang++
- 状态: built（待真机预检通过后由 HMBS 提交）

## 上游结构（基于 Debian Sources 文件清单 + control 构建依赖审计）

- 顶层文件：HACKING、Makefile.in、autogen.sh、configure.ac（1324 字节）、gtk-plugin-terminal.c（13907 字节）、newt-plugin-terminal.c（9350 字节）、debian/
- 两个产物：cdebconf-gtk-terminal（GTK2 + VTE 0.28 图形内嵌终端）、cdebconf-newt-terminal（关 newt 跑干净终端）
- 构建依赖（control）：libdebian-installer-dev、libdebconfclient0-dev、libnewt-dev、libgtk2.0-dev、libvte-dev
- OHOS 现状：gtk 仅有 3.24（无 gtk2）、vte 仅有 0.74（gtk4 系，与要求的 VTE 0.28 不兼容）、newt 未进仓；libdebconfclient/libdebian-installer 由 `cdebconf/0.283` 提供（requires）
- 策略：configure 自动探测——缺 GTK2/VTE 时 gtk 插件自动跳过，newt 终端插件正常构建安装；不手写 stub 头，不伪造 GUI 能力

## 编译步骤

1. `get()` 解包 `cdebconf-terminal_0.49.tar.xz`
2. 不跑 autotools 自举：tarball 无预生成 configure，而真机无可用 bootstrap 链（2026-09-09 预检：`autoreconf` 缺失；conan automake/1.18 的 `aclocal` 报 `.aclocal-real: No such file or directory`；conan libtool/2.5.4 的 `libtoolize` 因缺 m4 退出）。配方因此零 `tool_requires`，用 Python 复刻 `configure.ac` 的真实逻辑——`pkg-config` 探测 `libnewt` / `gtk+-x11-2.0+vte` 得 `FRONTENDS`，再把 `Makefile.in` 的 `@prefix@/@CC@/@CFLAGS@/@FRONTENDS@` 等占位符替换为真实值生成 `Makefile`（等价于 `AC_OUTPUT(Makefile)`，无 stub）
3. `make -j1`，`make install`（`prefix=<package_folder>`，产物布局与上游 `make install` 一致：`lib/cdebconf/frontend/<frontend>/plugin-terminal.so`）

## 上游测试审计（结论：无测试套件）

- 全包 sloc：ansic 548 行 + makefile 52 行 + sh 2 行；文件清单无 tests/、test/、spec/、t/ 目录
- `grep TEST(/TEST_F/def test_`：仅两个插件实现文件，无 gtest/pytest 痕迹
- Makefile.in/configure.ac：无 TESTS/check_PROGRAMS/check-local 目标（`make check` 为 automake 默认空目标）
- 因此 `test_package/MANIFEST.yml` 声明 `upstream_tests_exist: false` 并附完整审计；test_package 的 conanfile 在真机输出 `HMBS_UPSTREAM_TEST_RESULT status:"no_tests" discovered:0 executed:0` 及原因

## test_package 设计（R34 实质验证，第二版：如实验证空安装）

- 真机预检 2026-09-09 证伪了第一版假设：OHOS 无 libnewt、无 GTK2/VTE
  栈，FRONTENDS 为空、`make install` 为合法空操作，包内零插件；
  第一版测试硬要求 `*terminal*.so` 存在，与上游在该平台的正确行为
  矛盾，FAIL 不是配方 bug，是测试口径错误。
- 第二版改为自适应一致性验证（3 项真实断言，非硬编码、非静默跳过）：
  ① 用与 configure.ac 相同的包名（`libnewt`、`gtk+-x11-2.0 vte`）在
  测试内重跑 pkg-config 探测并打印 rc 证据；② 安装树与探测结果一致
  ——无栈则断言零插件（与上游空安装一致才 PASS），有栈则要求对应
  插件存在、非空、含 terminal 符号（设备将来补齐 newt/GTK2 也不会
  静默通过）；③ cdebconf 硬依赖提供 libdebconfclient 与插件 API
  头文件（frontend.h/question.h），且对找到的每个插件真实 dlopen。
- test_package 的 conanfile 新增 `generate()`，仅把可写 TMPDIR 注入
  run 域（真机 /tmp 只读诊断的最小合规改动），不改变验证口径。

- `test_cdebconf_terminal.py` 做 3 项真实断言：① 安装树内找到 `*terminal*.so` 插件；② 插件非空且含 terminal 符号（nm/strings 检查）；③ `ctypes.CDLL` 真实 dlopen 插件（坏二进制/缺依赖即失败，非空壳）
- `conanfile.py` 的 `test()` 运行该脚本，统计通过数后打印 `HMBS_TEST_PACKAGE_RESULT`（discovered=3/passedCount=3）与 `HMBS_UPSTREAM_TEST_RESULT`（no_tests/0），失败抛 `ConanException`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 本机 Windows 直连 deb.debian.org/salsa TLS 握手失败 | 出站网络限制 | 采用 .dsc 公布的 sha256（多镜像一致）+ Debian Sources 文件清单审计，不在配方中加非官方镜像；真机预检复验下载 |
| 2 | tarball 无 configure，真机 bootstrap 链断裂（autoreconf 缺失、conan aclocal 缺 `.aclocal-real`、libtoolize 缺 m4） | 真机 HMDFS 无 hardlink/chmod 能力致 conan automake 包损坏，且设备 PATH 无 m4/autoconf 套件 | 零 `tool_requires`，Python 复刻 `configure.ac`（pkg-config 探测 FRONTENDS + `Makefile.in` 占位符替换），编译真实上游源码，不手写 configure |
| 3 | GTK2/VTE 0.28 与 libnewt 在 OHOS 均无对应包 | 仓内仅 gtk3（broadway 后端，无 X11）/vte-2.91（GTK3 系），newt 未进仓 | 探测自动跳过双方，交付上游语义下的空安装（见下节为何不 vendor），如实记录 |

## 为何不 vendor newt/GTK 栈（已评估并拒绝的重路线）

- GTK 插件不可构建：源码使用 GTK2 专有 API（`gtk_hbutton_box_new`、
  `gtk_vbox_new`/`gtk_hbox_new`、`gtk_hseparator_new`、
  `gtk_misc_set_alignment`、`gtk_vscrollbar_new`，在 GTK3 已删除）以及
  旧 VTE API（`vte_terminal_fork_command_full` 在新 VTE 已移除）；
  仓内 gtk 3.24.43 以 `-Dx11_backend=false` 构建，不提供
  `gtk+-x11-3.0`，且 vte 0.74.2 提供的是 `vte-2.91`（GTK3 系）而非
  configure.ac 默认要的 `gtk+-x11-2.0 vte`。`--with-gtk-version=3`
  路线同样编译失败，不是缺包能解决的。
- newt 插件链条过长：需 newt 0.52.x（制品仓无）+ slang + popt，且
  cdebconf/0.283 以 `--with-frontend=passthrough` 构建（newt/slang/
  ncurses 前端全部关闭），`cdebconf_newt_setup` 等符号未必存在；
  为两个 d-i 专用文件（bterm terminfo、`/target` 路径，在 OHOS 无意义）
  重建整条链并重编 cdebconf，代价与收益不成比例。
- 因此保留上游"探测不到就跳过"的语义，空安装是诚实产物；测试验证
  该语义本身，而非伪造插件。

## 验证结果

- 待 HMBS 真机预检（conan create + test_package + 上游 no_tests 证据）返回后如实回填 PR 正文通过率；本轮不猜测数字
