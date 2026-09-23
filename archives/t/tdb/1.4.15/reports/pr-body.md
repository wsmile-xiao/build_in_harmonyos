- **三方库名称**：tdb（Samba trivial database）
- **上游版本**：1.4.15
- **上游仓库地址**：https://tdb.samba.org/（发布源 `https://download.samba.org/pub/tdb/`）
- **适配路径**：路径 A（基础适配）+ 路径 B（知识库扩展，见下方"路径 B 知识贡献说明"）
- **使用知识库**：E002（/tmp 只读）、E046/E047（HMDFS 权限归一化，chmod 不生效）、E192（musl robust mutex，构建开关层自动探测）、E339（bundled waf 版本核对——本包内置 waf 2.1.6 未触发）、E490/E528（autotools 专项，waf 构建不适用）；新增知识草稿 2 对（见下方"路径 B 知识贡献说明"）

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 37 | 来源：`wscript` 的 `tdb1_unit_tests` 列表（TAP 接口 `test/tap-interface.h`），基础读写/事务/遍历/恢复/加锁/deadlock 等 |
| 集成测试 | 2 | 来源：`test/test_tdbbackup.sh`、`test/test_tdbdump.sh`（waf `testonly` 直接执行） |
| 其他测试 | 1 | `tools/tdbtorture.c` 多进程并发压力测试（waf `testonly` 末段执行） |
| **合计** | **40** | 另有可选的 python 绑定测试 `python/tests/simple.py`（45 项，需 pytdb），本包未启用（见补充说明） |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 37 | 不变 | 设备真机全量执行，37/37 通过 |
| 集成测试 | 2 | 不变 | 设备真机全量执行，2/2 通过 |
| 压力测试 | 1 | 不变 | `testsuite returned 0` |
| 鸿蒙特有测试（消费者） | 1 | **新增** | `test_package` 消费者程序真实调用公开 API（tdb_open/tdb_store/tdb_fetch/tdb_delete/tdb_close）共 9 处断言；另执行包内 `tdbdump` 读取消费端创建的数据库 |
| **合计** | **41** | **+1** | 上游 40 程序全保留执行 + 新增消费者测试 1 |

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例
- [ ] **是**，存在对上游测试用例的修改（请在下方逐条说明）

> 说明：全部补丁均不触碰测试用例本身。补丁 0002 仅在 `--disable-python` 配置下给
> `wscript` 的 `testonly` 增加守卫（显式跳过 pytdb 绑定测试并打印原因），上游 C
> 测试的注册、执行与断言逻辑保持原样。

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [x] **否**，上游已有测试用例覆盖（C 测试套件 40 程序全量执行）
- [ ] **是**，上游无测试用例，适配后补全了测试（请在下方说明）

## 验证结果

- 编译状态：通过（`conan create` 全量验证 EXIT=0，profile `ohos-aarch64-device`，含 `make test` + test_package）
- 上游测试用例通过率：**40/40（100%）**（37 TAP 单测 + 2 shell 集成 + tdbtorture；逐类计数见 `reports/test-report.md`）
- 新增测试用例通过率：**1/1（100%；9 处断言）**

## 路径 B 知识贡献说明

- **新增草稿**（与归档适配同一原子 PR 交付）：
  - `knowledge/drafts/DRAFT-11055-wafsamba-standalone-build-policy.kv` / `.md`
  - `knowledge/drafts/DRAFT-11055-waf-testonly-execution-accounting.kv` / `.md`
