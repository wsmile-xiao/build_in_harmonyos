# Python 3.9.0 OpenHarmony 失败测试详情

> **测试日期**: 2026-03-26 | **补丁版本**: 20 补丁（0001-0020）
> **前次**: 2026-03-21，11 补丁，80 个失败 → **本次 45 个失败（-35）**

## 失败测试列表 (45个)

### 1. 多进程/多线程/终端相关 (8个)

| 测试 | 错误类型 | 原因分析 |
|------|----------|----------|
| test_multiprocessing_fork | PermissionError | sem_unlink 失败, POSIX 信号量行为差异 |
| test_multiprocessing_forkserver | PermissionError | Socket bind: Operation not permitted |
| test_multiprocessing_spawn | PermissionError | os.fstat(): Permission denied |
| test_threading | AssertionError | 线程相关断言失败 |
| test_signal | Multiple errors | 信号处理机制差异 |
| test_pty | PermissionError | os.openpty(): Permission denied |
| test_openpty | PermissionError | os.openpty(): Permission denied |
| test_fcntl | Multiple errors | 文件锁相关 |

**根因**：OpenHarmony 的进程/线程模型与 Linux 有差异：
- POSIX 信号量 (`sem_unlink`) 行为不同
- Unix domain socket 绑定受限
- PTY/终端设备权限限制

**与上次对比**：test_multiprocessing_main_handling ✅ 已通过，test_concurrent_futures ✅ 已通过

### 2. 文件系统相关 (10个)

| 测试 | 错误类型 | 原因分析 |
|------|----------|----------|
| test_pathlib | PermissionError | 文件操作权限 |
| test_posixpath | Multiple errors | 路径处理 |
| test_shutil | PermissionError | 文件操作权限 |
| test_tempfile | PermissionError | 临时文件权限 |
| test_tarfile | Multiple errors | tar 文件处理 |
| test_mmap | Multiple errors | 内存映射 |
| test_dbm_dumb | AssertionError | dbm 数据库, 文件权限差异 |
| test_uu | Multiple errors | uuencode |
| test_stat | Multiple errors | 文件状态 |
| test_import | Multiple errors | 模块导入 |

**根因**：
- 文件权限模型差异
- `fstat()` 对管道/终端返回 EACCES
- 硬链接/软链接创建受限 (SELinux)

**与上次对比**：test_gzip ✅ 已通过，test_zipfile ✅ 已通过

### 3. 终端/输入相关 (2个)

| 测试 | 错误类型 | 原因分析 |
|------|----------|----------|
| test_readline | Multiple errors | readline 库相关 |
| test_getpass | Multiple errors | 密码输入 |

**与上次对比**：test_eof ✅、test_cmd_line ✅、test_utf8_mode ✅、test_repl ✅ 已通过

### 4. 编译/构建相关 (4个)

| 测试 | 错误类型 | 原因分析 |
|------|----------|----------|
| test_compileall | Multiple errors | 批量编译 |
| test_py_compile | Multiple errors | pyc 编译 |
| test_distutils | PermissionError | 构建系统 |
| test_venv | Multiple errors | 虚拟环境 |

**与上次对比**：test_compile ✅ 已通过

### 5. 网络/服务相关 (4个)

| 测试 | 错误类型 | 原因分析 |
|------|----------|----------|
| test_socket | Multiple errors | socket 操作 |
| test_selectors | Multiple errors | I/O 多路复用 |
| test_httpservers | Multiple errors | HTTP 服务器 |
| test_ioctl | skipped | ioctl 操作 |

### 6. 区域/编码相关 (4个)

| 测试 | 错误类型 | 原因分析 |
|------|----------|----------|
| test_locale | Multiple errors | 区域设置 |
| test_c_locale_coercion | Multiple errors | locale 强制转换 |
| test_format | Multiple errors | 格式化 |
| test_strptime | Multiple errors | 时间解析 |

**根因**：OpenHarmony 的 locale 支持不完整

### 7. 调试/分析相关 (1个)

| 测试 | 错误类型 | 原因分析 |
|------|----------|----------|
| test_tools | Multiple errors | 工具相关 |

**与上次对比**：test_gdb → 已移至跳过列表；test_trace ✅、test_traceback ✅、test_tracemalloc ✅、test_inspect ✅ 已通过

### 8. 其他 (12个)

| 测试 | 分类 |
|------|------|
| test_argparse | 参数解析 |
| test_code | 代码对象 |
| test_ctypes | FFI |
| test_generators ⚠️ | 生成器（**新增失败**） |
| test_importlib | 导入系统 |
| test_lib2to3 | 代码转换 |
| test_mailbox | 邮箱 |
| test_netrc | netrc |
| test_pdb | 调试器 |
| test_posix | POSIX |
| test_source_encoding | 源码编码 |
| test_sysconfig ⚠️ | sysconfig（**新增失败**） |

**注意**：test_generators 和 test_sysconfig 是本次新增的失败测试（回归）。

## 与上次对比（2026-03-21，11补丁）

### 从失败→通过（35个测试改进）

| 测试 | 说明 |
|------|------|
| test_concurrent_futures | 多进程/多线程 |
| test_doctest | 文档测试 |
| test_embed | 嵌入式 |
| test_eof | EOF 处理 |
| test_exceptions | 异常 |
| test_faulthandler | 信号处理 |
| test_fstring | f-string |
| test_gc | GC |
| test_gzip | gzip 文件处理 |
| test_json | JSON |
| test_logging | 日志 |
| test_runpy | 运行模块 |
| test_support | 测试支持 |
| test_sys | 系统 |
| test_trace | 跟踪 |
| test_traceback | 回溯 |
| test_tracemalloc | 内存跟踪 |
| test_unittest | 单元测试 |
| test_utf8_mode | UTF-8 模式 |
| test_warnings | 警告 |
| test_weakref | 弱引用 |
| test_zipfile | zip 文件处理 |
| test_inspect | 代码检查 |
| test_io | I/O |
| test_calendar | 日历 |
| test_capi | C API |
| test_cmd_line | 命令行参数 |
| test_compile | 编译 |
| test_parser | 解析器 |
| test_tabnanny | 缩进检查 |
| test_unicodedata | Unicode 数据 |
| test_struct | 结构体 |
| test_repl | REPL 交互 |
| test_site | site 模块 |
| test_cprofile | 性能分析 |
| test_multiprocessing_main_handling | 多进程主处理 |

### 从失败→跳过（1个）

| 测试 | 说明 |
|------|------|
| test_gdb | gdb 调试器，Red Hat Bug 1866884 |

### 新增失败（2个回归）

| 测试 | 说明 |
|------|------|
| test_generators | 生成器测试 |
| test_sysconfig | sysconfig 模块 |

## 失败原因统计

| 失败原因 | 测试数量 | 占比 |
|----------|----------|------|
| Permission denied / Operation not permitted | ~15 | 33% |
| 进程/线程机制差异 | ~8 | 18% |
| 文件系统差异 | ~10 | 22% |
| locale 支持不完整 | ~4 | 9% |
| 终端设备差异 | ~2 | 4% |
| 其他平台差异 | ~6 | 13% |

## 建议

1. **多进程应用**：使用 `subprocess` 替代 `multiprocessing`，或测试具体功能是否可用
2. **文件操作**：注意文件权限差异，避免依赖硬链接/软链接
3. **终端应用**：避免依赖 readline、PTY 等功能
4. **国际化**：测试 locale 相关功能是否满足需求
5. **回归测试**：test_generators 和 test_sysconfig 需要调查回归原因
