# wayneko 0_git20260326 测试报告（HarmonyOS PC / aarch64）

## 1. 结论

- 编译状态：**通过**（`conan create`，host=build=`ci/conan/profiles/ohos-aarch64`，exit 0）
- 上游测试用例：**上游 0 用例**（清点证据见 §2）→ 通过率不适用
- 适配后新增测试用例：**152/152 通过（100%）**
  - 层 1（`build()` 内，`tests/`）：117/117
  - 层 2（`test_package/`）：23/23
  - 层 3 鸿蒙特有测试（`test_package/test_wayneko_ohos.c`）：12/12
- 本地 CI 模拟（`ci/conan/build_and_test.sh`）：JC/L0/L1/L2/L4/L5 全部 pass，Pass rate 100.0%（1/1）

## 2. 上游测试清点（R51）

清点命令与结果：

```
$ tar tzf wayneko-437a8a708ea68f0288becb047b582e84ef3e412c.tar.gz | sed 's:^[^/]*/::' | sort
LICENSE  Makefile  README  bash-completion  ext-idle-notify-v1.xml
neko-bitmap.xbm  wayneko.1  wayneko.c  wlr-layer-shell-unstable-v1.xml
xdg-shell.xml  zsh-completion
```

- 无 `tests/`、无 `*_test.*` / `test_*.c`
- Makefile 目标仅 `wayneko` / `install` / `uninstall` / `clean`（`.PHONY: clean install`），
  **无 `check` / `test` 目标**：`make -n check` → `make: *** No rule to make target 'check'.`
- 无任何 CI 配置（无 `.gitlab-ci.yml` / `.github/` / `.build.yml` / `.builds/`）

⇒ 上游确认无测试套件，适配后按 R51 + `docs/TEST_QUALITY_SPEC.md` 补全两层真实测试。

## 3. 层 1：补充行为测试（`tests/`，117 断言）

`tests/Makefile.check` 驱动，`conanfile.py` 的 `build()` 中执行 `make -f tests/Makefile.check check`，
日志留 `make ... check` 痕迹（CI L1c）。

`tests/test_wayneko.c` 以 `#define main wayneko_cli_main` + `#include "wayneko.c"` 编译**真实上游源码**
（只读，不修改上游），断言真实行为：

| 覆盖对象 | 断言内容 |
|---|---|
| `colour_from_hex` / `colour_from_flag` | 0xRRGGBB、0xRRGGBBAA 解析；非法输入拒绝；预乘分量按独立实现重算比对 |
| `get_argument` | 参数存在/越界（缺参）语义 |
| `atlas_init` | 图集创建成功、尺寸 512×128、填充图非空 |
| 动画状态机 | `animation_next_state` / `surface_next_frame` 状态迁移、tick 推进、run 上限 |
| `timespec_diff` / `wants_sleep` | 时间差计算；昼夜困倦阈值判定 |
| `usage` | 用法文本包含全部 9 个文档化选项 |

实测结果（W3 日志原始行）：

```
wayneko layer-1 behaviour suite: 117 passed, 0 failed
wayneko layer-1 behaviour suite OK
[layer-1] make check target completed
```

## 4. 层 2：消费者测试（`test_package/`，23 断言）

`test_package/test.sh` 通过 `conanrun` 环境执行**已安装的 `bin/wayneko`**，断言真实退出码与诊断文本：

| 场景 | 断言 |
|---|---|
| `--help` | exit 0；输出含 `Usage: wayneko` 及 9 个选项（10 断言） |
| 未知选项 | exit ≠ 0 且含 `Unknown option` |
| `--type bogus` | exit ≠ 0 且含 `Unknown argument 'bogus' for flag '--type'` |
| 缺少参数（`--type`） | exit ≠ 0 且含 `requires a parameter` |
| 非法颜色（`--background-colour nothex`） | exit ≠ 0 且含 `Invalid colour` |
| `WAYLAND_DISPLAY` 未设置 | exit ≠ 0 且含 `WAYLAND_DISPLAY is not set` |
| `WAYLAND_DISPLAY=nonexistent-display` | exit ≠ 0 且含 `Can not connect to wayland display` |

实测结果（conan create 日志原始行）：

```
[test] test_package assertions: 23 passed, 0 failed
[test] test_package PASS
```

**真实性证明（R34 / CI L1e）**：破坏性反向验证——移除包的 `bin/` 后重跑同一脚本，
23 断言中 17 条失败，证明测试真实依赖被测包产物，而非空壳。

## 5. 鸿蒙特有测试（层 3，12 断言）

`test_package/test_wayneko_ohos.c` —— 仅 OHOS 目标编译（`#ifndef __OHOS__ #error` 守卫），
对**已安装**的 `bin/wayneko` 做 ELF 级平台断言：

| 覆盖对象 | 断言内容 |
|---|---|
| ELF 形态 | 合法 ELF64 / 小端 / `EM_AARCH64` / `ET_DYN`（PIE） |
| 安全基线 | `PT_INTERP`（动态链接）/ NX 非可执行栈 / RELRO |
| 依赖链 | `DT_NEEDED` 含 `libwayland-client` 与 `libpixman-1`（Conan 依赖已嵌入产物） |
| 移植守卫 | 无 glibc 专属 `backtrace`/`backtrace_symbols_fd` 未定义符号（`#ifdef __GLIBC__` 守卫生效） |

实测结果（conan create 日志原始行）：

```
wayneko: built OHOS-specific consumer test
wayneko OHOS-specific consumer test: 12 passed, 0 failed
```

## 6. 本地 CI 模拟（预审）

```
CI_PACKAGES=archives/w/wayneko/0_git20260326 CI_BRANCH=feat/wayneko-0_git20260326 \
  zsh ci/conan/build_and_test.sh
```

实测门禁结果（完整日志见 `reports/w3-local-ci.log`）：

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

另有 `conan-verify` G1–G4 + L2/L4/L5 全过（见 `reports/conan-verify-report.md`）。

## 6. 已知限制（如实申报）

- wayneko 是图形 layer-shell 客户端，需运行中的、实现 `zwlr-layer-shell-unstable-v1` 的
  Wayland 合成器才能真正绘制画面；CI/无头环境无法验证真实渲染，测试覆盖的是
  CLI 行为、颜色解析、图集创建与动画状态机等真实函数。
- 静态 `wayland-scanner` 依赖设备提供的 `/data/service/hnp/expat.org/expat_2.7.3/lib/libexpat.a`
  （Conan expat 包只含 `libexpat.so`，无静态库）；该路径缺失时 `_expat_static()` 以明确信息
  失败（不静默降级）。同一路径被已合入 main 的 `archives/w/wayland-protocols/1.36.1` 无条件使用。
