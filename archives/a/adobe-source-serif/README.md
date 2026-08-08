# adobe-source-serif

Source Serif 4 是 Adobe 发布的开源衬线字体家族，包含多种光学尺寸、字重和可变字体。

## 功能概述

- 提供桌面 OTF 与 TTF 静态字体。
- 提供 Roman 与 Italic 可变字体。
- 使用 SIL Open Font License 1.1 发布。

## OHOS 适配

字体是平台无关的数据资源，不需要修改上游文件。Conan 包将字体安装到
`share/fonts/adobe-source-serif/`，并通过 `cpp_info.resdirs` 暴露资源目录。
消费者测试会读取实际包内字体，解析 SFNT/OpenType 表目录并验证必要表。

## 依赖关系

无编译依赖和运行时依赖。

## 参考资料

- 官网：https://adobe-fonts.github.io/source-serif/
- 源码仓库：https://github.com/adobe-fonts/source-serif
