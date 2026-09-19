# qbe 1.2 HarmonyOS 适配笔记

## 状态

- 平台任务: #9848「qbe 1.2」；分支: `feat/qbe-1.2`
- 当前状态: 适配归档完成；设备端上游全量测试（49/50 PASS + 1 上游 skip）与消费者 E2E（12/12 断言）已实测通过；`conan-verify` G0–G4 PASS（含干净 `conan create` 内再次全量运行，日志 `reports/conan-create.log`）；本地 CI 门禁与 W4 审计进行中

## W0 依赖检查

- 无 Conan 依赖（`conanfile.py` 无 requires）；构建与测试仅需 C 编译器与 POSIX 工具（sh/sed/awk/diff）。
- `conan download qbe/1.2 -r=ohpcd --only-recipe` → 未找到；`conan list "qbe/*" -r=ohpcd` → `Found 0 ... recipes`（确认未发布，可适配）。

## 源码与构建分析

- 官方源码: https://c9x.me/compile/release/qbe-1.2.tar.xz
- SHA256: `a6d50eb952525a234bf76ba151861f73b7a382ac952d985f2b9af1df5368225d`（设备重下核对一致）
- 许可证: MIT；语言: C（`-std=c99`）；构建系统: 纯 POSIX Makefile（`make` 直出 `qbe`；`PREFIX`/`DESTDIR` 安装规则）。
- `Makefile` 依据 `uname -m` 生成 `config.h`：aarch64 → `#define Deftgt T_arm64`（设备原生路径即 arm64 目标，无需交叉）。
- 上游测试: `test/` 共 64 个 `.ssa`；`tools/test.sh all`（=`make check`）按 glob `[!_]*.ssa` 实际执行 50 个；
  下划线前缀 14 个（`_alt/_bf99/_bfmandel/_chacha20/_dragon/_fix1..4/_live/_rpo/_spill1..3`）默认不跑（上游设计，非本适配裁剪）。
- 测试链: `qbe -o *.s` → `cc -g -o exe（*.s + 用例内嵌 driver）` → 原生执行 → stdout diff 或返回码检查。
- 临时文件: `tools/test.sh` 第 7 行 `tmp=/tmp/qbe.zzzz`（硬编码，见下节问题 1）。

## 关键问题与修复（真实报错）

### 1) `/tmp` 只读：上游测试驱动 49/50 全灭（故障先复现，后修复）

- 未打补丁原样运行（设备）:
  `sh tools/test.sh all` → **`49 of 50 tests failed!`**，逐项报错 `cannot open '/tmp/qbe.zzzz.s'`。
- 根因: `tools/test.sh` 硬编码 `tmp=/tmp/qbe.zzzz`；HarmonyOS `/tmp` 只读
  （`touch /tmp/...` → `Read-only file system`；E002/E052 同族问题）。
- 修复: `patches/0001-tools-test.sh.patch`（1 行，最小改动）:
  `tmp=/tmp/qbe.zzzz` → `tmp=${TMPDIR:-/tmp}/qbe.zzzz`；不改默认行为、不引入平台宏、无绝对路径。
- 修复后（同一设备、同一源码树，`TMPDIR` 指向 build 目录）: **`All is fine!`**，rc=0；
  `[ok]` 49 + 上游声明 SKIP 1（`dark.ssa` 首行 `# skip arm64 arm64_apple rv64`）+ FAIL 0。

### 2) 其他已知点核查（逐项）

- `-lpthread`: 设备 clang 15.0.4 可直接链接，49 项无链接错误。
- `-no-pie`/qemu: 仅 `TARGET=arm64/rv64` 交叉分支需要；设备原生（`TARGET=""`）直接以 `${CC:-cc}` 编译运行。
- `qbe.ref`: 上游 tarball 不含（发布物才带），汇编差异比对分支自然跳过——保持上游语义，不作为失败。
- `qbe -h`: 输出 usage（退出 0）；`--version/--help` 因 getopt 短选项不受支持 → CI L2 非阻塞告警（同 crasm 先例）。
- `install(1)`: 设备 PATH 无 install → `package()` 用 `copy()` 安装（安装规则已核读，不修改上游 Makefile）。
- **不得静默跳过**: 唯一 SKIP 为上游 `dark.ssa` 的首行声明，非本适配引入；14 个下划线用例为上游 glob 设计不纳入 `make check`。

## 上游测试清点与实测（R51 三步法）

| 步骤 | 结果 |
|---|---|
| ① 清点 | `test/` 目录 `.ssa` 共 **64**；`make check` = `tools/test.sh all`；上游 glob `[!_]*.ssa` 排除 14 → 默认执行 **50** |
| ② 实际运行 | 设备原生路径实测（2026-09-16）：执行 **50** = PASS **49** + 上游声明 SKIP **1**（dark.ssa, arm64） + FAIL **0**；rc=0 |
| ③ 如实回填 | 通过率 **49/49（100%）**（按可执行且未声明跳过的用例）；含 stdout 比对 13 项、返回码检查 36 项 |

- 逐项结果: 设备侧证据目录 `tmp/qbe-evidence/test-patched.log`（归档仓库外留存；摘要见 `reports/test-report.md`）。
- 修复前对照: `tmp/qbe-evidence/raw-test-unpatched.log`（49 项 `cannot open '/tmp/qbe.zzzz.s'`）。

## 配方要点

