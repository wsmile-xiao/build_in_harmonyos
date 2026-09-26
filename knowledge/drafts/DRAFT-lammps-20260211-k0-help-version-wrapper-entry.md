# DRAFT-lammps-20260211-k0-help-version-wrapper-entry

**机制**：主命令名与包名不一致、且上游 CLI 仅认单横线短旗标（`-h`）而拒绝 `--help`/`--version` 时，在 `conanfile.py::package()` 里用 `conan.tools.files.save` 随包生成一个**包名命名的 POSIX sh 包装入口**（`bin/<包名>`，0755）：`--help` 委托主命令 `-h`、`--version` 打印包名与版本后 rc=0、其余参数 `exec` 主命令原样透传；`commands.json` 的 `executable` 指向包装入口，`test_package` 增补存在性与两个 rc=0 断言。

## 症状与签名（lammps 20260211 实证）

- `lmp --version` / `lmp --help` / `lmp -version` 均 rc=1，`ERROR: Invalid command-line argument: ... (src/lammps.cpp:490)`；仅 `lmp -h` rc=0。
- 框架 L2 烟测固定用双横线旗标（`ci/conan/build_and_test.sh:1686` 起，`timeout 15 "$bin" --version` 失败再试 `--help`）⇒ L2 记 skip。
- K0 新令（2026-09-25）：主命令必须能响应 `--help` 或 `--version` 之一且 rc=0；主命令名与包名不一致时必须随包提供同名或带包名前缀的包装入口。

## 根因

上游 CLI 面与框架烟测旗标约定不匹配，叠加主命令名（lmp）≠ 包名（lammps）。改上游参数解析 = 改产物形态（多窗既定红线）；改框架 L2 = 框架改动（须单开 PR）。

## 已试方案

- 参数校验探针（把 `-version` 必败断言化，66b0238a2）：保住了「不假装旗标可用」的诚实性，但 L2 仍 skip，K0 仍不满足 ⇒ 不足。
- 多窗一致拒绝的「为凑 L2 绿灯改上游/改框架」：红线，不做。

## 最终方案与验证

`package()` 生成 `bin/lammps` 包装（不改 lmp 二进制、不改上游解析）+ `commands.json executable: lammps` + test_package 断言（存在、--help rc=0 含 banner、--version rc=0 含版本串）。真机验证：`conan create` 后 test_package 全绿（本轮 finish 回写），`lmp` 原面行为逐字不变（`--version` 仍 rc=1，由 version_probe.sh 继续断言）。

## 适用边界 / 反例 / 风险

- 上游本身支持 `--help` 或 `--version` 之一（rc=0）⇒ 不适用，commands.json 保持上游主命令。
- 主命令名与包名一致 ⇒ 按 K0 条文无需包装入口。
- 图形/GUI 服务类包无 CLI 面 ⇒ 不适用（属其他条款）。
- 包装入口必须用 `$(dirname "$0")` 自解析同目录主命令，避免依赖 PATH 形态；`--version` 输出取配方版本串，避免解析上游 banner 的脆弱 grep。

## 查重与新增价值

- 宽口径查重（命令原文见 notes.md「路径 B 查重」）：CMAKE_SYSTEM_NAME 5457 / build_script_folder 267（含 scripts/）/ ENABLE_TESTING 114 等**复用族不构成新条目**；包装入口机制无同族条目（`recipe-search lammps` 6173 条零命中）。
- K0 条文侧引用的 (E447) 在本仓知识库是 SDL2 vendored Find 桥接（`knowledge/doc/E447.md`），同名不同义，非重复。
- 新增价值：把「K0 合规」从一次性手工动作沉淀为可跨库复用的配方模式，附 commands.json/L2 联动与两条 forbid 反例。
