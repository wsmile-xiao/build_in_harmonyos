# DRAFT-lief-1.0.0-ohos-runtime-linux-linkmap-sigsegv — LIEF runtime/linux 用例在 OHOS musl 下 SIGSEGV

## 错误特征

启用 LIEF runtime 特性（LIEF_RUNTIME=ON）构建 unittests 后，运行 runtime 用例：

```text
$ ./build-runtime/tests/unittests/unittests "lief.test.runtime.linux"
lief.test.runtime.linux
  handle
-------------------------------------------------------------------------------
test_runtime_linux.cpp:37: FAILED: {Unknown expression after the reported line}
due to a fatal error condition:
  SIGSEGV - Segmentation violation signal
===============================================================================
test cases: 1 | 1 failed
assertions: 2 | 1 passed | 1 failed
RUN_EXIT=139
```

- dlopen("librt.so.1", RTLD_NOW) 成功（断言 1 passed），随后 `Module::from_handle(H)` 段错误
- unittests --list-tests：14 test cases（runtime 用例已实际纳入注册）

## 触发条件

- 构建配置：`-DLIEF_RUNTIME=ON -DLIEF_RUNTIME_PLATFORM=linux -DLIEF_RUNTIME_ARCH=arm64`
  （上游要求显式声明 PLATFORM/ARCH，缺任一即配置失败）
- 平台：OpenHarmony PC aarch64（clang15，musl 加载器）
- 入口：tests/unittests/test_runtime_linux.cpp（仅随 LIEF_RUNTIME 编译进 unittests）

## 根因分析

`src/runtime/linux/Module.cpp:310` `Module::from_handle(void* H)`：

```cpp
const auto* lmap = reinterpret_cast<const details::link_map*>(H);  // glibc 内部结构
phdr_info.dlpi_name = lmap->l_name;
phdr_info.dlpi_addr = lmap->l_addr;
```

上游把 dlopen 返回的不透明句柄直接按 glibc `include/link.h` 的 `link_map` 布局解读。
OHOS musl 加载器的 dlopen 句柄并非 glibc link_map 布局（musl 使用 `struct dso`），
强转后读 `l_name`/`l_addr` 字段即 SIGSEGV。这是上游测试对 glibc 加载器内部结构的
硬依赖，属真实上游平台条件（非当前库适配缺陷）。

## 修复/规避

无需源码补丁（核心解析 API 完全正常）：

1. OHOS/musl 下保持 `LIEF_RUNTIME=OFF`（上游默认），runtime/linux 用例不计入
   当前配置可执行集合（本库 conanfile.py 即保持 OFF）
2. 上游将 `from_handle` 改为基于 `dl_iterate_phdr`/`dladdr` 的 musl 兼容实现后，
   可重新启用 LIEF_RUNTIME 并运行该用例

## 验证

- 最小纳入实证：LIEF_RUNTIME=ON 配置 exit 0、构建 exit 0、unittests 注册 14 用例
  （从 13 增至 14）、实际运行该用例 → SIGSEGV（RUN_EXIT=139）
- 日志：/storage/Users/currentUser/zhuo/tmp/evidence-runtime-test.log
  （sha256 6f211005adb98ab8409381437f27bb63356cd88a157e851236f637109ff49188）

## 适用边界

- 适用：OHOS/musl + LIEF runtime 特性（1.0.0，1.x 系列待验证）；其他强转 dlopen
  句柄为 glibc 内部结构的上游 runtime 自省代码
- 反例：核心解析 API（Parser/header/sections/symbols）正常；glibc 化 Linux 环境可运行

## 查重差异

- 未命中既有条目：E338（passwd NULL SIGSEGV）、E013（缺 -ldl）、E019（LD_LIBRARY_PATH）、
  E073（symlink 加载）、E068（find_library）均不同根因，仅 SIGSEGV/core dumped 关键词面
- similar_to: E338；caused_by/prerequisite_of/conflicts_with: 无

## 来源

- 库: lief/1.0.0（LIEF-1.0.0.tar.gz, sha256 2cf41269...b682abd）
- 任务: lief-1.0.0-r02-pc4-21-20260917T033445Z（r01 已建 to_json 草稿，本轮新增）
- 证据: reports/test-ledger.md（双口径台账）、reports/knowledge-candidate-ledger.md