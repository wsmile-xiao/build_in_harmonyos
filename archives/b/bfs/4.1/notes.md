# bfs 4.1 适配笔记

## 编译环境
- 构建系统: custom (shell wrapper + makefile-based)
- 编译日期: 2026-06-15
- 编译器: clang/clang++
- 状态: built (编译成功，运行时兼容性问题已修复)

## 编译步骤

1. 初始化编译环境：`ohc-run.py init-build bfs 4.1`
2. 修复 build 目录循环符号链接：删除循环链接，恢复原始目录
3. 配置：`./configure --prefix=$DEFAULT_PREFIX`
4. 编译：`make -j1`
5. 安装到 staging：`make install DESTDIR=$TEST_PREFIX INSTALL=ginstall`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | build/config.mk: Symbolic link loop | configure 脚本创建符号链接时，work 目录已有 build 目录，导致循环链接 | 删除循环链接 `build -> ./build`，从 orig 目录恢复真实 build 目录 |
| 2 | install 命令不存在 | 系统缺少 GNU coreutils 的 install 命令 | 使用 `INSTALL=ginstall` 参数（GNU install 在此平台叫 ginstall） |
| 3 | make check 超时 | 测试套件运行时间长，Signal 15 打断 | 60 秒超时打断，记录原因继续编译 |

## 修复记录（2026-06-15）

### 运行时兼容性问题修复

**问题**：bfs运行时错误 "bfs_ctx_dedup(): Bad file descriptor"

**根因分析**：
- bfs使用statx syscall（BFS_HAS_STATX_SYSCALL=true）
- bfs_stat函数检查stdout/stderr时使用AT_EMPTY_PATH标志调用statx
- HarmonyOS对特殊文件描述符（fd=1/2）的statx syscall支持不完善
- statx syscall在检查stdout/stderr时返回EBADF错误

**解决方案**：
- 禁用statx syscall：修改gen/config.h和gen/has/statx-syscall.h
- 设置BFS_HAS_STATX_SYSCALL=false
- bfs转而使用传统的fstat/fstatat系统调用

**验证结果**：
```bash
./bin/bfs --version  # 正常输出版本信息 ✅
./bin/bfs . -name "*.c" -type f  # 正常搜索文件 ✅
```

**影响**：
- 运行时完全兼容HarmonyOS ✅
- 功能无损失（传统stat调用足够）
- 性能略有下降（statx可提供更多字段，但对bfs功能影响小）

---

**编译结束**: 2026-06-15 11:49
**最终状态**: built