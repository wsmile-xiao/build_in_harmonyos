# libecap

## 简介

libecap 是 eCAP 内容适配协议的 C++ 实现库，为 ICAP/eCAP 内容分析与改写
（如 Squid 内容适配）提供 `adapter` / `host` / `common` 三组 API。

## OHOS 适配

- 1.0.1 版本：Autotools 构建（官方 `libecap-1.0.1.tar.gz` 源码包）
- 无外部依赖，仅需 C++ 标准库
- 上游无自带测试套件，适配后以 `test_package` 消费者测试验证

## 依赖

无。

## 功能验证

```bash
conan create archives/l/libecap/1.0.1 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
```

## 参考

- 官网: https://www.e-cap.org/
- 源码: https://www.e-cap.org/archive/libecap-1.0.1.tar.gz
