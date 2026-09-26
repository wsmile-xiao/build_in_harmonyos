# DRAFT-8976-mpop-1.4.22-probed-but-unguarded-libc-symbol：AC_CHECK_FUNCS 探到了"没有"，调用点却没守护 —— 链接期 undefined symbol 的正解是用上游自己的 HAVE_ 宏

> Contributor: 主理-63 | Status: Draft | Updated: 2026-09-26
> Source: mpop 1.4.22 适配（任务 8976）；触发场景：G2 `conan create` 的 CCLD 阶段报
> `ld.lld: error: undefined symbol: getpass / referenced by password.o:(password_get)`，
> 而**同一次构建生成的 `config.h` 里已经写着 `/* #undef HAVE_GETPASS */`**
> 对应：`knowledge/drafts/DRAFT-8976-mpop-1.4.22-probed-but-unguarded-libc-symbol.kv`
> Issue：#3446（https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/issues/3446）

## 现象

configure 全绿、编译一路到最后一个目标才炸，报错点离根因很远：

```text
  CCLD mpop
ld.lld: error: undefined symbol: getpass
>>> referenced by password.o:(password_get)
clang: error: linker command failed with exit code 1
```

第一反应通常是"依赖没声明""链接参数丢了""conan 的 `cpp_info` 不对"。三条都在本包上排除过：
`gnutls`/`libidn2` 两条声明齐全且 DT_NEEDED 实测闭合，`-l` 列表里没有 mpop 缺的东西。

真相在 `config.h`：上游 `configure.ac` **已经**探测了这个函数，而且探测结果是正确的 ——
OHOS libc 的 `unistd.h` 不声明 `getpass`、动态符号表里也没有它，所以
`AC_CHECK_FUNCS([getpass])` 规规矩矩留下了 `/* #undef HAVE_GETPASS */`。
但 `src/password.c:215` 是**无条件**调用 `getpass()`：宏探到了却没被用起来。

## 三种失效形态的区分（本条的位置）

| 形态 | 探测结果 | 现实 | 失败位置 | 已收录处方 |
|------|---------|------|---------|-----------|
| 探测为真、运行期不可用 | `HAVE_FOO` 定义 | 调用了才失败 | 运行期 | **E320**（`fmemopen`）：改用 `AC_RUN_IFELSE` 探测并回退 |
| libc 连结构/访问器都不提供 | 探测本身无从写起 | 编译期就红 | 编译期 | **E516**（`_res`/`__res_state()`）：跳过 generic 路径 |
| **探测为假、调用点漏守护** | `HAVE_FOO` **未定义** | 符号根本不存在 | **链接期** | **本条**：复用上游自己的 `HAVE_` 宏补 `#ifdef` |

第三种最容易误判，因为工具链把"你已经知道没有"这件事完全沉默掉了。

## 根因（机制链，与目标平台无关）

autoconf 的函数探测只负责写 `config.h`，**不替调用点负责**。上游只要有任何一处
`#ifdef HAVE_X` 漏写，X 在目标 libc 上不存在时就会以链接期 undefined symbol 的形式暴露，
而不是 configure 期的"优雅关闭"。Linux glibc 上长期不发作，因为 glibc 提供这些历史函数；
换到 OHOS/musl 这类精简 libc 就集中出现，高发作区是终端/口令/进程类可选接口
（`getpass`、`ttyname_r`、`utmpx` 一族、`crypt`、`fork` 的可选分支）。

本机制与目标平台无关：在任何不提供该符号的 libc 上都同样复现。

## 方案（按顺序做）

1. **先定位"探测已存在"，不要先动链接参数。** 在同一份构建目录里看 `config.h`
   （或 configure 日志对应行）里该函数的 `HAVE_` 宏。若它已经是 `/* #undef HAVE_X */`，
   说明探测逻辑没问题，缺的只是调用点守护 —— 这一步能省下大量错方向调试。
2. **用上游自己的宏加守护，不要新增探测、不要伪造声明。**
   在调用点包 `#ifdef HAVE_GETPASS`（确保 `config.h` 的引入路径在上游已有），
   `#else` 复用上游**本来就实现**的替代路径；不改 `configure.ac`、不扩探测宏集合、
   不用 `-include` 塞一个假原型（假原型能把编译带过去，但符号照样不存在，只是把崩溃挪到运行期）。
   mpop 的 `#else` 分支不需要新写：它本来就支持 `password_program`（`--passwordeval`）
   与 `netrc` 两条取口令路径，守护后行为自然退化到这两条。
3. **把功能后果变成可观察事实。** 关掉的分支必须有替代品或断言撑着：本包在消费者测试里
   断言 `mpop --version` 打印的 `Authentication library: built-in`（同一手法也用于
   `--without-libgsasl` 的后果），并把跑不到的 3 项能力逐条声明 skipped 附实测签名。
   目标是"哪些能力在这个构建里不存在"能从日志读出来，而不是靠 PR 正文保证。
4. **交付卫生。** 补丁走随包 `patches/`，在 `conandata.yml` 的 `patches` 段把
   「探测已存在、调用点漏守护」的因果写进 `patch_description`，
   审查人不重跑链接也能判断该补丁是不是最小改动。

## 验证方法

```bash
cd archives/m/mpop/1.4.22
python3 scripts/ohc-run.py conan-verify mpop 1.4.22
# 期望：G1/G2/G3 PASS；日志里 4 条 Apply patch 含 0004，且 CCLD 不再报 undefined symbol
# 反证：临时撤掉 patches/0004 后重跑，应复现 ld.lld: error: undefined symbol: getpass
```
