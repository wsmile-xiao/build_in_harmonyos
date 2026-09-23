# libcsys 5.0.0 — W4 独立审计报告（Pre-PR）

- **Verdict**: ✅ **PASS**（P0/P1 清零；仅 P3/信息性意见）
- **Auditor**: subagent-W4-independent
- **时间**: 2026-09-13T16:31:15Z
- **分支**: feat/libcsys-5.0.0（HEAD 已提交 `9e4e91f08`）
- **待审包**: `archives/l/libcsys/5.0.0/`
- **审计方式**: 独立重下载 + 直接读仓库真实文件 + 运行官方脚本；区分「真实运行」与「只读代码」

---

## 一、结论摘要

| 级别 | 数量 | 是否阻塞 |
|------|:----:|:--------:|
| P0（欺骗） | 0 | — |
| P1（配方错误） | 0 | — |
| P2 | 0 | 否 |
| P3 / 信息性 | 6 | 否 |

**verdict = pass**。所有 P0 欺骗检测项与 P1 配方正确性项均通过，仅剩非阻塞的 P3/信息性意见。

> 说明：本次审计**未重新执行完整 `conan create`**，而是核验已记录的构建产物与日志、并对补丁做静态 + dry-run 比对。凡未亲手跑过的，本报告不声称跑过。

---

## 二、P0 欺骗检测（逐项证据）

### 2.1 源码包 sha256 — ✅ 一致
自己重下载（不信配方里的值）：

```
$ /usr/bin/curl -sSL -o $HOME/tmp/verify/verify-libcsys.tar.gz \
    https://gitlab.com/cubocore/libcsys/-/archive/v5.0.0/libcsys-v5.0.0.tar.gz
$ sha256sum $HOME/tmp/verify/verify-libcsys.tar.gz
8ba5ddcdcf6162a0db229f2b95312784a30760f09e919960fedb5fd9fe7f9cb9   (28945 bytes)
```
与 `conandata.yml` / 版本级 `manifest.yaml` 的 sha256 **逐字相同**。非全零/全 f/过短。

### 2.2 test_package 真实调用被测 API — ✅ 真实
`test_package/test_libcsys.cpp` include 的 `csys/*.h` 与调用的符号，逐一对照上游 `$HOME/tmp/builds/libcsys-v5.0.0/csys/*.h`：

- 10 个类全部被真实调用：`FileUtil`、`CpuInfo`、`MemoryInfo`、`SystemInfo`、`NetworkInfo`、`DiskInfo`、`InfoManager`、`BatteryManager`、`Power`、`StorageManager`。
- 每个调用符号均在上游头文件存在（如 `getCpuCoreCount`/`getCpuPercents`/`getCPUFrequencies`/`formatKHz`、`getMem*/getSwap*`、`getHostname..getAppCaches`、`getIOBytes`、`getDisks/getDiskIO`、`update/getMemUsed`、`batteries()`、`systemCanSuspend/systemCanReboot`、`devices()/blocks()`）。
- 共 **41 个 `CHECK()` 断言**（`grep` 计 41，排除 `#define` 行）。

**非空壳、非仅打印。**

### 2.3 test() 真实执行二进制 — ✅ 真实
`test_package/conanfile.py::test()` 调 `self.run(<bindir>/test_libcsys, env="conanrun")`（并设 `LD_LIBRARY_PATH`）。构建日志佐证：

```
.ci_logs/conan_build_libcsys_5.0.0.log:290
libcsys/5.0.0 (test package): RUN: ./test_libcsys
```
非 `echo`/`print`/`true`。

### 2.4 补丁每个 hunk 真实对应上游缺陷 — ✅ 正确
逐一对照上游原文，并 **dry-run 应用**（`git apply --check -v` 与 `patch -p1 --dry-run` 均成功，命中 `csys/{infomanager.cpp,power.cpp,systeminfo.cpp}` 的准确行号）：

