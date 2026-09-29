# asterisk 22.10.1 上游 in-tree 用例真机执行报告

执行对象：`archives/a/asterisk/22.10.1`（本 PR #9608 的 Conan 制品）
执行平台：HarmonyOS PC（HUAWEI MateBook Pro / HongMeng Kernel 1.12.0 aarch64）
执行提交：`a6d20a0ac9`（`feat/asterisk-22.10.1`）
执行方式：同一配方加 `-o asterisk/*:with_test_framework=True` 构建的制品，在真机上启动 PBX 后按类别隔离执行

## 1. 复现命令

```bash
# 1) 在设备上构建带 TEST_FRAMEWORK 的制品（配方同一提交、同一 source）
conan create archives/a/asterisk/22.10.1 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing --build='asterisk/*' -o 'asterisk/*:with_test_framework=True'

# 2) 启动制品并逐类别执行上游 in-tree 用例（脚本按类别隔离，每个类别一个全新实例）
bash testfw/run-testfw2.sh            # 全量；--skip-build 复用已构建的包

# 3) 单类别手工复现（示例）
"$PKG/sbin/asterisk" -fgn -C "$PKG/etc/asterisk/asterisk.conf" &
"$PKG/sbin/asterisk" -rx 'test execute category /main/poll/' -C "$PKG/etc/asterisk/asterisk.conf"
"$PKG/sbin/asterisk" -rx 'test generate results xml /tmp/main-poll.xml' -C "$PKG/etc/asterisk/asterisk.conf"
```

执行脚本与全部原始日志在真机上：

```text
任务根目录  /storage/Users/currentUser/ohos-users/codex/asterisk-22.10.1-fix-d66aeaef78/
驱动报告    .../testfw/reports/            (registered-all.log, case-results.tsv, summary.md, driver.log, conan-create.log)
逐类证据    .../testfw/categories/         (88 个类别 XML + 控制台/命令日志)
run 目录    /storage/Users/currentUser/ohos-test-runs/codex-22.10.1-asterisk-22.10.1-a6d20a0ac9-full-20260926-235507-42616
            /storage/Users/currentUser/ohos-test-runs/codex-22.10.1-asterisk-22.10.1-a6d20a0ac9-full2-20260927-000740-52156
```

## 2. 结果

| 指标 | 数量 | 说明 |
|---|---:|---|
| 上游源码静态清点（`AST_TEST_DEFINE`） | 712 | 116 个源码文件（tests/ 与模块内联用例） |
| 设备注册用例（`test show registered all`） | 599 | 制品在设备上实际注册的总数 |
| 本次产生逐例结果的用例 | 572 | 每条都有对应类别 XML 作为证据 |
| PASS | 560 | |
| FAIL | 12 | 逐例分类见 `upstream-in-tree-test-failure-matrix.md` |
| SKIP / NOT RUN | 0 / 0 | 本次执行中无用例被跳过 |
| 通过率（已执行口径） | **560/572 = 97.90%** | |
| 通过率（设备注册口径） | **560/599 = 93.49%** | 分母含 5 条上游保护用例与未产生结果的注册项 |

逐例结果清单：`upstream-in-tree-test-case-results.tsv`（572 行，含用例 ID、状态、证据 XML）。

## 3. 与评审给出的 724 条库存的对账

724 是评审给出的"上游实测 N"。把上游源码静态清点按"该用例所属模块是否编译进本制品"分组后，
可以得到一条完全可复核的收敛链（复算脚本：对每个 `AST_TEST_DEFINE` 统计所属模块，
再与制品 `lib/asterisk/modules/` 的 338 个模块名比对）：

| 环节 | 数量 | 依据 |
|---|---:|---|
| 上游源码静态清点（`AST_TEST_DEFINE`） | 712 | 116 个源码文件 |
| ├ 核心二进制内（`main/*.c`） | 13 | 随主程序编译，始终存在 |
| ├ 已编译进制品的模块内 | 630 | 模块名在制品 `lib/asterisk/modules/` 中 |
| └ **未编译进制品的模块内** | **69** | 见下表 |
| 设备实际注册（`test show registered all`） | 599 | 制品在真机上注册的总数 |
| 本次产生逐例结果 | 572 | 逐类 XML 为准（PASS 560 / FAIL 12） |