- **知识主题 1（主）——Samba wafsamba 系独立库在 OHOS 的构建范式**：`PYTHON=python3` 驱动的**原地** waf configure/make（`IN_LAUNCH_DIR` standalone 判定、包装脚本的 `PYTHONHASHSEED`/`WAF_MAKE` 守卫、conan 集成的 `--prefix`/`--disable-python`）；`lib/replace` **沙箱必失败强制运行探针**的诚实处置——mkstemp 探针硬编码 `/tmp`（E002）且断言 0600（HMDFS 归一化为 0640，E046），上游标 `mandatory=True` 直接中断 configure，修法为改非致命并接受 `not found` 走内置替代实现（禁止放宽断言/硬编码设备路径/`__OHOS__` 宏）；**python 绑定决策树**——`python3-config --embed` 携带平台不存在的 `-lintl` 致 pyembed 探针 fatal，纯 C 库用官方 `--disable-python` 规避，需要 pytdb 时经 waf `python_cross_compile()` 旁路注入正确链接参数。
- **知识主题 2（主）——waf `testonly` 测试套件在 OHOS 的执行与对账**：shell 集成测试 + 37 个 TAP 二进制 + `tdbtorture` 的单入口执行结构；逐项通过率对账方法（`...tdb1-` 计数须与 `wscript` 列表长度一致）；`--disable-python` 下上游仍会把 python3 记入 `python_interpreters` 而误跑 pytdb 绑定测试（`import tdb` 失败致整套测试误判红），修法为 testonly 加 `env.disable_python` 守卫**显式跳过并打印原因**（不得注释/静默跳过或伪造通过），PR 中如实标注"可选绑定测试未启用"。
- **触发实例**：tdb 1.4.15 真机适配（本 PR）。configure 两处 fatal 中断（mkstemp 探针、pyembed `-lintl`）与 `make test` 的 python 测试误判红均有原始日志与逐层定位记录（见 `notes.md`）。
- **查重结论与新增价值**（`draft-review` 预审，knowledge/graph/index.tsv 766 条 + 795 草稿）：
  - 主题 1：质量预检 signature/root_cause/rec 全 ✅；TOP 相似度 E357=0.11、**E339=0.11**（sig=0.0、kw=0.04、cat=0.5——仅类别词重合，错误面与修法均不同）、E320=0.04、E192=0.01 → **预审建议 create（疑似新知）**。wafsamba/talloc/ldb/tevent 的构建体系面此前无任何正式条目或草稿。
  - 主题 2：TOP 相似度 E318=0.08（sig/kw 全 0）→ **预审建议 create（疑似新知）**。
  - **与 E339 的差异**：E339 为旧版 bundled waf 的 `imp` 模块级崩溃修法；本包实测内置 waf 2.1.6 已带 py3.12+ shim、**未触发**（草稿中以"版本核对项"如实记录），本条增量为探针处置/绑定决策/测试执行层，E339 正交。
  - **与 E192 的差异**：musl robust mutex 本包由 wafsamba 自动探测关闭 `USE_TDB_MUTEX_LOCKING`（无需补丁），草稿仅作为决策树一支引用，不重复其条件编译修法。
- **验证证据**：`reports/test-report.md`、`reports/w3-local-ci.log`（37 TAP + 2 shell + tdbtorture 全过、python 测试显式跳过、消费者 9 断言 + 包内 tdbdump 实跑）、`reports/audit-result.json`（W4 独立审计 pass，0 P0/P1）。
- **知识库扩展 Issue**：不适用（Issue 机制已废弃，按任务说明执行）。

## 补充说明

### 构建系统与关键适配点

tdb 1.4.15 使用 **Samba waf（wafsamba）** 而非 autotools/cmake：

1. 配方以 `PYTHON=python3 ./configure --prefix=<pkg> --disable-python && make -jN && make test`
   直调上游包装脚本（原地构建，`--prefix` 指向包目录；`PYTHON` 由配方显式传入，R33）；
2. **补丁 0001**：`lib/replace` 的 `HAVE_SECURE_MKSTEMP` 运行探针硬编码写 `/tmp`
   （鸿蒙只读）并断言文件权限 0600（HMDFS 归一化为 0640），在鸿蒙**必失败**且上游标
   `mandatory=True` → configure 中断。改为非致命后检查如实报 `not found`，
   `lib/replace` 自动启用内置 mkstemp 替代实现（不放宽断言语义、不硬编码设备路径）；
3. **musl robust mutex**：`pthread_mutexattr_setrobust` 未声明，configure 自动探测
   关闭 `USE_TDB_MUTEX_LOCKING`（无需显式传 `--disable-tdb-mutex-locking`），
   37 个单测（含 mutex 系列）在无 robust mutex 模式下全部通过；
4. **python 绑定（pytdb）未启用**：平台 `python3-config --embed` 输出含平台不存在的
   `-lintl`，pyembed 探针无法链接，故以官方 `--disable-python` 构建纯 C 库；
   **补丁 0002** 让 `make test` 在禁用时不误跑 python 绑定测试（显式打印跳过原因）。
   上游 45 项 python 绑定测试未运行（特性未启用，非"上游无测试"），已在测试报告如实标注。

### 验证命令

```bash
python3 scripts/ohc-run.py conan-verify tdb 1.4.15 --profile ohos-aarch64-device
python3 scripts/ohc-run.py finish tdb 1.4.15 built
make test          # 37 TAP + 2 shell + tdbtorture 全过；python testsuite skipped (--disable-python)
```

### 已知限制

| 未执行项 | 技术原因 |
|----------|----------|
| `python/tests/simple.py`（45 项 pytdb 绑定测试） | 本包以 `--disable-python` 构建纯 C 库；平台 python 工具链 `--embed` 输出携带不存在的 `-lintl`，启用绑定需先修复平台 python 配置 |
| robust mutex 锁模式 | 平台 musl 未实现 `pthread_mutexattr_setrobust`，上游自动降级（与其它非 robust 平台一致） |

### 本次升级说明（路径 A → A+B）

按仓库先例（#9734 cdo / #9735 cln / #9810 cyrus-sasl-sql）在**同一 PR** 内原子交付知识草稿与「路径 B 知识贡献说明」，PR 标题使用【知识库扩展】前缀；未新开 PR、未换分支、未改动任何框架文件（`ci/`/`scripts/`/`templates/`/`SKILL.md` 等）。新增知识与本适配过程一一对应，全部证据可从 `notes.md` 与 `reports/` 复现。
