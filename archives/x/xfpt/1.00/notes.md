# xfpt 1.00 适配笔记

## W0 依赖结论

```text
依赖数量：0
已满足依赖：N/A（无外部依赖）
缺失依赖：无
是否需要拆分依赖适配：否
阻塞点：无
下一步：W4 本机验证 → W5 真机 shadow CI
```

- 上游：https://github.com/PhilipHazel/xfpt （Philip Hazel / University of Cambridge）
- 版本：1.00，tag `xfpt-1.00`，发布于 2023-03-08
- 许可证：GPL-2.0-only（LICENCE 文件为 GPLv2 全文）
- W0 审计结论：xfpt 1.00 为纯 C 项目，`grep -i pcre src/` 无任何匹配，
  链接命令仅 `$(CC) -o xfpt $(OBJ)` —— 历史上的 PCRE 依赖在 1.00 之前已被
  上游移除，仅依赖 libc，无需拆分依赖适配。

## W1 源码/构建系统分析

- 语言：纯 C（src/ 下 8 个 .c：dot/error/globals/misc/para/read/tree/xfpt）
- 构建：autoconf 生成的 configure（configure.ac 无 AC_CANONICAL_HOST、
  无 config.guess/config.sub —— 不会触发 E007 平台识别问题）
  + 顶层 Makefile.in 递归进 src/Makefile
- 关键差异点：
  1. configure 不接受 `--host`（无 canonical host 支持），交叉编译必须以
     `CC=/path/to/clang CFLAGS=...` 变量赋值方式传入（R33：编译器取自
     `tools.build:compiler_executables`）。
  2. `make install` 无 DESTDIR 支持（BINDIR=@prefix@/bin），采用
     `configure --prefix=<build>/prefix` + `make install` 暂存再拷贝。
  3. 运行需要 share 数据（stdflags/stdmacs），编译进 DATADIR，可用 `-S` 覆盖；
     test_package 通过 `-S <pkg>/share/xfpt` 验证打包的 share 数据。
- 上游测试：testing/runtest（Perl 脚本，diff 比对 infiles/outfiles，
  9 个输入文件 + cmd.err 命令行检查）。失败时交互读 /dev/tty。
  本机（Windows）与 CI 均无 perl → build() 中检测到无 perl 时降级跳过并
  记录（工作流 §6.2 要求说明原因），真机 W5 验证。

## W2 配方设计

- `package_type = "application"`，CLI 工具 → 软件级 `commands.json`（R38）
- settings 四项齐全；无 options（非库）
- source：官方 tag 归档（上游 release 页无 asset，tarball 404，tag 归档为
  唯一官方源，R39/PF7 合规）
- 无补丁（patches: []）
- `sh ./configure` 规避 HMDFS 执行权限问题（E087）
- OHOS 上条件自签 ELF（binary-sign-tool 存在时）

## W4 本机验证

- 源码 SHA256 复核：`64cb7ada103ad42849a91f98df1aaa02573dc0784eb2d325f25cba07bc065ff4`（与 conandata.yml 一致）
- Python 语法检查：`python -m py_compile conanfile.py test_package/conanfile.py` 通过
- YAML 结构检查：conandata.yml / manifest.yaml / MANIFEST.yml 解析通过
- JSON 结构检查：commands.json 解析通过
- `git diff --check` 通过
- OHOS 工具链语法验证：用 DevEco SDK clang `--target=aarch64-linux-ohos
  --sysroot=<ohos sysroot> -fsyntax-only` 编译 src/ 全部 8 个 .c 文件通过，
  证明源码无需补丁即可被 OHOS 工具链编译
- 目录边界：改动仅 `archives/x/xfpt/`
- 上游测试：本机无 perl，未执行（见 W0/W1 说明，非静默跳过）
- test_package 等价消费验证：产物为 OHOS aarch64 二进制，本机（Windows）无法
  执行，留待 W5 真机

## W5 真机/shadow CI 结果（已完成，2026-09-29）

设备：HarmonyOS PC aarch64（HongMeng Kernel 1.12.0），job `xfpt-1.00-20260929`，
run 目录 `~/ohos-test-runs/codex-1.00-xfpt-1.00-20260929-conan-*`。

