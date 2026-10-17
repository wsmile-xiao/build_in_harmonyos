# libcitadel

Citadel 共享工具库, 含 StrBuf、hash、MIME 解析、vCard/vNote 等 Citadel Server、客户端与 WebCit 共用代码。

## OHOS 适配

- 构建系统: autotools (configure + make)
- 依赖: zlib/1.3.1
- 默认静态构建, 保留上游 `libcitadel` ABI 与 `libcitadel.h` 头文件
- 上游 `make check` 在配方 build() 末尾运行

## 依赖

- zlib 1.3.1

## 功能验证

```bash
pkg-config --modversion libcitadel
```

## 参考

- 官网: https://www.citadel.org/
- 源码: http://easyinstall.citadel.org/libcitadel.tar.gz
- 版本锁定包: https://deb.debian.org/debian/pool/main/libc/libcitadel/libcitadel_917.orig.tar.gz
