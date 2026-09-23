# yacas 1.9.1 适配笔记

## 任务来源

- 平台任务 contrib-12236（开源鸿蒙PC专项积分赛），分支 `feat/yacas-1.9.1`，2026-09-19 认领
- 上游：https://github.com/grzegorzmazur/yacas （145 stars，非 fork，tag v1.9.1 实拉核验存在）
- 语言实测（R47 lang-preflight）：cpp（GitHub lang 字段标 JavaScript 系 jyacas/web 前端干扰，源码实测 C++ 主体）

## 选库核验（§3.2 否决线）

1. 他人已移植：`archives/` 比对 + 同源反查均无；制品仓无 yacas（设备实测）
2. 语言/构建生态：C++ + CMake 3.10，CI 工具链具备
3. 难度定级：A（纯编译适配，零补丁、零外部依赖；GUI/Kernel/Java 组件按平台裁剪关闭）

## 上游测试清点（R51）

- tests/ 下 53 个 .yts 脚本测试（ctest 注册，上游 test-yacas runner 驱动）
- cyacas 引擎 C++ 单元测试（ENABLE_CYACAS_UNIT_TESTS=ON 构建）
- 实测统计见下文与 PR 描述

## 平台适配要点

- **GUI/Kernel/Jyacas 关闭**：Qt/Jupyter/Java 不在本平台，保留控制台与库
- **脚本库随包交付**：控制台运行期加载 share/yacas/scripts，安装规则上游自带
- **LD_LIBRARY_PATH 盾**：build() 显式清空

## 编译结束

设备实机验证（2026-09-20，OHOS aarch64）：

- `conan-verify`：G0/G1/G2/G3/G4 + L2/L4/L5 全部 PASS（RC=0）
- CI 同源闸门：L0/L1/L4/L5 全 pass，Pass rate 100%
- 上游测试：ctest **82/82 全过（100%）**——53 个 .yts 脚本测试 + 29 个 C++ 单元测试（gtest/1.17.0.2 为昨天本账号合入发布的包）
- test_package：库级 6 项断言（脚本库加载 + 5 项求值）+ CLI 2 项全过

踩坑记录（已修复）：

1. `if (UNIX)` 选错源码分支：CMake 无 Platform/HarmonyOS 模块（E092），UNIX 未定义 → 编了 win32commandline.cpp（windows.h 缺失）。配方 cache_variables 钉 UNIX=ON，零补丁
2. tests/test-yacas shebang `#! /bin/bash` 在平台不存在（bash 在 /data/service/hnp/bin）→ ctest 53 个 .yts 全部 BAD_COMMAND 未运行。补丁 0001 改 `#!/usr/bin/env bash` 后 82/82 全过
3. ENABLE_CYACAS_UNIT_TESTS=ON 需要 GTest——gtest/1.17.0.2 恰为本账号昨日合入发布，visible=False 引用（不进消费者依赖）
4. CYacas 引擎的中缀运算符来自脚本库：测试须先 DefaultDirectory(scripts)+Load(yacasinit.ys)（与上游控制台一致）；Result() 带尾部分号
5. 版本探针：yacas 无 --version，版本在控制台启动 banner（"This is Yacas version '1.9.1'"）
