# DRAFT-ohos-autotools-configure-re-exec-cwd-env — OHOS autotools configure 重执行 shell 的 cwd 环境变量坑

> **Contributor**: GoliWie | **Status**: DRAFT | **Updated**: 2026-08-25
> **Severity**: blocking (3) | **Category**: ohos / autotools / conan / configure / shell
> **Audience**: 所有在 OHOS 上 autoreconf 自举 + configure 以 CONFIG_SHELL=bash 重执行的 autotools/Conan 配方

## 触发（trigger）

- GitHub archive 无 configure → 配方 build() 内 autoreconf 自举；profile 设 `CONFIG_SHELL=bash`，configure 自举后以 bash 重执行。
- OHOS 默认 `/system/bin/sh` 为 toybox sh，**不 export 当前目录环境变量 PWD**。
- configure 报错：`configure: error: working directory cannot be determined`。

## 机制（root cause）

- 真机探针（Curation Auditor 独立复核）：`sh -c 'echo PWD=[$PWD]; env | grep -e ^PWD'` → PWD 是 shell 局部变量但 env 中无 PWD。
- bash 启动时 getcwd() 失败：`env -u PWD bash -c 'pwd'` → `shell-init: error retrieving current directory: getcwd: cannot access parent directories: Operation not permitted`，pwd 输出为空。
- configure 的 ac_pwd 检查（autoconf 生成 `ac_pwd=\`pwd\` && test -n "$ac_pwd" && ...` 的 as_fn_error 分支）命中 `working directory cannot be determined`。
- `CONFIG_SHELL=/bin/sh` 在 conanbuild 后置覆盖下无效（已证伪）。

## 修复（rec）

```python
# build() 内、configure 前
os.environ["PWD"] = str(self.build_folder)   # bash 启动读 $PWD，不再 getcwd()
```

修复有效性：本轮权威 CI 日志 ci-round2-se-2.28.2.log（sha256 `9649d06a9c8091eaedc073cea52286595c5c1f90dcaf815b3b79fbd876a24cdf`）0 处该错误；configure 正常执行至 `configure: creating ./config.status`（445 行）。

## 跨库证据（cross-library）

设备 tmp 树同一 autoconf 错误分支（configure 含同一 as_fn_error 串，SHA-256 独立复算）：

| configure 文件 | SHA-256 |
|---|---|
| gnumeric-1.12.57/configure | `69824de9ad787088b25f8301c13c68981afd1917ac21ae6fb8ecbd16d0dcb53a` |
| goffice-0.10.57/configure | `fa81ec0658a1569461464b54fd033f1f9342a11eb88603007a6640d43018238a` |
| dbg-src/goffice-0.10.57/configure | `fa81ec0658a1569461464b54fd033f1f9342a11eb88603007a6640d43018238a` |
| goffice-src/goffice-0.10.57/configure | `fa81ec0658a1569461464b54fd033f1f9342a11eb88603007a6640d43018238a` |
| tmp.XXXXNCdffa/enchant-2.8.2/configure | `c82596c2c0d9f239b853cd484608d2ea7f3e9c3d65f98bcfa53fa3a7967e6c40` |

设备真实命中日志（跨库真实命中，非本库一次性补丁）：
- conan-create-debug.log（sha256 `a7ee82982c1b80fd2af4cf6e2dcc87b8242d6fd22441b138d369181046427f52`）：dejagnu/1.6.3 构建真实命中 `configure: error: working directory cannot be determined`。
- conan-create-r4.log（sha256 `f8a8cbefb4d45bcd74ce864b2f9ccbdb57f84632e097a9855633a71c6f41a771`）：配套 `shell-init: error retrieving current directory: getcwd: cannot access parent directories` / `job-working-directory: ...` 诊断。

## 查重（dedup，Curator/Auditor 双重独立检索）

- `grep -rl "working directory cannot be determined" knowledge/` → **0 命中**
- `grep -rl -e "PWD" knowledge/graph knowledge/drafts` → E079（硬链接）、E292（Arrow 测试数据环境变量）、DRAFT-sdcc（make -C 嵌套构建）、E327-draft-acpica——均无 PWD 预置条目。
- `grep -rl "getcwd" knowledge/` → DRAFT-sdcc（make 递归、不同触发）、E330-draft-2301（测试 runner shell、不同触发）、musl-glibc 文档、operations/packaging.md。
- 最相近条目逐项差异：E330-draft-2301（测试 runner 的 shell 能力探测，forbid `os.environ.*CONFIG_SHELL`，触发不同）、DRAFT-sdcc-gcc-trim-hmdfs（make -C 子目录 getcwd + HMDFS，修复为 (cd && make)，触发不同）、E232（configure 首进程 shell 前缀 Permission denied/126，错误签名与修复面不同）、E319-draft-TOYBOX-PATCH（patch 应用工具，无关）。

## Source

- Package: `archives/s/source-extractor/2.28.2`（conanfile.py build()，sha256 `55163ba9a6e1d5a82231e1f1c8e082df192ee654efb0c1954454783ed9e7f29a`）
- Candidate: `64f1909f346d9847281d2fea1b70c5cbe0ec4a28`（feat/astromatic-1.3，round-2 权威 CI PASS + upstream FULL_PASS 1/1）
- Similar: E232、E330-draft-2301、DRAFT-sdcc-gcc-trim-hmdfs、E319-draft-TOYBOX-PATCH
