# DRAFT-gcc-ada-missing-gnatprep-adb-p-preprocess

> **Contributor**: ohpcd | **Status**: DRAFT | **Updated**: 2026-09-20
> **Severity**: high | **Category**: ada / gnat / toolchain / autotools
> **Source**: task libncursesada@6.3.20211021（CI #50329，原生 OHOS 构建）

## 使用说明（何时用）

当 Ada（autotools）库在 `make` 阶段报：

```
make[1]: gnatprep: No such file or directory
make[1]: *** [Makefile:241: terminal_interface-curses-trace.adb] Error 127
```

先别怀疑 PATH 或 profile——先确认工具链包里到底有没有这个可执行文件：

```
$ ls <gcc-ada 包>/bin
aarch64-linux-ohos-gcc  gcc  gcc.real  gnatbind  gnatchop  gnatclean
gnatlink  gnatls  gnatmake      # 就是没有 gnatprep
$ ls <gcc-ada 包>/libexec/gcc/aarch64-linux-ohos/9.5.0/
cc1  cc1plus  collect2  gnat1  lto-wrapper      # 也没有
```

结论：**ohpcd 的 gcc-ada 是一个不完整的 GNAT 集合**。凡上游 Makefile 用
`$(ADAPREP)`（= `gnatprep`）把 `.adb_p`/`.ads_p` 预处理成 `.adb`/`.ads` 的库，
在原生 OHOS 构建里都必然在这一步 Error 127。

## 适用范围

- **直接**：AdaCurses（`libncursesada`）及其派生——`src/Makefile.in:88` 定义 `ADAPREP = gnatprep`，
  `:241` 用它从 `terminal_interface-curses-trace.adb_p` 生成 `terminal_interface-curses-trace.adb`；
  `samples/Makefile.in:94` 同样定义 `ADAPREP`。
- **同构**：任何 `tool_requires("gcc-ada")` 的原生 OHOS 构建中、需要 GNAT 前端配套工具
  （gnatprep / gnatkr / gnatstub / gnatfind …）的项目；这些工具在 gcc-ada 包里同样缺席。
- **不适用**：工具链自带完整 GNAT 套件（GNAT Community、Alire、发行版 `gnat` 包）时。

## 输入 / 输出定义

**输入**

| 项 | 说明 |
|---|---|
| 构建系统 | autotools（Makefile.in 里有 `ADAPREP` 变量） |
| 预处理模板 | `*.adb_p` / `*.ads_p`（GNAT 预处理语法：`#if SYM then` / `#elsif` / `#else` / `#end if;` / `$name`） |
| 定义 | Makefile 传入的 `-DADA_TRACE=<TRUE|FALSE>`，可能还有 `@GNATPREP_OPTS@`（configure 探测得到的 `-T`） |
| 工具链 | ohpcd `gcc-ada/9.5.0`（OHOS/armv8） |

**输出 / 判定**

| 条件 | 结论 | 动作 |
|---|---|---|
| `ls <gcc-ada>/bin/gnatprep` 不存在且 Makefile 引用 `ADAPREP` | 必然 Error 127 | 提供等价 `gnatprep`（推荐 shim） |
| configure 探测 `gnatprep -T` | 必须让它失败 | shim 无输入文件时 `exit 2`，使 `GNATPREP_OPTS` 为空、且绝不读 stdin 挂死 |
| shim 处理 `.adb_p` | 输出必须能被 `gnatmake` 直接编译 | 保留未定义 `$name`（上游只有注释里的 `$Revision`） |

## 示例

配方内联一个最小实现并置于 PATH 首位：

```python
import os, sys

_GNATPREP_SHIM = r'''
import re, sys
# … 支持 -D name[=value]、#if/#elsif/#else/#end if;、$name 替换 …
def main(argv):
    # 无输入文件 -> exit 2（让 configure 的 `gnatprep -T` 探测失败，且不读 stdin）
    ...
'''

def _gnatprep_shim(self):
    bindir = os.path.join(self.generators_folder, "gnatprep-bin")
    os.makedirs(bindir, exist_ok=True)
    target = os.path.join(bindir, "gnatprep")
    with open(target, "w", encoding="utf-8") as fh:
        fh.write("#!{}\n".format(sys.executable))
        fh.write(_GNATPREP_SHIM.lstrip("\n"))
    os.chmod(target, 0o755)
    return bindir

def generate(self):
    env = ...
    env.prepend_path("PATH", self._gnatprep_shim())
    ...
```

实测输出（`-DADA_TRACE=FALSE` / `TRUE` 两分支均正确展开，`$Revision` 原样保留）：

