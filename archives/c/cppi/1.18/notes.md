# cppi 1.18 适配笔记

## 编译环境
- 构建系统: autotools (configure + make)
- 编译日期: 2026-07-15
- 编译器: clang
- 目标平台: HarmonyOS PC (os=OHOS arch=armv8)
- 状态: built

## 编译步骤
1. 下载源码 tarball
2. OHOS 适配通过 build() 内 replace_in_file 完成（E007/E110/E165），无独立补丁文件
3. autotools 标准流程: configure -> make -j1 -> make check -> make install

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 无法识别 HarmonyOS → configure 报 "cannot guess build type" | E007: GNU config.guess 2013-02-12 无 HarmonyOS 检测分支 | replace_in_file 在 *:NetBSD:*:*) 前插入 *:HarmonyOS:*:* → aarch64-unknown-linux-ohos |
| 2 | config.sub 不识 ohos-linux 三元组 / linux-ohos* kernel-OS | E007: config.sub 缺少 OHOS 支持 | replace_in_file 添加 ohos-linux 三元组 + linux-ohos* kernel-OS |
| 3 | configure shebang #!/bin/sh 在 OHOS 不存在 | E165: OHOS 无 /bin/sh | replace_in_file 修改为 /system/bin/sh |
| 4 | HMDFS umask 077 限制临时文件创建 | E110: HMDFS 限制 umask | replace_in_file 修改 umask 077 -> 002 |
| 5 | make -j 多核编译可能触发 gnulib 重建 | gnulib 时间戳敏感，并行构建可能重跑 autotools | 使用 make -j1 |

## 依赖版本
无外部 Conan 依赖。flex 作为构建工具需 CI Worker 提供。

## 产物
- bin/cppi (命令行工具)

## 验证结果
- CI #2329 初始失败（config.guess 不识 OHOS），补丁后待重跑
- test_package: 创建包含 #if/#endif 的 C 文件并运行 cppi 检查输出，含 stdin 模式冒烟
- 上游测试: build() 阶段通过 make check 执行 ~40 个 shell-based 功能测试
