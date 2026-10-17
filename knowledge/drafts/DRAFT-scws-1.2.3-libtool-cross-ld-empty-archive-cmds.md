# DRAFT: macOS 交叉验证时 libtool 空 archive_cmds（.so 静默缺失）

## 基本信息

- **严重度**: 2
- **类别**: autotools / libtool / cross-compile / ohos-local
- **发现于**: scws/1.2.3（2026-09-27，macOS + ohos-local 交叉验证）
- **状态**: draft（pending-editor-review）

## 错误特征

最终可见报错（make 阶段、链接可执行文件时）：

```
clang: error: no such file or directory: '../libscws/.libs/libscws.so'
make[2]: *** [scws] Error 1
```

真正的根因信号在 configure 阶段：

```
checking for ld used by /Users/metyierzhen/ohos-toolchain/clang... /usr/bin/ld
```

以及生成的 `libtool` 脚本中：

```
archive_cmds=""
with_gnu_ld="no"
```

**隐蔽性**：libtool 链接库时无任何报错，只创建 `.libs/libscws.so -> libscws.so.1.1.0`
等符号链接，`.so.x.y.z` 实体从未生成。

## 根因分析

macOS 本机用 ohos-local profile 交叉验证时，预生成 configure 内嵌的 libtool 宏
`LT_PATH_LD` 通过编译器驱动探测链接器，OHOS 交叉 wrapper 未覆盖该探测，返回
macOS 宿主 `/usr/bin/ld`。它不报 GNU 兼容信息 → `with_gnu_ld=no` → libtool.m4 的
`linux*` 分支无法生成 GNU 式 `archive_cmds`，该变量为空 → 实际 `-shared` 链接被
静默跳过。

## 修复（已在 scws/1.2.3 验证）

配方 `generate()` 的 OHOS 交叉分支向 configure_args 固定：

```python
tc.configure_args.extend([
    "LD=ld.lld",        # ld.lld --version 报 "compatible with GNU linkers"
    "AR=llvm-ar",
    "RANLIB=llvm-ranlib",
])
```

前提：ohos-local profile 的 `[buildenv]` 已把 ohos-sdk llvm/bin 加入 PATH。
CI 原生构建分支不要覆盖 LD，由 worker 环境自行探测。

## 修复前后证据

| | 修复前 | 修复后 |
|---|---|---|
| libtool archive_cmds | `""`（空） | `$CC -shared ... -o $lib` |
| .libs/ 产物 | 只有符号链接，无 .so 实体 | libscws.so.1.1.0（ELF 64-bit ARM aarch64） |
| make 结果 | cli 链接 `no such file or directory` | conan create / W3 全绿 |

## 适用范围 / 不适用范围

- 适用：macOS 开发机交叉构建（ohos-local 或异构 build profile）+ 源码包自带
  预生成 configure + libtool 的共享库项目。
- 不适用：CI OHOS worker 原生构建（ld 解析正确，libopendbx/1.4.6 已验证）；
  CMake/Meson 项目；纯静态库配方。

## 与既有知识的差异

E072/E122/E268 覆盖的是 config.guess/config.sub 不识别 ohos 三元组（configure
响亮失败）。本条发生在三元组识别之后，是 libtool 链接器探测阶段的静默失败，
错误特征与修复手段均不重叠。
