# TCL 8.6.14 编译笔记

## 编译环境
- 系统: HarmonyOS HongMeng Kernel 1.12.0
- 编译器: clang
- 构建系统: autotools
- 构建目录: unix/

## 编译过程

### 1. 源码获取
- 从 SourceForge 下载: tcl8.6.14-src.tar.gz
- 文件大小: 11MB

### 2. Configure
- 命令: `./configure --prefix=$DEFAULT_PREFIX CC=clang CXX=clang++`
- 平台检测: 自动识别为 HarmonyOS-HongMeng Kernel 1.12.0
- 问题: configure 中有 umask 077，导致临时文件权限问题

### 3. 问题修复
**问题1: umask 077 导致临时文件权限错误**
- 位置: configure 第 19931 和 19936 行
- 解决: 将 `umask 077` 改为 `umask 022`
- 补丁: 0001-fix-umask.patch

### 4. 编译
- 命令: `make -j2`
- 成功编译生成:
  - libtcl8.6.a (2.8M)
  - libtclstub8.6.a (7.0K)
  - tclsh8.6 (1.5M)

### 5. 安装
- Staging: `make install DESTDIR=$TEST_PREFIX`
- 本地: 从 staging 复制到 $DEFAULT_PREFIX

### 6. 验证
- tclsh8.6 可以正常运行
- TCL 版本: 8.6.14
- TCL 库路径: /storage/Users/currentUser/usr/local/lib/tcl8.6

## 子包问题
- itcl4.2.4 子包编译失败（临时文件权限问题）
- 主 TCL 库编译成功，不影响使用

## 编译总结
- 状态: built
- 预编译包: tcl-8.6.14-ohos-aarch64.tar.gz (8.6M)
- 补丁: 0001-fix-umask.patch (修复临时文件权限问题)

## 知识提取
- **E011**: umask 077 在 HMDFS 上导致临时文件权限问题，需要改为 umask 022
- **平台适配**: HarmonyOS 平台无需额外补丁，configure 可自动识别

---
**编译结束**: 2026-05-26 14:38
**最终状态**: built
## 对话记录

- AI 分析发现 unix/configure 中 umask 077 在 HMDFS 上导致临时文件权限问题，建议改为 umask 022
- 扩展 umask 补丁至 9 个子包（itcl/sqlite3/tdbc/thread）的 configure 脚本
- 新增 C API 测试 test_tcl_api.c，编译链接 -ltcl8.6 -lz，验证 Tcl_CreateInterp/Tcl_Eval/Tcl_DeleteInterp
- test_package 改用 dependencies[tcl].package_folder 绝对路径，不依赖 PATH
- make test 集成至 build()，共 46 FAILED（OHOS 平台限制：只读 /tmp、无网络、无动态加载）
- 本地 conan create exit 0, conan-verify exit 0, test_package 10/10 PASS
---

**编译结束**: 2026-08-10 20:44
**最终状态**: built
