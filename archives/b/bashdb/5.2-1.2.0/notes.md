# bashdb 5.2-1.2.0 适配笔记

## 编译环境
- 构建系统: autotools（源码包不含 configure，需 autogen.sh 生成）
- 编译日期: 2026-08-14
- 编译器: clang/clang++（bashdb 纯 bash 脚本，无 C 代码）
- 状态: published
- 平台: OpenHarmony PC (aarch64)，bash 依赖 bash/5.3（ohpcd 制品仓）

## 编译步骤

1. `NOCONFIGURE=1 bash autogen.sh`（内部 autoreconf --install 生成 configure；NOCONFIGURE=1 防止 autogen.sh 自动运行 configure）
2. `bash configure --prefix=$PREFIX --build=aarch64-unknown-linux-gnu`（显式用 bash 运行 configure，绕开 HarmonyOS shebang 脚本执行限制）
3. `make SHELL=bash MAKEINFO=true -j1`（SHELL=bash 因为 /bin/sh 对 make 的 jobserver/权限有限制；MAKEINFO=true 跳过 makeinfo 缺失的 doc 生成）
4. `make check SHELL=bash MAKEINFO=true LOG_COMPILER=bash`（LOG_COMPILER=bash 使集成测试用 bash 显式运行，绕开 shebang 限制）
5. `make install SHELL=bash`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 拒绝 bash 5.3 | configure.ac 版本检查只接受 '5.0'/'5.1'（case 分支，'OK_BASH_VERS' 单引号内不展开） | 补丁 0001：case 加入 '5.2'/'5.3' |
| 2 | shunit2 测试全 FAIL: "please declare TMPDIR with path on partition with exec permission" | HarmonyOS 拒绝通过 shebang 执行脚本文件（bad interpreter: Permission denied），shunit2 的 noexec phantom 检查失败 | 补丁 0012：phantom 文件去掉 shebang（bash 可解释无 shebang 文本脚本） |
| 3 | `info variables` 报 /dev/fd/63: Permission denied | bash 进程替换 `< <(...)` 依赖 /dev/fd，HarmonyOS 不可访问 | 补丁 0002：进程替换改为命令替换+here-string `<<< "$(declare)"` |
| 4 | bashdb 临时文件写入 /tmp 失败（Read-only file system） | bashdb 默认 _Dbg_tmpdir=/tmp，HarmonyOS /tmp 只读（E002） | 补丁 0003：默认改用 ${TMPDIR:-/tmp} |
| 5 | 集成测试过滤文件写 /tmp 失败 | check-common.sh.in 及多个 test-*.in 硬编码 /tmp | 补丁 0004-0009：改为 ${TMPDIR:-/tmp} |
| 6 | test-misc 的 tty 命令因 /tmp 只读失败 | misc.cmd `tty /tmp/misc-output.check` 无法写入 | 补丁 0010-0011：tty 目标改为相对路径 ./misc-output.check |
| 7 | 集成测试 shebang 执行失败（/usr/bin/env 不存在 + HarmonyOS shebang 限制） | test-*.in shebang `#!/usr/bin/env bash`；make check 直接 exec 测试脚本 | make check 加 LOG_COMPILER=bash；配方的 make check 命令已含 LOG_COMPILER=bash |
| 8 | autoreconf 需要 aclocal/automake，环境缺失 | 本地 OpenDesk 环境无 automake 包 | 本地编译安装 automake 1.17 到 $HOME/.opendesk-tmp/autotools（CI 环境已预装 autotools）；构建时 PATH 需包含 |
| 9 | conan 命令 shebang 损坏 | pip 安装的 conan 脚本 shebang 指向不可执行解释器 | 编译 C wrapper（exec python3.12 -m conans.conan）放入 PATH 前置 |
| 10 | make 使用 /bin/sh 报错 | make 默认 SHELL=/bin/sh 权限受限 | 所有 make 命令显式 SHELL=bash |

## 源码修改（补丁）

| 补丁 | 文件 | 修改内容 |
|------|------|----------|
| 0001 | configure.ac | bash 版本检查支持 5.2/5.3 |
| 0002 | command/info_sub/variables.sh | 进程替换 → here-string（/dev/fd 限制） |
| 0003 | init/opts.sh | _Dbg_tmpdir 默认用 $TMPDIR（/tmp 只读） |
| 0004 | test/integration/check-common.sh.in | 过滤文件写 $TMPDIR |
| 0005-0009 | test/integration/test-*.in（5 个） | 过滤文件写 $TMPDIR |
| 0010 | test/data/misc-output-50.right | tty 期望路径更新 |
| 0011 | test/data/misc.cmd | tty 目标改相对路径 |
| 0012 | test/unit/shunit2 | phantom 文件去掉 shebang |

## 依赖版本

- bash/5.3（ohpcd 制品仓，运行时依赖）
- automake 1.18 / libtool 2.5.4 / pygments 2.20.0（tool_requires，构建期自解析；
  automake 提供 aclocal 解决 CI 缺 autotools（E178），pygments 让 test-bug-loc 可运行）
- autoconf 2.72 / perl 5.42.0（CI 预装）

## 验证结果

```bash
# make check（全部通过）
test/unit:     25 PASS, 0 FAIL, 0 SKIP
test/integration: 45 PASS, 0 FAIL, 1 SKIP（test-sig 上游自禁 exit 77；其余含 test-bug-loc 全部通过）

# bashdb 实际运行
bashdb --version              → bashdb, release 5.2-1.2.0
bashdb --library ... test.sh  → 调试会话正常（That's all, folks...）
```

## 注意事项

- bashdb 为纯 bash 调试器，无 C 库；制品为 bin/bashdb + share/bashdb/*.sh
- bashdb 运行依赖 bash 的 --debugger 支持（制品仓 bash/5.3 已编译 debugger 支持）
- 集成测试的 tty 目标改为相对路径，运行目录需可写
- conan-verify G2（conan create）需 PATH 包含 automake（本地环境）；CI 环境已预装
---

**编译结束**: 2026-08-14 04:02
**最终状态**: published