```
$ gnatprep -DADA_TRACE=FALSE src/terminal_interface-curses-trace.adb_p out.adb
# FALSE: 无 with Interfaces.C / 无 traceC / 有 null 体
$ gnatprep -DADA_TRACE=TRUE  src/terminal_interface-curses-trace.adb_p out.adb
# TRUE : with Interfaces.C / pragma Import(traceC) / _traces()
```

## 查重差异表

| 既有条目 | 收录状态 | 问题面 | 本条的增量（差异化） |
|---|---|---|---|
| `DRAFT-ada-gnats-native-only-toolchain-cross-build-trap` | 草稿 | gcc-ada/binutils **只有 OHOS/armv8 制品**、必须原生构建 | 非本题——那是「在哪台机器构建」；本条是「工具链**套装不完整**」，原生构建照样缺工具 |
| `DRAFT-gcc-ada-ohos-link-only-libunwind` | 草稿 | gcc-ada **链接期** libunwind 注入缺失 | 非本题——那是链接契约，本条是**预处理工具缺失**（make 早期） |
| `DRAFT-gcc-ada-ohos-xpm-seed-loader` | 草稿 | gcc-ada 自身构建需要 Alpine GNAT seed | 非本题——那是编译器包**如何被造出来**，本条是**消费方如何使用**它 |
| E064（conftest 首次执行被安全门拦） | 正式 | 未签名 ELF 不可 exec | 非本题——那条在 configure，本条的 Error 127 在 make，且根因是文件根本不存在 |
| E489/E517（OHOS 未签名 ELF） | 正式 | exec 安全门 | 非本题 |

> 全库查证（2026-09-20）：`knowledge/` 全文检索 `gnatprep`、`No such file or directory`、`Error 127`
> 等关键词，**无正面撞车**；本条为真增量。

## 验证证据

**① 工具链包里确实没有 gnatprep（决定性证据）**

```
$ ls <gcc-ada 包>/bin | grep -i gnat
gnatbind
gnatchop
gnatclean
gnatlink
gnatls
gnatmake
$ find <gcc-ada 包> -name 'gnatprep*'
（空）
$ find <conan 缓存> -name 'gnatprep*'
（空）
```

**② 上游确实要用它**

```
$ grep -n 'gnatprep' src/Makefile.in samples/Makefile.in
src/Makefile.in:88:ADAPREP		= gnatprep
src/Makefile.in:241:	$(ADAPREP) -DADA_TRACE=@ADA_TRACE@ @GNATPREP_OPTS@ $(srcdir)/$(ABASE)-trace.adb_p $@
samples/Makefile.in:94:ADAPREP		= gnatprep
$ grep -n 'gnatprep' configure
17558:gnatprep -T 2>/dev/null >/dev/null && cf_cv_gnatprep_opt_t=yes   # 探测 -T 支持
```

**③ CI 实测报错（构建 #50329）**

```
rm -f terminal_interface-curses-trace.adb
gnatprep -DADA_TRACE=FALSE  .../src/terminal_interface-curses-trace.adb_p terminal_interface-curses-trace.adb
make[1]: gnatprep: No such file or directory
make[1]: *** [Makefile:241: terminal_interface-curses-trace.adb] Error 127
```

**④ 修复后在本地原生链路（binfmt_misc + qemu-aarch64，与 CI 同源工具链，build==host）端到端通过**

```
$ gnatprep -DADA_TRACE=FALSE  <src>/...adb_p  trace.adb   # shim，rc=0
$ make -j1                                               # include/gen/src/doc/samples 全部构建
$ conan create ... -pr:h=ohos-aarch64-wsl-native -pr:b=...  # EXIT=0
  [ok] gnatprep shim -> .../conan/gnatprep-bin/gnatprep
  ...
  libAdaCurses.a / share/ada/adainclude/*.ad[bs] 安装完成
  test_package: BUILD_OK
  run_pty.py ./ncursesada-consumer  ->  LIBNCURSESADA_CONSUMER_OK  ->  PTY_OK
```

## 平台侧修法建议

1. 这类「工具链套装不完整」的包，建议在 `gcc-ada` 的 recipe `package_info` 或包说明里显式列出
   **实际提供的 GNAT 工具清单**，避免每个下游库各撞一次；
2. 若长期要支持 Ada 生态，ohpcd 的 gcc-ada 制品最好补齐 gnatprep（它只是一个很小的独立 Ada 程序），
   否则每个用 `$(ADAPREP)` 的上游库都要自带 shim；
3. 知识库可考虑统一一条「gcc-ada 缺失工具 → 用等价 shim 补齐」的处置口径（本条即该口径的第一例）。
