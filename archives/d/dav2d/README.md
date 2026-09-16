# dav2d

dav2d is a small and fast AV2 decoder from the VideoLAN project (successor of dav1d for the AV2 codec).

## OHOS 适配

- **构建系统**: Meson 纯 C 配置（`enable_asm=false`，无需 NASM；`enable_tools/examples/docs` 关闭，只产出动态库）。
- **上游测试**: `enable_tests=true` 构建 6 个 header API 测试，`meson test` 在真机执行；`testdata_tests=false`（需额外克隆 dav2d-test-data 仓库）。
- **平台修复**: 复用 libdav1d 1.5.4 已验证的 Meson machine file 补丁（ar/ranlib 绝对路径、shell 脚本编译器包装、`-D_POSIX_C_SOURCE=200809L`、`-Qunused-arguments`）与 ELF 自签名流程。

## 依赖

- 无 Conan 依赖；系统库仅 `pthread`、`libm`（musl 由 libc 提供）。

## 参考

- 上游: https://code.videolan.org/videolan/dav2d
- 首个版本公告: https://www.videolan.org/news.html（2026-05-31 dav2d 新 AV2 解码器）
