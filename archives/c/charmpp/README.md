# Charm++ (charmpp)

Charm++ 是一个基于 C++ 的并行编程框架/运行时，采用「迁移式对象（chare）+ 消息驱动」的执行模型，
广泛应用于大规模并行计算（分子动力学 NAMD、宇宙学 ChaNGa 等）。本归档为 **netlrts** 构建
（支持单机多进程与 TCP 多节点），交付编译器驱动 `charmc`、进程启动器 `charmrun`、
接口生成器 `charmxi` 与全部运行时静态库。

## 功能概述

- **chare/array/group/SDAG 并行模型**：`charmc` 编译 `.ci` 接口文件并链接 Charm++ 运行时
- **多进程运行**：`charmrun ++local +pN ./app` 单机多进程；`charmrun` 亦支持主机文件多节点
- **自动负载均衡**：TreeLB/MetisLB/RefineLB 等内建策略
- **检查点/迁移、reduction、zero-copy、projections 追踪**等运行时特性

## OHOS 适配要点

| 问题 | 根因 | 解决方案 |
|------|------|----------|
| 构建脚本无法执行 | OHOS 无 `/bin/bash` | 用 `/data/service/hnp/bin/bash` 调用；脚本 shebang 补丁 |
| bash 路径解析错乱 | HMDFS 下 bash getcwd 失败 | 调用 bash 前 `export PWD=<dir>` |
| `Unsupported operating system HarmonyOS` | charm CMake 平台分支 | HarmonyOS 并入 linux 分支 |
| hwloc configure 失败 | config.guess/sub 不识别 OHOS | 补丁支持 `aarch64-unknown-linux-ohos` |
| `config.status` 权限失败 | HMDFS 下 `mktemp -d` 目录不可写 | 构建期 mktemp wrapper(exit 1) 触发 mkdir 回退 |
| `getcontext` 未定义 | OHOS musl 无 ucontext | 线程后端改 FCONTEXT（boost-context arm64 asm） |
| `-host` 编译用 g++ | CMK_NATIVE_* 固化过早 | conv-config.sh 调整赋值次序 |
| `.ci` 预处理失败 | 无 `cpp` 命令、clang 不认 .ci | `clang -E -P -x c++ -o` |
| charmrun 节点静默退出 | OHOS 无 SIGIO（F_SETOWN/O_ASYNC） | 关闭异步 IO（CMK_ASYNC_NOT_NEEDED=1） |
| charmrun 启动即退出 | getpwuid 无记录且无 `id` 命令 | mylogin 回退 `LOGNAME`/`USER` |

## 依赖关系

### 编译依赖

- `zlib/1.3.1`（制品仓；CMake `find_package(ZLIB REQUIRED)` 探测头文件，链接走 `-lz`）

### 运行时依赖

- OHOS 系统 `libc++_shared.so`、`libz.so`（系统库）
- 包内所有 Charm++/Converse 库均为静态 `.a`

## 已知限制（HarmonyOS PC）

- zero-copy 消息机制依赖 `process_vm_readv`，OHOS 沙箱拒绝（EPERM）→ 相关上游测试 10 项失败
- `++processPerSocket` 的 CPU 亲和性绑定路径段错误（`CmiInitCPUAffinity`），单机多进程
  （`++local +pN`，默认绑定）不受影响

## 使用方式

```sh
conan install --requires=charmpp/8.0.2 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64
# 或直接在 hnp 环境中使用打包的 charmc/charmrun
charmc -language charm++ -o hello hello.ci hello.C
./charmrun ++local +p4 ./hello
```
