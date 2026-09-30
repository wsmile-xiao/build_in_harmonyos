# offbrand-lib 1.0.0 适配笔记

## 编译环境
- 构建系统: makefile（纯 Makefile，无 configure、无 install 目标）
- 编译日期: 2026-09-29
- 编译器: clang 15.0.4（aarch64-unknown-linux-ohos）
- 状态: built
- 上游: https://github.com/theck01/offbrand_lib (tag v1.0.0, MIT)
- SHA-256: d949084179abb0373e541a346d56c9399c3ecd92a8e2e5a4804c87b4e9900d79

## 编译步骤

1. `ohc-run.py init-build offbrand-lib 1.0.0 --url=.../v1.0.0.tar.gz` — 下载官方 tag 源码
2. `ohc-run.py lang-preflight` — 语言预检 c 匹配通过（R47）
3. 源码审计：官方 URL/SHA-256 核验通过；无 file://、缓存路径、绝对路径污染
4. 上游测试枚举（8 个独立可执行）并全部构建运行通过（8/8=100%）
5. `ohc-run.py conan-init` 生成配方 → 重写为 Makefile 型配方（无 configure 需直驱 make）
6. `ohc-run.py conan-verify` 迭代修复：
   - 补 `options.shared`（package_type=library 必需）
   - `package()` 用 keep_path=False 精确 join 头文件/归档目录
   - 归档 `offbrand.a` 重命名 `liboffbrand.a`（CMakeDeps lib<name>.a 查找）
   - 消费者测试存 obj 兼容实例（裸 malloc 指针被 ob_release 解引用 → 段错误）
   - 鸿蒙专项测试 test_ohos：引用计数/obmap/obstring 正则，断言按上游语义修正
7. 全门禁通过：G1-G4、L2/L4/L5 PASS

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | G2 "Library 'offbrand' not found in package" | ARFLAGS=rvs 产出无 lib 前缀归档 offbrand.a，CMakeDeps 按 lib<name>.a 查找 | package() 重命名 liboffbrand.a（草稿 DRAFT-offbrand-lib-1.0.0-raw-makefile-nolib-prefix-cmakedeps） |
| 2 | conan create 报 "Package type is 'library', but no 'shared' option declared" | Conan 2 对 library 类型要求声明 shared 选项，但上游仅产静态归档、无 shared 变体 | 按上游现状改为 `package_type="static-library"` 并移除 shared 选项（W4 审计建议） |
| 3 | copy() 落盘 include/include、lib/bin 嵌套 | conan copy keep_path=True 保留 pattern 目录层 | keep_path=False + src 精确 join 子目录 |
| 4 | 消费者测试段错误（SegFault） | 裸 malloc 指针非 obj 兼容实例，dealloc 时被 ob_release 解引用 | 改用 obstring_new 公开类实例 |
| 5 | test_ohos 正则断言失败 | obstring_match_regex 无匹配返回空字符串（长度 0）而非 NULL | 断言改为 length==0；"code 42" 长度 7 |
| 6 | make all 报 scripts/prepare: No such file | 上游 shebang `#!/bin/bash`，本机无 /bin/bash | 配方手动 mkdir bin 目录，只构建 bin/offbrand.a 目标 |
| 7 | make: jobserver mkfifo: Operation not permitted | 环境限制 make -j 作业服务管道 | CMake 构建用 -- -j20 在 conan 内正常；未影响结果 |

## 源码修改

无补丁（patches/ 为空）。配方内直驱 make + 手工安装，不修改上游源码。

## 依赖版本

无第三方 Conan 依赖。仅使用 OHOS musl libc 标准头（stdlib/stdio/string/assert/time/regex.h）。

## 验证结果

```bash
# 上游测试（8/8 通过）
./bin/tests/obdeque_test  # TESTS PASSED
./bin/tests/obint_test    # TESTS PASSED
./bin/tests/obmap_test    # TESTS PASSED
./bin/tests/obstring_test # TESTS PASSED
./bin/tests/obtest_test   # TEST PASSED
./bin/tests/obvector_test # TESTS PASSED
./apps/minlog/bin/tests/NCube_test  # TESTS PASSED
./apps/minlog/bin/tests/RTable_test # TESTS PASSED

# test_package（conan create，2/2 通过）
./test_offbrand-lib  # OK (obstring/obvector public API verified)
./test_ohos          # ALL HARMONYOS TESTS PASSED

# 配方验证
ohc-run.py conan-verify offbrand-lib 1.0.0  # G1-G4, L2/L4/L5 全 PASS
```

## 知识路径

路径 B（知识库扩展）：候选台账 + 七轴查重完成；
草稿 DRAFT-offbrand-lib-1.0.0-raw-makefile-nolib-prefix-cmakedeps (.kv/.md 配对)
随本库归档同 PR 交付。
---

**编译结束**: 2026-09-29 09:56
**最终状态**: built
