# mrename 1.2 适配笔记

## 编译环境
- 构建系统: none（上游发布物只有两个 POSIX shell 脚本，无任何构建系统）
- 编译日期: 2026-09-21
- 编译器: 不适用（解释型脚本，无编译产物）
- 状态: built

## 选型与语言预检（R47 登记）

`lang-preflight` 对本包判定 `detected_language=other`：上游发布树只有
`README`、`mrename`、`mcpmv` 三个文件，脚本无扩展名，故语言统计器取不到
可计数源文件（`build_system: none`，`manifest: 未发现语言 manifest 文件`）。

本包仍按「无构建 / 打包族——解释型脚本工具」适配，依据：

- 本仓库已合并的同形态先例 38 个（`package_type="application"` + 空 `build()`），
  其中 `archives/a/acme.sh/3.1.3` 是纯 shell CLI，同样采用
  libexec + bin wrapper + 软件级 `commands.json` 的布局；
- SKILL v12.21 已为该族类提供 `templates/conanfile-headeronly.py.tmpl` 变体 C
  （解释型脚本工具打包），并明确 R34/R51 同样适用；
- 该族类对 CI 无额外工具链要求（不需要 Rust/OCaml 之类环境），
  W0b 的「历史命令在 CI 环境里逐字可执行吗」判据成立。

## W0 依赖发布检查

配方 `requirements()` / `tool_requires` 均为空，本包对制品仓零依赖，
W0 无待查条目（`finish` 的 R36 依赖检查同样为 0 项）。

运行期只使用 POSIX 基础命令：`sh`、`find`、`sed`、`cp`、`mv`、`ls`、`more`、
`cat`、`rm`，均由系统基础工具集提供，不引入 Conan 依赖。

## 编译步骤

无编译。配方流程为：`source()` 取上游 tarball 并 `apply_conandata_patches()`
→ `build()` 空实现 → `package()` 把两个脚本安装到 `libexec/mrename/`，
在 `bin/mrename` 生成可重定位 wrapper，`README` 作为许可证声明装入 `licenses/`。

wrapper 的职责是把 `libexec/mrename` 前置进 `PATH` 后再 `exec` 真实脚本——
上游 `mrename` 用 `find ./ -name "$1" -exec mcpmv ...` 调用辅助脚本，
`find -exec` 走 `execvp` 语义，必须能从 `PATH` 找到 `mcpmv`；
wrapper 通过解析自身真实路径推导 `libexec` 位置，因此包可安装到任意前缀。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 在 POSIX shell 下运行即报 `[: ==: unexpected operator`，copy/move/help 全部失效 | 脚本 shebang 声明 `#!/bin/sh`，实现却用 bash 专有的 `test ==` 运算符 | `patches/0001-mcpmv.patch`、`0002-mrename.patch`：全部改为 POSIX `=` |
| 2 | `nnumber=$[$number+1]` 在非 bash shell 下不展开，编号恒为空 | `$[ ]` 是 bash 早期废弃语法，POSIX 未定义 | 改为 `$((number + 1))` |
| 3 | `echo -n` 在 dash 等实现下原样打印 `-n`，确认提示串错乱 | `echo -n` 非 POSIX 行为 | 改为 `printf '%s'` |
| 4 | 含空格的文件名被拆成多个参数，重命名失败 | `find -exec` 与 `cp`/`mv` 的参数未加引号 | 传参与命令统一加引号，并用 `--` 终止选项解析 |
| 5 | 安装到非 `/usr/bin` 前缀后 `mcpmv` 找不到，功能静默中断 | 上游假定两个脚本都在 `PATH` 中 | 配方生成 wrapper，按自身路径推导并前置 `libexec` 到 `PATH`（不改上游脚本逻辑） |
| 6 | OHOS CI（构建 #57971）上 move 模式把同一文件改名两次（`c.log` → `pre1c.log` → `pre2pre1c.log`），含空格文件名同样；copy 模式会把刚生成的副本再复制一遍 | 上游 `find ./ -name "$1" -exec mcpmv ...` 在 `find` 仍在读取的目录里边遍历边改名。OHOS 的 `find` 由 toybox 提供，读一个目录项就处理一个；改名产生的新目录项可能出现在当前读取位置之后，于是被再次匹配、再次改名（POSIX 未规定遍历期间新增目录项是否返回）。GNU find 基于 fts 先把整个目录读完再处理，所以桌面 Linux 上看不出来 | `0002-mrename.patch`：先把 `find` 的全部匹配结果存进变量（快照），再逐个调用 `mcpmv`（`IFS` 设为换行、`set -f` 关闭通配，含 `* ? [ ]` 与空格的文件名均安全） |

Debian 侧对同一 bashism 问题的处置是把 shebang 改成 `#!/bin/bash`
（`debian/patches/20-shebang-patch.patch`），等于引入 bash 运行期依赖。
本次适配改为彻底 POSIX 化，保留 `#!/bin/sh`，在 HarmonyOS PC 的基础
shell 环境下即可运行，不要求额外安装 bash。

