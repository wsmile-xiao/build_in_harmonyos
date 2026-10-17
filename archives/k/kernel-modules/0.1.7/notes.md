# kernel-modules 0.1.7 适配笔记

## 编译环境
- **软件标识**: kernel-modules 0.1.7 = 上游 Arch Linux 官方仓库软件 kernel-modules-hook（pkgver=0.1.7，arch=('any')）
- **上游仓库**: https://github.com/saber-nyan/kernel-modules-hook（无 tag、无 release，默认分支 master，锁定 commit d5bb3c3750b8e9f7a45a9e3e7893b42e66cbd084）
- **构建系统**: custom（纯 POSIX shell/配置文件类工具，无 C/C++ 编译 → 数据/配置资源包）
- **编译日期**: 2026-09-19
- **平台**: armv8 / os=OHOS（默认 profile，等价 HarmonyOS PC aarch64）
- **状态**: built（conan create 验证通过 + test_package 9/9 PASS）
- **补丁数量**: 0（无源码补丁）

## 上游测试清点（R51 强制）

上游仓库 `saber-nyan/kernel-modules-hook@d5bb3c3`（GitHub API contents 全文件清单，commit 级证据）：

```
file .SRCINFO                        (870B)  — Arch 打包脚本元数据
file .gitignore                      (333B)
file 10-linux-modules-post.hook      (434B)  — 制品：libalpm hook（rsync 恢复模块）
file 10-linux-modules-pre.hook       (367B)  — 制品：libalpm hook（rsync 备份模块）
file PKGBUILD                       (1493B)  — Arch 打包脚本
file README.md                       (705B)
file UNLICENSE                      (1211B)  — 制品：公有领域许可证
file kernel-modules-hook.install     (232B)  — Arch 打包安装脚本
file linux-modules-cleanup.conf       (36B)  — 制品：systemd-tmpfiles 规则
file linux-modules-cleanup.service   (310B)  — 制品：systemd oneshot 清理服务
```

**结论**：上游**确无 tests/ 目录、无测试脚本、无 CI 测试**——10 个文件中 3 个为 Arch
打包脚本（PKGBUILD/.SRCINFO/kernel-modules-hook.install）、1 个 README、1 个 UNLICENSE、
1 个 .gitignore、5 个制品文件（两个 hook + cleanup.conf + cleanup.service + UNLICENSE）。
纯配置/数据类工具，无任何可运行测试入口。

**补全测试**（PF3/R34）：test_package 真实执行校验打包产物——
`test_kernel_modules.py` 校验 5 个制品文件存在且非空 + 从 hook/service 提取
Exec/ExecStart 内嵌 shell 命令真实执行 `sh -n` / `bash -n` 语法校验（9 断言，非
print-only/pass-only 空壳）。

## 适配说明

### 1. conandata.yml — 多文件 dict 源 URL 方案（仿 cute_files/1.0.0）
- 上游无 tag 且本机 github.com 主域/codeload tarball 不可达（仅 raw.githubusercontent.com
  可达）→ 不用 `get()` tarball，改 `download()` 逐文件下载。
- conandata.yml 用 dict 形式：每制品文件独立 `url`（https 官方 raw）+ `sha256`。
  5 个制品 sha256 与上游 PKGBUILD `sha256sums` 逐项核对完全一致
  （pre-hook f7ea2947…、post-hook 900502d0…、conf 4169b44c…、service 5d947290…、
  UNLICENSE 7e12e5df…），且与 .build-cache/kmh-src/ 实测 sha256sum 一致。
- R39/PF7：全部 https 官方源（raw.githubusercontent.com 为上游官方托管）。

### 2. build() — 无编译，sh -n / bash -n 校验内嵌 shell 命令（参考 akms/0.3.0）
- 纯数据/配置包无编译；build() 校验上游配置内嵌 shell 命令可解析：
  - 两个 hook 的 `Exec = /bin/sh -c '…'`（rsync 备份/恢复）→ `sh -n -c`；
  - service 的 `ExecStart=/bin/bash -exc '…'`（含 bash 特有 `[[ ]]`）→ `bash -n -c`。
- 提取逻辑要点（`_extract_exec_cmd`）：
  1. 正则须加 `re.MULTILINE`（Exec 行不在文件首行）；
  2. 须还原 systemd ExecStart 转义 `$$` → `$`、`\'` → `'`，得到 systemd 实际传给
     shell 的原始命令；
  3. 命令体含单引号（service 的 `'%v'`），传给 `self.run` 时必须用 `shlex.quote`
     包一层，否则引号错乱。
- 校验失败（含提取不到 Exec 行）→ raise ConanException，杜绝"假校验"。

### 3. package() — 数据/配置资源包布局
- 5 个制品文件 → `share/kernel-modules-hook/`（OHOS 无 libalpm/systemd 运行时，聚合到
  共享目录，对应上游 PKGBUILD `usr/share/libalpm/hooks` 等布局语义）；
- UNLICENSE → `licenses/`（与 akms/cute_files 先例一致）。
- 打包产物与上游文件大小完全一致（367/434/36/310/1211B）。

### 4. commands.json 处理（R38/PF8）
- 本包 `package_type=application`（与 akms/ausweisapp-nftrules 先例一致）但**无可执行
  bin**（纯数据/配置包）——按 ausweisapp-nftrules（同为纯数据包）先例在软件级创建
  `archives/k/kernel-modules/commands.json`（R38/L0k：package_type=application 即强制
  声明），`binary: false`（无实际可执行文件，与模板默认一致）。
