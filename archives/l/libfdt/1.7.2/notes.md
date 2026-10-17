# libfdt 1.7.2 适配笔记

## 编译环境
- 构建系统: makefile（`make libfdt`，无 configure）
- 编译日期: 2026-09-17
- 编译器: clang/clang++（Conan conf 提供，R33）
- 状态: built（待真机预检通过后由 HMBS 统一提交）

## 编译步骤

上游为 dtc 发行归档（libfdt 无独立 tarball），配方仅构建库部分：

```bash
make -j1 CC=clang AR=llvm-ar EXTRA_CFLAGS="-fPIC -O2" libfdt
make -j1 CC=clang AR=llvm-ar EXTRA_CFLAGS="-fPIC -O2" tests
```

打包产物：

- `include/fdt.h`、`include/libfdt.h`、`include/libfdt_env.h`
- `lib/libfdt.a`（默认静态；`shared=True` 时为 `libfdt.so.1.7.2` + `libfdt.so.1` / `libfdt.so` 实文件拷贝）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | clang 报错 unknown warning option `-Wsuggest-attribute=format`，且 `-Werror` 提升为失败 | GCC 专属警告选项 | 补丁 0001 从 Makefile WARNINGS 移除该 flag（与 device-tree-compiler/1.7.2 同款，已在 CI 验证） |
| 2 | `ln -sf` 版本化别名在部分鸿蒙文件系统可能不受支持 | hmdfs 拒绝 symlink | `package()` 将 `.so.1` / `.so` 别名落盘为实文件拷贝（libcidr 同款做法），构建期沿用上游 `ln -sf`，失败时由真机日志驱动修复 |

## 源码修改

- `patches/0001-makefile-clang-unknown-warning-option.patch`：仅移除 GCC 专属警告 flag，无功能改动。

## 依赖版本

无外部依赖（libyaml/python/valgrind 均为上游可选缺省关闭项）。

## 验证结果

- 上游测试：`tests/Makefile.tests` 的 libfdt C 套件（LIB_TESTS 66 + LIBTREE 3 + DL 2 = 71 个二进制），在配方 `build()` 中 `make tests` 构建后逐个执行，非空输出 + 退出码双重判定（空输出 rc=0 计为 incomplete，防止空 fixture 假通过）。
- test_package：消费者视角链接已打包的 `libfdt`，覆盖建树/加属性/读回/头部校验（见 `test_package/test_libfdt.c`）。
- 具体通过数以真机预检日志为准（本轮未提交，真机未运行，不预填数字）。

## 交付物

| 文件 | 说明 |
|------|------|
| `include/fdt.h`、`libfdt.h`、`libfdt_env.h` | 公开头文件 |
| `lib/libfdt.a` 或 `lib/libfdt.so*` | 静态/共享库 |

## 注意事项

- 同源工具包 `device-tree-compiler/1.7.2` 已验证完整 `make check`（2070 例 PASS）；本库包聚焦其中 71 个 libfdt API 用例，工具链端到端用例归工具包所有，避免重复计数。
- 本轮严禁 commit/push；工作树待 HMBS 真机全部门禁通过后统一提交。
