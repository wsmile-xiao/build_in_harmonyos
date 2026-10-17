# libfixbuf

CERT NetSA IPFIX 协议库 (C, autotools)。

## 版本
- 2.4.1 (2020-12-22): https://tools.netsa.cert.org/releases/libfixbuf-2.4.1.tar.gz

## OHOS 适配
- 构建: autotools configure + make -j1, 纯库 (--disable-tools)。
- 依赖: glib2/2.88.0 (pkgconf 探测)。
- 平台补丁: config.guess/sub 识别 OHOS; configure 临时目录改用 TMPDIR。
- 上游无测试套件 (已审计): test_package 真实调用 InfoModel/Session/Template API (5 断言)。

## 参考
- https://tools.netsa.cert.org/fixbuf2/index.html
- https://tools.netsa.cert.org/fixbuf2/release-history.html
