# depqbf 5.01 适配笔记

## 编译环境
- 构建系统: makefile
- 编译日期: 2026-09-10
- 编译器: clang 15（HarmonyOS PC 真机，conan profile 提供）
- 状态: built（待真机预检回填证据后由 HMBS 统一提交）

## 编译步骤

1. 下载上游源码 `https://github.com/lonsing/depqbf/archive/version-5.01.tar.gz`（sha256 见 conandata.yml）。
2. `make CC=<conan-cc> -j1 libqdpll.a depqbf`：构建静态库与 CLI 二进制，跳过 Linux `-soname` 动态库分支。
3. 交付物：`libqdpll.a`（C API，头文件 `qdpll.h`）、`depqbf`（QDIMACS 求解器二进制）。
4. test_package：CMake 构建 `test_qdpll`（链接 `depqbf::qdpll`，19 个检查点）+ `test_bin.sh`（`--version`/`--help` 与 SAT/UNSAT 求解，6 个检查点）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游无 `make check` / `ctest` 入口 | 5.01 时代仅有 `examples/` 手工演示程序，无自动化测试框架 | 在 `test_package/MANIFEST.yml` 声明 `upstream_tests_exist: false` 并附三项审计；新增的 25 个检查点全部记为适配后新增，不冒充上游覆盖 |
| 2 | 默认 `make` 会走 Linux `-soname` 动态库分支 | makefile 按 `uname` 区分 Darwin/Linux，OHOS 下动态库无验证价值 | 显式目标 `libqdpll.a depqbf`，只构建静态库与二进制 |
| 3 | `libqdpll.a` 规则硬编码 `ar`/`ranlib` | 上游规则未使用 `$(AR)` 变量，传参无效 | 仅传递 `CC`，归档沿用 worker 的 `ar`/`ranlib`；若真机预检报归档器缺失再补补丁 |

## 源码修改

无补丁。`patches/` 目录未创建，`conandata.yml` 无 `patches` 段。

## 依赖版本

- 无外部 Conan 依赖（纯 C99，`--dep-man` 等功能均为源码自带）。

## 上游测试审计

- `makefile`：仅 `depqbf` / `libqdpll.a` / `libqdpll.so.1.0` / `clean` 目标，无 `check`/`test`。
- 源码归档 `depqbf-version-5.01/`：无 `tests/`、`test/`、`run_tests` 等测试设施；`examples/makefile` 仅用 `gcc` 构建 6 个演示程序，无断言与期望输出比对。
- 发布包与 Debian 打包（`depqbf_5.01-3`）同样未注册自动化测试。
- 结论：上游 5.01 确无自动化测试，`test_package/MANIFEST.yml` 已按规范写入 `upstream_tests_exist: false` 与非空 `upstream_test_audit`。

## 验证结果

待 HMBS 真机预检回填（本轮不猜测数字）：

```bash
# 预期在真机执行（由 HMBS 调度，环境与官方 CI 同源）
# conan create archives/d/depqbf/5.01 --user=ohpcd --channel=stable -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
```

- test_package 真实调用 `libqdpll` C API（create/configure/scope/add/sat/get_value/delete）与 `depqbf` 二进制（SAT 退出码 10 / UNSAT 退出码 20），非空壳测试。
- 证伪预案：若预检只看退出码 0，需检查 `test_qdpll` 的 19 行 PASS 输出与 `test_bin.sh` 的 SAT/UNSAT 回显非空；必要时可将 `test_qdpll` 替换为 `exit 1` 桩确认 harness 能捕获失败。

## 交付物

| 文件 | 说明 |
|------|------|
| `lib/libqdpll.a` | 静态库（C API） |
| `include/qdpll.h` | API 头文件 |
| `bin/depqbf` | QBF 求解器命令行工具 |
| `licenses/COPYING` | GPL-3.0 许可证文本 |

## 注意事项

- `depqbf --version` 输出到 stderr，返回码 0；求解 SAT 返回 10、UNSAT 返回 20，`test_bin.sh` 已按此断言，`set -e` 下需先 `set +e` 再捕获。
- 本配方同时交付库与工具：`package_type = "library"` + `bindirs = ["bin"]`，软件级 `commands.json` 已声明 `depqbf` 工具。
- 任何配方或测试改动后，旧验证立即失效，须经 HMBS 真机全部门禁后才可提交。
