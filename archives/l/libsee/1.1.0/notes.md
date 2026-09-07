# libsee 1.1.0 适配笔记

## 结论
- 状态：`built`（OHOS Conan clean create、真实 dlopen/dlsym consumer、修复后的 LD_PRELOAD consumer 均通过；原始未打补丁探索的 139 仍按历史结果保留；未标记 `published`）。
- 构建系统：CMake；语言：C；许可证：Apache-2.0。
- Conan 依赖：无。上游没有 install()、CTest 测试或公开头文件；真实产物仅为 `libsee.so`。

## 源码与构建
- URL：`https://github.com/ashvardanian/LibSee/archive/refs/tags/v1.1.0.tar.gz`。
- SHA256：`8d8a38757e06f266c8490faff2af116fa84b41de646446c0311998a99ab5539f`。
- recipe 显式调用 Conan export/apply hooks；`0001-libsee.c.patch` 仅在 C library 未声明 `__STDC_LIB_EXT1__` 时不导出 Annex K `_s` wrappers，避免可选符号缺失导致 preload 崩溃。该条件是能力探测，不绑定具体 OS。
- recipe 通过 CMakeToolchain 强制 `-fPIC -fno-builtin -nostdlib -nostartfiles` 和 `-shared`，`package()` 手工复制 build 目录下的 `libsee.so` 到 `lib/`。

## 验证结果
- 最终设备使用 host/build `ci/conan/profiles/ohos-aarch64`，显式 `compiler.cppstd=17`、`compiler.libcxx=libc++`、`os.version=6.0`、`tools.build:jobs=1`；Conan create/test_package 成功。
- 上游 `libsee_test.c` 为空，CMake 未启用测试或注册 `add_test()`，因此上游测试统计为 `TOTAL=0 PASS=0 FAIL=0 SKIP=0 NOT_RUN=0`，不是伪造的通过。
- test_package 是真实 dlopen/dlsym 消费者，调用 `libsee_print_size` 并逐字比较 `1,234,567` 及长度 9；随后用 OHOS bash 以 `LD_PRELOAD` 加载包内 `libsee.so`。5 个断言全部通过：`TOTAL=5 PASS=5 FAIL=0 SKIP=0 NOT_RUN=0`。
- 未打补丁的独立 `LD_PRELOAD` 探索命令退出 139（SIGSEGV），完整原始结果保存在 `reports/exploration.txt`；应用补丁并重编译后，以 `/data/service/hnp/bin/bash -c true` 验证退出 0，并输出真实 malloc/free/memmove 统计。原始失败保留为诊断证据，不被覆盖。
