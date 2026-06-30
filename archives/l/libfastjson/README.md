# libfastjson

## 简介
libfastjson 是一个高性能的 JSON C 语言实现库，从 json-c 分支而来。提供 JSON 解析、生成、操作等完整功能。

## OHOS 适配
- 构建系统: autotools
- 编译参数: `--prefix=$DEFAULT_PREFIX`
- 编译器: clang / clang++
- 1.2304.0 版本编译成功，状态: **published**

## 依赖
- 无编译依赖

## 功能验证

### make check 结果
全部 17 项测试通过 (PASS: 17, FAIL: 0, SKIP: 0)：

| 测试项 | 结果 |
|--------|------|
| ucs_copyright_char | PASS |
| test_float | PASS |
| test1 | PASS |
| test2 | PASS |
| test4 | PASS |
| testReplaceExisting | PASS |
| test_parse_int64 | PASS |
| test_cast | PASS |
| test_parse | PASS |
| test_locale | PASS |
| test_charcase | PASS |
| test_printbuf | PASS |
| test_obj_iter-del | PASS |
| test_object_object_add_ex | PASS |
| test_many_subobj | PASS |
| test_obj_obj_get_ex-null | PASS |
| chk_version | PASS |

### 编译产物验证
```bash
# pkg-config 验证
pkg-config --modversion libfastjson  # 输出: 1.2304.0

# 库文件验证
ls -la $HOME/usr/local/lib/libfastjson*
```

产物清单:
- libfastjson.so.4.3.0 (动态库)
- libfastjson.so → libfastjson.so.4 → libfastjson.so.4.3.0 (符号链接)
- libfastjson.a (静态库)
- libfastjson.la
- libfastjson.pc (pkg-config)
- 头文件: atomic.h, json.h, json_object.h, json_object_iterator.h, json_object_private.h, json_tokener.h, json_util.h

### 质量门禁
- G1 二进制完整性: PASS
- G2 功能可用性: PASS
- G3 可移植性: PASS
- G4 档案完整性: PASS

## 预编译包
- `libfastjson-1.2304.0-ohos-aarch64.tar.gz` (554KB) — ELF 已签名，已 strip
- `libfastjson-1.2304.0-ohos-aarch64-debug.tar.gz` (372KB) — 调试符号包

## 使用方法
```c
#include <libfastjson/json.h>

// 解析 JSON
json_object *obj = json_tokener_parse("{\"key\":\"value\"}");

// 创建 JSON 对象
json_object *new_obj = json_object_new_object();
json_object_object_add(new_obj, "name", json_object_new_string("test"));

// 获取值
const char *val = json_object_get_string(json_object_object_get(obj, "key"));

// 释放
json_object_put(obj);
```

编译链接: `clang -lfastjson main.c -o main`

## 踩坑记录
1. configure 首次执行返回 RC=127（autotools 初始化问题），重试后成功
2. 原始 tarball 中 config.guess/config.sub 为空文件，configure 过程中自动填充

## 参考
- 主页: https://github.com/rsyslog/libfastjson
- 详细测试报告: `1.2304.0/reports/test-report.md`