- `build()`: `apply_conandata_patches()` → `make -j1 SHELL=sh CC=<conf> CFLAGS="-std=c99 -O2 -g -Wall -Wextra -Wpedantic"`
  （R9: `-j1`；R33: 编译器来自 `tools.build:compiler_executables`；`SHELL=sh` 兼容无 `/bin/sh` 主机）。
- 上游测试在 `build()` 内、`can_run(self)` 时执行（层 1）:
  `TMPDIR=<build-folder>/qbe-test-tmp CC=<conf> sh tools/test.sh all`。
- `package()`: `bin/qbe`、`LICENSE`、`README` 与 `doc/*.txt`；OHOS 下若 `/data/service/hnp/bin/binary-sign-tool` 存在则自签名（设备上不存在，跳过；与 crasm 先例一致）。
- `commands.json`（软件级, R38）: name=qbe, type=tool, versions."1.2".ref=`qbe/1.2`。

## 验证命令

```sh
# 上游全量测试（配方 build() 内自动化）
TMPDIR=<build-folder>/qbe-test-tmp CC=<clang> sh tools/test.sh all

# 归档验证（设备，G0-G4）：PASS
python3 scripts/ohc-run.py conan-verify qbe 1.2 --profile ohos-aarch64-device
```

### conan-verify 结果（2026-09-16 18:15，profile `ohos-aarch64-device`）

| 关卡 | 结果 |
|---|---|
| G0 预构建风险 | ✅ PASS（无知识库命中风险） |
| G1 配方完整性 | ✅ PASS（name/version/source/build/package/package_info/export_sources/conandata/test_package+MANIFEST 全项） |
| G2 干净构建 | ✅ PASS——`conan create` 内：补丁应用 OK、`All is fine!`（49 [ok]，1 上游 skip）、包内 8 个文件、`test_package` 输出 `qbe consumer E2E passed: target=arm64 hello='hello from qbe' exit=42` |
| G3 同名库隔离 | ✅ PASS（纯可执行包，无 lib/） |
| G4 产物完整性 | ✅ PASS（工具提示"无法找到程序包 ID"，与 skypat 等先例一致的非阻断项） |
| L2/L4/L5 | 跳过（工具在该引用格式下无 cache 路径；本地 CI 门禁覆盖） |

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| `bin/qbe` | 包内 | arm64 后端 CLI（SSA → 汇编） |
| `share/doc/qbe/` | 包内 | README + doc/（abi/il/llvm/rv64/win）.txt |
| `licenses/LICENSE` | 包内 | MIT |
| `packaging/qbe-1.2-ohos-aarch64.tar.gz` | 714,880 B | 发布打包产物（release tarball） |

## 注意事项

- `/tmp` 只读是共性前提；补丁将临时文件改到 `${TMPDIR:-/tmp}`，默认行为保持不变。
- 设备共享：构建前已确认无其他 `conan create` 并发（或等待其结束）。

## 对话记录

### 对话 #1 [2026-09-16]

- 问题: 未打补丁运行上游 `tools/test.sh all` → `49 of 50 tests failed`，逐项 `cannot open '/tmp/qbe.zzzz.s'`（OHOS `/tmp` 只读）
- 处理: 复现取证后加最小补丁 0001（`tmp=${TMPDIR:-/tmp}/qbe.zzzz`，默认不变、无平台宏），`build()` 以 TMPDIR 驱动测试
- 结果: 同环境 `All is fine!`（49 [ok] + 1 上游 skip + 0 fail）；正式 `conan create` 内复验一致

### 对话 #2 [2026-09-16]

- 问题: 设备/CI 工具链无 GNU `install(1)`（设备 PATH 实测），设备亦无 `/data/service/hnp/bin/binary-sign-tool`
- 处理: `package()` 用 `copy()` 而非上游 `make install`；签名逻辑按 crasm 先例"工具存在才签"
- 结果: 包内 `bin/qbe` + LICENSE + docs 齐全；消费者 E2E（test_package）通过

### 对话 #3 [2026-09-16]

- 问题: 共享真机全局同一时间只允许一个 `conan create`；期间排队等待 onednn/tdb 的构建窗口
- 处理: 每步操作前检查 `ps -ef | grep conan create`，仅空闲窗口运行 conan-verify / 本地 CI / finish
- 结果: `conan-verify` G0–G4 PASS；本地 CI 门禁 1/1（L0/L1/L1e/L4/L5 PASS，L2 非阻断）；`finish` 完成（step5b 为仓库全局知识草稿积压告警，非本包问题）

### 对话 #4 [2026-09-16]

- 问题: 平台 CI #48822 在 `test_package` 编译期失败——`clang-15: error: unable to execute command: No such file or directory`，
  根因是 CI worker 上 `ld.lld` 加载 `libxml2.so.16` 失败（`test()` 以 `env="conanrun"` 运行只注入包 bin 的 PATH，
  缺 profile `[buildenv]` 的 SDK `LD_LIBRARY_PATH`）；同次 CI 的 `build()`（含上游 50 项全量）已通过（`All is fine!`）
- 处理: `test()` 改用 `env="conanbuild"`（profile `[buildenv]` 注入 OHOS SDK clang 的 PATH 与 LLVM lib 到 `LD_LIBRARY_PATH`）；
  测试脚本去除对 `pipefail` 的硬依赖（POSIX sh 兼容，支持时才启用），保证 CI worker 以 `/bin/sh` 驱动也可运行
- 结果: 本地 conan-verify / 本地 CI 门禁复验通过；W4 审计重新执行；推送后重触发 `/ai review` + `/rebuild`
状态: built
---

**编译结束**: 2026-09-16 19:34
**最终状态**: built
