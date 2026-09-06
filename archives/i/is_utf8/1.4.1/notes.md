# is_utf8 1.4.1 适配笔记

## 编译环境
- 构建系统: cmake（上游 `cmake_minimum_required(VERSION 3.15)`）
- 编译日期: 2026-09-03
- 编译器: clang 15.0.4 / clang++（OHOS aarch64，conan profile `ci/conan/profiles/ohos-aarch64`）
- 状态: built（conan-verify 全门禁通过；published 待合并后 release 流水线 upload 确认）
- worktree/分支: `wt-is_utf8-1.4.1` @ `feat/is_utf8-1.4.1`，基线 `f5131ee224`（upstream/main）

## 预检记录（W0 / W0b / R47）

| 项 | 命令/来源 | 结果 |
|---|---|---|
| 依赖发布检查 | `bash ci/scripts/preflight_check.sh is_utf8/1.4.1` | 通过（上游 is_utf8 无任何编译/运行依赖，requires 为空） |
| 制品仓同版本检查 (R35/R37) | `conan download is_utf8/1.4.1 -r=ohpcd --only-recipe` → `ERROR: ... [Remote: ohpcd]`（对照组 zlib/1.3.1 正常拉到 revision） | 制品仓无 is_utf8/1.4.1，首次适配 |
| 历史核验 W0b | `git log --grep is_utf8`、`archives/` 全树、SUMMARY.md | 本仓库无 is_utf8 归档/notes，无历史结论可迁移；archives/s/sponge 的 notes 仅提及自带同名内部副本，与本包无关 |
| CI 能力矩阵 | 语言/构建系统 = C++/CMake | clang/cmake/make 在 CI ✅（SKILL W0b 表），可正常立项 |
| 语言预检 R47 | `ohc-run.py lang-preflight is_utf8 1.4.1` | task=cpp, detected=cpp，exit 0；证据：build_system=cmake、project(is_utf8)、源文件 3 个 cpp 100% |
| 同分支 open PR | `gitcode_pr.py list-prs --source-branch feat/is_utf8-1.4.1` | 0 条 |

## 编译步骤（设备端实跑）

探索构建（native）：
```bash
CC=clang CXX=clang++ cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cd build && make -j2
ctest --output-on-failure     # 1/1 Test #1: unit ... Passed 1.54 sec
```
配方构建：`conan create archives/i/is_utf8/1.4.1 -pr:h/-pr:b=ci/conan/profiles/ohos-aarch64 --build=missing --user=ohpcd --channel=stable`（由 conan-verify G2 执行，全日志见 `reports/conan-create.log`）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|---|---|---|
| 1 | configure 阶段触发外网下载 | 顶层 `add_subdirectory(benchmarks)` 无条件执行，`cmake/import.cmake` 用 `file(DOWNLOAD https://github.com/simdutf/simdutf/archive/v2.0.9.zip)` 拉基准依赖，干净 CI 环境不可靠且违反门禁（外部下载） | 补丁 `0001-CMakeLists.txt.patch` 新增 `IS_UTF8_BUILD_BENCHMARKS` 选项（默认 OFF）并把 `add_subdirectory(benchmarks)` 包进 if；配方显式传 `=OFF`。非平台条件宏，guard: none |
| 2 | conan-init 骨架误判 autotools | init-build 阶段无 CMakeLists 感知，骨架按 autotools 模板生成 | 按已合并同类配方 `archives/f/fast_double_parser/0.8.1`（同作者 simdutf 系）重写为 cmake 配方；OHOS 下 `CMAKE_SYSTEM_NAME=Linux`/`CMAKE_SYSTEM_PROCESSOR=aarch64` 沿用其已验证写法 |
| 3 | make jobserver mkfifo `Operation not permitted` | HMDFS 不支持 mkfifo（`/tmp` 只读、任务 TMPDIR 亦受限），仅 GNU Make 作业池告警 | 无实际影响（构建与 ctest 全部成功退出码 0），如实记录不处理 |

上游测试无失败项，**无豁免、无跳过用例**。

## 测试用例数（以实跑输出为准）

