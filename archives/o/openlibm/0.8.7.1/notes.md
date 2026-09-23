# openlibm 0.8.7.1 适配笔记（上游 0.8.7）

## 编译环境
- 构建系统: makefile (Makefile + Make.inc)
- 编译日期: 2026-09-04
- 编译器: clang/clang++ (15.0.4)
- 状态: built（本次 recipe 修订；conan create 设备复验待执行）

## 编译步骤

```bash
make USECLANG=1 libopenlibm.a -j1
make USECLANG=1 install-static install-headers install-pkgconfig DESTDIR=$TEST_PREFIX prefix=$DEFAULT_PREFIX
make USECLANG=1 -j1 check
```

`check`/`test` 已接入 `conanfile.py` 的 `build()`，`conan create` 会在编译完成后自动执行；
失败会直接使构建失败，不再依赖构建后的单独人工命令。

## 上游测试清单

- `test/test-double`：1118 个常规用例 + 932 个 exception flag 用例。
- `test/test-float`：1101 个常规用例 + 923 个 exception flag 用例。
- 合计 4074 个用例；根 Makefile 的 `check: test/test-double test/test-float` 依次运行两者。
- v0.8.7 没有 regression 测试目录；`test/inf_torture.c` 和 `test/libm-bench.cpp` 未接入上游 `check` 目标。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | test_package 编译失败：`<openlibm_complex.h> file not found` | 头文件内部用无前缀 include | `includedirs = ["include/openlibm"]` |
| 2 | test_package 链接失败：动态库找不到 | 静态模式下 Makefile 仍生成 .so | 根据 `shared` 选项分别构建 |
| 3 | GitHub 下载超时 | 本地环境无法直连 github.com | source() 加镜像 fallback |

## 验证结果

### 上游测试（make check）
- test-double: 1118 + 932 = 2050 项全通过
- test-float: 1101 + 923 = 2024 项全通过
- 命令已在设备侧记录通过；本轮把同一命令接入 `build()` 后，仍需重新执行 `conan create` 验证自动化路径。

### Conan test_package
- 100% tests passed (1/1)

## 待设备复验

```bash
conan create . --profile=ohos
```

预期构建日志包含：

```text
make USECLANG=1 -j1 check
test/test-double
test/test-float
```