## 源码修改

- `patches/0001-mcpmv.patch`（+7/-7）：`test ==` → `=`、`$[ ]` → `$(( ))`、
  `cp`/`mv` 参数加引号并加 `--`、`$1` 加引号。
- `patches/0002-mrename.patch`（+20/-7）：`test ==` → `=`（3 处）、
  `[ ! $3 ]` → `[ -z "$3" ]`、`echo -n` → `printf '%s'`；
  `find -exec mcpmv` 改为先快照匹配结果再逐个处理（问题 6），
  传给 `mcpmv` 的参数加引号。

两个补丁都不含平台宏（无 `__OHOS__`），是通用可移植性修复。

## 依赖版本

无第三方依赖。

## 上游测试清点（R51 第 1 步）

| 项 | 结果 | 证据 |
|---|---|---|
| 发布物文件数 | 3 | `tar tzf mrename-upstream-1.2.tar.gz` → `README`、`mcpmv`、`mrename` |
| `tests/` 目录 | 0 | 源码树内无测试目录 |
| 注册测试用例（ctest/pytest/make check） | 0 | 无构建系统，无测试注册点 |
| 上游 CI 配置 | 0 | 源码树无 CI 配置文件 |
| Debian autopkgtest | 0 | salsa `debian/1.2-17` 的 `debian/` 下无 `tests` 目录 |

上游确无测试用例，因此按 R51 第 3 步由 `test_package` 补齐真实功能测试
（18 条断言，其中 dash 轮次仅在 runner 装有 dash 时执行，见 `test_package/MANIFEST.yml`）。

## 验证结果

补丁前后在同一台机器、同一组用例下的对照实验（用例见
`test_package/test_mrename.sh`，11 条通用断言）：

```bash
# A. 未打补丁 + dash（严格 POSIX shell）
$ dash test_mrename.sh <orig>/mrename
passed=5 failed=6
mrename: 93: [: ==: unexpected operator
mrename: 96: [: ==: unexpected operator

# B. 打补丁后 + dash
$ dash test_mrename.sh <patched>/mrename
passed=11 failed=0

# C. 打补丁后 + bash（确认未回退）
$ bash test_mrename.sh <patched>/mrename
passed=11 failed=0
```

### CI 构建 #57971 失败与修复（问题 6）

首次 PR CI（OHOS runner，`/system/bin/sh` 执行）结果为 `passed=11 failed=2`：

```
  FAIL move: renamed file present: expected <1> got <0>
  FAIL spaces: filename preserved: expected <1> got <0>
  skip dash round: dash not installed on this runner
```

本地复现方法：只把 `mrename` 调用的 `find` 换成 toybox 0.8.14（官方静态二进制），
其余条件不变。修复前的包在 ext4 上 move 200 个文件：

| find | 文件系统 | 改名一次 | 改名两次及以上 |
|---|---|---|---|
| GNU find | ext4 | 200 | 0 |
| toybox find | ext4 | 119 | **81** |
| toybox find | tmpfs | 200 | 0 |

文件数 ≤ 60 时本地 ext4 上看不出问题，而 OHOS runner 上单个文件就会触发，
说明是否暴露取决于文件系统的目录项布局——**不能靠小目录测试放心**。
为此 `test_package` 新增 200 文件的 bulk move 断言，并收紧 copy/move 的文件总数断言
（此前 copy 用例只匹配 `item<N>[ab].txt`，漏看了 `item3item1a.txt` 这类二次副本）。

修复后（快照匹配结果再处理）对照：

```bash
# 修复前包 | toybox find | ext4
passed=16 failed=2      # bulk: 200 个只改对 119 个，81 个被改名两次
# 修复后包 | toybox find | ext4 / tmpfs
passed=18 failed=0
# 修复后包 | GNU find | 测试脚本分别用 dash、bash 解释
passed=18 failed=0
# 修复后包 | toybox find | ext4 | 1000 个文件
total=1000 once=1000 twice=0（编号 1..1000 连续）
```

打包后的完整验证（`conan create`，含 `test_package` 18 条断言）结果见
`reports/test-report.md`。

## 注意事项

- 产物全部是解释型脚本，包内没有 ELF 文件，因此不存在交叉架构运行问题：
  `test_package` 是**真实执行**，不是 qemu 模拟。
- dash 轮次只在 runner 装有 dash 时执行：本地 x86_64 runner 上实跑通过；
  OHOS CI runner 没有 dash，测试如实输出 `skip dash round`，不计入通过数。
- 快照按行切分匹配结果，文件名中含换行符的文件不在支持范围内
  （上游 README 本就只面向同一目录下的普通文件名）。
- `package_id()` 调用 `self.info.clear()`：产物与编译器/架构无关，
  同一份包适用于所有目标平台。
- 上游 `mrename -h` 通过 `more` 分页输出帮助；非交互环境下 `more`
  等价直通，测试在管道中读取帮助文本正常。
---

**编译结束**: 2026-09-24 00:30
**最终状态**: built
