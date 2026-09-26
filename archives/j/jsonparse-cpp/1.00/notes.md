# jsonparse-cpp 1.00 适配笔记

## 编译环境
- 构建系统: custom（上游无构建系统，README 直接给出 clang 编译）
- 编译日期: 2026-09-26
- 编译器: clang 15.0.4 (aarch64-unknown-linux-ohos)
- 状态: built
- 上游: https://github.com/liufeigit/jsonParse (tag v1.00)

## 编译步骤

上游项目无 Makefile/CMake/configure，README 指定直接编译：

```bash
clang -O2 -fPIC -c parse.c object.c
llvm-ar -r libjsonParse.a parse.o object.o
```

conanfile.py build() 中手动完成该编译（R33：编译器从 Conan conf 取，不裸用 `${CC}`），
静态库产物 libjsonParse.a，安装头文件 parse.h / object.h。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 链接失败：`undefined symbol: gcvt`（object_toString/__toFloatString 调用） | 上游使用 glibc 遗留函数 `gcvt()` 做 double→string；OHOS libc 无此函数声明与符号 | patches/0001-object.c.patch：改为可移植的 `snprintf(str, 30, "%.17g", d)`，任何 libc 通用 |
| 2 | init-build 内置下载器把 GitHub 页面当源码（"下载内容是 HTML"） | URL 指向仓库主页而非 tag 归档 | 使用官方 tag 归档 `https://github.com/liufeigit/jsonParse/archive/refs/tags/v1.00.tar.gz`，SHA-256 已核验 |

## 源码修改

- patches/0001-object.c.patch：`__toFloatString()` 中 `gcvt(d, 30, str)` → `snprintf(str, 30, "%.17g", d)`

## 依赖版本

无第三方依赖（纯 ANSI C 标准库）。

## 验证结果

- 上游测试：`test/testStr.c`（解析 test/citm_catalog.json，parseJSON + object_toString + object_free），编译运行成功，status=1727204（解析长度），exit=0
- test_package 消费者测试：通过公开头文件 parse.h/object.h 调用 parseJSON/object_toString，验证 round-trip 输出含 `"arr"`、`"name":"希望666"`、`"value"`，exit=0
- conan-verify：G1/G2/G3/G4 全 PASS
- W3 本地 CI（build_and_test.sh）：L0/L1/L1e/L5 通过，通过率 100% (1/1)
- W3 junk 门禁命中 3 个其他库（cloog/kics）提交前已存在的基线文件，已按 oh-executor 规则完成基线隔离复验（记录 SHA-256、临时隔离、复跑通过、原样恢复、恢复后哈希一致）

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | 无构建系统 C 库配方（手动编译 parse.c+object.c → libjsonParse.a） |
| conandata.yml | 官方 tag 源 + SHA-256 + 补丁声明 |
| patches/0001-object.c.patch | gcvt → snprintf 移植修复 |
| test_package/ | 消费者测试（真实 API 调用验证） |

## 注意事项

- 库名 parseJSON 为 C 函数；包内静态库名为 libjsonParse.a（上游 README 命名）
- 仅产出静态库与头文件，无 CLI，非 tool 类型库，不需要 commands.json
---

**编译结束**: 2026-09-26 07:50
**最终状态**: built
