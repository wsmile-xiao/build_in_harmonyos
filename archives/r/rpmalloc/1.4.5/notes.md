# rpmalloc 1.4.5 适配笔记

## 编译环境
- 构建系统: configure.py (Ninja generator) + clang 15.0.4 (OHOS SDK)
- 编译日期: 2026-09-08
- 编译器: clang/clang++
- 状态: built

## 编译步骤

rpmalloc 使用自研 Python Ninja 生成器（configure.py），非 autotools：

```bash
python3 configure.py --target linux --toolchain clang --config release --arch arm64
ninja
# 产物: bin/linux/release/arm64/librpmalloc.so / librpmallocwrap.so, lib/linux/release/arm64/librpmalloc.a
# 上游测试: ./bin/linux/release/arm64/rpmalloc-test
```

Conan 配方（archives/r/rpmalloc/1.4.5/conanfile.py）在 build() 中从 source 目录执行
configure.py + ninja，编译器取自 Conan conf（R33）并注入 CC/CXX/AR 环境变量供
configure.py 的 clang 工具链读取。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 编译报 unknown warning option '-Wno-unsafe-buffer-usage' (-Werror) | 上游 build/ninja/clang.py 使用 clang 16+ 旗标，OHOS clang 15 不支持 | 补丁 0001：从 clang.py 移除该旗标 |
| 2 | 上游测试 test_crossthread 在 rpmalloc_finalize 触发 "Memory leak detected" 断言（exit 134，-O2/-O3 确定性复现；-O0 通过） | 跨线程释放把完全释放的 span 以 relaxed CAS 推入 span_free_deferred 链表，消费者用 acquire exchange 取出；aarch64 弱内存序 + 优化下 next 指针写入与 CAS 间缺 release 同步 → 链表损坏/span 永不 unmap | 补丁 0002：atomic_cas_ptr 由 memory_order_relaxed 升级为 acq_rel/acquire（该 helper 唯一调用点即 deferred span 入链） |
| 3 | conan-verify G2 失败 | 生成配方为 autotools 模板，与 rpmalloc 实际构建系统不符；configure.py 在 build 目录不可见 | 重写 conanfile.py 适配 Ninja 构建，build() 中 cd 到 source 目录执行 |

## 源码修改

- patches/0001-build-ninja-clang.py.patch: 移除 -Wno-unsafe-buffer-usage（clang 15 兼容）
- patches/0002-rpmalloc-rpmalloc.c.patch: atomic_cas_ptr relaxed → acq_rel/acquire（aarch64 弱内存序 deferred free 竞态修复）

## 依赖版本

无第三方依赖（rpmalloc 无外部依赖，仅需 libc/libpthread/dl）。

## 验证结果

```bash
# 上游完整测试套件（修复后全通过）
./bin/linux/release/arm64/rpmalloc-test
# 输出: All tests passed (exit 0)
# 覆盖: test_alloc/test_realloc/test_superalign/test_crossthread/test_threaded/
#       test_threadspam/test_first_class_heaps/test_large_pages/test_named_pages/test_error

# Conan 配方验证（G1-G4 通过）
TMPDIR=~/tmp python3 scripts/ohc-run.py conan-verify rpmalloc 1.4.5

# 消费者 smoke test（test_package/test.c 调用 rpmalloc/rpfree/rprealloc）
# 经 conan create 执行通过
```

## 交付物

- conanfile.py + conandata.yml + test_package/ + patches/（CI 输入）
- manifest.yaml + notes.md + reports/（AI 元数据）

## 注意事项

- rpmalloc 是库类型（.a/.so），非命令行工具，无需 commands.json（R38）
- 系统无同名 rpmalloc 库，默认静态即可（R26 不适用）
- 补丁 0002 为 aarch64 弱内存序平台必须；x86 强内存序下不触发但保留无害
