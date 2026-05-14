# mujs — OpenHarmony 编译记录

## 基本信息

- **软件**: mujs（轻量级 JavaScript 解释器）
- **最新版本**: 1.3.9
- **构建系统**: Makefile
- **目标平台**: ohos-aarch64
- **编译状态**: ✅ success
- **测试结果**: ✅ 10/10 通过

## 已编译版本

| 版本 | 状态 | 编译日期 | 补丁数 | 测试结果 |
|------|------|----------|--------|----------|
| 1.3.9 | success | 2026-05-07 | 0 | 10/10 ✅ |

## 编译指导

mujs 使用简单的 Makefile 构建系统，无需 configure 脚本。

```bash
# 编译命令
make release HAVE_READLINE=no prefix=$DEFAULT_PREFIX

# 安装命令（staging）
make install HAVE_READLINE=no prefix=$DEFAULT_PREFIX DESTDIR=$TEST_PREFIX

# 本地安装
make install HAVE_READLINE=no prefix=$DEFAULT_PREFIX
```

**注意事项**:
- 需要禁用 readline 支持（HAVE_READLINE=no），因为系统缺少 readline 库
- 无 configure 脚本，直接使用 make 编译
- 无官方测试套件，需要构造测试用例验证功能

## 补丁清单

当前版本无需源码补丁，编译过程顺利完成。

## 已知限制

- readline 支持已禁用（缺少 readline 库）
- 版本显示为 1.3.8（源码 VERSION 实际为 1.3.9）

## 功能验证

```bash
# 验证 mujs 可执行
$ mujs
Welcome to MuJS 1.3.8.

# 执行测试脚本
$ mujs test1_basic_math.js
Test 1: PASSED

# 运行完整测试套件
$ for f in reports/test-scripts/*.js; do mujs "$f"; done
```

测试覆盖：基本数学运算、字符串操作、数组/对象、函数闭包、控制流、JSON、正则表达式、错误处理、Date对象、内置对象方法。

## 快速安装

```bash
# 下载预编译包
tar xzf mujs-1.3.9-ohos-aarch64.tar.gz -C ~/usr/local
cd mujs-1.3.9-ohos-aarch64
sh install-mujs-1.3.9.sh
```

## 归档位置

`archives/m/mujs/1.3.9/`