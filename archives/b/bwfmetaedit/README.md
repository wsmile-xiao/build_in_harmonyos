# BWF MetaEdit

BWF MetaEdit 是一个用于广播波形格式（BWF）文件的元数据编辑工具，支持嵌入、验证和导出 BWF 文件中的元数据。

## 功能概述

- 导入、编辑、嵌入和导出 WAVE 音频文件中的指定元数据元素
- 从 Format Chunks 和 bext/INFO chunks 导出技术元数据（CSV/XML）
- 评估、验证和嵌入 MD5 校验和（应用于 WAVE 文件的数据块）
- 生成显示 WAVE 文件构造错误的报告
- 支持联邦机构音频-视觉工作组指南（FADGI）和 EBU 规范

## OHOS 适配要点

1. **构建系统位置**：CLI 版本的构建系统位于 `Project/GNU/CLI` 目录，非标准位置
2. **自动生成 configure**：需要先运行 `autogen.sh` 生成 configure 脚本
3. **HMDFS 权限问题**（E011）：configure 脚本中 `umask 077` 在 HMDFS 上会导致目录对当前进程不可写，需修改为 `umask 022`
4. **pthread_cancel 限制**（PSCAN-MUSL-001）：musl/OHOS 不支持 `pthread_cancel`，需添加 `#ifdef __OHOS__` 条件编译跳过相关代码

## 依赖关系

### 编译依赖
- zlib（压缩库）
- automake、autoconf、libtool（构建工具）

### 运行依赖
- 无额外依赖（静态链接）

## 参考资料

- 官网：https://mediaarea.net/BWFMetaEdit
- 源码：https://github.com/MediaArea/BWFMetaEdit
- FADGI 指南：http://www.digitizationguidelines.gov/guidelines/digitize-embedding.html