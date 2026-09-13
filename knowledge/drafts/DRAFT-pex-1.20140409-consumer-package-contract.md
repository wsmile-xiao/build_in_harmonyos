# pex 1.20140409 安装后消费者契约复核（知识库草稿，路径 B）

> 状态：DRAFT，仅作为 `pex` PR #9365 的路径 B 申请候选。
> 最终是否转正、是否认定为 B 类，由知识库维护者和赛事评审决定。

## 为什么需要独立的消费者测试

`pex` 上游测试位于源码工作树的 `t/*.t`，它们能验证源码脚本的
仓库、元数据和 `pg_config` 行为，但不能完整证明 Conan 安装结果满足
消费者契约。OHOS 上尤其需要确认安装后的入口不是仍然指向不存在的
`/bin/sh`，并确认 XDG 数据目录和本地包仓库操作没有因为打包路径变化
而失效。

因此本条目将两类证据分开：

- 上游 TAP：17 个计划文件、98 个计划断言；
- Conan `test_package`：安装后消费者视角的 15 项断言。

消费者通过率不能冒充上游通过率，上游的可选 Perl YAML 依赖和 OHOS
权限语义也不能用消费者测试结果覆盖。

## 本轮 15 项消费者覆盖

`test_package/test_pex.sh` 通过 `/system/bin/sh` 调度并验证：

1. `bin/pex`、man page、README 和 LICENSE 的安装布局；
2. `bin/pex` 可执行位和 OHOS 兼容的 `#!/system/bin/sh` 或 POSIX shebang；
3. `pex --help` 及 `init/install` 命令提示；
4. `XDG_CACHE_HOME` 和 `XDG_DATA_HOME` 对 cache/repository 路径的影响；
5. 本地 Git 仓库初始化，以及 `search`、`cat` 的实际输出；
6. 非法命令的非零返回码和错误诊断。

测试声明和复核口径写入：

```text
archives/p/pex/1.20140409/test_package/MANIFEST.yml
```

其中 `assertion_count: 15` 表示消费者断言数，`test_package_evidence`
记录覆盖范围与 shadow CI #43900 的通过结果；上游测试则由
`upstream_tests` 和 `upstream_test_evidence` 单独声明。

## 验证边界

- Windows 主机只能做 shell 语法和临时 package-layout 验证，不能替代
  Conan、OHOS shell 或目标架构运行；
- shadow CI #43900 已报告 Conan `test_package` 通过，且 L0/L1 门禁通过；
- 制品仓在 2026-09-11 查询仍无 `pex/1.20140409`，不能把 CI 通过写成
  制品已经发布；
- 本条目只说明测试证据如何分层，不代表 B 类认定已经完成。

## 来源

- 上游：`https://github.com/petere/pex`
- 版本：`1.20140409`
- PR：`https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos/pull/9365`
- 配方：`archives/p/pex/1.20140409/conanfile.py`
- 消费者测试：`archives/p/pex/1.20140409/test_package/test_pex.sh`
- 测试声明：`archives/p/pex/1.20140409/test_package/MANIFEST.yml`
