# mmh 0.4 — 测试报告（R51 三步法）

## 一、环境

| 项 | 值 |
|---|---|
| 平台 | HarmonyOS PC（aarch64），宿主 `uname -s` = `HarmonyOS` |
| 编译器 | OHOS clang 15.0.4（`/data/service/hnp/bin/clang`） |
| Conan | 2.29.1（OHOS 适配版） |
| Profile | `ci/conan/profiles/ohos-aarch64`（os=OHOS/6.0，arch=armv8，libc++，cppstd=17） |
| 依赖 | `ncurses/6.6`（静态，制品仓二进制；仅 `libncursesw.a`） |
| 构建 | `conan create . -pr:h=… -pr:b=…`，rc=0（2026-10-04 真机） |

## 二、上游测试清点（R51 第 1 步：先清点）

| 清点项 | 结果 | 证据 |
|---|---|---|
| 套件入口 | `test/runalltests` → `test/runtest` 逐例驱动 | `head -40 runalltests` |
| 用例目录 | 28 个 | 设备 `find tests -mindepth 1 -maxdepth 1 -type d \| wc -l` = 28 |
| 用例脚本 | **57 个**（`test-*`，排除 `*~`） | 设备 `find tests -name 'test-*' ! -name '*~' -type f \| wc -l` = 57 |
| SKIP 语义 | 上游 `test_skip()` 置 rc 120；`runtest` 映射为 SKIP | `common.sh:12-15`、`runtest:62-66` |
| 环境缺口 | 无 valgrind / 无 UTF-8 locale / 无 ed | 逐例日志（§三.3） |

**N = 57。** 逐例明细与驱动差异见 `reports/upstream-test-run.md`。

## 三、实际运行验证（R51 第 2/3 步：运行 + 回填实测）

### 3.1 test_package（`archives/m/mmh/0.4/test_package/`）

真机 `conan create` 内的消费者测试（`conanfile.py` 依次以 `bash` 驱动
`test.sh`、`test_e2e.sh`——OHOS 内核拒 shebang 脚本 execve）：

| # | 用例（test.sh 冒烟） | 断言 | 结果 |
|---|---|---|---|
| 1 | `mhparam -Version` | 输出含 `mhparam -- mmh-0.4` | ✅ PASS |
| 2 | `mhparam version` | 输出 `mmh-0.4` | ✅ PASS |
| 3 | `folder -create +smoke` | 落盘 `mail/smoke` | ✅ PASS |
| 4 | `folders` | 列出 `smoke` | ✅ PASS |

| # | 用例（test_e2e.sh 完整消费者端到端） | 断言 | 结果 |
|---|---|---|---|
| 1/8 | `inc -file` 投递 mbox | `inbox+` 2 条消息（1-2），cur=1 | ✅ PASS |
| 2/8 | `scan` | 双 Subject 正确显示 | ✅ PASS |
| 3/8 | `pick -subject multipart` | 命中 2 号消息 | ✅ PASS |
| 4/8 | `mhlist` | 列出 `application/octet-stream` 部件 | ✅ PASS |
| 5/8 | `mhstore -auto -part 2` | 提取 base64 附件并校验内容逐字节相等 | ✅ PASS |
| 6/8 | `refile -src` | 消息移入 `archive` | ✅ PASS |
| 7/8 | 归档复查 | `archive+` 1 条消息（1-1） | ✅ PASS |
| 8/8 | 终态复查 | `inbox+` 1 条（2-2），cur=2 | ✅ PASS |

日志尾部：`== test.sh: ALL-PASS ==`、`== test_e2e.sh: ALL-PASS ==`。

### 3.2 上游测试套件（真机等效驱动，全量 57 例）

```sh
sh $HOME/mmh-fix/run-mmh-suite.sh
# === FINAL: TOTAL=57 PASS=49 SKIP=6 FAIL=2 MODE=runtest ===
```

