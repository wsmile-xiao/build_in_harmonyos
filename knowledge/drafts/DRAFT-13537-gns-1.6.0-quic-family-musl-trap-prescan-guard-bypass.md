# QUIC 族 musl 坑的预扫判定：特性宏守卫使 CMSG/affinity 坑不触发

- **软件**: gamenetworkingsockets 1.6.0（HarmonyOS PC 适配）
- **对照**: msquic 2.6.1（同族，三补丁）
- **结论**: 零源码补丁——坑被上游特性宏守卫在预处理器阶段裁掉

## 现象

适配 Linux epoll/datagram 系网络库（QUIC/UDP 族）到 OHOS（musl）时，已知两个高频坑：

1. `pthread_setaffinity_np` 未声明（glibc 扩展，musl 不提供）
2. `CMSG_NXTHDR` 宏内部 size_t/ptrdiff_t 混用，`-Werror -Wsign-compare` 下在宏展开处报错

msquic 2.6.1 两个坑全踩（三个补丁）。问题是：同族库是否需要照搬补丁？

## 根因

坑只在**调用点真实进入编译单元**时成立。两库的上游设计差异决定坑的命中：

| | msquic 2.6.1 | gamenetworkingsockets 1.6.0 |
|---|---|---|
| affinity 调用 | 有（CxPlatThreadCreate 尾部无条件段） | 零调用 |
| CMSG 遍历 | datapath_linux.c 无守卫直接展开 | `#if PlatformSupportsRecvMsg() && PlatformSupportsRecvTOS()` 守卫 |
| OHOS 下守卫取值 | — | `PlatformSupportsRecvTOS()` = `PlatformSupportsRecvMsg() && defined(IP_RECVTOS)`，musl 探测失败 → false → **整段被预处理器裁掉** |

## 处置

适配前做三步预扫，而不是照搬同族补丁：

```bash
# 1) affinity 预扫：零调用即免 affinity patch
grep -rn "setaffinity" src/ --include="*.c" --include="*.cpp" --include="*.h"
# 2) CMSG 使用点与外层守卫宏
grep -rn "CMSG_NXTHDR" src/ --include="*.cpp"
# 3) 守卫宏的平台判定链（取值链要到 platform 头的 #if/#else）
grep -n "PlatformSupportsRecvTOS" src/public/tier0/platform_sockets.h
```

判定物证：configure 日志的 check_symbol_exists 探测行 + 源码守卫链行号。守卫取 false → 免 patch；无守卫 → msquic 式 pragma 降噪。

## 验证

- 零补丁 `conan create` G2 全绿
- 上游 ctest 3/3 PASS：crypto（2.09s）/ connection_quick（206s，回环真实收发走完整 recv 路径）/ connection_soak（长测）
- 若坑真实存在，connection_quick 的 recv 路径会直接编译失败或运行崩溃

## 关键点

- "同族库"不是坑的判定依据，"守卫宏在该平台的实际取值"才是
- 预扫成本（3 条 grep）远低于预打无效补丁再排错的成本
- msquic 的三个补丁模式（affinity 守卫 + CMSG pragma ×2）仍是"无守卫场景"的标准答案——本条目是其**边界判定**，不推翻它
