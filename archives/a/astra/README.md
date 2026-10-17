# astra

## 简介

Command-Line Interface for DataStax Astra，上游 datastax/astra-cli 通过 GraalVM native-image（在 GitHub Actions 中完成 AOT 编译）发布为独立 aarch64 glibc 预编译二进制。

## 功能特性

- 管理 DataStax Astra DB 数据库
- 支持数据库创建、列出、删除等操作
- 支持 API Key 管理
- 内置 Shell 补全（bash/zsh）

## 上游信息

- 上游仓库: https://github.com/datastax/astra-cli
- 官方文档: https://docs.datastax.com/en/astra-cli
- 版本: 1.1.0
- 许可证: Apache-2.0

## 鸿蒙适配说明

- 适配路线: 下载上游 GitHub Actions 预编译的 `astra-linux-arm64.tar.gz`，用 git-xet/qsv/spotify_player 验证过的 patchelf + vendor gcompat + build glibc-shim + ELF re-sign 流程把 aarch64 glibc 二进制适配到 OHOS musl，绕过真机无法跑 GraalVM JVM 的硬限制
- 运行时依赖: zlib-ng-compat（提供 libz.so.1）
- 不在本机运行 GraalVM native-image：OHOS HongMeng Kernel 与 HotSpot aarch64 backend 不兼容（JVM SIGILL exit 132，周期 1-9 验证），上游 native-image 已在 GitHub Actions 中完成
- 不 vendor GraalVM JDK / Gradle：astra 二进制适配路线本身不消费 JDK/Gradle；test_package 跑原生 CLI 断言 + CLI determinism 契约测试，不 fork JVM
- 上游 graalvm/gradle 配方已由其他 PR 合入 upstream/main，本 PR 不重复提交

## 版本列表

| 版本 | 状态 | 编译日期 |
|------|------|----------|
| [homebrew](./homebrew/) | pending | TBD |
