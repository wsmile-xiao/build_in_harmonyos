# libjodycode

## 简介

libjodycode 是 Jody Bruchon 开发的通用实用函数库，主要为 jdupes（增强版重复文件检测工具）等软件提供底层支持。该库包含字符串处理、数值排序、哈希计算、文件系统操作、路径处理、错误信息管理等跨平台实用功能。

- **许可证**: MIT
- **作者**: Jody Bruchon <jody@jodybruchon.com>
- **源码仓库**: https://codeberg.org/jbruchon/libjodycode

## 主要功能

| 功能模块 | 说明 |
|---------|------|
| **字符串比较** | `jc_streq`/`jc_strneq`/`jc_strcaseeq`/`jc_strncaseeq` — 等值比较（返回 0=相等, 1=不等） |
| **数值字符串排序** | `jc_numeric_strcmp` — 数值感知的字符串排序（"9" < "10"） |
| **哈希计算** | `jc_block_hash` — Jody 块哈希算法，支持普通和滚动模式 |
| **文件系统操作** | `jc_access`/`jc_stat`/`jc_fopen`/`jc_opendir`/`jc_readdir`/`jc_closedir`/`jc_getcwd` |
| **路径处理** | `jc_collapse_dotdot` — 折叠 `..` 和 `.` 路径组件（需绝对路径） |
| **大小后缀** | `jc_size_suffix` — 支持 B/KB/MB/GB/TB/PB 等大小单位转换 |
| **错误信息** | `jc_get_errname`/`jc_get_errdesc`/`jc_print_error` — 自定义错误码信息查询 |
| **格式化输出** | `jc_fwprint` — 跨平台宽字符串输出（Windows Unicode 支持） |
| **内存安全** | `jc_oom`/`jc_nullptr` — 内存分配失败/空指针异常处理 |
| **闹钟定时** | `jc_start_alarm`/`jc_stop_alarm` — 定时闹钟信号处理 |

## 鸿蒙平台编译信息

| 项目 | 值 |
|------|-----|
| 版本 | 4.1.2 |
| 构建系统 | 纯 Makefile（无 configure 脚本） |
| 编译器 | clang 15.0.4 |
| 目标架构 | AArch64 (aarch64) |
| 编译状态 | ✅ published |
| 编译日期 | 2026-05-25 |
| 外部依赖 | 无（仅依赖 libc） |
| 补丁数量 | 0（源码无需修改） |

## 编译方法

```bash
# 编译
make PREFIX=$DEFAULT_PREFIX CC=clang -j1

# DESTDIR 安装（打包用）
make install DESTDIR=$TEST_PREFIX PREFIX=$DEFAULT_PREFIX

# 本地安装（模拟用户部署）
make install PREFIX=$DEFAULT_PREFIX
```

## 鸿蒙平台注意事项

1. **SIMD 自动禁用**: Makefile 在非 x86_64 平台自动设置 `-DNO_SIMD -DNO_SSE2 -DNO_AVX2`，无需手动修改
2. **纯 Makefile 项目**: 无 configure 脚本，使用 `PREFIX` 和 `DESTDIR` 变量替代 `--prefix` 和 DESTDIR 参数
3. **软链接**: Makefile 使用 `ln -sf` 创建 `.so` 符号链接，在 HMDFS 环境下可能需要 `rm -f && ln -s`（R5 铁律）
4. **测试覆盖有限**: 项目仅提供 dummy `test.sh`（输出 "OK"），无正式测试套件
5. **API 约定**: 字符串比较函数返回 0=相等/1=不等（类似 strcmp），`jc_collapse_dotdot` 要求绝对路径

## 交付产物

| 文件 | 说明 |
|------|------|
| `libjodycode.so.4.0` | 共享库 (AArch64 ELF64) |
| `libjodycode.so.4 → libjodycode.so.4.0` | 版本符号链接 |
| `libjodycode.so → libjodycode.so.4` | 开发符号链接 |
| `libjodycode.a` | 静态库 |
| `libjodycode.h` | 头文件 |
| `libjodycode.7` | man 手册页 |

## 功能验证测试

编译后执行了 47 项真实功能验证测试（静态链接），覆盖以下 API：

1. 版本信息 (jc_version, jc_verdate, jc_api_version 等)
2. 文件访问检查 (jc_access)
3. 工作目录获取 (jc_getcwd)
4. 文件状态检查 (jc_stat)
5. 字符串比较 (jc_streq, jc_strneq, jc_strcaseeq, jc_strncaseeq)
6. 数值字符串排序 (jc_numeric_strcmp)
7. 块哈希计算 (jc_block_hash，含确定性验证)
8. 错误信息查询 (jc_get_errname, jc_get_errdesc)
9. 格式化输出 (jc_fwprint)
10. 路径折叠 (jc_collapse_dotdot，含单点/双点/相对路径错误)
11. 文件打开 (jc_fopen)
12. 大小后缀表 (jc_size_suffix)
13. 目录操作 (jc_opendir, jc_readdir, jc_closedir)
14. 安装产物完整性 (so/a/h/man 全部存在)

**测试结果**: 47/47 通过，libjodycode 在鸿蒙平台功能正常。