上游（conanfile `build()` 内 `cmake.test()`，can_run 时执行）：
```
Test project .../build
    Start 1: unit
1/1 Test #1: unit .................. Passed   1.93 sec
100% tests passed, 0 tests failed out of 1
```
unit 程序内部断言（运行输出逐行核对）：
- `hard_coded()`：`Testing 5 good sequences.` + `Testing 37 bad sequences.` → **42 条**（条目数以运行时 printf 实测 5/37 为准；源码中多个条目由跨行相邻字符串字面量拼接而成，与数组条目数不一一对应）
- `brute_force()`：10000 个随机 UTF-8 串 × (1 次正校验 + 1000 次单 bit 翻转与参考实现差分) → **10,010,000 条**
- 上游合计 **10,010,042 条断言，1 个 ctest 测试程序**

test_package（消费者视角，`./is_utf8_test` 实跑）：
```
is_utf8 test_package: assertions=65820 failures=0
All is_utf8 consumer checks passed.
```
构成：1 字节全量差分 256 + 2 字节全量差分 65536 + 定向序列 24 + 64KiB SIMD 主循环 3 + 空输入显式 len=0 共 1 = **65,820 条**。
总断言 `65820` 由程序自计数打印，非静态估算。

与 `test_package/MANIFEST.yml`、PR 正文口径一致：upstream_test_count=1，test_package_test_count=1，assertion_count=10,075,862（10,010,042 + 65,820）。

## 断言可失败性验证（两次真实失败 + 恢复）

1. **test_package 期望值改错**：把 `{"\xed\xa0\x80", false}`（U+D800 代理对，合法期望=非法）临时改为 `true` 重编译运行：
   ```
   FAIL [targeted] at index 20
   is_utf8 test_package: assertions=65820 failures=1
   exit=1
   ```
   恢复期望值后复跑：`assertions=65820 failures=0`，exit=0。
2. **上游 unit.cpp 期望改错**：将 good 序列 `"abcde12345"` 替换为非法字节串 `"\xff\xfe"`（`.orig` 树不受污染，编译自 scratch 副本）：
   ```
   bug goodsequences[1]
   exit=1
   ```
   未变异对照：exit=0（即上文 ctest Passed 的同一二进制来源）。

## 验证结果

```bash
python3 scripts/ohc-run.py conan-verify is_utf8 1.4.1   # rc=0
# G1 配方完整性 PASS / G0 预构建风险 PASS / G2 conan create(干净源码+补丁+上游 ctest+test_package) PASS
# G3 系统同名库隔离 PASS（无 bin/，无系统同名冲突）
# G4 记 PASS 但带告警「无法找到程序包 ID」（conan-verify 按 user/channel 引用查缓存失败）；
# conan-verify 侧 L2/L4/L5 因同一原因显示「跳过（无 cache 路径）」——
# 这三道的真实证据来自 finish 的本地 W3（CI 同源 build_and_test.sh）：
#   L0_RESULT=pass: all checks passed
#   L1_RESULT=pass: test_package executed
#   L2_RESULT=skip: no bin/ dir（库包无 executable，合法跳过）
#   L4_RESULT=pass: patches clean
#   L5_RESULT=pass: lib/ has content
# 日志: reports/conan-verify-report.md, reports/conan-create.log, reports/w3-local-ci.log
```
产物：`lib/libis_utf8.a`、`include/is_utf8.h`、`lib/cmake/is_utf8/*`（上游导出 config），licenses 收 MIT/BOOST/APACHE 三份。无 bin/，库类型，无需 commands.json（R38）。

## 补丁

- `patches/0001-CMakeLists.txt.patch`（+4/-1）：新增 `IS_UTF8_BUILD_BENCHMARKS`（默认 OFF）并守卫 `add_subdirectory(benchmarks)`。无 `__OHOS__` 等平台宏（R8/quality#6），全平台行为一致（默认关基准，显式 ON 可恢复）。

## 注意事项

- 上游只提供静态库；下游如需动态链接需自行处理（本包按 static-library 交付）。
- `search-url` 工具给出的 waterlan.home.xs4all.nl 候选为个人镜像，按 R39 弃用，采用 GitHub 官方 tag 归档 `v1.4.1.tar.gz`。

