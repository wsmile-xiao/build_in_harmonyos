# adobe-source-han-serif-otc

Adobe Source Han Serif OTC 提供泛中日韩（Pan-CJK）OpenType Collection 字体。

## 功能概述

- 提供 ExtraLight、Light、Regular、Medium、SemiBold、Bold、Heavy 七种字重。
- 每个 TTC 集合包含日文、韩文、简体中文、繁体中文和香港繁体中文五个字体面。
- 使用 SIL Open Font License 1.1 发布。

## OHOS 适配

字体是平台无关的数据资源，不需要修改上游文件。Conan 包将七个 TTC 字体集合安装到
`share/fonts/adobe-source-han-serif-otc/`，并通过 `cpp_info.resdirs` 暴露资源目录。
消费测试会解析实际 TTC 集合头、全部 35 个 SFNT 字体面、表目录和必要表。

## 依赖关系

无编译依赖和运行时依赖。

## 参考资料

- 发布页：https://github.com/adobe-fonts/source-han-serif/releases/tag/2.003R
- 源码仓库：https://github.com/adobe-fonts/source-han-serif
