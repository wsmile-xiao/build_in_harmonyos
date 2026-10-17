# picohttpparser 1.4 适配笔记

## 编译环境

- 构建系统: 无（上游 Makefile 只有测试目标 `test`）；配方直接编译单一翻译单元
- 编译日期: 2026-10-11
- 编译器: clang 15.0.4（`/data/service/hnp/bin/clang`）+ `llvm-ar`
- 平台: HarmonyOS 6.0 / aarch64 (armv8)，原生构建（build = host = OHOS，非交叉编译）
- Conan: 2.29.1，profile: `ohos-aarch64`

## 上游测试清点（R51 第一步，实测非推断）

| 项 | 值 |
|----|-----|
| 测试入口 | 上游 Makefile `test` 目标 → 编译 `test-bin` → `prove -v ./test-bin` |
| 测试源 | `test.c`（TAP 输出，基于 picotest 框架） |
| 顶层条目 | 8（`request` / `response` / `headers` / `chunked` / `chunked-consume-trailer` / `chunked-leftdata` / `chunked-overhead` + 1 个顶层 mmap 内存检查） |
| 断言 | 299 条 `ok`，0 条 `not ok` |
| 运行结果 | 直接执行 `test-bin` 与 `prove -v ./test-bin` 结论一致：`All tests successful`（Files=1, Tests=8），退出码 0 |

## 编译步骤

1. `source()`：下载官方 v1.4 tag tarball，再下载 picotest 钉定 commit tarball 到 `source_folder/picotest`
2. `build()`：`clang -O2 -fPIC -c picohttpparser.c -o picohttpparser.o`，`llvm-ar rcs libpicohttpparser.a`（`shared=True` 时改为链接 `libpicohttpparser.so.1.4`）
3. `build()` 末尾运行上游测试：按上游 Makefile 同款参数 `-Wall -fsanitize=address,undefined` 编译 `test-bin` 并执行
4. `package()`：安装 `include/picohttpparser.h` 与库文件
5. `conan create` 自动执行 `test_package/`（CMake + CMakeDeps 消费者视角测试）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `conan create` 报 `Package type is 'library', but no 'shared' option declared` | Conan 2 中 `package_type = "library"` 强制要求声明 `shared` 选项 | 补 `options`/`default_options`（`shared=False`、`fPIC=True`），并**真正实现** shared/static 两条构建路径，不是只声明不用 |
| 2 | 运行上游测试报 `cannot execute binary file`（Error 126） | 写成 `bash "<binary>"`：bash 会把该参数当作**脚本**解析，ELF 无法作为脚本执行 | 改为 `bash -c '"<binary>"'`（与 zlib 配方同款包装方式） |
| 3 | GitHub 源码 tarball 中 `picotest/` 为空目录 | 源码 tarball 不含 git submodule 内容 | `conandata.yml` 增加第二个 source：`h2o/picotest` 钉定 commit（`70b97975…`），保证可复现 |
| 4 | `phr_decode_chunked` 完整消息返回值不是 0 | `consume_trailer` 未置位时，尾部 CRLF 作为未解码字节返回（实测为 2） | 按实测语义修正消费者测试断言，并补 `consume_trailer=1`（返回 0）用例 |
| 5 | （W4 审计 P2）运行上游测试时未传上游 Makefile 的 `TEST_ENV` | 只复刻了编译参数 `-Wall -fsanitize=address,undefined`，漏掉 `UBSAN_OPTIONS=print_stacktrace=1:halt_on_error=1`，导致 UBSan 可恢复诊断不会让构建失败，与上游行为不完全一致 | 运行 test-bin 时按上游注入 `UBSAN_OPTIONS`，并在 `test_package/MANIFEST.yml` 写明等价性依据（`done_testing()` 退出码 + TEST_ENV），避免过度声明 |

## 源码修改

无。上游源码零补丁，本版本不存在 `patches/` 目录。

## 依赖版本

无外部依赖（仅 libc）。测试额外需要上游 `.gitmodules` 声明的 picotest，作为第二个 source 获取（钉定 commit），不引入新的 Conan 依赖。

## 验证结果

```bash
# 默认（静态）
conan create . -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing --build="picohttpparser/*"
# → rc=0；上游测试 8/8 顶层条目、299 条断言全通过；test_package 35 checks, 0 failures

# 共享
conan create . -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing \
    --build="picohttpparser/*" -o "picohttpparser/*:shared=True"
# → rc=0；同上测试结论

# 消费者测试运行输出
picohttpparser consumer test: 35 checks, 0 failures
```

产物：

| 形态 | 文件 |
|------|------|
| 静态（默认） | `lib/libpicohttpparser.a`、`include/picohttpparser.h` |
| 共享（`shared=True`） | `lib/libpicohttpparser.so.1.4`（实体）+ `libpicohttpparser.so.1` + `libpicohttpparser.so`（符号链接，`rm -f` 后重建，遵循 R5） |

## 注意事项

- 本库无系统同名库（不存在 `/lib/libpicohttpparser.so`），不触发 R26 静态约束；默认仍与 1.2 一致采用静态，保持下游 lib 名解析不变。
- 上游测试使用 ASan/UBSan（上游 Makefile 自带），在 OHOS clang 15 上编译与运行均正常。
- 1.2 归档为早期模板产物（manifest/notes 含占位符、未集成上游测试），本版本按规范重做，未改动 1.2 目录内容。
