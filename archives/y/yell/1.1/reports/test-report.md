# yell 1.1 测试报告（OHOS aarch64）

- 包引用：`yell/1.1@ohpcd/stable`
- Profile：`ci/conan/profiles/ohos-aarch64`（os=OHOS 6.0 / arch=armv8 / clang 15）
- 构建方式：FreeBSD port `do-build` 单行命令的等价调用（`clang -O3 -DNDEBUG -Wall yell.c -o yell`，编译器 stdio 重定向到日志文件）
- 执行日期：2026-09-28

---

## 0. 测试汇总（机器可读）

### 上游测试

| 项 | 数量 |
|------|------|
| 总测试数 | 0 |
| 通过 PASS | 0 |
| 失败 FAIL | 0 |
| 跳过 SKIP | 0 |

### 鸿蒙特有（test_package）

| 项 | 数量 |
|------|------|
| 总测试数 | 6 |
| 通过 PASS | 6 |
| 失败 FAIL | 0 |
| 跳过 SKIP | 0 |

---

## 1. 上游测试（R51 第 1-3 步）

### 1.1 清点（第 1 步）

| 项 | 结论 | 证据 |
|----|------|------|
| 测试目录 | 无 | 解包目录 4 个文件（Makefile / yell.c / yell.h / README），无 `tests/` |
| 构建系统注册的测试入口 | 0 个 | 顶层 `Makefile` 仅有 `default`（打印提示）/ `install` / `deinstall` 三个目标 |
| ctest / pytest / meson test 注册 | 无 | 上游无 CMake/Meson/Python 测试配置 |
| `make -n check` | 失败 | `make: *** No rule to make target 'check'.  Stop.` |

### 1.2 结论

上游**无任何测试套件**（0 个用例）。已按仓内惯例在 `ci/config/no_official_test.txt`
登记（先例：acpi_call——同为「Makefile 仅 default/install 目标、无 check」）。
上游无用例，不适用第 2/3 步（运行与统计）。

---

## 2. 鸿蒙特有测试（test_package，6 项端到端断言）

test_package 以 bash 脚本（`test_package/test.sh`，`set -euo pipefail`）对
**conan 安装出来的** `bin/yell` 实测（解释器按 `$CONFIG_SHELL` → 固定候选清单
解析，禁用 `shutil.which("bash")`，先例 zpaq 7.15）：

| # | 断言 | 实测结果 |
|---|------|----------|
| T1 | 安装产物存在、为普通文件且可执行 | PASS |
| T2 | `readelf -h`：ELF64 / Machine=AArch64 | PASS |
| T3 | `readelf -d`：DT_NEEDED **仅** `libc.so`（纯 C，无 libc++/libm 依赖） | PASS |
| T4 | 运行退出码 0（OHOS 无 `/dev/speaker`，`play()` 的 `open` 有 `if (handle >= 0)` 守卫——优雅降级契约） | PASS |
| T5 | 运行无任何输出（无诊断信息） | PASS |
| T6 | 二次运行幂等（退出码 0，无状态无崩溃） | PASS |

```
test_package PASS: T1 installed binary present and executable
test_package PASS: T2 ELF64 AArch64 binary
test_package PASS: T3 DT_NEEDED is exactly libc.so
test_package PASS: T4 run exits 0 without a speaker device
test_package PASS: T5 run produces no output
test_package: all 6 checks passed
```

反向验证（L1e 语义）：test_package 的 conanfile.py 从
`self.dependencies["yell"].package_folder` 显式解析二进制路径——删除包内容
即测试失败。

---

## 3. 编译验证

- `conan create`（G2 干净构建）通过：clang 15.0.4，`-Wall` **零告警**。
- 产物：`bin/yell`（ELF64 AArch64，动态链接 musl，`DT_NEEDED` 仅 `libc.so`）。
- 打包内容：`bin/yell` + `licenses/README`（上游）+ `licenses/LICENSE`（归属说明）。

## 4. 结论

- 上游测试：0/0（无测试套件，已在 `ci/config/no_official_test.txt` 登记）
- 鸿蒙特有测试：6/6 通过（100%）
- 综合判定：**通过**（本地 W3 conan-build-test 全绿，`.ci-result.json` 由
  finish 自动写入）
