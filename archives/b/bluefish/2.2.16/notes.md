# bluefish 2.2.16 适配笔记

## 编译环境
- 构建系统: autotools（发行包自带 configure，无需 autoreconf）
- 编译日期: 2026-09-05
- 编译器: clang/clang++（OHOS aarch64 原生）
- 状态: built

## GTK 版本决策（W0 关键结论）
任务前提"2.2.x 系列依赖 GTK2"与实际源码不符：
- 2.2.16 configure.ac 默认探测 `gtk+-3.0 >= 3.2.2 gdk-3.0`（GTK3 主路径），
  GTK2 仅在显式 `--with-gtk2` 或 GTK3 完全缺失时回退；
- 源码大量使用 GTK3 API（GtkGrid、GTK_CHECK_VERSION(3,x,y) 分支）。
- 制品仓实测：无 gtk2 / gtk/2.x（conan list + download 探针均无），只有
  gtk/3.24.38/3.24.43（GTK3）。结论：**走 GTK3 主路径，无需 GTK2 包**，
  依赖链沿用 gtk/3.24.43 + glib + pango + gdk-pixbuf + libxml2（已发布）。

## 编译步骤
1. conan create 走 `-pr:h=ohos-aarch64 -pr:b=ohos-aarch64`（与 CI 相同）。
2. configure 关键选项（裁剪不可用/不需要的可选组件）：
   ```
   --disable-nls --disable-spell-check --disable-python
   --disable-update-databases
   --with-freedesktop_org-menu=no --with-freedesktop_org-mime=no
   --with-freedesktop_org-appdata=no --without-theme-path --without-icon-path
   ```
   - enchant/gucharmap/python 都是可选依赖，显式禁用保持最小依赖面；
   - freedesktop menu/mime/appdata/主题图标在 OHOS PC 无桌面集成目标。
3. `make -j1 && make -j1 check`（check 仅含 desktop 文件校验，RC=0）。
4. `make install DESTDIR=<package>`（--prefix=/ 保证包内路径为 bin/share）。
5. 对 bin/bluefish 自签名（binary-sign-tool -selfSign 1，校验 .codesign）。
6. 构建期图标嵌入需 gdk-pixbuf-csource（Makefile 运行其生成 htmlbar_icons.c/
   toolbar_icons.c），该工具在 Conan 包内为未签名 ELF → 复制+自签名到
   build 树 host-tools/ 并通过 GDK_PIXBUF_CSOURCE 注入（configure 期生效）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess "cannot guess build type" | 2018-02-24 config.guess 不识别 HarmonyOS uname | 补丁 0001：`*:HarmonyOS:*:*)` 分支 echo `aarch64-unknown-linux-ohos` 并 exit |
| 2 | config.sub 拒绝 linux-ohos triplet | OS/内核候选表无 ohos | 补丁 0002：os 候选 + `-linux-ohos*` 内核表各加一行 |
| 3 | config.status "can't create ./confXXXX/subs1.awk: Permission denied" | Autoconf 2.71 config.status 用 umask 077 建临时目录，HMDFS setgid 下 0700 不可写 | 补丁 0003：configure 两处 umask 077→022（缺此补丁 conan create 必挂） |
| 4 | 编译报错 "use of undeclared identifier 'pixmap_abbr'" | configure 探测 `gdk-pixbuf-csource... no` → Makefile 变量空 → htmlbar_icons.c 未生成（C 数组缺失） | host-tools 复制+自签名 gdk-pixbuf-csource（含 gdk-pixbuf-pixdata/glib-compile-resources 一并准备），generate()/build env 注入 GDK_PIXBUF_CSOURCE 与 PATH |
| 5 | gdk-3.0/gio-unix-2.0 pkg-config 探测失败 | PkgConfigDeps 未生成这两个传统模块名 | generate() 生成别名 .pc（gdk-3.0←gtk+-3.0，gio-unix-2.0←gio-2.0），Libs/Cflags 一致；目标存在时跳过 |
| 6 | GTK3 GUI 在 OHOS 无显示可运行 | 无 X server | 如实交付编译/链接级 + 无头验证：--version/--help/--selftest 均在打开显示前退出；plain 启动按预期 fail closed（Cannot open display, rc≠0） |
| 7 | 上游零测试 | bluefish 发行不携带测试 | 补丁 0004 增加 --selftest：14 项对生产代码的程序化检查 |

## 源码修改（补丁）
| 补丁 | 文件 | 内容 |
|------|------|------|
| 0001 | config.guess | HarmonyOS uname 分支（echo+exit 三元组） |
| 0002 | config.sub | linux-ohos OS 支持（2 行） |
| 0003 | configure | config.status 临时目录 umask 022 |
| 0004 | src/bluefish.c | 无头 --selftest（提前于 GTK display 打开处理）；选项表加入 --selftest；include <string.h> |

## 依赖版本
- gtk/3.24.43, glib/2.84.0.1, pango/1.50.14.1.1, gdk-pixbuf/2.44.6.1,
  libxml2/2.15.3.1（全部已发布制品仓，含传递闭包 binary）
- 源码 tarball sha256=14e6476f…5dd74（bennewitz 与 sourceforge 双源一致）

## 验证结果
```bash
# 本地无头验证（conan test_package，28 断言全过）
bluefish --version      # Bluefish Editor 2.2.16, rc=0
bluefish --help         # Usage + 选项表, rc=0
bluefish --selftest     # 14 项 PASS + self-test: PASS, rc=0
bluefish                # GUI 路径：无显示 → fail closed rc≠0
```
GUI 交互无法自动化（OHOS PC 无 X server），如实说明。

## 注意事项
- refresh-patch 规则扫描会把 configure 判为"生成物"跳过；configure 补丁
  需先 `track-edit` 登记 configure 再 refresh（tracker 精准模式逐文件生成）。
- 本地 conan create 用 4 补丁全量验证过（含 umask 补丁）；W3 本地 CI 同样
  4 补丁通过（.ci-result.json exit_code=0）。
---

**编译结束**: 2026-09-07 02:20
**最终状态**: built
