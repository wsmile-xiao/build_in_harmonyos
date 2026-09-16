- **三方库名称**：wayneko
- **上游版本**：0_git20260326（上游无 release tag，按 commit 固定：`437a8a708ea68f0288becb047b582e84ef3e412c`，提交日期 2026-03-26）
- **上游仓库地址**：https://git.sr.ht/~leon_plickat/wayneko
- **适配路径**：路径 A（基础适配）
- **使用知识库**：openharmony-compile-agent（v12.19/v12.20）

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 0 | 来源：无（上游无测试套件） |
| 集成测试 | 0 | 来源：无 |
| 其他测试 | 0 | 无 |
| **合计** | **0** | 清点证据见下 |

清点方式（R51 三步法第一步，逐项核实）：

- tarball 文件清单（`tar tzf`）：仅 11 个文件，无 `tests/` 目录、无 `*_test.*` / `test_*.c`
- `Makefile` 目标仅 `wayneko` / `install` / `uninstall` / `clean`（`.PHONY: clean install`），无 `check` / `test`：`make -n check` → `make: *** No rule to make target 'check'.`
- 仓库/源码包内无任何 CI 配置（无 `.gitlab-ci.yml` / `.github/` / `.build.yml` / `.builds/`）

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 117 | +117（新增） | `tests/test_wayneko.c`：编译真实上游 `wayneko.c`，覆盖颜色解析、参数解析、图集创建、动画状态机、时间差/困倦阈值、用法文本 |
| 集成测试 | 23 | +23（新增） | `test_package/test.sh`：执行已安装的 `bin/wayneko`，断言真实退出码与诊断文本 |
| 鸿蒙特有测试 | 12 | 新增 | `test_package/test_wayneko_ohos.c`：仅 OHOS 编译（`#ifndef __OHOS__ #error` 守卫），对已安装二进制做 ELF/AArch64/PIE/NX/RELRO/DT_NEEDED 依赖链与 glibc backtrace 守卫有效性断言 |
| **合计** | **152** | **+152（新增）** | |

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例
- [ ] **是**，存在对上游测试用例的修改

上游本身无测试用例，且本次适配**未修改任何上游源码**（`patches: {}`，无补丁）；
补充测试以 `#define main wayneko_cli_main` + `#include "wayneko.c"` 方式在**只读**前提下
编译真实上游翻译单元。

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [ ] 否，上游已有测试用例覆盖
- [x] **是**，上游无测试用例，适配后补全了测试

- **补全的测试范围**：三层共 152 断言——层 1（117，`build()` 内由 `make -f tests/Makefile.check check` 驱动，CI 留痕 L1c）；层 2（23，消费者视角执行已安装二进制）；层 3 鸿蒙特有测试（12，ELF 级平台断言）
- **补全原因**：上游 wayneko 仅有一个 Makefile 与单个 `wayneko.c`，不含任何测试框架/测试目录/`check` 目标，按 `docs/TEST_QUALITY_SPEC.md` 三层测试体系与 R51 要求补齐；并按赛事规则补充鸿蒙特有测试
- **新增测试文件清单**：
  1. `tests/test_wayneko.c` — 层 1 行为测试（117 断言，真实调用上游函数）
  2. `tests/Makefile.check` — 层 1 测试驱动（提供 `check` 目标，使 `build()` 留下 CI L1c 可识别的 `make ... check` 痕迹）
  3. `test_package/test.sh` — 层 2 消费者测试（23 断言，执行已安装二进制）
  4. `test_package/test_wayneko_ohos.c` — 鸿蒙特有测试（12 断言，仅 OHOS 编译：ELF64/AArch64/PIE/NX/RELRO、DT_NEEDED 依赖链、glibc backtrace 守卫有效性）
  5. `test_package/MANIFEST.yml` — 上游测试清点声明（含清点命令与 `upstream_tests: []` 实证）

## 验证结果

