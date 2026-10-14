# libosmo-dsp 0.5.0 — 适配笔记

## 包定位与依赖事实（源码级核对）

- 上游 configure.ac 全部依赖只有一个：`PKG_CHECK_MODULES(FFTW3F,
  fftw3f >= 3.2.0)`。**不依赖 libosmocore**（有别于 libosmo-abis 等
  家族成员），因此也没有跨 DSO TLS 模型议题（无需 -fno-emulated-tls）。
- fftw3f（单精度）在 registry 缺位：已合入的 fftw/3.3.10.x 是默认
  双精度构建（真机包内实测仅 libfftw3.so + fftw3.pc）。本链路配套提交
  依赖项 PR `fftw3f/3.3.10`（同一上游 tarball + `--enable-single`）。

## 版本口径说明

- 上游 release 目录（downloads.osmocom.org/releases/libosmo-dsp/）最新
  发布名为 **0.5.0**；但 tarball 内层目录与 `.tarball-version` 均为
  `0.4.0.10-dce1`（git-version-gen 沿用旧 tag 的上游打包瑕疵）。
- 本配方归档口径按发布名 **0.5.0**（与下载 URL、任务口径一致），
  conan get 使用 `strip_root=True` 对内层目录名不敏感。

## 构建细节

- `LT_INIT([pic-only])`：上游默认构建共享/静态按 libtool 默认，配方按
  options 显式传 `--enable-shared/--disable-static`（与家族一致）。
- 上游有 clang 特判（configure.ac 对 `*clang*` LD 改写 archive_cmds），
  无需额外处理。
- 无 make check：上游无 tests/ 目录、Makefile.am 无 check-TESTS，
  PR 对比表按"上游 0 组 / 适配后 0 组（探针 1 项）"如实填写。

## 验证

见 PR 正文。真机 conan create 全链路（fftw3f 依赖从本 PR 配方构建）+
test_package 探针：osmo_cxvec_alloc 构造 8 点复向量 → osmo_cxvec_scale
缩放 → osmo_cxvec_norm_sq 能量断言 → osmo_cxvec_free。
