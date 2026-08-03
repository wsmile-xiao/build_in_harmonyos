# laniakea-spark 0.1.1 编译与验证记录

## 基本信息

- 软件名：laniakea-spark
- 版本：0.1.1
- 源码：https://files.pythonhosted.org/packages/36/88/0062d7ddeef56b5de29fa56449f96b6a2549e05bdd133fc69780a0e9d001/laniakea-spark-0.1.1.tar.gz
- SHA-256：923d3782f1b8f669a461d01207a68d2b2b63ccc41e8d395bb44d1c213d3af967
- License：LGPL-3.0-or-later
- 适配路径：archives/l/laniakea-spark/0.1.1

## 适配方式

- 该包是纯 Python Laniakea job runner。
- 上游 `setup.py` 在构建元数据阶段直接 `from spark import __version__`，PEP517 build isolation 下会触发 `ModuleNotFoundError: spark`；recipe 因此不使用 pip 构建，而是手动复制 `spark/` 模块和数据文件。
- 生成可重定位 `bin/lk-spark` launcher，并提供轻量 `--version` / `--help` 分支，用于 CI 和 test_package 验证；真正 daemon 路径仍转入上游 `spark.cli:daemon`。
- 完整 daemon 运行依赖 Lighthouse 服务、ZeroMQ 证书和 Debian builder 工具，test_package 不伪造这类外部环境。

## 依赖说明

- 上游直接运行依赖：`tomlkit>=0.8`、`pyzmq>=16`、`python-debian>=0.1.28`、`firehose>=0.5`。
- `firehose 0.5` 导入 `firehose.model` 时还需要 `six`，但其 PyPI 元数据未自动安装该依赖；测试环境显式补充 `six==1.17.0`。
- 该 recipe 不声明 native Conan target 依赖；Python 运行依赖由消费环境提供，并在 test_package 中按固定版本安装后验证。

## 上游测试统计

- PyPI 0.1.1 source release 未包含上游 tests 目录。
- 上游测试用例数：0。
- recipe `build()` 执行 `compileall` 语法/字节码检查，不把该检查计为上游测试。

## 新增 test_package 覆盖

1. `lk-spark --version` packaged command。
2. `lk-spark --help` packaged command。
3. `spark` 包导入和版本校验。
4. `LocalConfig._make_client_uuid()` 确定性 UUID。
5. malformed TOML 配置触发 `SystemExit(6)` 故障路径。
6. `spark.connection.JobStatus` 导入，覆盖 pyzmq 相关模块面。
7. `spark.utils.deb822.Changes.add_file()` 生成 md5/sha1/sha256 记录。
8. `spark.utils.firehose.create_firehose()` 创建空报告。
9. invalid firehose report type 触发 `KeyError` 故障路径。

## 已知限制

- HarmonyOS PC 模拟器在线，但当前镜像无 `python/python3`，因此不声明模拟器运行态通过。
- 完整 daemon 需要外部 Lighthouse 服务、证书和 Debian builder 工具，不作为本地离线 test_package 条件。
