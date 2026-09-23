# 测试报告 — xa 2.4.1 (xa65)

> **项目**: xa（6502/65C02/65816 交叉汇编器）  
> **测试日期**: 2026-09-18  
> **测试环境**: HarmonyOS PC（HongMeng Kernel 1.12.0 aarch64，HAD-W32/W24，OHOS SDK clang 15.0.4，Harmonybrew userland）  
> **测试类型**: 官方测试套件（44 例）+ test_package 功能测试（12 例）

---

## 一、测试摘要

| 指标 | 数值 | 百分比 |
|:----:|:----:|:------:|
| 总测试数 | 56 | 100% |
| 通过 (PASS) | 56 | 100% |
| 失败 (FAIL) | 0 | 0% |
| 跳过 (SKIP) | 0 | 0% |

**核心功能通过率**: ✅ **100%**

---

## 二、测试结论

### 2.1 总体评价

✅ **优秀** — 上游 44 例回归在 OHOS aarch64 上全部通过（逐字节产物比对），test_package 12 条功能断言全部通过；无宿主不兼容用例，无跳过。

### 2.2 主要问题

| 问题类别 | 影响范围 | 严重程度 |
|----------|----------|----------|
| Perl shebang 不可执行（无 /usr/bin/perl；env 无法携带 -s） | 上游测试驱动无法启动 | 🟡（已修复：2 个可移植性补丁） |
| `install(1)` 缺失 | 无法使用上游 `make install` | 🟢（已规避：package() 直接 copy） |
| GitHub 直连下载不稳定 | 本地取源 | 🟢（已规避：官方 URL + 镜像/预下载机制，sha256 与 codeload 二次核验） |

### 2.3 可用功能清单

```
✅ xa 汇编器: 原始可执行文件/o65 对象/列表/标签表/字符集/兼容语法，错误诊断与退出码
✅ file65: o65 文件信息打印
✅ ldo65: o65 链接（多目标合并为可执行）
✅ reloc65: o65 重定位（段基址调整）
✅ uncpk: cpk 归档创建/列表/解包
✅ printcbm: CBM BASIC 列表反汇编
```

### 2.4 已知限制

1. 上游 `make install` 依赖 `install(1)`（OHOS 无）；Conan 包内产物位置与上游安装布局一致（bin/ + share/man/man1），但不再随附上游的 `mkrom.sh` 便利脚本（上游 install 亦不安装）。
2. 上游测试套件需要宿主 `perl`（设备与 CI 的 GNU userland 均已具备）；配方在 perl 缺失时硬失败而非跳过。
3. `printcbm` 自上游 2.4 起标记弃用（功能仍完整）。

---

## 三、测试详情

### 3.1 通过的测试

#### 3.1.1 上游回归套件（tests/harness -tests=ALL，44/44）

| # | 测试目录 | 功能 | 结果 |
|---|----------|------|------|
| 1 | adrm | 寻址模式与优化 | ✅ PASS |
| 2 | align | 对齐/段方向 | ✅ PASS |
| 3 | alxl | '816 宽度规则 | ✅ PASS |
| 4 | aserr | .assert / #error 语法 | ✅ PASS |
| 5 | binclude | 二进制 include（大小写） | ✅ PASS |
| 6 | branch | 分支范围 | ✅ PASS |
| 7 | ca65 | ca65 兼容模式（-XCA65） | ✅ PASS |
| 8 | chardelimiter | 字符定界 | ✅ PASS |
| 9 | charset | 字符集处理 | ✅ PASS |
| 10 | chppch | 预处理字符切换（-p） | ✅ PASS |
| 11 | cll | 标签/列表 | ✅ PASS |
| 12 | comcom | 注释嵌套 | ✅ PASS |
| 13 | cpktest | 真实程序回归（cpk） | ✅ PASS |
| 14 | cpp | 预处理器随机用例 | ✅ PASS |
| 15 | csapiec | 重定位模式指针运算 | ✅ PASS |
| 16 | dos51 | 标签作用域回归 | ✅ PASS |
| 17 | expando | 宏展开 | ✅ PASS |
| 18 | fordef | 前向定义标签优化告警 | ✅ PASS |
| 19 | incerr | include 错误定位 | ✅ PASS |
| 20 | ldoreloc | ldo 重定位表读取 | ✅ PASS |
| 21 | line | 行号/输出 | ✅ PASS |
| 22 | linkr | .dsb 与链接 | ✅ PASS |
| 23 | listing | 列表输出 | ✅ PASS |
| 24 | masmcom | -M 兼容注释 | ✅ PASS |
| 25 | math | 表达式（含除零） | ✅ PASS |
| 26 | mode | 段模式 | ✅ PASS |
| 27 | mvnmvp | MVN/MVP 寻址（'816） | ✅ PASS |
| 28 | neg_offset | 负数偏移/重定位 | ✅ PASS |
| 29 | nonl | 末行无换行 | ✅ PASS |
| 30 | op816 | '816 操作码 | ✅ PASS |
| 31 | openpp | 开放 #if 处理 | ✅ PASS |
| 32 | pparity | 宏参数元数 | ✅ PASS |
| 33 | ppdefines | 预处理器定义 | ✅ PASS |
| 34 | ppstrings | 字符串内不替换 | ✅ PASS |
| 35 | quotch | 特殊字符引号 | ✅ PASS |
| 36 | recmac | 递归宏 | ✅ PASS |
| 37 | recucom | 递归注释 | ✅ PASS |
| 38 | relmode | 段切换/绝对模式 | ✅ PASS |
| 39 | relocmode | 重定位模式 | ✅ PASS |
| 40 | relocundef | 未定义引用检测 | ✅ PASS |
| 41 | reset_segment | 段重置条件 | ✅ PASS |
| 42 | stringcom | 字符串注释 | ✅ PASS |
| 43 | undef | 未定义标签/重定位 | ✅ PASS |
| 44 | usb65 | 宏与作用域真实程序 | ✅ PASS |

