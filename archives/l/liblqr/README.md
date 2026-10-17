# liblqr

## 简介

liblqr (Liquid Rescale) 是 Carlo Baldassi 编写的 C/C++ seam carving 内容感知
图像缩放库：在保持重要视觉内容的前提下对图像做宽度/高度方向的液体缩放，
被 GIMP LiquidRescale 插件等广泛使用。输入普通数组图像, 输出多尺寸表示,
支持 8-64 bit/通道、灰度/RGB/CMY 及自定义颜色模型, 提供易用且文档完备的 API。

## OHOS 适配

### 0.4.2（upstream/main）

- 使用 autotools 构建系统（configure + make -j1）
- 单一运行时依赖 glib-2.0（configure.ac PKG_CHECK_MODULES）
- OHOS 下固定 --build/--host=aarch64-unknown-linux-gnu（ctpl/cdecl/castget 先例，绕过 2009 年版 config.guess 对 OHOS 的识别）
- 依赖图与已合入 ctpl/0.3.5 对齐：glib/2.88.0 + zlib/1.3.1.1（override）+ tool_requires pkgconf/3.0.5
- 上游 0.4.2 不含测试套件, 由 test_package 真实调用 API 验证
- 默认静态库（liblqr-1.a）, 头文件位于 include/lqr-1, pkg-config 名 lqr-1

### 0.4.3（feat/liblqr-0.4.3）

- 上游为 autotools 工程（AC_DISABLE_STATIC + LT_INIT([win32-dll])），
  三补丁适配：config.guess/config.sub 增加 linux-ohos 三元组；configure
  移除内嵌 umask 077（E114：HMDFS setgid 构建目录下 mktemp 目录不可进入）。
- glib 依赖走 Conan glib/2.88.3，经 pkg-config 消费（与上游 lqr-1.pc 的
  Requires: glib-2.0 一致）。
- 产物：liblqr-1.so.0.3.2（SONAME liblqr-1.so.0）/ static liblqr-1.a，
  头文件 include/lqr-1/，pkg-config 名 lqr-1。
- 上游 v0.4.3 无 release 资产，源码用 archive/refs/tags/v0.4.3.tar.gz。
- 上游无测试套件（无 TESTS、无 tests/ 目录），make check 为 automake
  默认空目标，配方真实执行以证明。

## 依赖

- glib（运行时；0.4.2 配方用 glib/2.88.0，0.4.3 配方用 glib/2.88.3）

## 功能验证

0.4.2：

```bash
pkg-config --modversion lqr-1
# 输出: 0.4.2
```

0.4.3：

```bash
# 消费者冒烟测试（test_package 自动执行）
./test_lqr_package   # 7/7 PASS（失败即非零退出）
```

## 参考

- 官网: http://liblqr.wikidot.com
- 上游仓库: https://github.com/carlobaldassi/liblqr
- 下载页: http://liblqr.wikidot.com/en:download-page
- 源码 (v0.4.3): https://github.com/carlobaldassi/liblqr/archive/refs/tags/v0.4.3.tar.gz
