# esniper 2.35.0 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-08-21
- 编译器: clang/clang++
- 状态: published

## 编译步骤

1. `conan install --requires=curl/8.15.0 -pr:b=ohos -pr:h=ohos -b=missing --build=missing` 准备 curl 依赖
2. 创建 curl-config wrapper 修复路径问题
3. `./configure --prefix=$DEFAULT_PREFIX --with-curl-config=<curl-config-wrapper>`
4. `make -j1` (HMDFS 不支持 mkfifo，不能用 -j2)
5. `make install DESTDIR=$TEST_PREFIX`
6. `make check` — 无测试目标

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | curl-config --libs 返回不存在的构建路径 | Conan curl 包的 curl-config 脚本硬编码构建路径 | 创建 wrapper 脚本修正路径 |
| 2 | config.status subs1.awk Permission denied | HMDFS/SELinux: umask 077 创建的临时目录无法写文件 | configure 中 umask 077 → umask 022 |
| 3 | make -j2 jobserver mkfifo 失败 | HMDFS 不支持 FIFO | 使用 -j1 |

## 源码修改

- `configure`: umask 077 → umask 022（行 4463/4468，修复 HMDFS/SELinux 临时目录权限）

## 依赖版本

- curl/8.15.0

## 验证结果

```bash
$ esniper -v
esniper version 2.35.0
```

### 上游测试用例

esniper 是纯命令行拍卖工具，上游源码树无 test/ 目录，根 Makefile.in 无 check/test 目标，
configure 无 --enable-tests 选项。上游测试用例数：**0**。

### 适配后补全测试用例（test_package/test.sh）

上游无测试套件，适配后补全 3 项断言测试，实质执行 esniper 二进制并校验退出码与输出：

| # | 测试 | 退出码 | 断言 | 源码依据 |
|---|------|--------|------|----------|
| 1 | `esniper -v` | 0 | 输出含 `version 2.35.0` | esniper.c:727 printVersion()+exit(0) |
| 2 | `esniper -h` | 1 | 输出含 `usage:` | esniper.c:571 usage(USAGE_LONG)+exit(1) |
| 3 | `esniper`（无参） | 1 | 输出含 `no auctions specified` | esniper.c:780 参数校验+exit(1) |

### 通过率

- 编译状态：**通过**（CI #29028，L0/L1 门禁均通过）
- 上游测试用例通过率：**0/0**（上游无测试套件，不适用）
- 新增测试用例通过率：**3/3（100%）**

```bash
$ test.sh /path/to/esniper
PASS [1/3]: esniper -v -> exit 0, version string present
PASS [2/3]: esniper -h -> exit 1, usage help printed
PASS [3/3]: esniper (no args) -> exit 1, error message present

Result: 3/3 tests passed (100%)
```

## 注意事项

- esniper 是命令行工具，需要 commands.json (R38)
- curl-config 路径问题需在 conanfile.py 中处理（通过 curl 依赖的 cpp_info 自动获取）
---

**编译结束**: 2026-08-21 09:57
**最终状态**: published
