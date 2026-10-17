# snowball - Snowball 词干算法库（libstemmer）

## 软件概述

Snowball 是 Martin Porter（Porter stemmer 作者）主导的词干提取（stemming）
项目：`algorithms/*.sbl` 用 Snowball 语言描述 29 种语言的词干算法，构建时先用 C
自举编译出 snowball 编译器，再由它生成各算法的 C 源码，与 `runtime/` 一起归档为
`libstemmer.a`。广泛用于搜索引擎（Xapian/Lucene 系）、信息检索与文本挖掘。

### 主要功能

1. **libstemmer C 库**：
   - `sb_stemmer_list()` — 枚举可用算法（29 种语言）
   - `sb_stemmer_new(lang, encoding)` — 创建词干器（语言名/ISO 639 别名）
   - `sb_stemmer_stem()/sb_stemmer_length()/sb_stemmer_delete()` — 提取词干
   - UTF-8 全量支持 + ISO-8859-1/2、KOI8-R 部分语言支持
2. **命令行工具**：
   - `stemwords` — 按 `-c 编码 -l 语言` 对词表/stdin 做词干提取
3. **算法**：阿拉伯语、亚美尼亚语、巴斯克语、加泰罗尼亚语、丹麦语、荷兰语、
   英语、芬兰语、法语、德语、希腊语、印地语、匈牙利语、印尼语、爱尔兰语、
   意大利语、立陶宛语、尼泊尔语、挪威语、porter（传统 Porter）、葡萄牙语、
   罗马尼亚语、俄语、塞尔维亚语、西班牙语、瑞典语、泰米尔语、土耳其语、
   意第绪语，共 29 种

## OHOS 适配

- **零补丁、零源码修改、零平台 flag**：纯 C + 单 GNUmakefile，开箱即编
  （适配机器实测 `make check` 全量 49 目标通过）
- CC/AR/RANLIB 由配方命令行注入（Conan conf，R33）
- 构建期需要 perl（`libstemmer/*.pl` 生成算法清单，env shebang）——
  ohos-aarch64 profile buildenv PATH 已含
- R9：全部 make 单作业（-j1）
- 默认静态库（R26）

## 依赖关系

- 编译依赖：无（零外部依赖，W0 核验）
- 运行依赖：无（系统 libc）
- 构建期工具：clang、llvm-ar、perl（profile 环境提供）

## 参考资料

- 官网: https://snowballstem.org/
- 源码: https://github.com/snowballstem/snowball
- 测试数据仓（不入库，仅验证用）: https://github.com/snowballstem/snowball-data
