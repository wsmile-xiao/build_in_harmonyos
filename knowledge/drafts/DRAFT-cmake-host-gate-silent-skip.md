# CMake 宿主门禁按 SYSTEM_NAME/SYSTEM_PROCESSOR 名称匹配 AND 判定并静默 return()，非 Linux 名称宿主需门禁正则与 Platform 模块双修

## 问题描述

上游 CMake 工程常用"宿主平台名称匹配"决定是否构建某个组件。当判断形如：

```cmake
if(NOT (CMAKE_SYSTEM_PROCESSOR MATCHES "(x86_64)|(ppc64le)|(aarch64)$" AND
        CMAKE_SYSTEM_NAME MATCHES "Linux"))
  message(STATUS "Not building XXX plugin: ...")
  return()
endif()
```

在不被 CMake 认识的宿主名（如 HarmonyOS）上，**两个条件都按"名称字符串"失败**，组件被直接 `return()` 跳过——**没有 CMake Error、没有编译错误，configure 以 rc=0 正常结束**，只在输出里留一行 `-- Not building ...` STATUS 提示。误信 rc=0 的构建方会得到一个"成功配置但目标组件根本不存在"的构建树。

案例（括注）：libomptarget-rtl-amdgpu 18.1.8 在 HarmonyOS PC 真机上的 amdgpu 插件即被该门静默跳过。

## 根因机理

两个弱探测条件在 HarmonyOS 宿主上同时失效：

1. **系统名半边**：CMake 按 `uname -s` 查找 `Platform/<name>.cmake`。HarmonyOS 宿主 `uname -s` 返回 `HarmonyOS`，CMake 无 `Platform/HarmonyOS.cmake`，于是 `CMAKE_SYSTEM_NAME=HarmonyOS`，不匹配 `"Linux"`，并伴随 `System is unknown to cmake, create: Platform/HarmonyOS` 警告。若依赖 LLVM 上下文，缺 Platform 模块还会在 `HandleLLVMOptions.cmake:194` 触发 `Unable to determine platform` 致命 SEND_ERROR（include 栈：`CMakeLists.txt` 的 include 处）。
2. **处理器半边**：`CMAKE_SYSTEM_PROCESSOR` 取自 `uname -p`。该设备内核 `uname -p` 返回 `unknown` → `CMAKE_SYSTEM_PROCESSOR=unknown`，不匹配任何架构正则。

AND 门禁任一半边失败即静默 `return()`。这是**双缺口**：只修系统名（给门禁加 HarmonyOS 分支）而平台模块缺位时，构建仍可能死在 LLVM 平台探测；只补 Platform 模块而门禁正则未放行、或 PROCESSOR 仍为 unknown 时，组件照样被跳过。两半必须同时处理。

## 诊断范式：不要相信 rc=0，用 STATUS 行清点

- configure 结束后对输出执行 `grep -E "Not building|System is unknown to cmake"`，清点被静默跳过的组件；
- 修复完成的判据是出现 `-- LIBOMPTARGET: Building AMDGPU NextGen plugin ...` 且 `Not building` 计数为 0，而不是 configure 退出码。

## 解决方案

**主案（门禁正则 + Platform shim 双修）**：

1. 门禁正则放行同名宿主（可向上游提交的最小修改）：

```cmake
if(NOT (CMAKE_SYSTEM_PROCESSOR MATCHES "(x86_64)|(ppc64le)|(aarch64)$" AND
        CMAKE_SYSTEM_NAME MATCHES "(Linux|HarmonyOS)"))
```

2. 自写 Platform 模块 shim 并经 `-DCMAKE_MODULE_PATH` 注入，把处理器名从 `uname -p` 的 `unknown` 纠正为真实目标架构：

```cmake
# Platform/HarmonyOS.cmake
set(CMAKE_SYSTEM_PROCESSOR aarch64)
include(Platform/Linux)
```

3. configure 收尾用 STATUS 行清点（见诊断范式）。

**fallback A（toolchain 强制 Linux，仅退路）**：`project()` 之前注入 `-DCMAKE_SYSTEM_NAME=Linux -DCMAKE_SYSTEM_PROCESSOR=aarch64`。诚实权衡：这是掩盖真实平台名而非修复——向构建系统谎称 Linux，会置 `CMAKE_CROSSCOMPILING=TRUE`、改变上游交叉编译语义，并污染项目内其他按系统名分支的逻辑（OS_LINUX 宏、安装路径、特性探测）。必须记录技术债，不得作为常规方案。

