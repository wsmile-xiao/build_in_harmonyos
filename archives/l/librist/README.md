# librist

RIST（Reliable Internet Stream Transport，可靠互联网流传输）协议的 C 实现
（VideoLAN RIST 项目，BSD-2-Clause），用于低延迟音视频流传输。
FFmpeg/OBS 通过它收发 `rist://` 流。

## OHOS 适配

- **构建系统**: Meson（上游唯一构建系统）
- **依赖策略**: cJSON 与 mbedtls 均使用上游自带的 contrib 内嵌源码，
  零外部 Conan 依赖；cmocka 仅作测试期 `test_requires`
- **编译选项**: `built_tools=false`（关闭需 libmicrohttpd 的 CLI 工具，
  保持最小依赖面）；`-Dtest=true` 全量执行上游测试

## 依赖

- 无常规依赖（自包含）
- 测试期：`cmocka/2.0.2`

## 功能验证

```bash
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
# 期望：meson test 全量通过＋test_package 双用例通过
```

## 参考

- 官网: https://code.videolan.org/rist/librist
- 源码: https://code.videolan.org/rist/librist/-/archive/v0.2.18/librist-v0.2.18.tar.gz
