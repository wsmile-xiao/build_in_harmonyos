# CUnit 2.1-3 — OpenHarmony 预编译包

## 基本信息
- **软件名**: CUnit
- **版本**: 2.1-3
- **编译日期**: 2026-06-30
- **构建系统**: autotools（custom 手动修复）
- **目标平台**: ohos-aarch64
- **编译器**: clang 15.0.4

## 文件清单
| 文件 | 说明 |
|------|------|
| `lib/libcunit.a` | 静态库 |
| `lib/libcunit.so` | 共享库（符号链接 → libcunit.1.so）|
| `lib/libcunit.1.so` | 共享库（版本化）|
| `include/CUnit/CUnit.h` | 主头文件 |
| `include/CUnit/Automated.h` | Automated 模式头文件 |
| `include/CUnit/Basic.h` | Basic 模式头文件 |
| `include/CUnit/CUError.h` | 错误码定义 |
| `include/CUnit/CUnit_intl.h` | 国际化支持 |
| `include/CUnit/Console.h` | Console 模式头文件 |
| `include/CUnit/CUCurses.h` | Curses 模式头文件（已禁用）|
| `include/CUnit/MyMem.h` | 内存管理 |
| `include/CUnit/TestDB.h` | 测试数据库 |
| `include/CUnit/TestRun.h` | 测试运行 |
| `include/CUnit/Util.h` | 工具函数 |
| `include/CUnit/wxWidget.h` | wxWidget 接口（已禁用）|
| `share/man/man3/CUnit.3` | man 手册 |
| `lib/pkgconfig/cunit.pc` | pkg-config 配置 |

## 使用说明
### 编译链接
```bash
# 使用 pkg-config
pkg-config --cflags --libs cunit

# 或手动指定
clang -I/usr/local/include -L/usr/local/lib -lcunit test.c -o test -lm
```

### 测试示例
```c
#include <CUnit/CUnit.h>
#include <CUnit/Basic.h>

int init_suite(void) { return 0; }
int clean_suite(void) { return 0; }

void test_example(void) {
    CU_ASSERT_EQUAL(2 + 2, 4);
}

int main() {
    CU_pSuite suite;
    CU_initialize_registry();
    suite = CU_add_suite("Example Suite", init_suite, clean_suite);
    CU_add_test(suite, "test_example", test_example);
    CU_basic_set_mode(CU_BRM_VERBOSE);
    CU_basic_run_tests();
    CU_cleanup_registry();
    return 0;
}
```

## 已知问题
1. **autotools 兼容性**: HarmonyOS HMDFS 的临时文件权限限制导致 autotools configure 流程受阻，已通过手动修复 config.guess/config.sub 解决（E007 补丁）
2. **libtool 共享库链接**: lld 链接器不支持 macOS 参数 `-single_module`，共享库由之前的手动编译方案生成
3. **Curses 模式**: 已在 configure 阶段禁用（--disable-curses）
4. **示例程序**: 已在 configure 阶段禁用（--disable-examples）
5. **测试程序**: 已在 configure 阶段禁用（--disable-tests）

## 变更日志
| 日期 | 变更内容 |
|------|---------|
| 2026-04-27 | 首次编译成功（手动编译，绕过 autotools）|
| 2026-06-30 | 重编译：应用 E007 补丁，configure 成功，手动创建 libcunit.a |
