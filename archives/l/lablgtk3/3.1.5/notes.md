# lablgtk3 3.1.5 适配笔记

**日期**: 2026-09-27
**run_key**: lablgtk3-3.1.5
**base**: a2798f3a1a8b39cc7431694ae6fee2745c5b90c2

## 概述

lablgtk3 3.1.5（OCaml GTK3 绑定，findlib 包）移植到 HarmonyOS PC aarch64。
纯 dune 构建（dune-project lang 1.8），release tarball 自带预生成
varcc.ml/propcc.ml，不需要 camlp5/ocamlfind/opam。产物为 findlib 包
（`(wrapped false)` 顶层模块 Glib/GWindow/…），本 run 只装必选包
`lablgtk3`（sourceview3/gtkspell3/goocanvas2/rsvg2 为可选子包，上游 `-p`
单包语义支持裁剪）。

## 构建链路

```
dune build -p camlp-streams   # vendored 纯 OCaml 库（varcc/propcc 工具依赖）
dune build -p cairo2          # vendored OCaml cairo 绑定（pkg-config 探测 cairo）
dune build -p lablgtk3        # 主包（opam build 字段原文语义）
dune build examples/buttons.exe  # 上游 run-test 对等（build-only 冒烟）
```

## 关键决策

### 1. vendor 而非独立包

依赖缺口只有 OCaml 库 cairo2(>=0.6) 与 camlp-streams(>=5.0)。单库门禁禁止
在 archives/ 新建其他库目录，两个小库随本包 vendor：官方归档 URL+sha256 写入
conandata.yml `vendor_sources`（cairo2 sha256 与 opam-repository 一致；
camlp-streams 的 GitHub 归档 tarball opam 只记录 sha512，sha256 由本 run 对
官方归档实测计算），构建时先建后拷进 findlib root，最终随包安装在
`lib/camlp-streams`、`lib/cairo`。第三方 license（camlp-streams: LGPL-2.1-only
WITH exception；cairo2: LGPL-3.0）已在 manifest.yaml 如实登记。

### 2. 显式 OCaml 环境（implement-policy §5）

OCaml 工具链经 tool_requires 消费制品仓 ocaml/4.14.1.1.4 + dune/3.17.0 +
findlib/1.9.8。构建期生成显式 `ocamlfind.conf`（path 按 newline 分隔多目录：
ocaml stdlib、dune 包 lib、findlib sitelib、vendor root）+ OCAMLLIB +
OCAMLPATH + CAML_LD_LIBRARY_PATH，零设备隐式状态依赖；TMPDIR 注入构建目录
（/tmp 只读）。

### 3. pkg-config 探测路径

src/dune 的 dune_config（dune.configurator）构建期执行
`dune_config -pkg gtk+-3.0 -version 3.18`。PKG_CONFIG_PATH 指向 PkgConfigDeps
为 gtk/3.24.43 依赖图生成的转发型 .pc（E527/E348 范式），generate() 内对
gtk+-3.0.pc / cairo.pc / glib-2.0.pc 存在性显式断言，缺件即早失败。

### 4. 无显示测试口径（E471 分类法）

上游事实：无单元测试（全树 runtest=0、无 test/ 目录）；opam run-test =
`dune build -p name -j jobs examples/buttons.exe`——编译冒烟，不运行。
OHOS PC 无原生显示后端（E463/E471），gtk_init() 运行必败，属真实显示依赖
而非库缺陷。据此：
- build-only 编译验证 = 上游语义正解（build() 内 `dune build
  examples/buttons.exe`）；
- 新增鸿蒙特有测试：T2 无显示器 API 探针——编译并真实运行链接 lablgtk3
  stubs + vendored cairo2 + glib 的原生程序，断言 Glib.Convert.get_charset
  与 Glib.Utf8 编解码闭环（不需要 gtk_init）；
- T3 另编译一个 GTK 窗口消费者（仅编译链接，运行面按显示依赖分类排除，
  不写成库测试失败、不虚报运行）。

## OHOS 平台事实（真机/仓内证据）