- 编译状态：**通过**
- 上游测试用例通过率：**不适用**（上游 0 用例，清点证据见上）→ 记作 0/0
- 新增测试用例通过率：**152/152（100%）**
  - 层 1：117/117（实测原始行 `wayneko layer-1 behaviour suite: 117 passed, 0 failed`）
  - 层 2：23/23（实测原始行 `[test] test_package assertions: 23 passed, 0 failed`）
  - 鸿蒙特有测试：12/12（实测原始行 `wayneko OHOS-specific consumer test: 12 passed, 0 failed`）

本地 CI 模拟（`ci/conan/build_and_test.sh`，CI_PACKAGES 指向本包，CI_BRANCH=`feat/wayneko-0_git20260326`）：

```
JC_RESULT=pass
L0_RESULT=pass: all checks passed
L1_RESULT=pass: upstream tests + test_package executed
L2_RESULT=pass: wayneko --help OK
L4_RESULT=pass: patches clean
L5_RESULT=pass: bin/ has content
  Success: 1
  Failed:  0
  Pass rate: 100.0% (1/1)
```

测试真实性佐证（R34 / CI L1e 破坏性反向验证）：移除包 `bin/` 后同一脚本 23 断言中 17 条失败，
证明测试真实依赖被测包产物。

## 补充说明

**适配要点 1：`wayland-scanner` 在 OHOS 上不可执行（关键决策）**

`wayland/1.22.0.1` 包虽然提供 `bin/wayland-scanner`，但 OHOS 拒绝 execve 从 Conan 缓存解出的
二进制（实测 `sh: .../p/bin/wayland-scanner: Operation not permitted`，exit 126）。
本配方沿用仓库内已合入的先例 `archives/w/wayland-protocols/1.36.1`：
在 `build()` 中从 wayland 1.22.0 源码**静态编译** `wayland-scanner`（仅依赖 libc），
再生成 `wlr-layer-shell-unstable-v1` / `xdg-shell` / `ext-idle-notify-v1` 三组协议绑定。
已实测该静态 scanner 可执行并正确产出：

```
$ ./wayland-scanner --version
wayland-scanner 1.22.0
```

**适配要点 2：构建参数不依赖 shell 环境变量（R33）**

未直接使用上游 Makefile 的 `pkg-config` 与裸 `${CC}`/`${CFLAGS}`，而是把解析后的
Conan 依赖路径显式传给 Makefile（`CC=` 取自 `tools.build:compiler_executables`，
`CFLAGS`/`LDFLAGS`/`LIBS` 由依赖包目录推导），避免 release worker 上变量为空导致静默失败。

**适配要点 3：RPATH 自定位**

链接期写入 wayland/pixman 库目录 RPATH，使安装后的 `bin/wayneko` 无需 `LD_LIBRARY_PATH`
即可运行（L2 smoke test 直接执行二进制）。

**已知限制**（如实申报，不隐藏）

- wayneko 为图形 layer-shell 客户端，需运行中的、实现 `zwlr-layer-shell-unstable-v1` 的
  Wayland 合成器才能真正绘制；CI/无头环境无法验证真实渲染画面，测试覆盖 CLI 行为、
  颜色解析、图集创建与动画状态机等真实函数（非 stub）。
- 静态 `wayland-scanner` 需 `libexpat.a`；Conan `expat/2.8.2` 只提供 `libexpat.so`，
  故 `_expat_static()` 依次尝试「Conan expat 静态库」→「设备路径
  `/data/service/hnp/expat.org/expat_2.7.3/lib/libexpat.a`」，两者皆无时以明确错误信息
  失败（不静默降级）。该设备路径与已合入 main 的 `wayland-protocols/1.36.1` 一致。

**质量自检**

- W3 本地 CI 结果由 `finish` 工具写入 `.ci-result.json`（`exit_code: 0`，含日志 SHA256），未手工修改
- W4 独立审计（子任务，上下文隔离）：`reports/audit-result.json`，verdict = **pass**，P0/P1 = 0
