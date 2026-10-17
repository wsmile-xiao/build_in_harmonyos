# gumbo-parser

gumbo-parser 是 Google 开发的纯 C99 HTML5 解析库，可将不可信或不完整的 HTML 输入构造成符合 HTML5 解析算法的 DOM 树。

## 功能概述

- HTML5 标记化和树构建
- 错误恢复与 parse error 记录
- UTF-8 输入处理
- C API：`gumbo_parse`、`gumbo_parse_with_options`、`gumbo_destroy_output`

## 安装产物

- 静态库：`libgumbo.a`
- 公共头文件：`gumbo.h`、`tag_enum.h`
- Conan CMake 目标：`gumbo::gumbo`，pkg-config 名：`gumbo`

## OpenHarmony 适配

配方使用 Conan profile 中的 `clang` / `clang++` / `llvm-ar` 直接编译上游 C 源文件生成静态库 `libgumbo.a`，不依赖 Autotools 或 Meson。上游 GoogleTest 子模块不在官方 v0.10.1 tag 归档中，配方另行从官方 GoogleTest `release-1.6.0` 归档补齐并校验 SHA-256，构建时用 `-DGTEST_USE_OWN_TR1_TUPLE=1` 兼容 OHOS libc++。

## 依赖关系

核心库无外部依赖，仅使用 libc。GoogleTest `release-1.6.0` 仅作为构建期测试依赖，不进入发布包。消费者测试直接链接打包后的 `libgumbo.a` 验证公开 C API。

## 版本

| 版本 | 状态 | 编译日期 |
|------|------|----------|
| 0.10.1 | built | 2026-07-23 |

## 参考资料

- 上游仓库：https://github.com/google/gumbo-parser
- 官方源码：https://codeload.github.com/google/gumbo-parser/tar.gz/refs/tags/v0.10.1
- 许可证：Apache-2.0
