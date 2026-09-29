# rulex

RuLex 是俄语发音词典及其访问库，提供 `librulexdb`、词典管理工具
`lexholder-ru` 和文本重音标注工具 `rulex`。

## 功能概述

- 使用 Berkeley DB 保存显式词典、隐式词典和发音规则。
- 通过 `librulexdb` 公共 C API 创建、查询和更新词典。
- 使用 `lexholder-ru` 构建、检查、检索和维护词典数据库。
- 使用 `rulex` 对 KOI8-R 俄语文本进行发音标注。

## HarmonyOS PC 适配

- 使用 Conan 中已发布的 `berkeley-db5/5.3.28`，不依赖系统隐式库。
- 使用字节语义的 locale 和等价的 KOI8-R 大小写映射，避免 OHOS libc 将
  单字节词典正则误判为无效多字节输入，保留完整词典构建和查询能力。
- 完整运行上游 430,015 条词典验证，并增加库 API 与无 KOI8-R locale
  的 HarmonyOS 专项测试。

## 依赖关系

- 构建工具：Autoconf、Automake、Libtool、Autoconf Archive。
- 编译和运行依赖：`berkeley-db5/5.3.28`。

## 参考资料

- 上游仓库：https://github.com/poretsky/rulex
- 项目说明：https://github.com/poretsky/rulex#readme
