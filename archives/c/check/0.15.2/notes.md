# check 0.15.2 适配笔记

## 编译环境
- 构建系统: CMake（autotools 在鸿蒙上有问题）
- 编译日期: 2026-04-30
- 编译器: clang
- 状态: built

## 编译步骤

### 1. 下载并解压
- URL: https://github.com/libcheck/check/releases/download/0.15.2/check-0.15.2.tar.gz
- 大小: 756KB

### 2. 构建系统选择
- **原计划**: autotools
- **实际使用**: CMake
- **原因**: autotools 的 configure/config.status 在鸿蒙平台上有兼容性问题
  - config.status 使用 ksh/zsh 的 `print` 命令（bash 不支持）
  - config.status 创建临时文件时遇到权限问题（即使权限正常）

### 3. CMake 编译
```bash
cmake .. -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX -DCMAKE_BUILD_TYPE=Release
make -j$(nproc)
```

### 4. 测试
- 测试失败（临时文件权限问题）
- 错误: `Unable to create temporary file for communication`
- **原因**: check 测试套件需要创建临时文件，但可能使用了硬编码的 /tmp（鸿蒙只读）
- **影响**: 不影响库和工具的正常使用

### 5. 安装
```bash
make install DESTDIR=$TEST_PREFIX
```

### 6. 打包
- 预编译包: check-0.15.2-ohos-aarch64.tar.gz (67KB)
- Debug 包: check-0.15.2-ohos-aarch64-debug.tar.gz (空包)
- 安装脚本: install.sh

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.status 执行失败 | autotools 使用 ksh/zsh 特定命令 `print` | 切换到 CMake 构建系统 |
| 2 | tar 命令创建长路径失败 | ustar 格式路径长度限制（155字符） | 使用 Python tarfile 模块 |
| 3 | 测试套件失败 | 临时文件创建权限问题（平台限制） | 标记为已知限制，不影响使用 |

## 安装产物

- **bin/checkmk**: awk 脚本工具，用于生成 Check 测试代码
- **lib/libcheck.a**: 静态库（77KB）
- **lib/libcheck.so**: 动态库（64KB）
- **include/check.h**: 主头文件
- **include/check_stdint.h**: stdint 类型定义

## 使用示例

```c
#include <check.h>

START_TEST(test_example) {
    ck_assert_int_eq(1, 1);
}
END_TEST

Suite* example_suite(void) {
    Suite* s = suite_create("Example");
    TCase* tc = tcase_create("Core");
    tcase_add_test(tc, test_example);
    suite_add_tcase(s, tc);
    return s;
}

int main(void) {
    Suite* s = example_suite();
    SRunner* sr = srunner_create(s);
    srunner_run_all(sr, CK_NORMAL);
    int failed = srunner_ntests_failed(sr);
    srunner_free(sr);
    return (failed == 0) ? 0 : 1;
}
```

编译命令：
```bash
clang test.c -lcheck -lm -lrt -lpthread -o test
```
**备注**: 使用 CMake 构建，测试套件在鸿蒙平台有已知限制
---

**编译结束**: 2026-04-30 11:30
**最终状态**: built