**辅助手段（范围有限，不是完整退路）**：LLVM 上下文中 `cmake/config.guess` 不认识 HarmonyOS，可替换为直接输出目标三元组（如 `aarch64-unknown-linux-ohos`）的 stub。它只解决 LLVM 自己的宿主三元组探测，**不解决** CMake 的 SYSTEM_NAME/SYSTEM_PROCESSOR 门禁，不能替代主案。

**禁止项**：见 .kv `forbid_*`——不得静默冒充 Linux 而不声明权衡；不得删除门禁 `return()` 或整体剔除插件目录绕过上游守卫。

## 诚实权衡（弱探测形态的边界）

平台名称匹配本质是**弱探测**：本条主案仍是"把名字加进白名单"，只是让弱探测在 HarmonyOS 上不再误判。长期出路是**平台能力探测**（探测具体接口/头文件/符号）或上游提供正经的 `Platform/HarmonyOS.cmake`（已按 CMake 官方提示提交 config），使宿主识别不再依赖名字枚举。在该目标达成前，名称匹配 + 显式清点是可审计的务实解。

## 验证（自包含，任何开新 shell 可复现）

```sh
uname -s; uname -p          # HarmonyOS 宿主：HarmonyOS / unknown
mkdir -p /tmp/gate-probe && cd /tmp/gate-probe
printf 'cmake_minimum_required(VERSION 3.20)\nproject(gate C)\nif(NOT (CMAKE_SYSTEM_PROCESSOR MATCHES "(x86_64)|(ppc64le)|(aarch64)$" AND CMAKE_SYSTEM_NAME MATCHES "Linux"))\n  message(STATUS "Not building AMDGPU NextGen plugin: only support AMDGPU in Linux x86_64, ppc64le, or aarch64 hosts")\n  return()\nendif()\nmessage(STATUS "BUILDING plugin")\n' > CMakeLists.txt
cmake -B build -S . ; echo rc=$?   # 预期：打印 Not building 行且 rc=0（静默跳过）
```

把 `MATCHES "Linux"` 改为 `MATCHES "(Linux|HarmonyOS)"` 后重跑，同一最小工程输出 `BUILDING plugin`——单独演示系统名半边；处理器半边可在 `uname -p` 为 unknown 的宿主上保持 `unknown` 再观察第一条件失败。

## 证据与归因说明（本 run 探针日志）

探针日志留档于本 run 临时目录，按时间序：

- **未打补丁**（probe-configure2.log:61）：原始措辞 `Not building AMDGPU NextGen plugin: only support AMDGPU in Linux x86_64, ppc64le, or aarch64 hosts`——系统名半边静默跳过的直接证据；同日志 :74 起 `AddLLVM.cmake:1962` 错误属另一机理（见姊妹条 DRAFT-cmake-cache-var-override-dropped-by-include），勿混引。
- **混合态**（probe-configure3.log）：名称补丁已应用、Platform shim 未就位。**该日志不是干净中间态**：:368 有未归因 SEND_ERROR（`HandleLLVMOptions.cmake:194 Unable to determine platform`，由缺 `Platform/HarmonyOS` 模块引发，属 LLVM 平台探测而非 amdgpu 门禁）；其 :739 的 `Not building AMDGPU ...（Linux/HarmonyOS 措辞）` 应归因于 AND 门**处理器半边**（`uname -p=unknown`），不能引作系统名门禁的证据。
- probe-configure4.log:65 / probe-configure5.log:63：Platform shim 渐次就位后仍被处理器半边拦截——证明双缺口必须双修。
- 最终修复后 configure 全通，权威 CI run3 实测插件构建且 test_package dlopen+dlsym 通过（run 日志为 CI 收尾证据）。

## 适用范围与同族条目

任何以系统名/处理器名匹配做宿主或组件门禁的 CMake 项目。同族：E140（CMAKE_SYSTEM_NAME=HarmonyOS 不匹配 Linux）、E092（System is unknown to cmake）、E090（meson host_system 名不匹配 linux）、E100（平台 unknown 导致组件禁用后测试仍链符号）、E532（if(WIN32)/elseif(UNIX)/else() 三分支不识别 HarmonyOS 落 else()）。本条新增价值：**AND 双条件的静默失败形态**与"正则 + Platform 模块双修、STATUS 清点收尾"的完整方案空间为既有条目未覆盖。
