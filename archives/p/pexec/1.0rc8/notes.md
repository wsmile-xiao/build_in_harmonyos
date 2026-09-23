# pexec 1.0rc8 适配笔记

## 编译环境
- 构建系统: autotools（GNU 项目自带 configure，1998–2007 年代脚本）
- 编译日期: 2026-09-15
- 编译器: clang 15 / clang++（OHOS aarch64 真机）
- 状态: built

## 编译步骤

1. W0 预检：`bash ci/scripts/preflight_check.sh pexec/1.0rc8` 通过；零外部依赖（无 requires）。
2. W0b：归档树无 pexec 同名/同版本；recipe-search 无相似配方，首版走 conan-init 骨架后人工定制。
3. 配方为 application 型（`bin/pexec` + 软件级 commands.json）：
   - `generate()`：`VirtualBuildEnv(self).generate()` —— conanbuild 环境提供 `CONFIG_SHELL/SHELL`，
     避免 configure 落到 HMDFS 受限的 `/bin/sh`（E386 家族）。
   - `build()`：
     a. 先把源码整树拷到浅层目录 `~/tmp/uc2/pexec-build-1.0rc8`（深 conan 缓存目录下 config.status
        报 `conf*/subs-1.sed: Permission denied`，E011/E114 同源）；
     b. 就地把 configure 里的 `(umask 077 && …)` 放宽（E011）；
     c. `sh configure --build=aarch64-unknown-linux-gnu --prefix=<pkg>` + `make -j1`
        （config.guess 不认识 HongMeng 内核，显式给 build 三元组跳过探测）；
     d. 断言 `src/pexec` 产物存在后拷回 build_folder。
   - `package()`：拷 `bin/pexec` 并 chmod 0755；`package_info()` 清空 includedirs/libdirs，只留 bindirs。
4. `conan-verify`（G0–G4 + L2/L4/L5）PASS；`finish` 的 W3 本地 CI 模拟通过（Pass rate 100.0% (1/1)）。

## 上游测试账本（四维）

- 上游源码静态声明总数 N_static = 0：1.0rc8 全树无 TESTS/check 目标、无测试脚本（清点见 `test_package/MANIFEST.yml`）。
- 实际执行数 N_executed = 0（上游无测试可执行）。
- 跳过数 = 0。
- 新增消费者测试 N_consumer = 1：`test_package/test_pexec.sh` 运行安装后的 `bin/pexec` 并断言行为
  （`--help` 横幅、`--version`、未知选项非零退出；共 3 条断言），由 `test_package/conanfile.py::test()`
  实际执行（`sh test_pexec.sh <pexec 路径>`）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | conan 缓存深目录下 configure 报 `conf*/subs-1.sed: Permission denied`（config.status 无法回读临时目录） | HMDFS 权限组合（E011/E114 同源） | build() 把源码拷到浅层 `~/tmp/uc2/pexec-build-<ver>` 编译；并放宽 configure 中的 `(umask 077 && …)` |
| 2 | `working directory cannot be determined` / `shell-init: getcwd failed` | conan profile 的 `SHELL`/`CONFIG_SHELL` 指向 `/data/service/hnp/bin/bash`（HMDFS 下 getcwd 必挂，E386 家族） | `generate()` 生成 VirtualBuildEnv（conanbuild 环境提供可用 shell） |
| 3 | `cannot guess build type` | 1990 年代 config.guess 不认识 HarmonyOS，其编译探针在 HMDFS 上还会 Permission denied | 显式 `--build=aarch64-unknown-linux-gnu`（跳过 config.guess 探测） |
| 4 | 编译器定位（CLI 工具的 CC/CXX） | 设备交互 shell 的 PATH 不等于 conan 工具链 | 从 `tools.build:compiler_executables` 取 CC/CXX 显式传入（R33） |

## 源码修改

无补丁（conandata.yml 的 `patches` 为空）；上述 umask / shell / 三元组三处适配全部在配方
`build()`/`generate()` 内就地完成，不携带源码补丁。

## 依赖版本

无外部依赖（零依赖工具包）。

## 验证结果

```bash
bash ci/scripts/preflight_check.sh pexec/1.0rc8        # PASS
python3 scripts/ohc-run.py conan-verify pexec 1.0rc8   # PASS（G2 conan create 干净构建）
python3 scripts/ohc-run.py finish pexec 1.0rc8 built   # W3 本地 CI 模拟：Pass rate 100.0% (1/1)
```

## 对话 #

- 2026-09-15 夜跑窗口（GLM-33）：首版适配、构建与提审（PR #10059）。
- 2026-09-15 晚（GLM-26 接手收尾）：补归档完整性 —— 重写本 notes（原为 conan-init 模板占位符）、
  补齐 `manifest.yaml` 的 `sha256` 与构建配置字段、删除 `test_package/CMakeLists.txt`
  （conan-init 骨架残留，引用不存在的 `test.c`；实际消费者测试走 `test_pexec.sh`）。

## 注意事项

- 工具型包（application）：软件级 `commands.json` 已声明，包内可执行文件为 `bin/pexec`。
- 上游 1.0rc8 无测试套件，消费者测试以安装后二进制的行为为断言载体。
- 构建在浅层临时目录进行（`~/tmp/uc2/pexec-build-<version>`），每次 build 先删除重建。
---

**编译结束**: 2026-09-15 21:06
**最终状态**: built
