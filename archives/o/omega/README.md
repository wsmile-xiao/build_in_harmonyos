# Xapian Omega

## 简介

Omega（Online MultiEngine Gatherer And analyser）是 Xapian 搜索引擎项目的
Web CGI 检索前端组件，随包提供 omindex 文件索引器与 scriptindex 等配套 CLI。
基于 Xapian 概率检索模型，支持 HTML/PDF/Office 等数十种文档格式的索引与
高度可定制的 omegascript 模板输出。

## 基本信息

- **软件名称**: omega（上游包名 xapian-omega）
- **显示名**: Xapian Omega
- **描述**: Xapian 搜索引擎的 CGI 检索前端与文件索引器
- **分类**: utility
- **官网**: https://xapian.org/omega
- **许可证**: GPL-2.0-or-later
- **构建系统**: autotools

## 版本列表

| 版本 | 状态 | 编译日期 |
|------|------|----------|
| 2.0.0 | built | 2026-09-10 |

## OHOS 适配说明

- config.guess/config.sub 识别 HarmonyOS（`uname -s`=HarmonyOS → `aarch64-unknown-linux-ohos`）
- configure 临时目录 umask 022（HMDFS + toybox mktemp 组合兼容）
- 消费 xapian-core 需修正发布包内 `xapian-config` 的 `prefix="/"` 重写产物
  （配方按依赖 package_folder 生成私有可执行副本）
- 静态 libmagic 需 `MAGIC` 环境变量指向包内 `share/misc/magic.mgc`，
  否则 omindex/omindextest 找不到 MIME 数据库
- 上游 `make check` 11 个注册用例已在 build() 内真实执行（真机 11/11 PASS）

## 安装与使用

```bash
conan install --requires=omega/2.0.0 -r=ohpcd
# 产出: bin/{omindex,scriptindex,omindex-list,dbi2omega,mbox2omega}
#       lib/xapian-omega/bin/{omega,mhtml2html,rfc822tohtml,...}
```