| 文件 | 上游原文 | 修复 | 判定 |
|------|----------|------|------|
| `infomanager.cpp:105` | `mCpuFrequencies[i] << xFrequencies[i];`（`xFrequencies`=`QList<qreal>`，OHOS 空表越界） | `... << xFrequencies.value(i, 0.0);` | ✅ 类型匹配：`QList<qreal>::value(qsizetype, const qreal&)`，`0.0` 为 qreal；越界安全 |
| `power.cpp:116` | `while (providers.empty()) { delete providers.takeFirst(); }`（条件写反 → 空表 takeFirst 越界） | `while (not providers.empty())` | ✅ 正确遍历空/非空容器 |
| `systeminfo.cpp:92-95` | `int size = gethostname(...); return QString::fromLatin1(hostname, size);`（成功返回 0 当长度 + 泄漏 + 未终止） | `char hostname[256]={0}; gethostname(hostname,sizeof-1); return QString::fromLatin1(hostname);` | ✅ 零初始化 + 有界 + strlen 终止；`fromLatin1(const char*)` 正确 |

- 补丁**未引入平台宏**（R8 合规），纯 POSIX 兼容修复。
- **未引入新 bug**。

### 2.5 无伪造状态：log_sha256 — ✅ 一致
```
$ sha256sum archives/l/libcsys/5.0.0/reports/w3-local-ci.log
73638f6b76144e5e963592cacfcb105c6c6680f83c170b64f89d01c0f800c6e4
```
与 `.ci-result.json` 的 `log_sha256` **完全一致**（`exit_code=0`、`integrity_hash=4aaf5255885c419d`）。

### 2.6 测试日志无自相矛盾 — ✅ 一致
`.ci_logs/conan_build_libcsys_5.0.0.log`：

- `171: No tests were found!!!` —— 上游 0 用例时 ctest 的正常输出（与声明一致）；
- `231/288: Testing the package` / `289: Running test()`；
- 41 条 `[PASS]`、**0 条 `[FAIL]`**；
- `343: libcsys test summary: assertions=41 failures=0`；
- 安装段显示 `libcsys.so.5.0.0` + `libcsys.so.5` + `libcsys.so` 版本链（SONAME 门禁满足）。

无互相矛盾/伪造迹象。

---

## 三、P1 配方正确性 — ✅ 全部通过

| 检查项 | 结论 | 证据 |
|--------|------|------|
| settings 四项 | ✅ | `settings = "os", "compiler", "build_type", "arch"` |
| name/version 与目录一致 | ✅ | `libcsys` / `5.0.0` |
| requirements | ✅ | `qtbase-sql-dbus/6.11.1`（**非** `qtbase/6.11.1`，故有 Qt6DBus）；日志 `Requirements: qtbase-sql-dbus/6.11.1 ... Cache` |
| package_type | ✅ | `"library"` |
| cmake_find_mode | ✅ | `"none"`（上游只装 `csys.pc`+头文件，无 Config.cmake，合理） |
| cpp_info | ✅ | `libs=["csys"]`、`includedirs=["include"]` |
| 版本号策略（R37） | ✅ | 首次适配，`5.0.0` 无后缀 |
| R32 平台判断 | N/A | 配方无 `if self.settings.os` 分支，无漏匹配 |
| R49 / PF6（/usr/local） | ✅ | 配方与 test_package **无** `/usr/local` 注入（日志里的 `/usr/local/bin` 来自运行环境 PATH，非配方注入） |
| R39 源 URL 官方 | ✅ | `https://gitlab.com/cubocore/libcsys/...`（官方上游） |
| CMAKE_SHARED_LIBRARY_SONAME 注入 | ✅ | 与 `archives/k/kdbusaddons/6.14.0/conanfile.py` 同款技术；实测产出 `.so → .so.5 → .so.5.0.0` 链 |

---

## 四、P2 / P3（对照 code-style.md 与 review-memory.md）

