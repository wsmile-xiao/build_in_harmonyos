# DRAFT-11759-vrpn-07.36-cmake-unix-var-false-gated-subdir-link-fail：CMake `UNIX` 变量 FALSE 致 `if(UNIX)` 门控子目录被静默跳过、链接期缺库

> Contributor: 主理-60 | Status: Draft | Updated: 2026-09-26
> Source: vrpn 07.36 适配（任务 11759）
> 对应：`knowledge/drafts/DRAFT-11759-vrpn-07.36-cmake-unix-var-false-gated-subdir-link-fail.kv`
> 同根因先例：E092（configure 期 unknown platform + toolchain 方案）、E532（三分支 else 兜底 FATAL + HarmonyOS 判据方案）——本条是同一根因在**单分支静默门控**形态下的另一条症状路径，解法不同。

## 现象

configure 全程无告警、构建推进正常，到链接 `vrpn_server` 时爆：

```console
ld.lld: error: cannot find -lvrpn_atmel
```

关键线索：报错的库**应该**由某个子目录产出，但 configure 日志里那个子目录
连"被跳过"的提示都没有——它压根没被纳入构建。

## 根因

HarmonyOS 主机 `uname -s` = `HarmonyOS`，CMake（含 4.1.2）没有
`Platform/HarmonyOS.cmake` 平台模块 ⇒ 平台检测分支全部落空。后果有两层：

1. configure 期可能报 `System is unknown to cmake`（**E092 已录**，解法是
   `-DCMAKE_SYSTEM_NAME=Linux` + toolchain）；
2. **更隐蔽的第二症状（本条）**：CMake 内建平台变量 `UNIX` 被置为 **FALSE**。
   探针实测（在 CMakeLists.txt 里临时插 `message(STATUS "UNIX=${UNIX}")`）：
   configure 输出 `UNIX=`（空）。

于是上游用 `if(UNIX)` 门控的「仅在 Unix 构建」子目录（vrpn 的 `atmellib`）
被**静默跳过**；而 server 侧目标以 `NOT WIN32`（或无条件）引用
`vrpn_atmel` ⇒ 链接期才爆缺库。两处门控语义本应等价，在 HarmonyOS 上
却因平台变量失衡而分叉。

与同族条目的区别（查重留痕）：

| | E092 | E532 | 本条 |
|---|---|---|---|
| 门控形态 | 平台模块缺失 | `if/elseif/else` 三分支 | 单 `if(UNIX)`、无 else |
| 爆发点 | configure 报 unknown platform | configure 期 `FATAL_ERROR "Unsupported platform"` | **configure 零告警**，链接期缺库 |
| 解法 | `CMAKE_SYSTEM_NAME=Linux` + toolchain | `elseif(UNIX OR CMAKE_SYSTEM_NAME STREQUAL "HarmonyOS")` | `if(NOT WIN32)`（零平台名） |

## 方案

把上游 `if(UNIX)` 门控改为 `if(NOT WIN32)`：

```cmake
# 上游（语义：除 Windows 外全构建）
if(UNIX)
  add_subdirectory(atmellib)
endif()

# 补丁后（语义不变，HarmonyOS 上成立）
if(NOT WIN32)
  add_subdirectory(atmellib)
endif()
```

一行补丁、不引入任何平台宏（PF5 合规），L4 patches clean 直接通过。

⛔ **不要**用 E092 的 `CMAKE_SYSTEM_NAME=Linux` 覆盖去"骗" `UNIX=TRUE`：
那会把上游所有 Linux 专属分支全部打开（init/安装路径/dl 等），副作用远大于
一行门控对齐。E092 的方案针对的是 configure 直接失败的形态；本条症状下
configure 已经能过，只差门控失衡这一处。

## 边界

- `if(UNIX AND X)` 复合条件**不要盲替换**，先确认该分支在 Linux 上的真实语义；
- 子目录被静默跳过不产生任何告警 ⇒ 排查要从**链接错误反查**被跳过的子目录，
  别在 configure 日志里找线索；
- `UNIX=FALSE` 是平台模块缺失的直接后果，各 CMake 版本表现一致，别误判成
  单机环境问题。

## 证据（vrpn 07.36，任务 11759，2026-09-26 B 机实测）

- 探针：configure 输出 `UNIX=`（空）；`uname -s` = `HarmonyOS`；CMake 4.1.2
- 症状：`vrpn_server` 链接期 `cannot find -lvrpn_atmel`
- 修法：补丁 0001（`archives/v/vrpn/07.36/patches/0001-CMakeLists.txt.patch`）
- 结果：L4 patches clean 通过；conan-verify 第 5 轮 G0-G4 与 L 段全 PASS
  （`reports/w3-local-ci.log`，`Success: 1 / Failed: 0`）