- ocaml/4.14.1.1.4 的 bin/ocamlc、bin/ocamlopt 为原生 ELF（上游 `ln -sf
  *.opt` 因 OHOS 拒绝符号链接改为 `cp -f`），直接可用；hmmac 拒绝
  shebang/字节码可执行（E253），本链全程原生 ELF。
- dune/3.17.0 与 findlib/1.9.8 在设备构建成功并发布（各自 notes.md）。
- gtk/3.24.43 提供 gtk+-3.0.pc 转发（manifest：PkgConfigDeps 别名 .pc），
  broadway-only 后端不影响编译/链接，仅影响运行（本 run 不运行 GTK 程序）。

## 版本映射与来源

- tag `3.1.5` → commit afbd6d2ee90b98cb0ea49cba34659e15b00cbfe3（与 opam
  x-commit-hash 一致）；归档 lablgtk3-3.1.5.tbz（867,518 字节），sha256 与
  opam-repository checksum 完全一致（Scout-A 三重交叉验证）。
- license: LGPL-2.1-or-later WITH OCaml-LGPL-linking-exception（lablgtk3.opam
  license 字段原文；examples/ 为 public domain；applications/ 不参与构建）。

## 回修记录

### round-01（权威 CI，rc=fail）

失败点：`dune build -p lablgtk3` 内两个 C stub 编译错误（vendor 链
camlp-streams/csexp/dune-configurator/cairo2 全部一次通过）：
- `ml_gdk.c:435: use of undeclared identifier 'AnyPropertyType'`（X11 atom，
  经 gdkx.h 暴露；0001 已按计划把 gdkx.h 排除）
- `ml_gtk.c:931: incompatible integer to pointer conversion`（gtk_plug_new
  未声明；broadway 安装的 gtkplug.h/gtksocket.h 内容本身以
  `#ifdef GDK_WINDOWING_X11` 守卫——设备头文件实证——故 gtkx.h include
  为空操作，plug/socket 符号既未声明也未导出）

知识检索：build-chain-pitfalls 无命中（非链接闭包类）；E463/E471/E527 确认
平台事实（无 X11 后端、"X11 backend not found" 错误签名族）；经验仓 main
gtk/cairo 条目为组件/.pc 转发类，无本签名命中。修复取上游自身平台分支语义
（win32/quartz 的 Unsupported/Val_unit/"only for X11" 桩路径），见 patch 0002
五处守卫（ml_gdk.c ×2、ml_gtk.c ×3，第三处为 ml_gtkwindow_init 的
plug/socket get_type 注册——不修则链接期必挂）。

### round-02（权威 CI，rc=fail）

失败点：tools 可执行链接 `undefined symbol: ffi_type_void / pcre2_*`，
lld 报供给者 `/storage/Users/currentUser/usr/local/lib/libgobject-2.0.a`。
实证链：clink sexp 已含全部 -L 闭包仍失败 → ocamlopt -verbose 抓真实链接行
→ ocamlopt 固定把 `-L/usr/local/lib` 排首位，lld 单目录内先 .so 后 .a，
该目录仅存静态 libg{lib,object,gio,module,thread,irepository}-2.0.a/
libintl.a（另一套 glib 2.88 构建），压过 -L 靠后的 conan 共享库。
修复：generate() 把 conan glib 包供给 .so 以绝对路径列为显式链接输入
（isfile 守卫，-lintl 由显式 libintl.so 取代）——build-chain-pitfalls
「显式闭包注入」范式的直用。

### round-03（权威 CI，rc=pass）

Build Summary 1/1（pass rate 100%），L0/L1/L4/L5=pass、L2=skip（findlib 包
无 bin/，符合预期）；test_package T0–T3 全过（T2 无显示器探针真机执行，
Glib UTF-8 闭环断言通过）；上游 run-test 对等 `dune build -p lablgtk3
examples/buttons.exe` 构建通过。CI 过程对 worktree 的原地改写（mirror-fallback
改写 conandata.yml、test_package 探针产物）已按 implement-policy §0 恢复原状，
未进候选提交。实测全程约 2.5 分钟（<3600s 默认门限，无需扩时配置）。
