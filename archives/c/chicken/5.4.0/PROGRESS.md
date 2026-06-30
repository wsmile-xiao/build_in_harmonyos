# chicken 5.4.0 编译进度

**日期**: 2026-04-29
**软件**: chicken 5.4.0
**构建系统**: autotools (自定义 Makefile)
**状态**: partial

## 编译步骤记录

| 步骤 | 状态 | 时间 | 备注 |
|------|------|------|------|
| Step 1 init-build | ✅ 完成 | 00:24 | 下载、解压、骨架创建 |
| Step 2 make | ✅ 完成 | ~200s | PLATFORM=linux PREFIX=$DEFAULT_PREFIX |
| Step 3 install (DESTDIR) | ✅ 完成 | 00:29 | staging 隔离安装 |
| Step 4 check | ⚠️ 部分 | ~180s | posix file-permissions 测试失败 |
| Step 5 verify-build | ✅ 完成 | 00:32 | G1-G4 质量门禁通过 |
| Step 6 package | ✅ 完成 | 00:33 | 生成 22MB 预编译包 |
| Step 7 本地安装 | ✅ 完成 | 00:33 | chicken --version 验证通过 |
| Step 8 finish | ✅ 完成 | 00:33 | 归档收尾，状态 partial |

## 编译参数

```bash
# 编译命令
make PLATFORM=linux PREFIX=/storage/Users/currentUser/usr/local

# 安装命令 (DESTDIR 模式)
make install DESTDIR=/storage/Users/currentUser/test-install-chicken-5.4.0 \
  PLATFORM=linux PREFIX=/storage/Users/currentUser/usr/local

# 测试命令
make PLATFORM=linux PREFIX=/storage/Users/currentUser/usr/local check
```

## 关键变量

- `PLATFORM`: linux (使用 Makefile.linux)
- `PREFIX`: ~/usr/local (运行时路径)
- `DESTDIR`: ~/test-install-chicken-5.4.0 (staging 目录)
- `BUILD_SRC_DIR`: ~/builds/chicken-5.4.0.work
- `BUILD_ARCHIVE_DIR`: archives/c/chicken/5.4.0

## 测试结果摘要

- 通过: 6376+ 测试
- 失败: 1 测试 (posix file-permissions)
- 总计: 6377+ 测试
- 状态: PARTIAL

## 产物清单

### 二进制文件
- chicken (2.7 MB) - Scheme-to-C 编译器
- csi (231 KB) - Scheme 交互式解释器
- csc (240 KB) - 编译器驱动
- chicken-install (772 KB) - egg 包管理器
- chicken-uninstall (96 KB) - egg 卸载工具
- chicken-status (121 KB) - egg 状态查询
- chicken-profile (84 KB) - 性能分析
- chicken-do (23 KB) - 构建辅助
- feathers (1.9 KB) - 调试器前端

### 库文件
- libchicken.so.11 (4.0 MB) - 动态库
- libchicken.a (7.5 MB) - 静态库
- *.import.so (44个) - 模块导入库

### 预编译包
- chicken-5.4.0-ohos-aarch64.tar.gz (22 MB)
- chicken-5.4.0-ohos-aarch64-debug.tar.gz (2.6 MB)
- install-chicken-5.4.0.sh (1.4 KB)

## 发现与知识

### 平台限制 (L1)

**E046: chmod 不生效**
- 现象: posix file-permissions 测试失败，期望权限 438，实际不符
- 原因: 鸦蒙平台 SELinux 限制
- 影响: 文件权限控制功能受限
- 解决: 标记为平台限制，不阻塞编译
- 参考: SKILL.md §7 Gotchas

### 编译经验 (L2)

**自定义 Makefile 构建系统**
- 特点: 不使用标准 configure，直接指定 PLATFORM
- 参数: `make PLATFORM=linux PREFIX=...`
- 注意: 不支持并行编译 (-j)
- 编译时间: ~200 秒

**DESTDIR 模式正确应用**
- configure --prefix=$DEFAULT_PREFIX (运行时路径)
- make install DESTDIR=$TEST_PREFIX (staging)
- 打包从 staging 提取

### 本版笔记 (L3)

- 无源码修改，补丁数为 0
- 预生成的 .c 文件直接可用
- 编译选项: -Os -fomit-frame-pointer -fno-strict-aliasing -fwrapv
- 编译器: gcc (clang 15.0.4)

## 问题记录

### 问题 1: posix file-permissions 测试失败

**详情**:
```
Error: (posix-tests.scm:116) assertion failed: 
(equal? (file-permissions "posix-tests.out") 438)
```

**分析**:
- 测试期望文件权限为 0666 (438)
- 实际权限因 SELinux 限制不符
- 属于鸿蒙平台已知限制

**解决**:
- 不阻塞编译流程
- 状态标记为 partial
- 归档完整，可分发

### 问题 2: G0 干净构建验证失败

**详情**: Python subprocess 平台限制

**解决**: 手动验证通过，不影响归档

## 对话记录

### Session 1: 编译流程执行

1. **init-build**: 成功初始化，下载源码
2. **编译**: make PLATFORM=linux 成功，耗时 ~200s
3. **安装**: DESTDIR 模式正确应用
4. **测试**: make check 发现 posix 测试失败
5. **打包**: ohc-run.py package 成功
6. **验证**: 本地安装，chicken --version 正常
7. **finish**: 归档收尾，状态 partial
8. **补充报告**: 添加 test-report.md, build-report.md, RELEASENOTE.md

---

**编译开始**: 2026-04-29 00:24
**编译结束**: 2026-04-29 00:33
**报告补充**: 2026-05-07 14:49
**最终状态**: partial
**归档完整**: ✅