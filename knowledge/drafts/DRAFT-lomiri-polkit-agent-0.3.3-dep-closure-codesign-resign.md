# DRAFT-lomiri-polkit-agent-0.3.3-dep-closure-codesign-resign：依赖制品 `.codesign` 段「存在但失效」→ 消费者侧 dlopen 被拒载

> Contributor: weijiapan | Status: Draft | Updated: 2026-09-30
> Source: lomiri-polkit-agent 0.3.3 适配（PR #13994，分支 `feat/lomiri-polkit-agent-0.3.3`）
> 对应：`knowledge/drafts/DRAFT-lomiri-polkit-agent-0.3.3-dep-closure-codesign-resign.kv`
> 近邻条目：**E489**（正式，构建树 ctest 闭包未签名）；**DRAFT-E077B**（SDK 自动签名段无效，产物面）；**DRAFT-E5xx**（未签名共享库 dlopen 拒绝，install 产物面）。三条与条目的界线见「与既有条目的界线」。
> 关联误命中：**E540**（zlib shadow CI runner PATH）——本次实际被引擎命中，方向完全不同。

## 触发场景

消费者包（下游配方 / 它的 `test_package`）运行时 dlopen 一个**已发布到制品仓的依赖包**所提供的共享库，而该库的 `.codesign` 段**存在但签名对 OHOS 加载器无效**。典型形态：

```console
# 编译、链接、conan create 的 build 段全绿；失败只出现在运行期
lomiri-polkit-agent/0.3.3 (test package): RUN: ./policykit-agent --version
Error loading shared library libnotify.so.4.0.0
Error relocating ./policykit-agent: notify_notification_show: symbol not found
ERROR: lomiri-polkit-agent/0.3.3 (test package): ConanException: Error 127 while executing
```

三个反直觉点，决定了它必须被单独记录：

1. **表象不是签名**。加载器拒载后报的是下游「符号找不到」——没有 `Permission denied` 字样，第一反应总是「漏依赖 / 搜索路径 / 符号版本」。
2. **编译期完全不可见**。clang/lld 只读符号表，`.codesign` 无效与否对编译链接毫无影响；`conan create` 的 build 阶段、G2 干净构建、CI 的编译门禁全都会绿。
3. **现有判据会漏报**。E489 的验证命令用 `llvm-readelf -S <elf> | grep codesign` 计数——本次实测该库**段存在（计数 1）却仍被拒载**，属假阴性。

## 根因

OHOS 加载器对 ELF 有签名门禁；签名段存在**不代表**签名有效。缺陷载体是**别人已发布的制品**，不是本包产物：

- 本包自己编译的 ELF 是好的 → 「本地跑得通、消费者一跑就挂」；
- 依赖包不可改（改了还得等它重新发布），所以**修法只能在消费者侧**：按 conan 依赖图枚举闭包，逐个「去旧段 + 统一重签」。

### 与既有条目的界线

| 条目 | 缺陷载体 | 修法位置 | 判据/表象 |
|---|---|---|---|
| **E489**（正式） | 本包**构建树**（ctest 运行闭包） | 配方 `build()` 期签构建树 | `dlopen.*Permission denied`；判据 `grep -c codesign` |
| **DRAFT-E077B** | 本包**产物**（SDK 自动插入的占位段） | `package()` 期四步重签 | `readelf` 有段但 exec 报 `Operation not permitted` |
| **DRAFT-E5xx** | 本包 **install 产物**（未签名） | `package()` 内签产物 + soname 别名 | `Error loading shared library ...: Permission denied` |
| **本条** | **已发布依赖制品**（第三方包） | **消费者侧**（本包 test_package/下游配方）闭包重签 | 编译全绿 → `symbol not found` + `Error 127`；**必须实跑 dlopen/三态对照**才可定因 |

关系：前三条都假设「ELF 由本包产出，可在自己配方里签」；本条处理的是**无法在本包配方里修上游**的情形，是它们的**消费者侧对偶**。

## 检测逻辑

### 判定顺序（避免误命中）

1. **先认表象**：编译全绿 + 运行期 `Error relocating ...: symbol not found` + `ConanException: Error 127` → 把「签名失效」列为**第一嫌疑**，而不是先去查搜索路径。
2. **再看段**：`llvm-readelf -SW <lib> | grep -c codesign` —— 只作**存在性**参考，**不得**作有效性判据（本次段存在仍拒载）。
3. **三态对照定因**（唯一变量 = 签名，三步结论必须一致）：
   - a) 原件 → 正常；
   - b) 仅 `llvm-objcopy --remove-section .codesign <lib>` → 复现 EACCES / symbol not found / rc=127；
   - c) 去段 + `binary-sign-tool ... -selfSign 1` → 恢复。
4. **最小 dlopen 探针**（不依赖测试框架）：
   ```bash
   LD_LIBRARY_PATH=<dep_pkg>/lib python3 -c "import ctypes; ctypes.CDLL('libnotify.so.4')"
   # 未签/失效 → OSError: Error loading shared library ...: Permission denied
   # 已签     → 正常返回
   ```

### 适用库范围

任何运行时经 dlopen 加载 conan 依赖共享库的 OHOS 消费者包；对**多库闭包**（GUI/服务类）风险最高——只需闭包里一个库签名失效，整条运行链就断。

## 处理方法（消费者侧闭包重签）

在**消费者侧**实施（本样例落在 `test_package/conanfile.py`，不污染本体配方、不越界改依赖包）：