> 驱动输出：`## ALL SELECTED TESTS PASS (ALL, n=44) ##`；产物全部由 `tests/hextool` 做逐字节比对。

#### 3.1.2 test_package 功能断言（sh test_xa.sh，12/12）

| # | 测试项 | 功能 | 结果 |
|---|--------|------|------|
| 1 | six-binaries-version | 六个二进制 `--version` 均成功 | ✅ PASS |
| 2 | xa-version-string | 输出版本 `xa (xa65) 2.4.1` | ✅ PASS |
| 3 | usage-text | 无参数输出 `Usage: xa` | ✅ PASS |
| 4 | raw-bytes | 汇编原始输出逐字节等于 `41 42 43` | ✅ PASS |
| 5 | bad-source | 未定义标签：非零退出码 + `not defined` | ✅ PASS |
| 6 | o65-object | `-c -R` 生成 o65 对象，file65 报 `object file` 且 text @ $1000 | ✅ PASS |
| 7 | label-list | `-l` 标签表含 `start` | ✅ PASS |
| 8 | ldo65-link | 两对象链接为 `executable file`，text @ $0400 | ✅ PASS |
| 9 | reloc65-relocate | `-bt 8192` 重定位后 text @ $2000 | ✅ PASS |
| 10 | uncpk-create-list | 创建 cpk 并列出成员 | ✅ PASS |
| 11 | uncpk-extract | 解包内容与原文件 `cmp` 一致 | ✅ PASS |
| 12 | printcbm | BASIC 行反汇编为 `print"HI"` | ✅ PASS |

### 3.2 失败的测试

无。

### 3.3 跳过的测试

无。

---

## 四、关键问题分析

### 问题1: 上游 Perl 测试驱动在 OHOS 上无法执行

**现象**：
```
tests/harness: bad interpreter: /usr/bin/perl: no such file or directory
```
（直接改 `#!/usr/bin/env perl -s` 后：）
```
env: exec perl -s: No such file or directory
```

**根因分析**：
OHOS 系统无 `/usr/bin/perl`，perl 由 Harmonybrew userland 提供在 PATH；同时 Linux 内核对 `#!` 只取解释器路径后的整段作为**单个**参数，`-s` 无法经 `env(1)` 传递（toybox env 不支持拆分/`-S`）。

**解决方案**：
补丁 `0001-tests-harness.patch` / `0002-tests-hextool.patch`：shebang 改为 `#!/usr/bin/env perl`，并在脚本内加入与 Perl `-s` 等价的开关解析（`-name=value` / `-name`，解析后从 @ARGV 移除）。所有调用方式与测试断言、期望产物均不变；`perl -s` 方式调用亦兼容（Perl 会先移除已解析开关）。

### 问题2: 上游 tag 归档的两级目录布局

**现象**：直接解压后工程位于 `xa65-xa-2.4.1/xa/`，`make`、补丁目标（`tests/harness`）路径全部错位。

**根因分析**：GitHub 归档保留仓库结构，xa65 仓库把项目放在 `xa/` 子目录，根目录另有独立 README。

**解决方案**：`conanfile.py` 的 `source()` 在 `get(strip_root=True)` 后将 `xa/` 内容提升到 source 根并移除仓库级 README；补丁路径按提升后的根目录书写。

### 问题3: `install(1)` 缺失导致上游 `make install` 不可用

**现象**：`make install` → `install: inaccessible or not found`。

**根因分析**：OHOS/toybox 未提供 `install(1)`。

**解决方案**：`package()` 直接 copy 6 个二进制与 6 份 man 手册到标准布局；与上游安装内容对齐（不含上游不安装的 `mkrom.sh`）。

---

## 五、测试环境

```
软件版本: xa 2.4.1 (xa65)，GPL-2.0-or-later
源码: https://github.com/fachat/xa65/archive/refs/tags/xa-2.4.1.tar.gz
      sha256 8fecdb9e64da84eb77d3572e73033bf3d1ca533c7291fb5d0d9735c5440eb67e
编译器: OHOS SDK clang 15.0.4 (aarch64-linux-ohos / armv8)
构建: make -j1（upstream Makefile）+ conan create（profile ohos-aarch64）
测试: perl tests/harness -tests=ALL（44 例） + sh test_package/test_xa.sh（12 例）
平台: HarmonyOS PC，HongMeng Kernel 1.12.0，aarch64
```

---

*报告生成时间: 2026-09-18*
