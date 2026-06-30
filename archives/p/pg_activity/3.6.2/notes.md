# pg_activity 3.6.2 适配笔记

## 编译环境
- 构建系统: Python/setuptools (pyproject.toml)
- 编译日期: 2026-06-09
- 编译器: Python 3.12.8 + setuptools
- 状态: built

## 编译步骤

pg_activity 是纯 Python 项目，使用 pip wheel + --target 方式安装。

1. 构建 wheel: `python3 -m pip wheel . --wheel-dir=$TMPDIR/wheels_pg_activity --no-deps`
2. 安装到 staging (DESTDIR模式): `python3 -m pip install wheel --target=$STAGING_PREFIX/lib/python3.12/site-packages --no-deps`
3. 创建入口脚本: 手动创建 $STAGING_PREFIX/bin/pg_activity (console_scripts entry point)
4. 安装到本地 ($DEFAULT_PREFIX): 同上步骤但目标为 $DEFAULT_PREFIX

### pip --prefix/--root 问题
pip 在此平台不支持 --prefix + --root 同时使用（报错 "Cannot set --home and --prefix together"），
因此使用 --target 替代 DESTDIR 模式安装 Python 包。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | SSL证书下载失败 | 系统SSL证书链不完整 | curl -k 手动下载 + init-build --no-download |
| 2 | pip --prefix + --root 冲突 | pip bug: "Cannot set --home and --prefix together" | 使用 pip --target 替代 DESTDIR |
| 3 | console script未生成 | pip --target 不创建 bin/ 入口脚本 | 手动创建 entry point wrapper |
| 4 | PYTHONPATH 不生效 | 此系统 Python 忽略 PYTHONPATH | 创建 .pth 文件添加路径 |
| 5 | psycopg/psycopg2 不可用 | 无 aarch64-ohos 二进制 wheel | 标记为可选运行时依赖 |

## 源码修改

无源码修改。pg_activity 是纯 Python 项目，无 C 扩展，无需适配 OpenHarmony。

## 依赖版本

| 依赖 | 版本 | 类型 |
|------|------|------|
| attrs | 26.1.0 | 必需 |
| blessed | 1.44.0 | 必需 |
| humanize | 4.15.0 | 必需 |
| psutil | 6.1.1 (系统自带) | 必需 |
| psycopg/psycopg2 | N/A | 可选运行时 |

## 验证结果

```bash
$ python3 -c "import pgactivity; print(pgactivity.__version__)"
3.6.2
```

pg_activity --version 需要 psycopg/psycopg2（可选运行时依赖），无 PG 服务器时不可用。

## 交付物

| 文件 | 说明 |
|------|------|
| packaging/pg_activity-3.6.2-ohos-aarch64.tar.gz | 预编译包（标准） |
| packaging/pg_activity-3.6.2-ohos-aarch64-debug.tar.gz | 预编译包（调试） |

## 注意事项

1. pg_activity 是 PostgreSQL 监控工具，运行时需要 PostgreSQL 连接
2. psycopg/psycopg2 是可选运行时依赖，不在打包中（用户自行安装）
3. 安装后需配置 PYTHONPATH 或 .pth 文件使 Python 能找到 pgactivity 模块
---

**编译结束**: 2026-06-09 21:10
**最终状态**: built