- 与 akms 的区别：akms 有可执行 `bin/akms` → `binary: true`；本包无 bin → `binary: false`。

### 5. R32 / R38 / 其他约束落实
- R32：validate() 检查 `settings.os in ("Linux", "OHOS")`，否则 ConanInvalidConfiguration。
- R38/PF8：settings 四项齐全（os/arch/compiler/build_type）。
- 不注入 `__OHOS__` 宏、不改共享系统前缀（无 SYS_PREFIX 注入）。
- 无 `bindirs`/`bin` 安装目标（无污染 /lib、/lib64 风险，R26 不适用）。

## 本地验证（必须跑，已跑通）

```bash
cd archives/k/kernel-modules/0.1.7
conan create . -pr=default
```

默认 profile：`os=OHOS os.version=6.0 arch=armv8 build_type=Release compiler=clang 15
compiler.libcxx=libc++ compiler.cppstd=17`（鸿蒙社区适配版 conan 2.29.1）。

关键输出（完整日志见 $HOME/kmh-conan-create.log，EXIT=0，两轮连跑均通过）：

```
kernel-modules/0.1.7: RUN: sh -n -c 'KVER="${KVER:-$(uname -r)}"; if test -e "/usr/lib/modules/${KVER}"; then rsync -AHXal --delete-after "/usr/lib/modules/${KVER}" /usr/lib/modules/backup/; fi'
kernel-modules/0.1.7: OK: 10-linux-modules-pre.hook 内嵌 shell 命令语法校验通过（sh -n）
kernel-modules/0.1.7: OK: 10-linux-modules-post.hook 内嵌 shell 命令语法校验通过（sh -n）
kernel-modules/0.1.7: OK: linux-modules-cleanup.service 内嵌 shell 命令语法校验通过（bash -n）
kernel-modules/0.1.7: Package '6b129b068851896169fae42d399fa922d239ce8a' created
kernel-modules/0.1.7: Full package reference: kernel-modules/0.1.7#8d289e967ec166adb56926ecb30b4b21:6b129b068851896169fae42d399fa922d239ce8a#6d7bec6173a324629a904957f2dabe8f

======== Testing the package: Executing test ========
kernel-modules/0.1.7 (test package): RUN: python3 ".../test_package/test_kernel_modules.py" ".../p"
=== kernel-modules L1 test ===
  PASS: share/kernel-modules-hook/ exists
  PASS: 10-linux-modules-pre.hook exists and non-empty
  PASS: 10-linux-modules-post.hook exists and non-empty
  PASS: linux-modules-cleanup.conf exists and non-empty
  PASS: linux-modules-cleanup.service exists and non-empty
  PASS: licenses/UNLICENSE exists and non-empty
  PASS: 10-linux-modules-pre.hook: Exec shell 命令 sh -n 语法校验通过
  PASS: 10-linux-modules-post.hook: Exec shell 命令 sh -n 语法校验通过
  PASS: linux-modules-cleanup.service: ExecStart bash 命令 bash -n 语法校验通过
=== Result: PASS=9 FAIL=0 ===
```

- **conan create 结果**: EXIT=0，构建 + 打包 + test_package 全部通过（build() 的 sh -n/
  bash -n 校验真实执行、test_package 真实执行 9 断言全过）。
- **打包产物核对**: `conan list kernel-modules/0.1.7:*` 缓存确认；Package folder 内
  5 个制品文件大小与上游 PKGBUILD 一致（367/434/36/310/1211B）。
- 无依赖（纯配置包，不 requires 任何包）→ W0 依赖预检天然通过，无 conan download
  验证需求。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `_extract_exec_cmd` 首次提取返回 None | 正则 `^` 锚点在无 `re.MULTILINE` 时只匹配文件首行，Exec 行在第 10 行 | 正则加 `flags=re.MULTILINE`（conanfile.py 与 test_package 测试脚本同步修正） |
| 2 | systemd service ExecStart 的 `bash -n` 校验需还原转义 | systemd 转义 `$$`（→`$`）与 `\'`（→`'`）是 unit 文件层语法，直接提取会带着转义字面量 | `cmd.replace("$$","$").replace("\\'","'")` 还原后再校验；命令体含单引号（`'%v'`），传参用 `shlex.quote` 保证 `sh -n -c` / `bash -n -c` 安全 |
| 3 | 本机 /tmp 只读（SKILL E002 已知陷阱） | OHOS /tmp 为只读文件系统 | 日志与临时文件改用 `$HOME` 下路径 |

## 知识沉淀

- **纯 POSIX shell/配置类工具适配模式**：无 C/C++ 编译、无测试套件 → 数据/配置资源包
  收录（不编译）；build() 用 `sh -n` 校验内嵌 shell 命令可解析（akms 先例推广）；
  test_package 校验打包产物内容 + 真实执行 shell 语法校验（R34）。
- **上游无 tag + github.com 主域不可达** → conandata.yml 用多文件 dict 形式
  （cute_files/1.0.0 先例推广），每文件独立 https 官方 raw URL + sha256（与 PKGBUILD
  逐项核对）。
- **systemd ExecStart 转义还原**：`$$`→`$`、`\'`→`'` 后才能得到 shell 实际执行的命令；
  校验含单引号的命令体必须 `shlex.quote`。
- **package_type=application 但无 bin 的数据包**：仍需软件级 commands.json（R38/L0k），
  `binary: false`（模板默认）；与有真实 bin 的 akms（binary: true）区分。
---

**编译结束**: 2026-09-19 03:30
**最终状态**: built
