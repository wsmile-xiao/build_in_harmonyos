# expat 2.7.1 适配笔记

## 编译环境
- 构建系统: cmake（原 autotools 因权限问题改用 CMake）
- 编译日期: 2026-04-25
- 编译器: clang / clang++
- 状态: success

## 编译步骤
1. 下载并解压 expat 2.7.1 源码
2. 更新 config.guess/config.sub（添加 HarmonyOS 支持）
3. 尝试 autotools 构建失败（configure 权限问题）
4. 改用 CMake 构建：`cmake -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX ..`
5. `make -j4 && make test && make install DESTDIR=$TEST_PREFIX`
6. `make install`（本地安装）
7. xmlwf --version 验证成功

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | autotools configure Permission denied | HMDFS 文件系统限制 + shell 临时文件机制（toybox sh 使用 /tmp） | 改用 CMake 构建 |
| 2 | config.guess 不识别 HarmonyOS | 缺少 HarmonyOS 检测分支 | 下载最新版 + 手动添加 aarch64:HarmonyOS 检测 |

## 依赖版本
- 无外部依赖

## 验证结果
```bash
make test
# 结果: 100% tests passed, 0 tests failed out of 2

xmlwf --version
# 显示: expat_2.7.1 ✅
```
