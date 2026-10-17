# wwl 1.3-db 适配笔记

## 编译环境
- 构建系统: makefile（手写 Makefile，无 configure）
- 编译日期: 2026-09-23
- 编译器: clang 15（OHOS SDK 26.0.0.18）
- 状态: built

## 编译步骤

1. 从 Debian pool 取上游发布的 `wwl_1.3+db.orig.tar.gz`（HTTPS，sha256 已固定）。
2. `make CC=<ohos clang> CFLAGS="-Wall -O2" -j1`，产出 `wwl`，并生成 `locator` 符号链接。
3. `package()` 安装 `bin/wwl`、`bin/locator`（真实副本）、`share/man/man1/wwl.1` 与 `locator.1`。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 源码只在明文 HTTP 主机发布 | 上游 `http://www.db.net/downloads/wwl+db-1.3.tgz`，而仓库规则禁止 conandata 出现明文 `http://` | 改用 Debian 同版本 `.orig.tar.gz`（HTTPS）并固定 sha256 |
| 2 | `locator` 模式如何分发 | 程序用 `basename(argv[0]) == "locator"` 选择模式 | 打包时把 `wwl` 复制为 `bin/locator` 并 `chmod 0755`，不依赖符号链接 |
| 3 | 上游无测试套件 | Makefile 无 `check`/`ctest` | 消费者测试覆盖 wwl(1) 手册中的全部算例（N=0，走补全口径） |

## 依赖版本

无三方依赖（仅 libc 与 libm）。

## 验证结果

```bash
# 上游测试：无（N=0）
# 消费者（test_package/test_wwl.sh）
WWL_CHECK_SUMMARY checks=10 fails=0
```

## 注意事项

- `wwl`/`locator` 的期望值取自上游 `wwl.1` 手册的算例，可在任意平台上复现。
