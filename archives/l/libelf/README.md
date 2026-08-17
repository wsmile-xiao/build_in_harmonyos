# libelf — OpenHarmony aarch64 适配

libelf 是一个免费的 ELF 目标文件访问库，提供读取和操作 ELF 格式文件的 API。

## 适配版本

| 版本 | 状态 | 构建系统 | 说明 |
|------|------|----------|------|
| 0.8.13 | built | cmake | 上游 autotools 不完整，使用 CMake 补丁 |

## 编译要点

- 上游 GitHub 镜像源 autotools 文件不完整（缺少 lib/Makefile.in），使用 CMakeLists.txt 补丁替代
- 需要生成 config.h 平台定义文件（aarch64/ohos 特定）
- 无外部依赖（纯 C 库）
