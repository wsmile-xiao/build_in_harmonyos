# DRAFT-gnat-consumer-ohos-hnp-binutils-path - GNAT 消费端需要 GNU binutils 在 PATH

> **Contributor**: codex | **Status**: VERIFIED DRAFT | **Updated**: 2026-09-17
> **Source event**: adacgi 1.6 HarmonyOS PC adaptation, shadow CI isolated job `adacgi-1.6-shadow-20260917-092524`

## 知识类型与提升边界

本条目是路径 B/B 类知识库扩展候选，不预占正式 E 编号。它只进入
`knowledge/drafts/**`，不修改 `knowledge/graph/`、`knowledge/doc/`、索引或运维规则，
也不声称已经 promote 或已获 B 类认定；是否提升及最终分类由知识库维护者和评审决定。

## 适用场景

适用于在 OHOS 上用 `gcc-ada`（或任何 GCC 系工具链）**作为 tool_requires 消费**、由
`gnatmake`/`gcc` 驱动现场编译 `.adb`/`.c` 的下游库，尤其运行在隔离 shadow CI job 中
（其 PATH 不含 `/data/service/hnp/bin`）。

## 问题模型

GNAT 的 `gcc` 驱动在汇编阶段用 `execvp("as")` 在 PATH 里找汇编器，**运行时并不读取
`AS` 环境变量**（`AS` 是 GCC 构建期变量）。OHOS 上 `/usr/bin/as` 受 SELinux 保护，任何
进程 `execvp` 它都得到 `Permission denied`；真正可用的 GNU Binutils 2.45 位于
`/data/service/hnp/bin/as`。隔离 job 的基础 PATH（`/bin:/usr/bin:/sbin:/usr/sbin:...`）
不含该目录，于是编译在汇编阶段失败：

```text
gcc.real: fatal error: cannot execute 'as': execvp: Permission denied
```

## 推荐方法

### 1. 在配方 generate() 前置 HNP binutils 目录

```python
from conan.tools.env import Environment

def generate(self):
    env = Environment()
    if str(self.settings.os) == "OHOS":
        env.prepend_path("PATH", "/data/service/hnp/bin")
    env.vars(self).save_script("gnat_binutils_env")
```

### 2. self.run 用 env 列表叠加该脚本

```python
self.run(gnatmake_cmd, env=["conanbuild", "gnat_binutils_env"])
```

### 3. 签名工具同样需要显式 fallback

`_sign_program`/`_sign_elf_tree` 内的 `shutil.which` 走的是 Python 进程 PATH，不受
`self.run` 的 env 影响，需为 `binary-sign-tool`/`llvm-objcopy`/`llvm-readelf` 增加
`/data/service/hnp/bin/...` 的显式 fallback。

## 与已有知识的差异

- `E012` 记录"鸿蒙 SDK 只提供 LLVM 工具链，没有 binutils"，但未覆盖 SELinux 保护
  `/usr/bin/as` 及 `execvp` 的 `Permission denied` 特征。
- `E450`（avr-gcc `-B` 搜索 unprefixed `as/ld/nm`）是交叉工具链**打包**阶段的驱动搜索；
  本条目是 GCC 驱动**运行时 `execvp` 在 PATH 找 as** 且系统 `as` 受 SELinux 保护，需前置
  `/data/service/hnp/bin`，两者触发点与解法不同。
- `DRAFT-below-ohos-unsigned-rust-toolchain` 覆盖未签名 cargo/rustc 的 EACCES；本条目是
  GCC 驱动的 `as` 子进程 `execvp` 失败，根因是 PATH 缺 HNP binutils 而非缺 ELF 签名。

## 禁止做法

- 不要依赖 `export AS=/data/service/hnp/bin/as` —— GCC 运行时忽略 `AS`，不解决 `execvp("as")`。
- 不要把 `/data/service/hnp/bin` 写进 conanfile 的 `package_info` 或污染全局环境。
- 不要用 `shutil.which` 的裸名 fallback（`objcopy`/`readelf`）而不显式给 `/data/service/hnp/bin/` 路径。

## 已验证示例

adacgi 1.6 首轮 shadow CI 在 `build()` 编译 `cgi.adb` 时命中
`cannot execute 'as': execvp: Permission denied`。按上述方法前置
`/data/service/hnp/bin` 到 PATH 并叠加 env 后，库单元编译与 test_package 消费测试全绿
（`ADACGI_LINKAGE=pass assertions=9`）。空 .s 探针实测：PATH 前置后 GNU as 正常汇编。

## 证据来源

- `archives/a/adacgi/1.6/conanfile.py`（generate + build）
- `archives/a/adacgi/1.6/test_package/conanfile.py`（generate + build + _sign_program）
- `archives/a/adacgi/1.6/notes.md`（真机 shadow CI 修复记录）