| 指标 | 值 |
|---|---|
| 上游测试总数 N | **57**（清点证据见第二节；实测驱动枚举数一致） |
| 实际运行数 N′ | **57**（全量执行，无遗漏） |
| 通过 / 失败 / 跳过 | **49 / 2 / 6**（通过率 49/57 = 86.0%） |
| 2 例 FAIL | `anno`（测试自造硬链接夹具，HMDFS EPERM 不可构造）、`rcvstore`（HMDFS 权限位归一 0660，`find -perm 0600/640` 必然落空）——均为平台文件系统语义归因，测试脚本未修改，证据见 `reports/upstream-test-run.md` §四 |
| 6 例 SKIP | 全部经上游 `test_skip()`（rc 120）：缺 valgrind ×1、上游自跳 ×1、缺 UTF-8 locale ×4 |
| 驱动差异 | D1-D7 全部显式披露（`reports/upstream-test-run.md` §二）；其中 ed 缺口以真实最小实现垫片（D7）修复 → `test-longlines` 由 FAIL 转 PASS 并留档前后日志 |

### 3.3 汇总（禁占位符，均为实测）

| 指标 | 值 |
|---|---|
| 本库 test_package 用例数 | **12**（冒烟 4 + 端到端 8） |
| test_package 通过 / 失败 / 跳过 | **12 / 0 / 0** |
| 其中完整消费者端到端用例 | 1 个（`test_e2e.sh`，8 例全链路；MANIFEST.`consumer_case_count`=1） |
| `conan create` | rc=0（真机 2026-10-04，含 test_package 双脚本 ALL-PASS） |
| `verify-build` 质量报告 | PASS（G1 ✅0/0/0 · G2 ✅0/⚠️1/❌0【包内无二进制提示，非阻断】 · G3 ✅0/0/0 · G4 ✅0/0/0）；输出见 `reports/quality-report.md` |

> 注：`quality-report.md` 为 `ohc-run.py verify-build` 原样输出；其 G4 明细行
> 「补丁: 9 个」是工具既有 glob 口径（`000*.patch` 仅命中 0001-0009，未计
> 0010-0013），实际补丁 13 个（`ls patches/0*.patch | wc -l`=13）；该口径在
> 主干仓多补丁包报告中一致存在（7 处「补丁: 9 个」，含 14 补丁的包），非本包异常。

## 四、平台归因实测明细（anno / rcvstore）

### 4.1 HMDFS 拒绝硬链接（anno 用例夹具不可构造）

- 用例日志（原样）：`ln: cannot create hard link from '…/Mail/inbox/8' to '…/Mail/inbox/8.link': Operation not permitted`
- 独立探针：`ln f f.link` → `Operation not permitted`；该结论同时是 D6
  （fcntl 锁）、补丁 0007（入箱回退）、安装 `LN=cp` 三个适配决策的共同根因。

### 4.2 HMDFS 权限位归一 0660（rcvstore 断言必然落空）

| chmod 请求 | 实得模式（ls -l） | `find -perm 0600` | `find -perm 0660` |
|---|---|---|---|
| `chmod 600 f` | `-rw-rw----`（0660） | 落空 | 命中 |
| `chmod 640 f` | `-rw-rw----`（0660） | 落空 | 命中 |

- 用例日志（原样）：`find …/inbox/23 -perm 0600 failed`、`…/inbox/24 -perm 640 failed`
  （文件存在，仅精确权限匹配不可满足）。

## 五、结论

- 上游 57 例全量执行：49 PASS / 6 SKIP（合法）/ 2 FAIL（平台文件系统语义
  归因，证据齐备、测试脚本零修改）。
- 适配后消费者用例 12/12 全过（含鸿蒙特有端到端 8 例，走通 inc→scan→pick→
  mhlist→mhstore→refile 完整邮件处理链路）。
- 质量门禁 `verify-build` Verdict PASS。
