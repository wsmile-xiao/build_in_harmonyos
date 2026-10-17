# adobe-source-han-serif-jp

Adobe Source Han Serif JP 提供面向日本地区字形规范的开源 OpenType/CFF 字体。

## 功能概述

- 提供 ExtraLight、Light、Regular、Medium、SemiBold、Bold、Heavy 七种字重。
- 使用日文地区字形。
- 使用 SIL Open Font License 1.1 发布。

## OHOS 适配

字体是平台无关的数据资源，不需要修改上游文件。Conan 包将七个 OTF 字体安装到
`share/fonts/adobe-source-han-serif-jp/`，并通过 `cpp_info.resdirs` 暴露资源目录。
消费者测试会逐个解析实际字体的 SFNT/OpenType 表目录和必要表。

## 依赖关系

无编译依赖和运行时依赖。

## 参考资料

- 发布与下载说明：https://github.com/adobe-fonts/source-han-serif/tree/release
- 源码仓库：https://github.com/adobe-fonts/source-han-serif
