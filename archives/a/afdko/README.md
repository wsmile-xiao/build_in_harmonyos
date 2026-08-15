# afdko

Adobe Font Development Kit for OpenType（afdko）是 Adobe 出品的字体开发工具集，提供 9 个 C 语言命令行工具（detype1、makeotfexe、mergefonts、rotatefont、sfntdiff、sfntedit、spot、tx、type1）与 Python 工具包，用于 OpenType 字体的开发、校验与转换。

## 功能概述

- 字体格式转换与校验（type1、tx、detype1）
- OpenType 字体构建与合并（makeotfexe、mergefonts）
- 字体变体与旋转（rotatefont）
- 字体数据差异对比（sfntdiff、sfntedit）
- 字体轮廓查看与检查（spot）

## HarmonyOS 适配要点

- 构建系统：CMake + ExternalProject（ANTLR4 runtime 从官方 GitHub tarball 拉取，CI 镜像 fallback）
- 编译器：clang 15.0.4（aarch64-unknown-linux-ohos，OHOS SDK）
- 可执行文件设 RPATH=$ORIGIN/../lib，运行时从包内 lib/ 加载 libxml2
- 上游 pytest 套件部分用例受 HMDFS tmpfile 权限限制（详见 notes.md）

## 依赖

- libxml2/2.15.3.1（conan 依赖，包内自带完整 .so.16.1.3 实体）

## 参考资料

- 上游仓库：https://github.com/adobe-type-tools/afdko
- 许可证：Apache-2.0