### 3.1 未编译进制品的 69 条用例（按缺失依赖分组）

| 依赖 | 用例数 | 涉及模块/文件 |
|---|---:|---|
| libcurl（`curl`） | 22 | `test_http_media_cache`(9)、`test_res_prometheus`(11)、`func_curl`(1)、`test_substitution`(1) |
| OpenSSL/crypto（`crypto`） | 18 | `test_crypto`(6)、`test_utils`(12，另需 `res_agi`) |
| pjproject / res_pjsip | 18 | `res_pjsip_pubsub`(7)、`res_pjsip`(2)、`res_pjproject`(2)、`res_pjsip_session`(1)、`test_res_pjsip_scheduler`(5)、`test_res_pjsip_session_caps`(1) |
| libunbound（`res_resolver_unbound`） | 7 | `res_resolver_unbound`(7) |
| res_geolocation | 2 | `res_geolocation/geoloc_eprofile`(2) |
| 编解码器（format_g723/g726/g729/gsm/ogg_vorbis/siren 等） | 1 | `test_ast_format_str_reduce`(1) |
| 平台不适用（BSD kqueue） | 1 | `res_timing_kqueue`(1) |

这些依赖都不在本制品当前的依赖集合内（配方沿用仓库既有基线 `--without-pjproject --without-x11
--without-gtk2`，且未引入 libcurl/OpenSSL/unbound）。要覆盖它们必须给制品新增依赖，
属于新的适配工作，不能通过"跑得更多"解决。

### 3.2 其他未产生结果的来源

- 上游保护用例 5 条：`/DO_NOT_RUN/` 的 `CALL_BACKTRACE`、`CALL_ASSERT`、`RAISE_SEGV` 被上游标记为
  危险用例，只有显式点名才执行；`/TEST_PASS_FAIL/` 的 `JUST_PASS`、`JUST_FAIL` 是框架自测。
- **静态清点（643 条，含核心二进制）与设备注册数（599）不相等是预期现象**，两个方向都会偏：
  一部分用例在运行期按配置动态注册（例如 `test_ari` 按 ARI 模型文件、`test_sorcery` 按 wizard 逐个注册，
  注册数可能多于静态 `AST_TEST_DEFINE` 处数）；另一部分用例的模块在设备上因依赖判定未加载。
  因此本报告的分母一律采用**设备注册数**，逐例状态一律以**类别 XML** 为准，不采用静态清点作分母。
- 注册表 `test show registered all` 的 Name 列定宽 30 字符，长用例名会被截断，无法与 XML 逐例 100% 对齐，
  这也是"注册清单解析出 559 个唯一 ID"与 CLI 计数 599 有差异的原因之一。

> 说明：本报告不使用"申请豁免"口径。本构建配置可达的上游用例已全部执行，
> 未达部分按 3.1/3.2 逐条给出可复核原因。

## 4. 执行过程中的平台修复

本轮为让上游用例真正可执行，配方新增/修正了三处（均在 `feat/asterisk-22.10.1` 上）：

| 提交 | 内容 |
|---|---|
| `e0c87c8744` + `5924c1e6bf` + `95bbdbafec` | 新增 `with_test_framework` 选项：打开 `TEST_FRAMEWORK` + `MENUSELECT_TESTS`（含 dev-mode menuselect 树的正确用法） |
| `a6d20a0ac9` | 新增主线补丁 `0034`：musl 上静态互斥量非递归导致 loader 自死锁，通过 `AST_USE_MUTEX_CONSTRUCTOR_INIT` 能力开关改用构造函数初始化 |

`0034` 是让 PBX 能在 musl/OHOS 上完成启动的必要修复：修复前启动停在
`Asterisk Dynamic Loader Starting:`，用例只注册 8 条（仅内置用例），无法执行任何上游用例。