- **占位符扫描**：全部 libcsys 文件 + 两份草稿 `grep` `(请填写)`/`[填写]`/`TODO`/`FIXME`/`XXX`/`<placeholder>` → **0 命中**。
- **manifest.yaml 必填字段**（ARCHIVE-SPEC §4.1/§4.2）：软件级 `software/display/description/category/versions` 齐备；版本级 `version/status/build_date/source.url/build.system` 齐备。
- **MANIFEST.yml 必填字段**：`package/homepage/upstream_tests_inventory/test_package_tests/assertion_count` 齐备。
- **测试数字自洽**：`41 断言 / 0 失败 / 退出码 0` 在 `manifest.yaml`、`test_package/MANIFEST.yml`、`reports/test-report.md`、`.cpp`（41 个 CHECK）、日志（`assertions=41 failures=0`）五处**完全一致**。
- **notes.md 模板占位符**：无残留。

### P3 / 信息性

- **F1** `draft-review DRAFT-9001`（短 ID）报 `草稿不存在` —— 工具按完整文件名 stem 精确匹配（`draft_review.py:208-211`），本仓草稿一律带后缀。用完整 stem `draft-review DRAFT-9001-libcsys-5.0.0-ohos-runtime-crashes --json` → **exit 0、verdict=create、无重复**。属调用约定，非缺陷。
- **F2** 草稿用 YAML 块标量 `>`，draft-review 朴素解析器判 `has_root_cause=false` / 标「空壳」；同类草稿 164/616、全量 201/604 被标空壳（含最新 DRAFT-6048）→ **工具解析限制，非本包内容缺陷**（.kv 字段实际完整）。
- **F3** `patch_description` 为长英文句、`patch_type=bugfix`；code-style §12 示例为短语/`portability`，但 ARCHIVE-SPEC §4.3 明确允许 `bugfix`，故 `patch_type` 合规，仅措辞风格差异。
- **F4** 版本级 `manifest.yaml` 缺可选字段 `conan_ref`（ARCHIVE-SPEC 列为「推荐」）。
- **F5** test_package 直接链接 `libcsys.so` 而非 `find_package(csys)`；因 `cmake_find_mode=none`（上游无 Config.cmake）设计使然，已说明。
- **F6** `test-report.md §4.2` 记录整仓扫描 JC 门禁 FAIL（由其它包 `cloog` 存量文件引发）—— 透明披露，非本包缺陷。

---

## 五、知识图谱

- `python3 scripts/ohc-run.py graph validate` → **exit 0**，`All checks passed (169 warnings)`（540 .kv / 540 .md / 540 index rows；warnings 均为既有 E 条目 category 长尾词，与 libcsys 无关）。
- `DRAFT-9001-libcsys-5.0.0-ohos-runtime-crashes.kv` 字段完整：`error_signature`/`match_keywords`/`root_cause`/`rec_approach`/`rec_description`/`forbid_*` 均非空。
- `draft-review <full-stem> --json` → exit 0，最高相似度 0.07（< 0.30）→ **verdict=create，无重复**。

---

## 六、被检文件 sha256（自算）

见 `audit-result.json` 的 `sha256` 字段（含 conandata.yml、conanfile.py、补丁、test_package 全部、两份 manifest、notes、报告、w3 日志、草稿 .kv、以及 `.ci_logs/conan_build_libcsys_5.0.0.log`）。

---

## 七、疑点 / 未决（不阻塞）

1. 本审计**未重跑** `conan create`；补丁正确性来自上游原文比对 + dry-run，非重编译验证。（`.conan-verified`/`.ci-result.json`/流水线日志均自洽，无造假迹象。）
2. F2 的「空壳」标记是否影响后续 `graph promote` —— 未实测 promote 路径；建议人工核验时留意。
3. `.ci-result.json` 的 `integrity_hash`（16 hex）算法未知，无法独立复算，仅确认文件未被篡改的间接证据（log_sha256 一致）。

*报告生成: 2026-09-13T16:31:15Z — subagent-W4-independent*
