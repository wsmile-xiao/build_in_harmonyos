# awscli

AWS Command Line Interface v2（`aws`）—— 管理 AWS 云服务的官方命令行工具。

## 简介

- 纯 Python CLI（Apache-2.0），v2 内嵌 vendored botocore/s3transfer
  （`awscli/__init__.py` 的 `TopLevelImportAliasFinder` 完成顶层别名映射），
  无需单独打包 botocore/s3transfer。
- 官方发布形态：PyPI 上的 `awscli` 是 v1 系列，v2 无 PyPI 包；本仓取官方
  GitHub tag 源码。
- 打包方式：`python-require`（copytree 到 `lib/python3.12/site-packages/` +
  生成 `bin/aws` 入口脚本），零 C/C++ 编译。

## 版本

| 版本 | 状态 | 构建日期 |
|---|---|---|
| 2.34.56 | built | 2026-08-27 |

详细适配说明（守护补丁、依赖决策、blocker、测试口径）见各版本目录的
README / notes.md。

## 平台适配要点（OHOS aarch64）

- 启动链依赖的 `awscrt`（C 扩展）与 `distro` 未在 ohpcd 发布，以守护补丁降级
  （`aws --version` 可启动，CRT 功能如实报错）；
- `docutils/0.23` 已发布并实测与 help.py API 兼容，已声明；
- `aws help` 渲染受 OHOS Python subprocess 裸命令名解析限制
  （groff/mandoc 管道不可用，受控报错）。
