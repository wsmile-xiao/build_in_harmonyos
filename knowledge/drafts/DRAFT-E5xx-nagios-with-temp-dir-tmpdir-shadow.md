# DRAFT: nagios 类 configure 的 --with-temp-dir 覆盖 TMPDIR 问题

## 场景

nagios（及可能的同族软件）在 OHOS 上 configure 通过、编译通过，但运行配置校验（`nagios -v`）或测试时报 `temp_path '/tmp' is not a valid directory`。

## 症状

```
$ nagios -v etc/nagios.cfg
Error: temp_path '/tmp' is not a valid directory
   Error processing main config file!
```
或 configure 后期：
```
./configure[7776]: can't create temporary file /tmp/shXXXXXX.tmp: Read-only file system
```

## 根因

nagios 的 configure.ac 定义了 `--with-temp-dir` 选项，处理逻辑：

```sh
TMPDIR=no
# --with-temp-dir 未传时：
if test "x$TMPDIR" = "xno"; then
    TMPDIR="/tmp"      # ← 无条件覆盖环境继承的 TMPDIR
fi
```

这个**同名 shell 变量 TMPDIR** 遮蔽（shadow）了环境变量——即使 `export TMPDIR=/data/...`，configure 运行到这段后 TMPDIR 也变回只读的 /tmp，并被写进生成的 config.h / locations.h，影响运行时 temp_path 默认值。

## 方案

configure 时显式传 `--with-temp-dir=$TMPDIR`（指向可写目录），让分支走 withval 而非默认 /tmp。

## 边界辨析（AI review 实战沉淀）

`--with-temp-dir` 解决的是「configure 内部 TMPDIR 变量遮蔽环境变量」；**不要扩大为修改 config.guess 的 umask**：

| 场景 | 临时目录路径 | umask 077 是否有问题 |
|---|---|---|
| config.guess `set_cc_for_build()` | `$TMPDIR/cgXXXXXX`（绝对路径，用户属主可写目录） | ❌ 无问题——0700 属主目录进程可访问；umask 077 是上游安全底线（防 TOCTOU），保持不动 |
| config.status | `./confXXXXXX`（相对路径，落在 HMDFS setgid 构建目录） | ✅ 有问题——属主继承为目录属主（≠构建 uid），drwx--S---（2700）构建进程无任何权限（E012/E136）→ conanfile 运行时注入 umask 022（非补丁） |

推论：从社区补丁（如 nylon）沿袭 config.guess umask 修改属于**过度修改**——本地复验证实还原上游 077 后构建测试全绿（nagios 4.5.14 PR #9573）。

## 验证

nagios/4.5.14：加该参数后 configure/编译/测试/`nagios -v` 配置校验全部通过（umask 077 还原后复验仍全绿）。