### 迭代记录

| 项 | r1 | r2 | r3 | r4（最终） |
|---|---|---|---|---|
| exit code | 1 | 1 | 1 | **0** |
| 排队 wait_seconds | 5 | — | — | 51 |
| L0 / L1 / L2 / L4 / L5 | KC fail | L1 fail | L1 fail | **全 pass** |
| 报错原文 | `permission denied: bash` | `mktemp: need XXXXXX` | 转换步骤 set -e 退出 | — |
| 根因 | shadow job PATH 缺 `/data/service/hnp/bin`（bash/git 不可达） | toybox mktemp 要求 X 在模板结尾 + /tmp 只读 | 测试输入缺 `.include stdmacs`（.docbook/.book/.chapter 是 stdmacs 宏非内建指令） | — |
| 解法 | job env.sh 追加 hnp PATH（job 环境文件，非基础设施） | 改用 `$TMPDIR/xfpt-test-$$.{txt,xml}` | 输入加入 `.include stdmacs` | — |

### 最终验证（r4）

- `conan create`（ohos-aarch64 profile，clang）：**pass**，包 `xfpt/1.00` 创建成功
- 上游测试：`testing/runtest`（设备有 perl，build() 内自动执行）
  **7/7 通过**：Test command line OK + Test 01–06 OK（100%）
- test_package：**6/6 断言通过**（binary、--version、-help、错误路径、
  DocBook 转换含 share 数据 -S、双输入文件拒绝）
- L1e 破坏性反向验证：`Negative test confirmed — test genuinely depends on xfpt`
- 门禁：G0=pass、G0e=pass、L0=pass、KC=pass、JC=pass、
  **L0/L1/L2/L4/L5 全 pass**，Build Summary Pass rate 100%（1/1）

### W5 执行命令（复现）

```sh
# 隔离 job（设备无 git，--repo-source 指向已有 repo 拷贝）
sh "$HOME/bin/ohos-prepare-isolated-conan-job.sh" \
  --user codex --job xfpt-1.00-20260929 \
  --package archives/x/xfpt/1.00 --repo-source <existing-repo>

# 传输包目录（scp，不走文本管道）后验证：
find archives/x/xfpt -maxdepth 3 -type f | sort

# 排队执行（runner 加 --lock；job env.sh 需含 hnp PATH）
sh "$HOME/ohos-users/codex/xfpt-1.00-20260929/run-conan-heavy.sh"
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | release 下载 URL 404 | 上游 1.00 release 页无 asset，asset 命名不是 xfpt-1.00.tar.gz | 用官方 tag 归档 https://github.com/PhilipHazel/xfpt/archive/refs/tags/xfpt-1.00.tar.gz |
| 2 | git worktree add 两次失败回滚 | 主仓库含文件名带 `\r\r` 的文件（archives/g/gama/2.29/patches/0002-dataparser-ungated.patch\r\r），Windows 文件系统无法检出，worktree add 视为致命 | `worktree add --no-checkout` + 分步 `checkout`，仅该文件检出失败（与主工作区同样显示 D，属既有状态，不处理） |
| 3 | configure 不能用 AutotoolsToolchain --host | 无 AC_CANONICAL_HOST | 手动 `sh ./configure CC=... CFLAGS=...` |
| 4 | make install 无 DESTDIR | 上游 Makefile.in 硬编码 @prefix@ | configure --prefix=<build>/prefix 暂存 |

## 依赖版本

- 无外部依赖（纯 C，仅 libc；PCRE 已被上游在 1.00 前移除）

## 注意事项

- `--version` 输出为 `xpft version 1.00 01-March-2023`（上游 typo "xpft"，
  test_package 断言按 `*"version 1.00"*` 匹配，不依赖 typo 存续）
- 上游 runtest 失败时读 /dev/tty 交互；真机跑时应确保全部通过或重定向
- 不修改基础设施目录；不混入其他库改动

---
**编译状态**: built（真机 shadow CI 全绿：L0/L1/L2/L4/L5 pass，上游测试 7/7，test_package 6/6）
**日期**: 2026-09-29
