# E577 — Automake 测试驱动无法以 shebang 启动测试脚本：改用 LOG_COMPILER 显式解释器

> Contributor: AtomCode (GLM-5.2) <atomcode-bot@atomgit.com> | Status: Draft | Updated: 2026-09-14
> Source: iec16022 0.3.1 适配（真机 shadow CI 隔离 job：make check 由 exit 126 修复为 PASS）

## 编号说明（查重口径）

取号前按两口径取并集核查全池：

1. **跨 worktree 文件形态扫描** — `knowledge/{graph,doc,drafts}` 下 `E<n>.kv`、`E<n>.md`、
   `E<n>-*`、`DRAFT-E<n>-*` 四种命名形态，扫描基线 `origin/main` 工作树 + 全部 60 个 worktree。
   注意 `DRAFT-<ID>-*` 的文件名前缀是 `DRAFT-`，只按 `^E\d+` 匹配会整类漏掉。
2. **主线文本引用扫描** — `git grep -E '(^|[^0-9A-Za-z_])E[0-9]{3,5}([^0-9]|$)' HEAD`，
   因为配方/manifest 会在注释里引用编号而不产生任何文件（"悬空但已被引用"）。
   **必须用整词边界**：朴素匹配会命中 sha256 子串（如 `13DE5726FA…`）造成假占用。

结果：`E543–E576` 全部已占用（E543 一号被 **25 份**不同草稿重复占用，是重灾区；
E571/E572/E573/E574/E575/E576 各有独立占用者），**首个空号为 E577**，
且 E577/E578 在两种口径下均零命中（file forms 0，text refs 0）。
`contributor_id: 1EC1` 亦经全池核查未被使用。

## 与相邻条目的差异（先读这一节，避免误合并）

本条的修复手段（`LOG_COMPILER`）与 E228 相同，但**根因与适用前提都不同**，不可互相替代：

| 条目 | 根因 | 修法 | 前提 |
|------|------|------|------|
| **E228** | Libtool 为动态链接测试生成**与 ELF 同名的无扩展名 wrapper**，HMDFS 阻止该 wrapper 直接执行 | 条件式 launcher：同目录存在 `.libs/<basename>` 才经 shell 启动 | 测试集**混合** wrapper 与真实 ELF；E228 明确**禁止**对混合集无条件套 `LOG_COMPILER=/system/bin/sh` |
| **E087** | HMDFS 上 `chmod` 不生效 → 脚本**缺执行位**（0600） | `sh ./script` 替代直接执行 | — |
| **E165** | `/bin/bash`、`/usr/bin/env` 等 **shebang 目标不存在** | 改写 shebang 指向已存在的解释器 | — |
| **本条 E577** | shebang 目标**存在**（`/bin/sh` 就在），但内核/SELinux **拒绝"经 shebang 启动脚本"这一机制本身** | `make check LOG_COMPILER=<shell>`，脚本作为参数交给 shell | **TESTS 全为 shell 脚本**（此时 E228 的禁止规则不适用） |

判定 E577 的决定性实验：把上游 `test/testsuite.sh` 的 `#!/bin/bash` 改成 `#!/bin/sh`
（目标解释器确实存在）后，错误**只是换了一行**，并未消失：

```text
# 改之前
test-driver: test/./testsuite.sh: /bin/bash: bad interpreter: No such file or directory
# 改之后（/bin/sh 一定存在，仍失败）
test-driver: test/./testsuite.sh: /bin/sh: bad interpreter: Permission denied
FAIL ./testsuite.sh (exit status: 126)
```

前者像 E165（目标不存在），后者证明是 E577（机制被拒）。**因此"改写 shebang"在本条场景是无效
修法**，只有让驱动不经 shebang 启动才成立。

> 与 `E543-draft-09EE` 的关系：该草稿的 `error_signature` 已含
> `test-driver: ./testscript: /bin/sh: bad interpreter: Permission denied` 且 `rec_approach`
> 提到 `make check 加 LOG_COMPILER=bash`，是本条最接近的已有记录。但它是 `title:` 为空、
> `match_keywords:` 仍为模板占位符 `keyword1, keyword2, keyword3` 的未审阅草稿（会命中 KC2），
> 且 `id: E543` 在全库被 **25 份不同草稿**重复占用。故本条按可独立提升的粒度重建：
> error_signature 收窄到 `test-driver:` 行，显式写出"TESTS 全为脚本"前提，并交叉引用 E228/E087/E165。
> **提升（promote）时应把 E543-draft-09EE 合并进本条并删除，而不是并存。**

