# W3 本地 CI 模拟证据报告 — dbskkd-cdb 3

> **本文件替代原先随 PR 提交的 `reports/w3-local-ci.log`**：仓库审查规则 19（`.gitcode/review-memory.md` 类别三
> 第 19 条）把 `*.log` 列为 PR 禁止文件，故原始日志不再入库；本报告是当轮原始日志的
> **逐字摘录（非全文）**：下列各行区间与原始日志逐字相同（未合并、未改写、未重排）；
> 原始日志（295 行）留存任务私有目录（PR 之外）供复核：
> `$HOME/tmp/dbskkd-cdb-3/raw-w3-local-ci-2bccf9b.log`（日志 sha256：`dfe3d503cfb64af5f2b5d4acd8298a9dde5d32d74ca07cb6da40ace6ba6bea4b`，见文末复核命令）。
> 同目录 `conan-verify-report.md` 是工具生成的门禁摘要（保持原样，未手工编辑），其中
> 「📄 日志: …/conan-create.log」一行是该工具的固定输出，指向的日志按规则 19 不再提交，
> 对应证据以本文件为准。


## 1. 命令

```bash
zsh ci/conan/setup.sh
CI_PACKAGES=archives/d/dbskkd-cdb/3 zsh ci/conan/build_and_test.sh
```

## 2. 环境准备与任务接收（原文摘录）

```
$ setup.sh (RC=0)
[step] Conan environment setup...
[step] Conan version: Conan version 2.29.1
[step] Disabling conancenter (private CI, not needed)
conancenter: https://center2.conan.io [Verify SSL: True, Enabled: False]
[step] remote 已就绪: ohpcd
[step] Importing profile from /storage/Users/currentUser/ws/wt-dbskkd-cdb-3/ci/conan/profiles/ohos-aarch64
[step] Profile file available at: /storage/Users/currentUser/ws/wt-dbskkd-cdb-3/ci/conan/profiles/ohos-aarch64
[step] Conan environment ready ✅
[step]   remote: ohpcd
[step]   profile: ohos-aarch64
[step]   conan: Conan version 2.29.1


$ build_and_test.sh archives/d/dbskkd-cdb/3 (RC=0)
[step] Conan build + test pipeline (CI, no AI)
[step]   scan_root: archives
[step]   profile: ohos-aarch64
[step]   channel: (no channel — plain name/version)
[step] Validating package build timeout overrides...
[step] G0: Knowledge graph integrity check...
        [ok] G0: Knowledge graph integrity check passed (540 entries)
G0_RESULT=pass
[step] G0e: Root directory whitelist check...
        [ok] G0e: Root directory whitelist passed
[step] CI_PACKAGES received: archives/d/dbskkd-cdb/3
[step] Found 1 package(s) to build

━━━ Building: dbskkd-cdb/3 ━━━
[step] L0: Quality gate checks...
```

## 3. L0 质量门禁（原文摘录）

```
[step] L0i: Checking dependency availability in registry (R36)...
        [ok] dependency in registry: cdb/20251021
[step] L0j: Checking version collision with registry (R37)...
        [ok] version not in registry yet (first publish)
[step] L0k: Checking commands.json for CLI tools (R38)...
        [ok] commands.json valid (type=tool)
[step] L0m: Checking directory structure (R39/L0m-4/L0m-5)...
        [ok] L0m: directory structure valid
[ok] L0: All quality gate checks passed
```

## 4. 知识库与垃圾文件门禁（原文摘录）

```
KC_ERRORS=0
        [ok] KC: knowledge check passed
```

```
JC_ERRORS=0
        [ok] JC: no junk files detected
```

## 5. conan create、L1/L1e/L2/L4/L5 与汇总（原文摘录）

> 本段紧接 31 个用例的 `[ok]` 行；用例逐行原文见 `conan-create-report.md` 第 4 节
> （同一轮同一份 `test_package/test.sh` 输出，权威副本只存一处）。

