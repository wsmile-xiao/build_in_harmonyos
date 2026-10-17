# rset 3.3 适配笔记

## 编译环境
- 构建系统: makefile（自研 configure sh 脚本 + BSD-style Makefile）
- 编译日期: 2026-10-03
- 编译器: clang 15.0.4 (aarch64-linux-ohos)
- 状态: built

## 编译步骤

```bash
TARGET_OS=Linux CC=clang ./configure   # 内部探测 strlcpy/arc4random → 选 Makefile.linux
make CC=clang -j1                      # 产物: rset miniquark renv rinstall rsub labelgrep rexec-summary
make install CC=clang PREFIX=$TEST_PREFIX
```

conan build() 中：`TARGET_OS=Linux CC={cc} {CONFIG_SHELL} ./configure` + `make CC={cc} -j1`（R33：CC 来自 Conan conf，非 shell env）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 复制 Makefile.bsd，构建失败 | 上游 `case $(uname)` 只识别 Darwin/FreeBSD/Linux；OHOS `uname` 返回 `HarmonyOS` 落入 `*)` 分支 | `TARGET_OS=Linux` 环境变量显式覆盖（configure 支持）；OHOS 为 musl libc，strlcpy/arc4random 探测通过，Makefile.linux 正常工作 |
| 2 | make 使用 `cc`，设备无该符号链接 | Makefile 未定义 CC 默认值依赖系统 cc | make 命令行传 `CC=clang`；conan 配方中来自 `tools.build:compiler_executables:c` |
| 3 | `make -j2` 报 jobserver mkfifo Operation not permitted | E074: HMDFS 禁 FIFO | 固定 `-j1` |
| 4 | `renv - -q` 失败 `awk: Unknown option 'q'` | OHOS `/usr/bin/awk` 是 toybox 0.8.12，违反 POSIX 将首个操作数之后的 `-q` 当 awk 选项；gawk 正常。rset 核心（input.c:496）调用 `renv - -q`，属真实功能障碍 | 补丁 0001：renv.awk 改为 `#!/bin/sh` + `exec awk -f /dev/fd/3 -- "$@" 3<<'EOF'` 单文件 polyglot，`--` 终止选项解析，脚本参数原样透传；单文件性质保留（rset 会把 renv 复制到远端 staging） |
| 5 | copyfile 报 `copy failed` | rutils.c `install_if_new` 硬编码 `execl("/usr/bin/install")`，OHOS 无 /usr/bin/install（仅 /bin/install） | 补丁 0002：/usr/bin/install 失败后回退 execl("/bin/install") |
| 6 | 编译产物执行报 `Operation not permitted (rc=126)` | E077: OHOS 内核拒绝加载无 .codesign 签名段的 ELF | binary-sign-tool sign -selfSign 1；conan package() 对 rset/miniquark 签名（脚本类 renv/rinstall/rsub/labelgrep/rexec-summary 无需） |
| 7 | tests/ 构建失败 `llvm-ld: No such file or directory` | LLVM 15 移除 llvm-ld；tests/Makefile 默认 LD=llvm-ld | 本地探索用 `LD=ld.lld`（链接 rset.o 可重定位目标）；conan 配方不构建 tests，无影响 |
| 8 | 上游 Ruby 测试中 WEBrick 文件下载全部 rc=18 (partial file) | OHOS ruby 3.4.5 的 IO.copy_stream 走 copy_file_range，在 HMDFS 上返回 EBADF，WEBrick 响应体发送中断 | 测试环境 preload 补丁（~/tmp/rset-test/cfr_fix.rb）覆写 IO.copy_stream 回退 read/write 循环；未改动上游代码与 gem，conan 配方不涉及（CI 无 ruby） |
| 9 | 权限断言类测试失败（mode 100660/100770 vs 期望 100644/100755） | E046: HMDFS chmod 被忽略，文件权限固定 660 | 平台限制，无法在本地文件系统修复；3 个测试用例因此失败，详见验证结果 |

## 源码修改

| 补丁 | 修改内容 | type |
|------|----------|------|
| 0001-renv.awk.patch | shebang 改 /bin/sh + fd3 heredoc polyglot，绕过 toybox awk 参数解析缺陷 | portability |
| 0002-rutils.c.patch | install_if_new 增加 /bin/install 回退 | portability |

两补丁均无平台条件编译宏（R8/PF5）。

## 依赖版本

无第三方依赖（纯 C99 + POSIX，libc: musl）。

## 验证结果

### 上游测试（R51 三步法）

- 清点：tests/ 目录 7 个 Ruby 测试脚本 + 13 个 C 辅助程序（tests/Makefile 注册），无 make check 目标
- 运行：本机 ruby 3.4.5 + webrick（bundler/inline），`ruby tests/test_*.rb` 逐个执行
- 结果：**37/40 通过（92.5%）**
  - test_renv 7/7 ✓（补丁 0001 后）
  - test_rsub 8/8 ✓
  - test_rset_worker 7/7 ✓
  - test_labelgrep 2/2 ✓
  - test_rinstall 1/2（失败例：`File.stat(dst).mode == 100644` 断言，实测 100660 —— E046 chmod 固定 660）
  - test_rset 1/2（失败例：dst mode 100755 断言，实测 100770 —— E046）
  - test_miniquark 11/12（失败例：`GET a file that does not have read permission` 期望 403，HMDFS 上 chmod 000 无效仍返回 200 —— E046）
- 3 个失败全部为 E046 平台限制（HMDFS 忽略 chmod），非功能缺陷；上游测试依赖 ruby，CI 环境无 ruby，故 test_package 采用消费者视角 smoke test

### test_package

见 test_package/test.sh：rset -V 版本断言、renv 过滤与 -q 错误路径（验证补丁 0001）、labelgrep 标签匹配、rinstall staging 安装内容校验、miniquark 可执行性。

## 交付物

| 文件 | 说明 |
|------|------|
| bin/rset | 主程序（Remote Staging Execution Tool） |
| bin/miniquark | 极简 HTTP 文件服务器（远端 staging 用） |
| bin/renv | awk 环境变量过滤脚本 |
| bin/rinstall | staging 安装辅助 sh 脚本 |
| bin/rsub | pln 块编辑 sh 脚本 |
| bin/labelgrep | pln 标签搜索 awk 脚本 |
| bin/rexec-summary | 并行执行日志汇总 awk 脚本 |
| share/man/man1/*.1, man5/pln.5 | 手册页 |

## 注意事项

- rset 是远程执行工具：本机产物可用性验证通过（-V/usage/renv/labelgrep），完整跨主机工作流需要 ssh(1) 到目标机，CI/测试环境无法覆盖，已在 test_package 说明
- conan 配方不执行上游 Ruby 测试套件（CI 无 ruby/bundler），已按 R34 提供实质消费端验证
- 制品仓 remote：ohpcd
## 对话记录

### 对话 #1（2026-10-03）

- 状态: built
- 编译命令：`TARGET_OS=Linux CC=clang ./configure && make CC=clang -j1`（E074 禁 -j2）
- 耗时：configure <1s，make -j1 约 30s（7 个 C 文件）
- 结果：7 个产物全部编译安装成功，conan create + test_package 全绿；上游 Ruby 套件 37/40（3 个失败均为 E046 权限断言）
- 遇到的问题：见上文「遇到的问题与解决方案」表
---

**编译结束**: 2026-10-03 09:17
**最终状态**: built
