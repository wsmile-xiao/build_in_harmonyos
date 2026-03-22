# Python 3.9.0 OpenHarmony 失败测试详情

## 失败测试列表 (80个)

### 1. 多进程/多线程相关 (14个)

| 测试 | 错误类型 | 原因分析 |
|------|----------|----------|
| test_multiprocessing_fork | PermissionError | sem_unlink 失败, POSIX 信号量行为差异 |
| test_multiprocessing_forkserver | PermissionError | Socket bind: Operation not permitted |
| test_multiprocessing_spawn | PermissionError | os.fstat(): Permission denied |
| test_multiprocessing_main_handling | PermissionError | 同上 |
| test_concurrent_futures | PermissionError | 同上 |
| test_threading | AssertionError | 线程相关断言失败 |
| test_signal | Multiple errors | 信号处理机制差异 |
| test_faulthandler | Multiple errors | 信号处理相关 |
| test_pty | PermissionError | os.openpty(): Permission denied |
| test_openpty | PermissionError | os.openpty(): Permission denied |
| test_fcntl | Multiple errors | 文件锁相关 |
| test_gc | Multiple errors | GC 相关 |
| test_io | Multiple errors | I/O 相关 |

**根因**：OpenHarmony 的进程/线程模型与 Linux 有差异：
- POSIX 信号量 (`sem_unlink`) 行为不同
- Unix domain socket 绑定受限
- PTY/终端设备权限限制

### 2. 文件系统相关 (12个)

| 测试 | 错误类型 | 原因分析 |
|------|----------|----------|
| test_pathlib | PermissionError | 文件操作权限 |
| test_posixpath | Multiple errors | 路径处理 |
| test_shutil | PermissionError | 文件操作权限 |
| test_tempfile | PermissionError | 临时文件权限 |
| test_tarfile | Multiple errors | tar 文件处理 |
| test_gzip | Multiple errors | gzip 文件处理 |
| test_zipfile | Multiple errors | zip 文件处理 |
| test_mmap | Multiple errors | 内存映射 |
| test_dbm_dumb | AssertionError | dbm 数据库, 文件权限差异 |
| test_uu | Multiple errors | uuencode |
| test_stat | Multiple errors | 文件状态 |
| test_import | Multiple errors | 模块导入 |

**根因**：
- 文件权限模型差异
- `fstat()` 对管道/终端返回 EACCES
- 硬链接/软链接创建受限 (SELinux)

### 3. 终端/输入相关 (6个)

| 测试 | 错误类型 | 原因分析 |
|------|----------|----------|
| test_readline | Multiple errors | readline 库相关 |
| test_repl | Multiple errors | REPL 交互 |
| test_eof | Multiple errors | EOF 处理 |
| test_getpass | Multiple errors | 密码输入 |
| test_cmd_line | Multiple errors | 命令行参数 |
| test_utf8_mode | Multiple errors | UTF-8 模式 |

**根因**：终端设备交互与 Linux 不同

### 4. 编译/构建相关 (5个)

| 测试 | 错误类型 | 原因分析 |
|------|----------|----------|
| test_compile | Multiple errors | 编译相关 |
| test_compileall | Multiple errors | 批量编译 |
| test_py_compile | Multiple errors | pyc 编译 |
| test_distutils | PermissionError | 构建系统 |
| test_venv | Multiple errors | 虚拟环境 |

**根因**：编译器/构建工具链差异

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

### 7. 调试/分析相关 (6个)

| 测试 | 错误类型 | 原因分析 |
|------|----------|----------|
| test_gdb | Multiple errors | gdb 调试器相关 |
| test_trace | Multiple errors | 跟踪相关 |
| test_traceback | Multiple errors | 回溯相关 |
| test_tracemalloc | Multiple errors | 内存跟踪 |
| test_inspect | Multiple errors | 代码检查 |
| test_tools | Multiple errors | 工具相关 |

### 8. 其他 (29个)

| 测试 | 分类 |
|------|------|
| test_argparse | 参数解析 |
| test_calendar | 日历 |
| test_capi | C API |
| test_code | 代码对象 |
| test_cprofile | 性能分析 |
| test_ctypes | FFI |
| test_doctest | 文档测试 |
| test_embed | 嵌入式 |
| test_exceptions | 异常 |
| test_fstring | f-string |
| test_httpservers | HTTP |
| test_importlib | 导入系统 |
| test_json | JSON |
| test_lib2to3 | 代码转换 |
| test_logging | 日志 |
| test_mailbox | 邮箱 |
| test_netrc | netrc |
| test_parser | 解析器 |
| test_pdb | 调试器 |
| test_posix | POSIX |
| test_runpy | 运行模块 |
| test_site | site 模块 |
| test_source_encoding | 源码编码 |
| test_struct | 结构体 |
| test_support | 测试支持 |
| test_sys | 系统 |
| test_tabnanny | 缩进检查 |
| test_unicodedata | Unicode 数据 |
| test_unittest | 单元测试 |
| test_warnings | 警告 |
| test_weakref | 弱引用 |

## 失败原因统计

| 失败原因 | 测试数量 | 占比 |
|----------|----------|------|
| Permission denied / Operation not permitted | ~25 | 31% |
| 进程/线程机制差异 | ~14 | 18% |
| 终端设备差异 | ~6 | 8% |
| 文件系统差异 | ~12 | 15% |
| locale 支持不完整 | ~4 | 5% |
| 其他平台差异 | ~19 | 24% |

## 建议

1. **多进程应用**：使用 `subprocess` 替代 `multiprocessing`，或测试具体功能是否可用
2. **文件操作**：注意文件权限差异，避免依赖硬链接/软链接
3. **终端应用**：避免依赖 readline、PTY 等功能
4. **国际化**：测试 locale 相关功能是否满足需求