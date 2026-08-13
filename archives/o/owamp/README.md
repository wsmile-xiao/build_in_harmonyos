# owamp

One-Way Active Measurement Protocol (OWAMP) 客户端/服务端工具包（RFC 4656）——测量两台主机之间的单向时延。

- 上游: https://software.internet2.edu/owamp/ （源码包 owamp-3.4-10.tar.gz）
- 版本: 3.4-10
- 许可证: Apache-2.0
- 产物: `owampd`（服务端）、`owping`/`owstats`/`owfetch`/`owup`（客户端）、`powstream`（连续测试守护进程）、`owtvec`（上游测试程序）、`libowamp.a`

## 适配说明（HarmonyOS PC / aarch64）

上游 tarball 自带 2014 版 configure（config.sub 2009 版不识别 `aarch64-unknown-linux-ohos`），
配方在 build() 中 `autoreconf -fi` 重新生成 autotools 文件；configure.ac 硬性依赖
i2util/1.2（`AC_SEARCH_LIBS I2AddrByNode` + 头文件检查，缺失即 configure 报错），由
已发布的 i2util/1.2 提供。适配补丁 5 个，详情见 `3.0.8/notes.md`（应为 `3.4-10/notes.md`）。
