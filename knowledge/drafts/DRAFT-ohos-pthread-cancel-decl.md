# DRAFT-ohos-pthread-cancel-decl：OHOS GNU pthread cancel 声明型兼容

> Contributor: nymphcast-0.2 适配 | Status: Draft | Updated: 2026-08-27
> Source: archives/n/nymphcast/0.2-alpha0（patch 0004）+ 设备 nm 实测 + Auditor B2-1

## 现象

NymphCast 服务端的 lcdapi 直接使用 GNU pthread 取消 API
（`pthread_cancel` / `pthread_setcanceltype` / `pthread_setcancelstate` /
`pthread_testcancel`）。OHOS 编译报 **undeclared identifier**，与
E085/E127 描述的"musl/HarmonyOS 不实现 pthread cancel"现象相同。

## 真机核验（知识修正的关键证据）

对设备运行 libc 与编译期 sysroot 分别探测：

| 符号 | /system/lib64/libc.so（nm -D） | sysroot pthread.h |
|------|-------------------------------|-------------------|
| pthread_cancel | **T** | grep=0（无声明） |
| pthread_setcancelstate | **W** | grep=0 |
| pthread_testcancel | **W** | grep=0 |
| pthread_setcanceltype | **0 命中**（B2-1） | grep=0 |

结论：**符号存在、仅头缺声明**。`undeclared identifier` 是声明缺失错误，
不是"平台不支持"。E085/E127 的"不实现/不支持"表述与设备运行时 libc 实证不符，
很可能是设备运行 libc 与编译期 sysroot libc 差异导致。

## 解决方案（声明型兼容）

符号存在 → 声明型 compat header（`extern "C"` + 正确函数签名），经
`CFLAGS/CXXFLAGS -include` 注入每个 TU，即可编译/链接/运行，无需 stub 或
行为回退。nymphcast 0004（ohos_pthread_compat.h）即此方案，round-9 权威 CI
PASS（编译/链接/test_package --version 运行）。

### B2-1 补证（Curation Auditor 确认）

`pthread_setcanceltype` **未**在设备 libc 导出（nm 0 命中）。0004 声明了它，
且 lcdapi LCDClient.cpp/LCDSensor.cpp 实际调用 `::pthread_setcanceltype`；
但 0001 的 `#ifndef __OHOS__` 把 lcdapi 连接块裁剪，最终产物 dynsym 无
pthread_cancel/setcancel 引用（llvm-readelf -Ws 全 0），所以未触发 link 失败。

**教训：取消系列必须逐符号 `nm -D` 探测，不能因 pthread_cancel/
setcancelstate/testcancel 存在而假定 setcanceltype 全集可用。** 声明未导出符号
在该路径被真正链接时会产生 undefined reference。

## 与既有条目的关系

- E085（musl 不实现 pthread_cancel，建议 PTHREAD_IN_USE_DETECTION_HARD/stub）：
  表述需修正为"符号是否存在于设备 libc 须实测；符号存在则声明型兼容即可"。
- E127（HarmonyOS 不支持，建议 undef KMP_CANCEL_THREADS）：同样需修正。
- E320-draft-ASP1（JACK 信号回退）：符号存在时 signal 回退属过度设计；
  声明型兼容可覆盖其"符号不存在"前提之外的情形。
- 冲突处理：与 E085/E127 的"不实现"表述冲突，最终表述以知识库主编确认为准。

## 查重（B2 去重证据摘要）

- 检索词：`pthread`（knowledge/graph/*.kv → E003/E026/E085/E094/E127/E133/
  E192/E202/E211/E224/E314 等 11 条）；`pthread_cancel` 全 knowledge。
- 最相近：E085、E127、E320-draft-ASP1-pthread-cancel-lifecycle。
- 差异：三者均以"符号缺失/不支持"为前提出方案；本条目以设备 nm 实证
  （T/W 符号存在）为前提，方案是声明型兼容头 + 逐符号探测，属知识修正。
- 新增价值：确立"先 nm -D 探测设备 libc → 声明型兼容 vs stub vs 行为回退"
  的决策路径，避免过度工程；修正影响面=libgpg-error/squashfs-tools/redis/
  mosquitto/iperf3（E085）+ libomp（E127）+ JACK（ASP1）。

## 禁止做法

- 不要因为"是 OHOS"就断定 pthread cancel 不支持（能力探测优先）。
- 不要声明未 `nm -D` 验证的取消系列符号（B2-1：setcanceltype 未导出）。
- 符号存在时不要用 no-op stub 吞掉真实取消语义或做过度信号回退。
