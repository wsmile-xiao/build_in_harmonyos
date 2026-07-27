# Argon2 20190702 适配笔记

## 编译环境
- 构建系统: makefile
- 编译日期: 2026-04-24
- 编译器: clang/clang++
- 状态: success

## 编译步骤
1. `git clone --branch 20190702` 下载源码（wget 下载超时，改用 git clone）
2. `make -j1 KERNEL_NAME=Linux LIBRARY_REL=lib` 编译
3. 手动复制文件到 staging 目录（install 命令不可用）
4. `make test` 运行测试

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | GitHub wget 下载超时 | 网络问题 | 使用 git clone 替代 wget |
| 2 | KERNEL_NAME 不识别 | HarmonyOS 不在 Makefile 支持列表中 | 设置 KERNEL_NAME=Linux 环境变量 |
| 3 | install 命令缺失 | HarmonyOS 无 install 命令 | 手动执行文件复制（cp、mkdir） |
| 4 | bash 路径问题 | install.sh 使用 /bin/bash，HarmonyOS 无此路径 | 使用 /data/service/hnp/bin/bash |

## 验证结果
- `make test` — 所有测试通过（Argon2i/Argon2d/Argon2id v=16/v=19 全部 OK）
- 功能验证：`echo -n "password" | argon2 somesalt -t 2 -m 16 -p 1 -l 32` → Verification ok
- 质量门禁 ohc-run.py verify-build → PASS

## 交付物
| 文件 | 大小 | 说明 |
|------|------|------|
| argon2-20190702-ohos-aarch64.tar.gz | 527KB | 预编译安装包 |
| debug.tar.gz | 12KB | 调试信息包 |

## 注意事项
- 使用 ref.c 参考实现，无 SIMD 优化
- 需设置 KERNEL_NAME=Linux
- 安装产物包含：bin/argon2, lib/libargon2.a, lib/libargon2.so.1, include/argon2.h, lib/pkgconfig/libargon2.pc
---

**编译结束**: 2026-07-15 21:48
**最终状态**: built
