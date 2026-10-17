- **三方库名称**：bti
- **上游版本**：034
- **上游仓库地址**：https://github.com/gregkh/bti
- **适配路径**：路径 A（基础适配）
- **使用知识库**：E129（HMDFS 上 `configure`/`config.status` 的 `umask 077` 临时目录对构建用户不可写；同族 E114/E491）。补丁 `0003` 采用的就是 E129 的推荐命令（`umask 077` → `022`）。`conan-verify` G0 预扫描另外命中 E490（autotools helper 脚本可执行位），本包发布 tarball 已保留 `configure`/`install-sh` 等可执行位，故配方无需 `chmod`，该条目未触发修复。

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 0 | 上游无 `tests/` 目录，`Makefile.am` 无 `check_PROGRAMS`/`TESTS` |
| 集成测试 | 0 | 同上 |
| 其他测试 | 0 | 同上 |
| **合计** | **0** | 上游无任何测试套件 |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 0 | 不变 | 上游无单元测试 |
| 集成测试 | 0 | 不变 | 上游无集成测试 |
| 鸿蒙特有测试 | 4 | 新增 | `test_package/test.sh` 对安装产物 `bin/bti` 的四项断言：T1 `--version` 版本串、T2 `--help` 用法、T3 缺失配置诊断、T4 离线 `--dry-run` 请求构造 |
| **合计** | **4** | **+4** | 上游合计 0 + 鸿蒙行 4 |

## 上游测试用例修改说明

- [x] **否**，未修改上游任何测试用例

## 补全测试用例说明

- [x] **是**，上游无测试用例，适配后补全了测试

- **补全的测试范围**：CLI 行为契约 4 项（上表「鸿蒙特有测试」行），全部在 `conan create` 的 `test_package` 阶段真实执行
- **补全原因**：上游 bti 自 2014 年后无维护、不含任何测试套件（`make check` 输出 `make: Nothing to be done for 'check'.`，退出码 0），只能以行为契约覆盖
- **新增测试文件清单**：
  1. `archives/b/bti/034/test_package/test.sh` — POSIX sh 脚本，断言 4 项并输出 `RESULT: 4/4 checks passed`
  2. `archives/b/bti/034/test_package/conanfile.py` — `test()` 调用 `test.sh`，对被测包安装出的 `bin/bti` 执行断言

## 验证结果

- 编译状态：通过
- 上游测试用例通过率：0/0（不适用——上游 0 个可运行测试入口）
- 新增测试用例通过率：4/4（100%）

## 文件改动记录

- 新增 `archives/b/bti/`（软件级 `manifest.yaml`、`README.md`、`commands.json`）与 `archives/b/bti/034/`（`conanfile.py`、`conandata.yml`、版本级 `manifest.yaml`、`notes.md`、`patches/`、`test_package/`、`reports/`）
- 未改动 `SKILL.md`、`ci/`、`scripts/`、`templates/`、`references/` 及任何其他软件目录；净 diff 无二进制条目

## 补充说明

1. **依赖图处置**：已发布的 `liboauth/1.0.3` 钉 `openssl/1.1.1w`，已发布的 `curl/8.15.0` 钉 `openssl/3.5.6.1`，二者各自只有一个 package_id，同时依赖即 `Version conflict`。配方在消费侧用 `override` 统一到 `openssl/3.5.6.1`；`liboauth` 是静态小库，构建时由 `--build=missing` 从源码重建（设备实测通过），消费方运行期不再依赖它。
2. **三处适配补丁**：`0001` 把 `bti-shrink-urls` 的 shebang `#!/bin/bash` 改为 `#!/bin/sh`（OHOS 没有 `/bin/bash`，直接执行 rc=126，`sh -n` 与 `--help` 实测通过）；`0002` 适配 json-c 0.13 起移除的 `is_error` 宏（3 处改为显式 NULL 比较）；`0003` 把 `configure` 中创建临时目录的两处 `umask 077` 放宽为 `022`（HMDFS 上 0700 目录对构建用户不可写）。三处均不含平台宏、无 `#ifdef` 守卫。
3. **readline 不是构建依赖**：上游运行期用 `dlopen` 尝试 `libreadline.so.6/5/4`、`libedit.so.2`，设备上不存在时回退 `fgets`。
4. **G4/L2/L4/L5 人工补测**：`conan-verify` 对纯可执行包在这四项上同时打印 `✅ PASS` 与 `⏭️ 跳过（无 cache 路径）`，按跳过处置后人工补测——G4 用包内容清单与 `package_info()` 的 `bindirs` 互证；L4 对 `bin/bti` 核 `DYN`/`GNU_STACK RW`/`GNU_RELRO`/`BIND_NOW`/`PIE`；L2 在包内制品上执行真实命令；L5 用两轮独立清缓存构建比对产物 sha256（5 项逐字节一致，`conanmanifest.txt` 首行为打包时间戳属预期漂移）。逐字记录见 `reports/conan-verify-supplement.md`。
5. **preflight 绕行留痕**：本 PR 为全新包，`--no-preflight` 绕行两项确定性误报——PF0 对 fork PR 的 `owner:branch` API 形态报错；PF9 对包级文件 `archives/b/bti/manifest.yaml`、`archives/b/bti/commands.json`、`archives/b/bti/README.md` 报「缺版本目录层」，而这三处文件由 ARCHIVE-SPEC v3.0 与 L0k 要求放在包级，与 PF9 的 5 段路径要求冲突。已本地等价执行 PF1-PF4：单软件目录原子性（净 diff 仅含 `archives/b/bti/`）、无源码归档（`git diff --numstat` 无 `-` 行）、`test_package` 真实存在且真跑消费者（`RESULT: 4/4 checks passed`）、依赖已发布（`conan install --build=never` 与 conan-verify G1 证据）。
6. **链接方式与运行环境**：`libcurl`/`libxml2`/`json-c` 按本仓非系统同名库的既定模型动态链接（依赖链由 Conan 管理），`liboauth`/`pcre`/`openssl` 静态链接；`bin/bti` 的 `DT_NEEDED` 为 `libcurl.so`、`libxml2.so.16`、`libjson-c.so.5`、`libc.so`。因此消费方需在 `conan install` 后用 conanrun 环境运行（`test_package` 正是这样跑通的）。W3 本地 CI 的 L2 冒烟不带 conanrun 环境，故 `bti --version` 打印非阻塞 `[warn]`，同轮 `bti-shrink-urls --help` 为 `[ok]`；该警告不代表产物不可用。
7. **证据索引**：`reports/notes-test-inventory.md`（上游零测试清点）、`reports/notes-native-build.md`（原生 configure/make/install 逐字）、`reports/conan-create-log.md`（采信轮 clean 日志逐字，含 `Apply patch` ×3 与 `RUN: make -j1`）、`reports/w3-local-ci-log.md`（W3 本地 CI 逐字，L0/L1/L2/L4/L5 全 pass）、`reports/conan-verify-supplement.md`（G4/L2/L4/L5 人工补测）。
