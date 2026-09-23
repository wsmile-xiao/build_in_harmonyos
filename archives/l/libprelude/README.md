# libprelude

> Prelude SIEM 的安全通信库（IDMEF 消息模型 + agent/manager 之间的 TLS 会话）。

## 简介

libprelude 是 Prelude 入侵检测/SIEM 体系的核心库：向上提供 IDMEF
（Intrusion Detection Message Exchange Format，RFC 4765）消息对象的建模、
路径访问、判据（criteria）解析与序列化，向下负责 analyzer ↔ manager 之间的
匿名 TLS / 证书 TLS 会话、事件上报、失败转移（failover）与连接池。Prelude
各组件（`prelude-ls`、`prewikka`、`correlator` 等）都以它为基础。

本次适配对象为 5.2.0（上游最后一个 5.x 正式版，2020-09-09 发布），autotools
构建，唯一强制依赖为 GnuTLS。

## 上游地址说明

原官网域名（`prelude-labs.org` / `www.prelude-siem.org`）已被劫持失效，官方发布页
的 `libprelude-5.2.0.tar.gz` 均为 404，无法校验也无法作为可信源。本目录的配方改用
**Prelude-SIEM 官方 GitHub 组织的 tag 归档** 作为上游源：

```
https://github.com/Prelude-SIEM/libprelude/archive/refs/tags/5.2.0.tar.gz
sha256: 8afcfc92735362834111f63520d8d96fed6f76450da1690678fa0afbfef9d742
```

该归档没有 autoreconf 产物（`configure`/`Makefile.in`/`config.h.in` 未提交），因此
配方在 `build()` 内自举，等价上游 `autogen.sh`。

## OHOS 适配要点

- **自举 + 工具依赖**：`tool_requires` automake/1.18 + libtool/2.5.4，宿主 HNP 提供
  autoconf/autoreconf 2.72；libtoolize 与 automake 的具体顺序见版本目录 `notes.md`。
- **libltdl**：上游用递归 libtool 模式，而制品仓的 libtool 包把独立 libltdl 发行版放在
  `share/libtool/`，配方从该包物化 `libltdl/` 并以 1 个源码补丁切到 subproject 模式，
  避免 `libprelude.so` 带着未定义的 `lt__argz_*` 符号出厂。
- **平台兼容**：config.guess 注入 HarmonyOS 分支（E007）、放宽 `umask 077`（E011）、
  la-free 私有依赖目录规避 `.la` 假路径（E236）、`-Wno-error=int-conversion`
  等旧 C 写法降级（E063）。
- **测试**：上游 `tests/` 9 个程序在 `build()` 里实跑（9/9 通过）；随树发布的 gnulib
  自检 160 项（139 通过 / 18 跳过 / 3 因内核与 libc 语义差异失败）已在报告中如实登记。
- **交付面**：纯库（`libprelude.so.28` + 头文件 + `libprelude.pc` + 配置模板）；
  语言绑定（需 swig）、gtk-doc 文档、`prelude-admin` 等服务端工具均显式关闭或剔除。

## 版本

| 版本 | 状态 | 说明 |
|------|------|------|
| [5.2.0](5.2.0/) | built | 首次适配（OHOS aarch64，clang 15） |
