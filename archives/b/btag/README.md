# btag

btag 是一个批量编辑音频文件标签并根据标签内容规范化文件名的命令行工具。

## 功能概述

- 读取和修改 TagLib 支持的音频文件标签。
- 批量设置、过滤和规范化艺术家、专辑、标题等字段。
- 按标签生成文件名，并提供预览改动的 dry-run 模式。
- 提供英语和西班牙语标题大小写规则。

## HarmonyOS 适配

- 使用 Conan 提供的 Boost、TagLib 和 libedit，并生成静态依赖链。
- 保留上游默认的 Boost.Locale 路径；本配方通过能力开关，在当前 OHOS Boost 包不提供该二进制组件时选择标准 C++ 进程 locale 回退。
- 当前 OHOS Conan 仓没有可用的 libcue 配方，因此关闭上游可选的 cue sheet 元数据读取功能；其余核心功能保持启用。
- 上游两个标题大小写 CTest 均在配方构建阶段启用并执行。

## 依赖关系

- Boost 1.84.0
- TagLib 1.13.1
- libedit 20240808
- zlib 1.3.1（由 TagLib 传递引入）

## 参考资料

- [项目主页](https://github.com/fernandotcl/btag)
- [release-1.4.1 源码](https://github.com/fernandotcl/btag/tree/release-1.4.1)