```
[step] dbskkd-cdb test_package summary: TOTAL=31 PASS=31 FAIL=0
[ok] dbskkd-cdb test_package: all 31 cases passed

[ok] dbskkd-cdb/3 — conan create passed
[step] L1: Verifying test execution from conan create log...
[ok] L1a: test_package was executed by conan create
[ok] L1b: Test execution evidence found in log
[step] L1c: No upstream make check/ctest in log (may be in test_package only)
[step] L4: Scanning patches for dangerous functions...
[step] L5: Baseline artifact check...
[ok] L5: bin/ has content
[step] L1e: Destructive negative test (R34)...
        [sabotage] bin/ moved away
[ok] L1e: Negative test confirmed — test genuinely depends on dbskkd-cdb
[step] L2: Smoke test (version/help check)...
[warn] L2: dbskkd-cdb --version/--help failed (non-blocking)

L0_RESULT=pass: all checks passed
L1_RESULT=pass: test_package executed
L2_RESULT=skip: dbskkd-cdb version/help failed
L4_RESULT=pass: patches clean
L5_RESULT=pass: bin/ has content
[step] Generating ci-metadata.json...
[ok] ci-metadata.json written

━━━ Build Summary ━━━
  Total:   1
  Success: 1
  Failed:  0
  Pass rate: 100.0% (1/1)
[step] All packages built and tested successfully ✅
[step] Pre-download: conandata.yml 已还原为官方 URL
```

## 6. 结论

| 项 | 结果 |
| --- | --- |
| `setup.sh` | RC=0 |
| `build_and_test.sh` | RC=0 |
| `G0`（知识图谱完整性） | pass（540 entries） |
| `G0e`（根目录白名单） | pass |
| `L0`（结构完整性：L0i 依赖已发布 / L0j 首发无冲突 / L0k commands.json / L0m 目录结构） | pass |
| `KC`（知识检查） | pass |
| `JC`（无垃圾文件） | pass |
| `L1`（测试执行验证：`L1a` test_package 已执行、`L1b` 有编译/运行痕迹） | pass |
| `L1c` | 无上游 `make check`/`ctest`（上游无测试入口，符合台账） |
| `L1e`（破坏性反向验证） | pass —— 移走 `bin/` 后测试失败，确认测试依赖被测产物 |
| `L2`（smoke: `--version`/`--help`） | **skip** —— 本包无版本开关、无参数即进入协议循环，工具探测形态不适用；已按协议行为人工补测（见 `conan-verify-supplement.md`「L2 消费者实际行为」） |
| `L4`（补丁危险函数扫描） | pass |
| `L5`（产物基线） | pass（`bin/` has content） |
| Build Summary | Total 1 / Success 1 / Failed 0 / Pass rate 100.0% (1/1) |

`L2_RESULT=skip` 属工具探测形态限制，不计为通过；该组判据由 `test_package` 的真实协议
用例与 `conan-verify-supplement.md` 的人工补测共同覆盖。

## 7. 原始日志可复核性

原始日志（按规则 19 不入库）留存于任务私有目录，任何人可在设备上复核本报告的逐字摘录
（第 2/3/4/5 节的摘录块首行即日志区间首行，块内空行均来自原日志本身；第 1/7 节的 `bash` 块是复核命令记录、不属日志摘录，其内空行属排版）：

```bash
sha256sum "$HOME/tmp/dbskkd-cdb-3/raw-w3-local-ci-2bccf9b.log"
# -> dfe3d503cfb64af5f2b5d4acd8298a9dde5d32d74ca07cb6da40ace6ba6bea4b

sed -n '1,30p;31,39p;66,67p;93,94p;264,295p' "$HOME/tmp/dbskkd-cdb-3/raw-w3-local-ci-2bccf9b.log"
```

> **覆盖范围（非全文）**：原始日志 295 行，本报告摘录第 1-30、31-39、66-67、93-94、264-295 行
> 共 75 行（环境准备与任务接收、L0 质量门禁、KC/JC 结果行、create 结果与 L1/L1e/L2/L4/L5、
> Build Summary）；未摘录第 40-65 行（KC 知识库质量门禁明细）、第 68-92 行（JC 垃圾文件门禁
> 明细）、第 95-263 行（conan 构建明细与 31 个用例逐行 `[ok]` 输出，后者见
> `conan-create-report.md` 第 4 节，权威副本只存一处）。这些未摘录部分不含本报告任何结论性数字。
