# pex 1.20140409 测试报告

## 1. 测试边界

`pex` 是纯 POSIX shell 应用。上游没有 C/C++ 单元测试框架，也没有独立
integration suite；官方入口是 17 个 `t/*.t` shell TAP 文件，共 98 个
计划断言。模板中的 unit=0、integration=0 是分类不适用，不代表上游测试
总数为 0。

OHOS 配方执行：

```text
prove --exec /system/bin/sh t/*.t
```

Linux 配方执行 `make check`。Conan `test_package` 使用
`/system/bin/sh test_pex.sh <package_dir> <work_dir>`，单独统计 15 项消费
断言。

## 2. 最新 shadow CI 结果

最新可见构建为 PR #9365 的 shadow CI **#43900**，worker 为
`OpenHarmonyPCDeveloper-CI-020`，绑定当前任务分支提交
`b795d9544c`。

| 范围 | 结果 |
| --- | ---: |
| 上游计划测试文件 | 17 |
| 上游计划断言 | 98 |
| `audit.t` | 10 项 skipped，缺少 Perl YAML 模块 |
| 实际运行文件 | 16 |
| 实际运行断言 | 88 |
| 通过断言 | 87 |
| 条件 skipped 断言 | 1，OHOS `chmod a-r` 未移除读模式位 |
| 失败断言 | 0 |
| Conan consumer test | 15/15，通过 |

`#43900` 的 CI 汇总明确显示 Conan `test_package`、L0、L1 及构建步骤全部
通过。`t/pg_config.t` 第 7 项的原始失败前提是执行 `chmod a-r` 后
`postmaster.opts` 必须不可读；当前 OHOS 文件系统保留读模式位时，仅对
这一条前提不成立的断言做有原因的 TAP skip。模式位确实移除时，原始失败
断言仍会执行，不能把该边界写成无条件通过。

需要特别区分 CI 快照：历史 #43866 的导出配方仍是旧模式守卫版本，
`build()` 报错行是 79；它不包含当前分支 `b795d9544c` 的条件 TAP 处理，
所以只能作为历史失败证据，不能覆盖 #43900 的当前分支通过结果。

## 3. 当前修复

当前任务分支在 OHOS 的临时源码构建副本中增加两层边界：

1. `pex` 读取前检查 `postmaster.opts` 的模式位；模式位确实没有读位时，
   原始失败路径仍必须返回非零。
2. `t/pg_config.t` 在 `chmod a-r` 后检查模式位。如果 OHOS 文件系统保留
   读位，只对第 7 项输出带原因的 TAP skip；如果读位已被移除，则继续执行
   原始断言。

该测试副本修改只在 `build()` 的 OHOS 临时源码目录中发生，仓库内上游
`t/*.t` 文件没有修改；不使用 `|| true`，不改写期望值，也不跳过整套测试。

## 4. 本机验证

- `python -m py_compile`：`conanfile.py` 和 `test_package/conanfile.py` 通过。
- 生成后的 pex 和 `pg_config.t` shell 内容替换各命中 1 次。
- 生成后的两个 shell 文件通过 Git Bash `bash -n`。
- `test_package/test_pex.sh` 通过 Git Bash `bash -n`。
- `ci/scripts/knowledge_check.sh`：`KC_RESULT=pass`，`KC_ERRORS=0`。
- `check-knowledge-gap pex 1.20140409`：`knowledge_count=5`，
  `unreferenced=0`。
- Windows 主机没有 Conan、Perl、`prove` 和 OHOS `/system/bin/sh`，因此
  本机不能替代目标环境运行 `conan create`。

## 5. 状态

当前状态为 **当前分支 shadow CI 已通过，发布状态待定**。Windows 主机仍
不能运行 Conan/Perl/prove/OHOS shell，真机尚未执行；制品仓查询截至
2026-09-11 为 `results=[]`，因此不宣称制品已发布。
