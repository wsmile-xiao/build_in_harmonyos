# nim 2.2.8 适配笔记

## 编译环境
- 构建系统: custom (Nim self-hosted bootstrap)
- 编译日期: 2026-08-19
- 编译器: clang 15.0.4 (aarch64-unknown-linux-ohos)
- 状态: built

## 编译步骤

Nim 编译器本身是用 Nim 语言编写的，需要通过 bootstrap 编译：

1. **克隆 csources_v3**: 从 https://github.com/nim-lang/csources_v3.git 克隆
   到指定 commit `eeab3ac46e93f10efda8e58c4db02b9438319d71`
2. **编译 bootstrap 编译器**: `make -C csources_v3 -j4 CC=clang uos=linux`
   - `uos=linux` 是必需的，因为 HarmonyOS 的 `uname` 返回 "HarmonyOS"，
     不匹配 Makefile 中任何 OS 分支。OHOS 是 Linux-like，所以覆盖为 linux。
   - csources 是纯 C 代码，用 clang 直接编译。
3. **编译 koch**: `bin/nim c --noNimblePath --skipUserCfg --skipParentCfg --hints:off --cc:clang koch`
   - `--cc:clang` 告诉 Nim 使用 clang 作为 C 编译器
4. **编译完整 Nim 编译器**: `./koch boot -d:release --skipUserCfg --skipParentCfg --hints:off --cc:clang`
   - koch boot 执行 3 次迭代编译，直到生成稳定的二进制
   - 最终产物在 `bin/nim`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | csources Makefile 报 "unknown operating system: harmonyos" | HarmonyOS 的 `uname` 返回 "HarmonyOS"，不匹配 Makefile 中的 OS 分支 | make 时传入 `uos=linux` 参数覆盖 OS 检测 |
| 2 | 链接器 lld 报 "xmlSetGenericErrorFunc: symbol not found" | OHOS SDK 的 lld 依赖 libxml2.so.16，但 LD_LIBRARY_PATH 未包含 SDK lib 目录 | 在 generate() 中设置 LD_LIBRARY_PATH 指向 SDK lib 目录 |
| 3 | Nim 编译器默认使用 gcc | Nim 配置默认 CC 为 gcc，但系统中无 gcc | 使用 `--cc:clang` 标志指定 clang |
| 4 | csources_v3 不包含在源码 tarball 中 | Nim 2.2.8 的 csources_v3 是独立的 git 仓库 | 在 build() 中使用 git clone 获取 csources_v3 |

## 源码修改

无源码修改。所有适配通过编译参数解决，不需要补丁。

## 依赖版本

无外部依赖。Nim 是自包含的：
- csources_v3 是纯 C 代码（用 clang 编译）
- stdlib 包含在源码树中
- 无外部 C 库依赖

## 验证结果

```bash
$ ./bin/nim --version
Nim Compiler Version 2.2.8 [Linux: arm64]
Compiled at 2026-08-19
Copyright (c) 2006-2026 by Andreas Rumpf

active boot switches: -d:release
```

## 交付物

| 文件 | 说明 |
|------|------|
| bin/nim | Nim 编译器二进制 (6.3MB) |
| lib/ | Nim 标准库 (312 个 .nim 文件) |

## 注意事项

- csources_v3 需要网络访问（git clone），在离线环境无法编译
- LD_LIBRARY_PATH 需要包含 OHOS SDK 的 lib 目录，否则链接器失败
- Nim 编译器生成的 C 代码需要调用 clang 进行编译，PATH 中需有 clang
---

**编译结束**: 2026-08-19 17:32
**最终状态**: built
