# libev 4.33 编译进度记录

## 编译信息
- 软件名: libev
- 版本: 4.33
- 构建系统: CMake（替代autotools，因HMDFS限制）
- 编译状态: built
- 编译日期: 2026-07-15

## 编译过程

### Phase 1: 初始化
- 下载源码: http://dist.schmorp.de/libev/libev-4.33.tar.gz
- SHA256: 507eb7b8d1015fbec5b935f34ebed15bf346bed04a11ab82b8eee848c4205aea
- 解压成功
- 环境检查通过

### Phase 2: autotools 配置尝试（失败）
- 首次尝试: config.guess (2018-02-24版) 无法识别 HarmonyOS
- 修复: 下载最新 config.guess/config.sub (2026版) + 应用 OHOS 补丁
  - config.guess 输出: aarch64-unknown-linux-ohos
  - config.sub 验证通过
- 二次尝试: configure 成功完成所有检测，但 config.status 失败
  - 错误: "can't create ./confXXX/subs1.awk: Permission denied"
  - 原因: HMDFS 文件系统限制 autotools 临时目录创建
  - VPATH 构建也失败（同样 HMDFS 限制）

### Phase 3: CMake 构建（成功）
- 由于 autotools 在 HMDFS 上无法工作，采用 CMake 替代
- 在 conanfile.py build() 中动态生成:
  - config.h.cmake: cmakedefine 模板，配合 CMake check_include_file/check_function_exists 自动检测
  - CMakeLists.txt: 简单的 CMake 构建文件
- CMake 自动检测到所有平台特性:
  - epoll, inotify, poll, select, eventfd, signalfd, timerfd
  - clock_gettime, nanosleep, floor, __kernel_rwf_t
- 编译成功，生成 libev.a (静态库)
- 测试通过: ev_version_major/minor + ev_default_loop + ev_loop_destroy

### Phase 4: 安装和验证
- 安装头文件: ev.h, ev++.h, event.h
- 安装库文件: libev.a
- 测试程序输出: "libev version: 4.33, Default loop created successfully, Test passed"

## 遇到的问题和解决方案

### 问题1: config.guess 无法识别 HarmonyOS (E007)
- 解决方案: 下载最新版 + 应用 patch-autotools-ohos.pl 补丁
- 知识沉淀: E007 (config.guess), E072 (config.sub)

### 问题2: HMDFS 文件系统限制导致 config.status 失败
- 现象: autotools config.status 无法创建临时子目录
- 原因: HMDFS 的特殊权限限制
- 解决方案: 放弃 autotools，使用 CMake 构建系统
- conanfile.py 在 build() 中生成 CMakeLists.txt 和 config.h.cmake

## 构建产物
- libev.a: 静态库 (~70KB)
- 头文件: ev.h, ev++.h, event.h

## 后续工作
- 无需补丁文件（CMake 构建不需要修改源码）
- config.guess/config.sub 补丁仅在尝试 autotools 时使用，最终未包含在配方中
---

**编译结束**: 2026-07-15 15:00
**最终状态**: built
最终状态: built (编译结束)
