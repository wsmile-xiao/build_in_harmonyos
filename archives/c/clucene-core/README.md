# clucene-core

CLucene 是流行的 Lucene 全文搜索引擎的 C++ 移植版，提供索引建立、检索、
分析器、查询解析等核心能力。上游 2.3.3.4 为最后一个正式发布版（2011）。

- 上游主页: https://clucene.sourceforge.net/
- 上游源码: https://downloads.sourceforge.net/project/clucene/clucene-core-unstable/2.3/clucene-core-2.3.3.4.tar.gz
- 许可证: LGPL-2.0-or-later OR Apache-2.0
- 构建系统: CMake（旧式，最低声明 2.4.0）

## OHOS 适配状态

| 版本 | 状态 | 说明 |
|------|------|------|
| 2.3.3.4 | built | 上游测试 159/159 通过（官方便携模式） |

关键适配点见版本目录 `2.3.3.4/notes.md` 与 `manifest.yaml`。

## 依赖

- zlib/1.3.1.1（实质依赖；boost 为上游残余探测逻辑，实际无消费，不声明）