## W4 独立审计与返修记录（2026-09-03）

首轮 W4 审计（独立只读子任务，输入含 code-style.md/review-memory.md 全量规则）判定
**verdict=fail（P0=0/P1=1/P2=4/P3=5）**。全部有效意见已在本轮修复并随提交入库：

| 级别 | 意见 | 处置 |
|---|---|---|
| P1 R39 | `conandata.yml` 的 sources.url 被本地 W3 的 `build_and_test.sh` "Mirror fallback" 步骤改写为 `gh-proxy.com` 优先列表，脚本虽打印「已还原为官方 URL」但实际还原到改写版 | 还原为单条官方 GitHub URL（sha256 不变）；教训：跑完 finish/W3 同源脚本后必须逐字段核对 conandata.yml，不能相信脚本自述。该脚本还原逻辑缺陷属框架问题，另行上报（本 PR 不触碰 ci/） |
| P2 | conanfile.py 残留 `url = ""  # CI fills this` 模板占位 | 填为 `https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos`（与 477 个已合并配方一致） |
| P2 | `patch_type: "conan"` 不符合项目固定值 | 改为 `"portability"`（corpus 3500+ 例） |
| P2 | 软件级 manifest.yaml 缺必须字段 | 按 templates/manifest-software.yaml 补齐 display/description/category/license/build_system/ohos_adaptation，versions 改映射式 |
| P2 | notes/README 把 conan-verify 的 G4 告警与 L2/L4/L5「跳过（无 cache 路径）」写成全部通过 | 已改为如实口径：真实通过证据来自本地 W3 同源脚本（L0/L1/L4/L5=pass、L2=skip 合法），见上文「验证结果」 |
| P3 | test_package/conanfile.py 缺文件头 | 补 shebang + docstring |
| P3 | 版本级 manifest patch_classification 被 finish 的 refresh-patch 步骤重置回工具默认（`platform_only: True`/`guard: 'pending'`，与补丁实际不符） | 重新回填 `type: portability`/`platform_only: False`/`guard: 'none'`（本 PR 后续不再重跑 finish，避免再次覆盖） |
| P3 | notes.md 末尾孤立 `---` | 已移除 |
| P3 | test_package 固定 C++11 覆盖 profile 的 cppstd=17 | 合理拒绝：is_utf8 公开 API 自 C++11 起提供，消费者测试取库自身标准，与已合并 fast_double_parser test_package 同口径；不影响被测库正确性 |

审计对欺骗类（R34/R9/R8/R19/R40）、W2 原子性、sha256 真值、断言计数与变异可失败性均做了独立复核并确认清白（含设备端重新下载 tarball 实算哈希、直接运行三个测试/变异二进制）。

复审轮次：第二轮审计员在完成独立验证（重下官方 tarball 实算 sha256、官方源码实套补丁、独立编译运行 unit/tp/破坏性 stub 对照组）后异常终止未出结论；第三轮独立审计对 `599b192ea8` 判 **verdict=pass（P0=0/P1=0/P2=1/P3=2）**——首轮 P1+P2 全部证实修复，欺骗类全清白。第三轮新发现唯一实质 P2：知识草稿 `.md` 第 33 行仍残留「G0–G4、L2/L4/L5 全 PASS」旧口径 → 已在后续提交修复（同口径文案）；两项 P3（reports 日志不入库的可核验性说明、本地 W3 脚本仍会再次污染 conandata 的框架回归风险）分别为仓库规范既成事实与框架侧问题，本 PR 内以本节文字记录。审计报告全文见 `reports/audit-result.json`（其 `reviewed_commit` 为修复前 SHA `599b192ea8917ac80763f700708896fee110970b`，P2 文案修复在其后的提交，配方/测试/补丁文件零改动）。审计明确提示：**合并前不得再跑 finish/build_and_test.sh**（会再次改写 conandata.yml 为镜像列表），后续如需重验一律用直接 `conan create`。

---

**编译结束**: 2026-09-03 20:16
**最终状态**: built
