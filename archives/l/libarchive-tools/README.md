# libarchive-tools

## 简介

libarchive-tools 是 libarchive 上游发行包构建的命令行工具集，
包含 bsdtar / bsdcpio / bsdcat / bsdunzip，随包附带其链接的
libarchive 运行库。

与 `libarchive`（库包）的区别：本包以 `package_type = "application"`
定位工具二进制，`bindirs = ["bin"]`，面向命令行使用场景。

## OHOS 适配

- 3.8.8 版本：autotools 构建（tar.xz 格式源码）
- 依赖：zlib/1.3.1.1（OHOS -fPIC 重编版）、xz/5.6.2（liblzma）
- `make check` 上游套件在 `build()` 真实运行，结果存入包内
  `res/libarchive-tools/check-summary.json`

## 功能验证

```bash
bsdtar --version
bsdcpio --version
```

## 参考

- 主页: https://www.libarchive.org/
- 上游仓库: https://github.com/libarchive/libarchive
