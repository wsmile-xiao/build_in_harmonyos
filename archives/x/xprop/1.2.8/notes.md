# xprop 1.2.8 — HarmonyOS PC 适配笔记

## 包概况

- 上游：https://gitlab.freedesktop.org/xorg/app/xprop（发布物 x.org/xorg.freedesktop.org individual/app）
- 版本：1.2.8（tarball 197390 字节，sha256=a8394338c99775160d733d54d73cdcdc5c9c80a0dc8cffd5be1b7c977254b745）
- 语言/构建：C，autotools（tarball 自带已生成 configure，免 autoreconf）
- 功能：查询/修改 X 窗口属性（WM_CLASS/WM_NAME/WM_PROTOCOLS 等），5 个 C 文件
- 上游测试：无（四类口径审计见 test_package/MANIFEST.yml）

## 依赖判定（W0）

- 权威依赖：configure.ac L42 `PKG_CHECK_MODULES(XPROP, [x11 xproto >= 7.0.25])`
- libx11：制品仓双轨 1.8.13/6.4.0 均已发布。本包硬链接集合仅 `-lX11`
  （Makefile.am `xprop_LDADD = $(XPROP_LIBS)`），未命中
  DRAFT-xbanish-1.8-x11-track-selection 钉轨者表的任何子库（libXi/libXt），
  属"未命中任何钉轨者"的平凡路径；轨选择跟随 X 客户端先例
  （xeyes 1.3.1/xclip/xsel 均锁 libx11/6.4.0）⇒ 取 6.4.0 轨。
- xproto：制品仓以 xorgproto/2025.1 发布（xproto 上游并入 xorgproto），
  transitive_headers=True 取头（X11/Xproto.h、keysymdef.h）。
- 运行期：libX11.so.6 的 DT_NEEDED 需要 libxcb.so.1/libXau.so.6（设备栈
  仅有 .a，xeyes 第 4 轮真机根因同款）⇒ libxcb/1.16 + libxau/1.0.11
  （run=True），test_package LD_PRELOAD 注入（libXau → libXdmcp → libxcb
  → libX11 依赖序）。

## 构建方案与已知坑（全部以先例预防，非踩坑后修）

1. **PKG_CHECK_MODULES 逃逸**：conan 包不随附 xproto.pc/x11.pc 全集且设备
   无 pkg-config x11 文件 ⇒ configure_args 预置 `XPROP_CFLAGS/XPROP_LIBS`
   （autotools 标准机制：宏见非空变量直接采用、不调 pkg-config；adcli
   KRB5_*、coturn SSL_*、xeyes XEYES_* 同款先例）。
2. **HMDFS getcwd**：conan 缓存父目录对 getcwd() 不可达 → build() 固定
   cwd 到 build_folder + 预置 PWD；_rewrite_configure 改写 configure 顶部
   pwd 判定回退 $PWD、umask 077 → 022（xeyes/nspr/aribb24 同款，E114/E129）。
3. **交叉编译三元组**：xprop 1.2.8 的 config.sub（2024 版）实测拒绝 ohos OS
   （Invalid configuration 'aarch64-unknown-linux-ohos'）⇒ `--build/--host`
   统一 `aarch64-unknown-linux-gnu`（仓库 libx11 配方/xeyes vendored 库同款，
   E007 显式三元组跳过平台检测），交叉工具链由 profile 的 CC/CXX 保证。
4. **ELF 签名**：OHOS 内核拒绝未签名 ELF ⇒ package() 内 binary-sign-tool
   selfSign（xeyes/clinfo 同款）。
5. **下载源**：设备直连 www.x.org 报 TLS 证书主机名不匹配（网络层问题），
   改用 xorg.freedesktop.org 官方镜像（同一发布物，xeyes conandata 同款）。
   该源不含 github.com 字样，不受 conan_verify.py ghfast.top 镜像注入影响。

## 测试与证据口径

- 上游四类口径逐项实测为 0（Makefile.am 无 TESTS/check；无 meson.build；
  configure.ac 无测试宏；源码树无 tests/ 目录）——不是"没找"。
- test_package 真实执行被测二进制（R34）：
  - ★实测口径：xprop 非 Xt 程序，main 在解析任何参数（含 -version/-root）
    前先经 dsimple.c Open_Display 连接 X server——dsimple.c L106
    XOpenDisplay 失败后 fprintf "unable to open display" 并 exit(1)
    （first-build 实测记录：`xprop:  unable to open display ''`，rc=1）。
  - 断言一 `xprop -version`（no-X）、断言二 `xprop -root`（主查询入口）：
    均断言 rc=1 + "unable to open display"，验证动态链接/签名/进入 main/
    上游错误处理全链路真实可达。
- not_covered 如实记账：-root 等查询/修改窗口属性的功能级行为需要 X server，
  本平台无 X server；-version 的版本输出因上游参数解析顺序（先连 display）
  在 no-X 环境不可单独验证——不宣称功能已真机验证。

## B 判定

none——本包适配无 OHOS 特有机制：X11 单库消费已被 xeyes/xclip/xsel 先例
覆盖（同构 autotools + libx11/6.4.0 + 逃逸 + HMDFS 三件套 + 签名）；选轨
问题属"未命中钉轨者"的平凡路径，DRAFT-xbanish-1.8-x11-track-selection 已
写明判据，本包是判据的平凡应用而非新机制；运行期 X 连接机制已命中 E461
（AF_UNIX 探针）。故按纯路径 A 交付，不建 DRAFT、不开 Issue。

## 适用边界

- 本笔记的依赖判定与先例引用适用于 x.org app 家族"只链 -lX11"的纯客户端
  小工具（xprop/xwininfo/xdpyinfo 类）；若包硬链接 libXi/libXt 等钉轨子库，
  轨选择必须先按 xbanish 选轨判据现测。

---

**编译结束**: 2026-09-24 02:43
**最终状态**: built