## 错误特征

`conan create` 进入 `make check` 后，automake 测试驱动报 126，测试套件整体记 FAIL：

```text
make  check-TESTS
FAIL: ./testsuite.sh
============================================================================
Testsuite summary for iec16022 0.3.1
============================================================================
# TOTAL: 1
# PASS:  0
# FAIL:  1
============================================================================
```

`test/test-suite.log` 给出真正的第一现场（**必须看这个文件，不要只看 stdout 摘要**）：

```text
test-driver: .../b/test/./testsuite.sh: /bin/bash: bad interpreter: No such file or directory
FAIL ./testsuite.sh (exit status: 126)
```

`make[3]: *** [Makefile:521: test-suite.log] Error 1` 只是级联结果。

## 根因

automake 的 `test-driver` 默认把 `TESTS` 里的每个条目当**可执行文件**直接 `exec`。
HarmonyOS 上这一路径被内核/SELinux 拒绝（E232 同一机制的另一处表现：脚本的
shebang/kernel-exec 通道在 `/storage/Users/...` 域下不可用），于是驱动拿到 126。

`CONFIG_SHELL` 救不了：它由 Autoconf 生成物读取，管不到驱动这次 exec。
改写 shebang 也救不了：拒绝的是"经 shebang 解释"这件事，与被解释器是否存在无关
（见上方对照实验）。

## 推荐方案

给 `make check` 传 `LOG_COMPILER`，automake 会执行 `$(LOG_COMPILER) ./script`，
脚本作为**参数**交给 shell，内核不再解析 shebang：

```python
# conanfile.py build()，原生 OHOS 分支
shell = "/system/bin/sh"
autotools.make(
    target="check",
    args=["-j1", f"LOG_COMPILER={shlex.quote(shell)}"],
)
```

要点：

1. **前提是 TESTS 全为脚本**。若测试集含 libtool wrapper 或真实 ELF，无条件套用会把 ELF
   当脚本解析——那属于 E228，须改用其条件式 launcher。
2. 默认分支（Linux/Windows 构建机）保持 `autotools.make(target="check", args=["-j1"])` 不变。
3. 该修法**不改上游任何测试文件**，断言强度不变；这是相对"改写 shebang/删测试"的关键优势。

## 回退方案

若上游测试不经 automake 驱动（自写 Makefile 直接 `./testsuite.sh`），则在 `build()` 中显式：

```python
self.run(f'"{shell}" "{os.path.join(self.source_folder, "test", "testsuite.sh")}"')
```

同样绕开 shebang，并由配方保证非零退出即失败（不得 `|| true`）。

## 禁止做法

- ❌ 对**含 libtool wrapper/ELF 的混合测试集**无条件设 `LOG_COMPILER=sh`（会把真实 ELF 当脚本，见 E228）。
- ❌ 仅改写测试脚本 shebang 就认为已修复（本条已实测无效：`/bin/sh` 仍 `Permission denied`）。
- ❌ 跳过报 126 的测试或用 `|| true` 掩盖，伪造成"通过"（P013：平台限制必须降级到可用方案，不得删减覆盖）。

## 验证

iec16022 0.3.1 真机 shadow CI（隔离 job）：

```text
# 修复前
FAIL ./testsuite.sh (exit status: 126)   → make check Error 2 → conan create failed
# 修复后
PASS: ./testsuite.sh
# TOTAL: 1  # PASS: 1  # FAIL: 0  # ERROR: 0
L1_RESULT=pass: upstream tests + test_package executed
```

六种输出格式（Text/EPS/PNG/Bin/Hex/UTF-8）与上游参考产物逐字节一致，说明未因绕开 shebang
而降低断言强度。设备侧另做一次离线复核：把参考产物放入脚本工作目录后
`sh testsuite.sh` 单独运行，六项各自打印 "… test passed"、退出码 0。

## 相关条目

- **E228** — Libtool 无扩展名 wrapper 的条件式 launcher（同修复手段，不同根因与前提）。
- **E232** — 同一"脚本 kernel-exec 被拒"机制在 `Autotools.configure()` 首进程上的表现。
- **E087** — HMDFS `chmod` 不生效导致脚本缺执行位（另一根因）。
- **E165** — shebang 目标不存在（另一根因；注意与本条的上方对照实验）。
- **E543-draft-09EE** — 最接近的已有草稿，提升时应合并进本条。
