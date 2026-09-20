# disk-filltest 0.8.2 适配笔记

## 任务

* 平台任务：#7153 `disk-filltest 0.8.2`（Route A 普通适配，分支 `feat/disk-filltest-0.8.2`）。
* 上游：`bingmann/disk-filltest`，tag `v0.8.2`，GPL-3.0-or-later，单个 `disk-filltest.c`（545 行）+ 最简 Makefile。
* 官网：`https://panthema.net/2013/disk-filltest/`。

## W0 依赖发布检查

* 上游仅包含 C 标准库与 POSIX 头文件：`errno.h fcntl.h getopt.h inttypes.h limits.h stdio.h stdlib.h string.h sys/time.h time.h unistd.h`（`sys/statvfs.h` 仅在非 MSVC/MinGW 分支包含）。
* 结论：**无第三方编译期/运行期依赖**，`requires()` 为空，不存在依赖链，W0 无需 `conan download` 任何包（PF4 依赖闸对空 requires 直接通过）。
* `lang-preflight`（R47）：`task=cpp, detected=c`，属 C/C++ 兼容族，判定继续适配；证据 `build_system=make`、源文件 1 个（c:1）占比 100%。

## R51 上游测试清点

| 项目 | 结果 | 证据 |
| --- | --- | --- |
| 测试目录 | 不存在 | `.orig` 仅 6 个上游文件：`disk-filltest.c`、`Makefile`、`README`、`COPYING`、`disk-filltest.1`、`.travis.yml`；按 `*test*`/`*check*` 检索除程序名外无命中 |
| `make check` 目标 | 不存在 | Makefile 目标为 `all`、`disk-filltest`、`disk-filltest.1.gz`、`install`、`install-bin`、`install-man`、`clean` |
| ctest / pytest 注册数 | 0 | 无 CMakeLists.txt、无 ctest/pytest 配置 |
| 上游 CI | 仅构建 | `.travis.yml` 的 `script:` 只有 `- make` |
| **上游用例数 N** | **0** | 以上四项，故无"上游测试通过率"可填 |

上游无可运行用例，按规则补写适配回归测试（见下）。

## 适配决策

1. **零源码补丁**：OHOS clang 15.0.4 + musl 下使用上游默认 `CFLAGS`（`-O3 -W -Wall -ansi`）直接编译通过，`patches: []`，不创建 `patches/` 目录（规范：有则保留，无则不创建）。
2. **不使用 `make install`**：上游 install 目标依赖 GNU `install` 与 `gzip`（生成 man 页 `.gz`），且把 `/usr/local` 作为默认 `prefix` 写在 Makefile 里；实测设备 PATH 中 `install`/`gzip` 均不可用（仅 `/system/bin` 存在），CI worker 与设备两侧行为不一致。改由配方 `package()` 用 `self.package_folder` 拼接路径复制 `bin/disk-filltest`、`share/man/man1/disk-filltest.1`、`licenses/COPYING`；man 页以**未压缩**形式安装（设备无 gzip，且避免构建机差异），`copy()` 保留源权限位以规避 HMDFS `chmod` 不生效（E046）。
3. **官方多源回退（R39/PF7）**：`conandata.yml` 声明同一 release 的两个官方发布物并各自校验 sha256 —— GitHub tag 归档（与 Debian `disk-filltest_0.8.2.orig.tar.gz` 同哈希）与作者官网 tarball。原因：设备侧 `github.com` 直连超时而 `panthema.net` 可达，CI worker 侧相反；两个归档内部 6 个文件逐个 sha256 相同，仅打包封装不同。`source()` 按声明顺序尝试，且**每次尝试前清空源码目录**，避免"下载成功但解压中断"留下混合树。
4. **补丁应用位置**：`apply_conandata_patches(self)` 放在 `build()` 而非 `source()`，与已合入的 abduco 0.6 参考包一致——本包 `patches: []`，该调用仅为保持框架约定的空操作。
5. **编译器来源（R33）**：`CC` 取自 Conan conf `tools.build:compiler_executables`，缺该键时回退 `self.settings.compiler`，与 profile 声明不一致时输出告警；命令行以 `CC="..."` 加引号拼接以兼容带参数的启动器。不裸用 shell 环境变量。
6. **命令行工具（R38）**：`package_type = "application"`，软件级 `commands.json` 就位；未上传制品仓前 `binary: false`。
7. **build_type 语义**：上游 Makefile 固定使用自身 `CFLAGS`（`?=` 语义下由环境决定是否覆盖），因此 Conan `build_type` 不改变优化级别；实测构建机与设备两侧均未注入额外 `CFLAGS`，产物一致。

## 共享设备安全约束

disk-filltest 的语义是"把路径写满"，本设备三人共用，因此全部验证（含 `conan create` 内的 test_package）一律：

* 只在临时目录内运行（`-C <scratch>`，脚本 `finally` 中 `rm -rf`）；
* 每次具备写盘能力的调用同时带 `-S 1 -f 1`（单文件 1 MiB、最多 1 个文件）上界，只读复验用 `-r`；
* 不使用 `-N`（跳过校验的擦盘模式）与 `-R`（重复填充）；
* 实测残留 0 文件、峰值占用 1 MiB；未对 `/data`、他人 worktree 或任何非本次临时目录执行填充。

## 验证结果

* `conan-verify disk-filltest 0.8.2 --profile ohos-aarch64-device` → G0/G1/G2/G3/G4 全部 PASS（exit 0）。
* 本地 CI 门禁（与平台同一脚本 `ci/conan/build_and_test.sh`，`CONAN_PROFILE=ohos-aarch64-device`）→ exit 0、Pass rate 100%：L0/L1/L1b/L1e/L4/L5 PASS，L2 为**非阻塞 skip**（该级只尝试 `--version`/`--help` 长选项，而上游 `getopt` 串为 `hs:S:f:ruUC:NR:V` 无长选项；本包不改上游 CLI 行为，短选项语义由 T1/T2 断言覆盖）。
* test_package：7 个功能用例 / 10 条断言全部通过（10/10），`assertion_count: 10` 与脚本内 `check()` 调用数一致；不使用 `can_run()` 提前返回，故 L1e 破坏性反向验证（移走 `bin/`）确会失败，已实测。
* 本包完整门禁日志与产物清单贴在 PR 正文「验证结果」小节，随评审可核；`reports/` 下仅 `audit-result.json` 入 PR（评审规则 19：`test-report`、`*.log` 等禁止入 PR），其余为本地工具产物。
* 状态 `built`：conan-verify 通过但未执行 `conan upload`，发布由 release 流水线负责。

## 已知框架行为（非本包引入）

* `conan-verify`/`finish`/`ci/conan/build_and_test.sh` 在设备侧会按 E017 预防逻辑对**临时副本**改写源码 URL 走镜像下载，运行后还原 `conandata.yml`；本包提交内容中的 URL 字段（`conandata.yml`、两级 `manifest.yaml`、`commands.json`）不含任何镜像域名，已用 `git grep -nE "ghfast|ghproxy|gh-proxy|cnb\.cool" -- archives/d/disk-filltest` 复核，唯一命中是本笔记中描述该现象的文字行。
* `finish` 的 step5b/step8 告警源于仓库存量（历史知识草稿完整性、`E219/E253/E305.kv` 字段缺失、`gen_summary` 的 `'str' object has no attribute 'append'`），与本包无关；`submit 就绪预检` 四项均为 ✅。

## 结束标记

**编译结束**: 2026-09-19 20:40
**最终状态**: built
---

**编译结束**: 2026-09-19 20:43
**最终状态**: built
