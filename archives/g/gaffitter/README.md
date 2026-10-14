# GAFFitter (gaffitter)

## 是什么

GAFFitter（Genetic Algorithm File Fitter）是 Douglas A. Augusto 开发的命令行
工具，用遗传算法求解装箱问题（Bin Packing）：把一组文件/条目组合进尽可能少的
固定容量卷（如 CD/DVD），使空间浪费最小。典型用法 `fit -t 700m *` 把当前目录
文件组合为若干 ≤700MB 的集合。也可用 `--di`（direct input）直接读
"大小 标识" 二元组流，不依赖真实文件。

上游（2005-2015，最终版 1.0.0）：
- 主页: https://gaffitter.sourceforge.net/
- 项目页: https://sourceforge.net/projects/gaffitter/
- 源码 tarball: https://downloads.sourceforge.net/project/gaffitter/gaffitter/1.0.0/gaffitter-1.0.0.tar.gz
- 许可证: GPL-3.0-or-later

## 功能概述

- 遗传算法全局搜索：`--ga-*` 系列参数控制种群/世代/交叉/变异概率等
- 过滤器式设计：支持 stdin 管道输入（`... | fit - -t 700m`）
- 直接输入模式：`--di` 读取 "size id" 对而非文件名（`--di-b/k/m/g/t` 指定单位）
- 备选搜索：`--ap`（Best Fit 快速近似）、`--sp`（顺序 Split）
- 输出控制：`--ss/--sb`（显示大小）、`--hi/--hs`（隐藏条目/摘要）、
  `--bs/--ew/--dw`（分隔/包裹/定界符）、`-1..-9` 预设搜索强度
- 容量/范围控制：`-t`（目标容量，必选）、`--min/--max`（条目大小范围）、
  `-B`（块大小对齐）、`--si`（1000 进制单位）

## OHOS 适配

- 产物：`bin/fit`（可执行文件名与包名不同，上游历史命名）
- 构建系统：CMake（上游声明 `cmake_minimum_required(VERSION 2.4)`；CMake ≥ 4.0
  需传 `CMAKE_POLICY_VERSION_MINIMUM=3.5`，官方兼容机制，配方内处理，无 patch）
- 平台依赖：纯 POSIX（`sys/stat.h`、`dirent.h`、`unistd.h`、`rand/srand`），
  musl libc 完整覆盖；无 `__OHOS__`/OS 名称分支，无补丁
- 依赖：无第三方库依赖（C++ 标准库 + libc）

## 依赖关系

- 编译依赖：无（仅 CMake + C++ 编译器）
- 运行依赖：无（静态链接 libc++/libc 由工具链决定）

## 参考资料

- 官网: https://gaffitter.sourceforge.net/
- SourceForge 项目: https://sourceforge.net/projects/gaffitter/
- SIGEVO Newsletter (2008) 介绍: https://dl.acm.org/doi/pdf/10.1145/1527055.1527061
