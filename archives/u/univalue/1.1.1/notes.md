# univalue 1.1.1 适配笔记

## 编译环境
- 构建系统: autotools（tar 不含 configure，需 autoreconf bootstrap）
- 编译日期: 2026-09-03
- 编译器: clang 15.0.4（/data/service/hnp/bin/clang），目标 aarch64-linux-ohos
- 状态: built（conan-verify 8 门禁全过，未 upload）

## 编译步骤
1. 官方源审计：tarball SHA-256=72760ce6…，与 GitHub tag v1.1.1 逐文件 blob 哈希全一致（80/80）。
2. `./autogen.sh`（= autoreconf --install --force）生成 configure。
3. config.guess/config.sub 打 OHOS 三元组补丁（E007/E072，等价 patch-autotools-ohos.pl：__OHOS__ LIBC 检测、HarmonyOS 系统识别 case、ohos-linux triplet、OS 白名单、kernel-OS 白名单 linux-ohos*）。
4. `./configure --prefix=...`（config.guess 现可识别 OHOS，无需 --build/--host）。
5. `make -j1 && make check -j1`：TESTS 3/3 全过（object/unitester/no_nul）。
6. `make install DESTDIR=...` staging 验证。
7. conan-init 生成配方；conan-verify 8 门禁（G0-G4+L2/L4/L5）全过。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure: cannot guess build type | config.guess 不识别 HarmonyOS（uname -s=HarmonyOS） | E007/E072：build() 内联 patch-autotools-ohos.pl 等价修改 config.guess/config.sub（5 处） |
| 2 | configure: Kernel 'linux' not known to work with OS 'ohos' | config.sub kernel-OS 白名单缺 linux-ohos* | 在 case $kernel-$os-$obj 白名单追加 linux-ohos*-（脚本 2.3 处匹配变体） |
| 3 | config.status: can't create ./confXXXXXX/subs1.awk: Permission denied | E114：HMDFS setgid 目录，configure 内 `umask 077 && mktemp -d` 生成 drwx--S--- 不可写临时目录 | E114：build() 运行时 _drop_umask_077() 从生成 configure 中删除 umask 077（a52dec/abiword 同款） |
| 4 | make: jobserver mkfifo: Operation not permitted | E074：鸿蒙 SELinux 禁止 FIFO | 全部 make 加 -j1 |
| 5 | test/object: libc++abi terminating uncaught std::runtime_error "JSON value is not an object or array as expected" | E259：conan Release 在 CPPFLAGS 注入 -DNDEBUG，上游 BOOST_CHECK(assert(v5.read(...))) 表达式被整体编译掉，v5 保持 VNULL，裸调 getValues() 抛异常 | E259 回退方案：generate() 追加 -UNDEBUG（CXXFLAGS 位于 CPPFLAGS 之后可正确撤销 NDEBUG），手动构建（无 NDEBUG）3/3 通过为佐证 |
| 6 | conan-verify G2: patch stream is incomplete | tar 不含 configure，补丁针对生成文件 | 生成文件修复全部改为 build() 运行时处理，conandata patches: [] |

## 源码修改

无 patches/（生成文件修复全部在 conanfile.py build() 运行时完成，符合 R6 只改源文件原则）。

## 依赖版本

- 无第三方运行时依赖（standalone 库，Bitcoin Core 用）。
- tool_requires: automake/1.18、libtool/2.5.4（autoreconf bootstrap，abiword-plugin-clarisworks 同款）。

## 验证结果

```bash
# 上游测试（make check，TESTS 3 个）
PASS: test/object
PASS: test/unitester
PASS: test/no_nul
# TOTAL: 3  PASS: 3

# conan create（ohos-aarch64 profile）
# test_package ctest 2/2
1/2 Test #1: test_univalue ...... Passed
2/2 Test #2: ohos_special_test .. Passed
100% tests passed, 0 tests failed out of 2
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | 自包含 autotools 配方（autoreconf bootstrap + OHOS 三元组 + E114 umask + E259 -UNDEBUG + make check） |
| conandata.yml | 官方 URL + SHA-256 |
| test_package/ | 消费者测试 test.cpp + 鸿蒙专项测试 ohos_special_test.cpp（ctest 2/2） |
| manifest.yaml / notes.md | 版本元数据与适配笔记 |

## 注意事项

- 任务路径：依赖项【依赖项】；知识命中 E007/E072/E114/E074/E259 全部为已收录正式条目，无新增知识价值，判路径 A。
- 提交前扫描确认 conandata.yml / conanfile.py 无本地路径或执行端绝对路径等禁止标记。
---

**编译结束**: 2026-09-03 15:43
**最终状态**: built
