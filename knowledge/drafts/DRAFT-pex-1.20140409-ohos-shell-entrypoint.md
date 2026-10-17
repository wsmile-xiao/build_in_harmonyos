# pex 1.20140409 在 OHOS 上的 shell 入口适配（知识库草稿，路径 B）

> 状态：DRAFT，仅作为 `pex` PR #9365 的路径 B 申请候选。
> 最终是否转正、是否认定为 B 类，由知识库维护者和赛事评审决定。

## 适用对象

`pex` 1.20140409 是一个纯 POSIX shell 应用，不生成 C/C++ 二进制。
上游主脚本使用 `#!/bin/sh`，上游测试也由 shell TAP 文件组成。OHOS
目标环境提供的系统 shell 路径是 `/system/bin/sh`，因此“如何启动测试”
和“安装后的 CLI 如何被消费者直接执行”必须分别验证。

## 问题边界

只把测试命令写成：

```text
prove --exec /system/bin/sh t/*.t
```

可以绕开测试启动时的 `/bin/sh` 路径，但不会修改最终安装的
`bin/pex`。如果安装文件仍保留 `#!/bin/sh`，用户通过 `PATH` 直接运行
`pex --help` 时仍可能在解释器查找阶段失败。

只修改安装后的 shebang 也不够：如果上游测试入口仍由环境默认 shell
启动，测试会在测试阶段先失败，无法证明脚本主体在 OHOS 上可执行。

## 推荐做法

1. 在 Conan `build()` 的 OHOS 分支中，以
   `prove --exec /system/bin/sh t/*.t` 启动官方测试。
2. 在 `package()` 阶段只修改安装副本的第一行，将
   `#!/bin/sh` 替换为 `#!/system/bin/sh`。
3. 保持脚本主体为 POSIX shell，不引入 bash 语法或新的运行时依赖。
4. 在 `test_package` 中检查文件可执行、首行 shebang、帮助命令、
   XDG 路径、仓库初始化和错误诊断。

本轮配方采用了上述边界：上游测试副本和安装副本分别处理，未修改
上游命令逻辑。消费者测试共 15 项，独立覆盖了可执行入口和本地仓库
操作。

## 验证证据

- 适配目录：`archives/p/pex/1.20140409`
- 配方：`conanfile.py`
- 消费测试：`test_package/test_pex.sh`
- 预期检查：
  - `head -n 1 <package>/bin/pex` 为 `#!/system/bin/sh` 或兼容的
    POSIX shebang；
  - `test -x <package>/bin/pex` 成功；
  - `/system/bin/sh test_package/test_pex.sh ...` 的 15 项消费断言通过。
- 上游测试入口仍保留为真实命令：
  `prove --exec /system/bin/sh t/*.t`。

## 与已有知识的差异

本条目不是泛化的 Toybox 命令兼容清单，也不是软链接权限问题。它
专门描述一个无编译步骤的 shell application 在 Conan 两个阶段中分别
处理入口路径的办法：build 阶段保证官方测试启动，package 阶段保证
安装后的 CLI 直接执行。

## 不能宣称的结论

- 不能因为 test_package 使用了 `/system/bin/sh`，就宣称所有目标镜像
  都提供 `curl`、`git`、`pg_config`、`psql` 或 Perl。
- 不能把 shebang 修正当成 PostgreSQL 扩展管理流程已经完成验证。
- 不能把本草稿视为已获 B 类认定；它只是与本库真实适配直接相关的
  路径 B 申请材料。

## 来源

- 上游：`https://github.com/petere/pex`
- 版本：`1.20140409`
- PR：`https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos/pull/9365`
- 相关文件：`archives/p/pex/1.20140409/conanfile.py`、
  `archives/p/pex/1.20140409/test_package/test_pex.sh`
