# bglibs

bglibs 是 Bruce Guenter 维护的 C 基础函数库集合，提供字符串（str）、格式化（fmt）、缓冲 IO（iobuf）、抽象数据类型（adt）、cdb、CRC、加密摘要（md5/sha 系列）、网络（net）与 Unix 辅助（unix）等模块。它是 cvm、vmailmgr 等 untroubled.org 系列工具的基础依赖库。

- 上游：https://untroubled.org/bglibs
- 构建：djb 风格 spac 生成 Makefile（conf-* 配置 + choose 特性探测 + libtool）
- 许可：LGPL-2.1-or-later

## 版本

| 版本 | 状态 | 说明 |
|---|---|---|
| 2.04 | built | aarch64 OHOS 适配完成（静态库），详见 `2.04/notes.md` |
