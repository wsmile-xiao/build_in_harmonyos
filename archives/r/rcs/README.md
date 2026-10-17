# GNU RCS

GNU RCS（Revision Control System）是一组管理文件多个修订版本的经典版本控制工具：`ci`（签入）、`co`（签出）、`rcsdiff`（修订间差异）、`rlog`（日志查询）、`rcs`（仓库管理）、`rcsclean`（清理）、`rcsmerge`（分支合并）、`ident`/`merge`。

## 功能概述

- 以 `,v` 后缀的 RCS 文件（`,v` 仓库）保存修订历史、锁与符号名
- `ci`/`co` 支持关键字展开（`$Id$`、`$Log$` 等）、分支、日期/状态选择
- `rcsdiff` 对比工作文件与修订；`rcsmerge` 基于diff3做三方合并
- 产物布局：`bin/` 下 1 个多调用真实二进制 `rcs` + 2 个独立二进制（`ident`、`merge`）+ 6 个 `#!/bin/sh` wrapper（`ci`、`co`、`rcsclean`、`rcsdiff`、`rcsmerge`、`rlog`）

## OHOS 适配

- 构建系统为标准 autotools（tarball 自带 configure 与预生成 Makefile.in，内嵌 gnulib，无 bootstrap）
- `config.guess`/`config.sub` 补丁识别 `aarch64-unknown-linux-ohos`（同 m4/diffutils 先例 E007/E072）
- configure 临时目录 `umask 077`→`022`（E011：HMDFS 无法回读 0700 目录）
- 设备 `/tmp` 只读：`rcs` 内部 `tmpfile(3)` 改为优先 `$TMPDIR`；`mkstemp` 系统临时目录不可用时回退 cwd
- 设备会话 `LOGNAME` 为空且无 passwd 条目：空登录名视为未设置（上游错误提示 "Please setenv LOGNAME" 即此语义），运行/测试环境需提供非空 `LOGNAME`
- HMDFS 忽略 `chmod(2)`，RCS 只读工作文件模型无法表达：上游测试 `t790`/`t900`/`t999` 在设备上无法通过（平台固有限制，其余 60/63 通过）
- 上游测试需以 `make check SHELL=<bash> MAKEINFO=true` 运行：系统 mksh 的 heredoc/命令替换在设备上不可靠，且 GNU make 不读环境变量 `SHELL`

## 依赖关系

- 编译依赖：`ed`（configure 强制探测；运行期仅在 diff3 不完全兼容时用于 `rcsmerge` 回退），通过 conan `tool_requires("ed/1.20")` 提供
- 运行依赖：`diff`（GNU diffutils，`rcsdiff` 必需，设备 `/data/service/hnp/bin` 已有）、`bash`/`sh`（wrapper 解释器，实测 `/bin/sh` 可用，E165）

## 参考资料

- 官网：https://www.gnu.org/software/rcs/
- 上游源码：https://ftp.gnu.org/gnu/rcs/（本包使用内容等价的 Debian orig tarball，见 conandata.yml）
