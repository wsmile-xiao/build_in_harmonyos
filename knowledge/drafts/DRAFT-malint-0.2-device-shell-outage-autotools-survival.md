# DRAFT-malint-0.2-device-shell-outage-autotools-survival — 真机系统 shell 双故障（/bin/sh 与 hnp bash 同时不可用）时的 autotools 构建存活链

> 触发实例: malint 0.2 HarmonyOS PC shadow CI（2026-10-01，job malint-0.2-20261001，r1–r5 五轮迭代）
> 库类型: 纯 C autotools 命令行工具（autoconf 2.59 官方 tarball，自带 configure）

## 问题

真机进入异常状态：`/data/service/hnp/bin/bash` 对用户完全不可访问（连
`ls` 都 Permission denied，同期其它库的 shadow CI run 在 KC 门禁同样挂掉），
`/bin/sh -c` 执行挂死或被拒，`/tmp` 只读。此状态下 autotools 包的 shadow CI
呈现三种连锁症状：

```
# 症状 1：CI KC 门禁（build_and_test.sh 内 `bash knowledge_check.sh`）
ci/conan/build_and_test.sh:980: permission denied: bash
[fail] KC: knowledge check failed — blocking build

# 症状 2：配方执行 configure（经 bash -c "./configure ..."）
bash: ./configure: /bin/sh: bad interpreter: Permission denied

# 症状 3：configure 的编译器检测（PATH 中的 cc 是 shebang 失效的 HMDFS 包装）
./configure: /storage/Users/currentUser/usr/local/bin/cc: /bin/sh: bad interpreter: Permission denied
```

设备上唯一可用 shell 是 HMDFS 的 `zsh`（/storage/.../usr/local/bin/zsh）。

## 根因

设备 shell 基础设施故障（疑似系统 bash ELF 签名/标签失效，E077/E009 家族），
不是包或配方的问题。识别要点：**同期其它库的 run 以相同方式失败**——先对比
`ls -dt ~/ohos-test-runs/*/` 里最近失败 run 的 stdout，确认是设备级故障再动手，
不要盲目改配方。

连锁机理：
1. CI/配方调 `bash` → 解析到死掉的 hnp bash → permission denied；
2. 换活的 shell（zsh）执行 `./configure` 时，zsh 读到 shebang `#!/bin/sh`
   去 exec /bin/sh → 同样故障 → bad interpreter；
3. configure 探测编译器时 PATH 中的 `cc`/`gcc` 若是 HMDFS 包装脚本
   （shebang 依赖 /bin/sh）→ 第三次踩同一雷。

## 方案：五环存活链（全部固化进 malint/0.2 conanfile.py，r5 验证全绿）

1. **shell 回退链**：`CONFIG_SHELL` 经 `shutil.which()` 校验，失效则回退
   PATH 中的 bash/sh：
   ```python
   shell = os.environ.get("CONFIG_SHELL", "")
   if not (shell and shutil.which(shell)):
       shell = "bash" if shutil.which("bash") else "sh"
   ```
2. **CI 门禁急救**（设备侧一次性）：HMDFS→HMDFS 复制 zsh 为 `bash` 放进
   job env.sh PATH 首位目录（`~/ohpc-ci-shadow/python-user/bin/bash`）。
   注意：系统分区→HMDFS 复制会被拒（标签/签名不随复制保留），只有
   HMDFS→HMDFS 复制的副本可执行。
3. **解释器直接执行**：configure 用 `{shell} ./configure` 直接解释（zsh 作为
   解释器读脚本，不 exec shebang 的 /bin/sh）；make 用 `make SHELL={shell}`
   注入子命令解释器（autoconf Makefile 默认 SHELL=/bin/sh）。
4. **TMPDIR/TMPPREFIX 双注入**：/tmp 只读时 clang 报
   `unable to make temporary file: Read-only file system`（TMPDIR 即可），
   而 **zsh 的 here-document 临时文件走 TMPPREFIX（默认 /tmp/zsh），不读
   TMPDIR**——必须两个都指到 build 目录自建 `tmp/`。
5. **CC 从 Conan conf 显式注入**（R33/zzuf 模式）：`tools.build:compiler_executables`
   的 c 编译器经 `env CC=... configure` 传入，绕开 PATH 中可能失效的
   cc/gcc 包装脚本。

## 验证

- r2 起加 zsh-as-bash 入口后 KC=pass；r3–r4 逐环修复后 r5 全绿：
  L0/L1/L2/L4/L5 全 pass，上游 regress 6/6 PASS，test_package PASS，
  exit 0（run codex-0.2-malint-…-214011-40857）。
- 本机（Windows）Git Bash 同一配方通过 configure 交叉验证，链路两端一致。

## 适用边界

- 设备 shell 故障期（/bin/sh 或 hnp bash 不可执行）的应急适配；
- 配方中的回退链（第 1/3/5 环）对健康设备零影响（正常 bash 直接命中），
  可以长期保留在配方里；
- 第 2 环（zsh-as-bash 设备入口）是 job 环境级 workaround，**不进仓库**，
  设备修复后应移除。

## 反例与禁止

- 不要因为 KC fail 就去改 ci/ 基础设施脚本（红线：绕 CI 改公共脚本）；
- 不要把系统分区二进制复制到 HMDFS 当 shell（exec 被拒，见上）；
- 不要把设备 shell 故障期的 workaround 写死为唯一路径——保留回退链而不是
  硬编码 zsh。

## 关系图

- 相邻不重复：E043（BASH_SOURCE，HiShell ash 语法）、E165（shebang 改
  /system/bin/sh）、E386（hnp bash getcwd 崩溃）、E037/E049（shebang/env
  可移植性）——均为单点 shebang/语法问题，未覆盖「系统 shell 入口整体故障
  + 五环存活链」这一触发面。
