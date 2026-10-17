# libtelnet

## 简介

libtelnet 是一个轻量级 C 库，用于实现 TELNET 协议（RFC 854）的状态机，支持
option negotiation（RFC 1143 规则）、NAWS、MSSP、TTYPE、ENVIRON、ZMP 扩展，
以及 MCCP2（zlib 压缩）选项。它不包含网络 I/O，只提供协议状态跟踪与事件
驱动的 API，网络读写由调用方完成。

## OHOS 适配（0.23）

- 官方源代码为 autotools 工程，tag tarball 不含预生成 configure，构建前需
  `autoreconf -fi`（配方 build() 内执行）
- `config.guess` 无法识别 HarmonyOS uname，需显式指定
  `--build/--host=aarch64-unknown-linux-ohos`
- configure 通过 `PKG_CHECK_MODULES(zlib)` 探测 zlib；zlib 缺失时 HAVE_ZLIB
  仍被定义为 0 但源码 `#if defined(HAVE_ZLIB)` 会编译 zlib 代码，导致链接
  失败 —— 需声明 zlib/1.3.1.1 依赖并把依赖 pkgconfig 加入 PKG_CONFIG_PATH
- util/ 下各程序（telnet-client/chatd/proxy/test）链接静态 libtelnet.la 时
  不传递 $(zlib_LIBS)，通过补丁显式追加（见 patches/0001-util-Makefile.am-zlib.patch）

## 依赖

- zlib/1.3.1.1（configure 强链接依赖，已发布制品仓）

## 功能验证

```bash
# 库级 smoke test（test_package 自动执行）
ctest --test-dir test_package/build/clang-15-armv8-17-release   # 1/1 PASS

# 上游协议状态机测试
make check   # run-all.sh 驱动 11 个 .test 场景全部 OK
```

## 参考

- 官网: https://github.com/seanmiddleditch/libtelnet
- 源码: https://github.com/seanmiddleditch/libtelnet/archive/refs/tags/0.23.tar.gz