1. `generate()`/`build()` 遍历依赖图（每个 `requires` 的 `cpp_info.libdirs`/`bindirs`，含传递依赖）收集所有 `*.so*`；
2. 过滤：只取 ELF（前 4 字节 `\x7fELF`）、**跳过符号链接**（软链用 `rm -f && ln -s` 重建，HMDFS 不支持 `ln -sf` 覆盖）；
3. 每个 ELF：`llvm-objcopy --remove-section .codesign` → `binary-sign-tool sign -inFile <f> -outFile <f> -selfSign 1`；
4. **任一步失败（含签名工具缺失）立即终止**，不得降级为「跳过」——否则错误会在下游才爆；工具不存在时按 `env_unsupported` 上报；
5. 重签后以**私有可写 TMPDIR** 跑消费者测试，验证真实 dlopen 路径。

```bash
# 闭包整体重签（日志一律重定向文件，勿管道 head，规避 SIGPIPE）
find <closure_lib_dirs> -name '*.so*' -type f -print0 \
  | xargs -0 -n1 sh -c 'llvm-objcopy --remove-section .codesign "$0" \
      && binary-sign-tool sign -inFile "$0" -outFile "$0" -selfSign 1' > resign.log 2>&1

# 消费者测试
TMPDIR=<writable-dir> ctest --output-on-failure -j1 > ctest.log 2>&1
```

**这不是上游修复的替代品**：依赖制品签名失效本身是依赖包缺陷，应在依赖包 `package()` 内自签（E077B/E5xx 路线）并重新发布；消费者侧重签只是本包内的必要兜底。

## 复现脚本（随包提供）

`archives/l/lomiri-polkit-agent/0.3.3/test_package/repro-code-sign-closure.sh`（POSIX sh，工具经 PATH 探测 + 已知 HNP 目录兜底，不硬编码本机路径；只在私有可写临时目录内改文件，绝不动 conan 缓存与共享前缀；日志一律重定向文件，规避 SIGPIPE）：

```bash
# 检测：逐库 dlopen 探针，列出签名失效（UNSIGNED）的库
sh test_package/repro-code-sign-closure.sh scan <conan_dep>/lib [<more_lib_dirs>...]

# 复现：三态对照（唯一变量 = 签名）
sh test_package/repro-code-sign-closure.sh demo <conan_dep>/lib <soname>
```

实测输出（2026-09-30，本机 aarch64 OHOS 6.0）：

```console
== 工具: objcopy=/data/service/hnp/bin/llvm-objcopy signer=/data/service/hnp/bin/binary-sign-tool
== 工作副本: <TMPDIR>/repro-codesign-3319/stage/libnotify.so.4.0.0*（不改动原始目录）
a) 原件              -> OK (期望 OK)
b) 仅去段            -> UNSIGNED (期望 UNSIGNED)
c) 去段 + selfSign   -> OK (期望 OK)
RESULT: 三态符合预期 —— 已确认为「.codesign 段存在但失效」，需在消费者侧对依赖闭包重签
```

签名工具缺失时脚本 exit 1 并明示按 `env_unsupported` 上报，不静默跳过。

## 测试样例结果（样例库：lomiri-polkit-agent 0.3.3）

环境：aarch64 / OHOS 6.0 / clang 15，conan 2.29.1，profile `ci/conan/profiles/ohos-aarch64`。

| 状态 | 结果 |
|---|---|
| 关闭重签（原始） | test_package 运行期 rc=127，`symbol not found: notify_notification_show`（dlopen EACCES） |
| 三重签对照 | 仅去 `.codesign` 段即复现；去段 + selfSign 恢复 → **签名是唯一变量** |
| 开启重签（闭包 38 个库 / 19.8MB） | test_package 6/6 通过；`conan create` exit 0；conan-verify G1/G0/G2/G3/G4 全 PASS |

证据文件：`archives/l/lomiri-polkit-agent/0.3.3/reports/conan-verify-report.md`（Verdict: PASS）、
`archives/l/lomiri-polkit-agent/0.3.3/.ci-result.json`（W3 exit_code=0，含日志 SHA256）。

## 限制与边界

1. 只在包内/私有可写目录操作；**禁止重签共享前缀**（`/usr/local`、`/lib`、`/lib64`）——CI worker 与本地共用文件系统会互相污染（E524/R49 教训）。
2. 软链一律 `rm -f && ln -s` 重建；不要指望 `chmod` 修复（HMDFS 上可能不生效，见 E046）。
3. 判定不得只看 `grep -c codesign`；必须实跑 dlopen/exec 或做三态对照。
4. 闭包全量重签而非只修命中库时，须在证据里写清覆盖范围（本例 38/38）。
5. 本坑在 CI 上同样成立：CI 干净环境拉取的是同一批已发布制品，签名失效与本地一致。

## 对知识库治理的建议

1. **E540 误命中**：本次 `symbol not found` 类报错被引擎命中 E540（zlib runner PATH）。建议为其 `match_keywords` 补负例（`codesign`/`dlopen`/`Error loading shared library` 共存时应优先签名类条目）。
2. **DRAFT-E077B / DRAFT-E5xx 建议提升**：两条与本次同族（签名面）却停在草稿目录、不在 `index.tsv`，引擎检索不到——本次正是因此才误命中 E540。建议主编评估提升，并在 E489 中补「段存在 ≠ 有效」的判据修正。
3. 若采纳本条，建议与 E489/E077B/E5xx 组成「OHOS ELF 签名门禁」条目族，按**载体 × 修法位置**索引（构建树 / 本包产物 / 依赖制品）。
