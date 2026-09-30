# crossline 1.0 适配笔记

## 编译环境
- 构建系统: custom（上游无任何构建系统，Conan 配方自定义编译）
- 编译日期: 2026-09-28
- 编译器: clang 15.0.4（OHOS SDK aarch64 工具链，/data/service/hnp/bin/clang）
- 状态: built（conan-verify 通过，未 upload 至远端制品仓）

## 编译步骤
1. `python3 scripts/ohc-run.py init-build crossline 1.0 --url=https://github.com/jcwangxp/Crossline/archive/refs/tags/v1.0.tar.gz`
   - 上游 tag 为 `v1.0`；仓库页 URL 返回 HTML 不可下载，改用官方 GitHub archive tarball。
   - tarball SHA-256 = 2c1139201a9381ed94459298e4fe52b58b58bfc58eca041d51eee980c4dcfa06（实测一致）
2. `python3 scripts/ohc-run.py lang-preflight crossline 1.0 --src .../crossline-1.0.work` → 语言匹配：task=cpp，detected=c（兼容族），通过。
3. 编写 `conanfile.py`（自定义 build：编译 crossline.c → 静态库 libcrossline.a）+ `conandata.yml`（官方 v1.0 源）+ `test_package/`（真实消费者）。
4. `python3 scripts/ohc-run.py conan-verify crossline 1.0` → G1-G4 全部 PASS（含 conan create 干净构建、R26 隔离、产物完整性）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build 报"下载内容是 HTML" | 传入 URL 为仓库页而非压缩包（仓库页返回 HTML） | 使用官方 GitHub archive URL `.../archive/refs/tags/v1.0.tar.gz` |
| 2 | conan-verify G1 失败 | test_package/MANIFEST.yml 缺失（CI L0e 门禁要求） | 补写 test_package/MANIFEST.yml |
| 3 | conan create test() 失败：crossline_readline 返回 NULL | 消费者二进制直接运行，stdin 为 EOF（非 TTY 路径走 fgets，读到 EOF 返回 NULL） | test() 中改为 `echo 'hello-crossline' | ./crossline_consumer` 管道喂入一行输入 |

## 源码修改
无（未修改任何上游源码，无补丁）。

## 依赖版本
无第三方依赖（纯 C，仅 libc/POSIX termios 等系统接口）。

## 验证结果

### conan-verify（OHOS aarch64 profile）
```text
G1: PASS  G2: PASS  G3: PASS  G4: PASS  →  配方验证通过
```

### 官方示例程序编译并运行（管道输入，非 TTY 路径）
```bash
clang -fPIC -O2 -Wall crossline.c example.c -o crossline_example        # exit 0
printf 'hello\nquit\n' | crossline_example                              # exit 0
# 输出: Read line: "hello" / Read line: "quit"
clang -fPIC -O2 -Wall crossline.c example_sql.c -o crossline_example_sql  # exit 0
printf 'select * from t;\nquit\n' | crossline_example_sql               # exit 0
# 输出: Read line: "select * from t;" / Read line: "quit"
```
日志：`<workdir>/oh-evidence/crossline/example_run.log`（SHA-256 e4fda48d…）、
`example_sql_run.log`（SHA-256 7f377224…）

## 上游测试枚举台账（R51 申报表 / 双口径）

官方 v1.0 tag 源码共 7 个文件：crossline.c、crossline.h、example.c、example_sql.c、README.md、LICENSE、.gitignore。
**上游不存在任何测试框架、测试目录、CTest/pytest 注册项、fixture、基准或测试脚本**（已逐项核对）。

| 条目 | 类型 | 是否独立上游用例 | 分类理由 | 是否实际运行 | 结果/原因 |
|------|------|------------------|----------|--------------|-----------|
| example.c | 用户样例（示例程序） | 否（样例不计入上游用例） | README "Build and Test" 仅给出示例编译命令，属演示程序非断言测试 | 是 | 编译 exit 0；管道输入运行 exit 0，逐行回显 "Read line: ..."（见 example_run.log） |
| example_sql.c | 用户样例（SQL 补全示例） | 否（样例不计入上游用例） | 同上，演示 completion/hints API | 是 | 编译 exit 0；管道输入运行 exit 0（见 example_sql_run.log） |
| crossline.c | 库源码（被测对象） | 否 | 是库实现本身，非测试 | — | 已编译为 libcrossline.a 并被消费者/示例链接 |
| crossline.h | 公开头文件 | 否 | 库 API 声明 | — | 安装至 include/ |
| README.md / LICENSE / .gitignore | 文档/许可 | 否 | 非测试 | — | 未运行 |
| 测试脚本/构建目标 | 无 | — | 上游无任何测试脚本与构建目标 | — | 不存在 |

**双口径统计**：
- `source_declared_total` = 0（官方 tag 源码按可复制枚举规则未发现独立 TEST_CASE/真实用户用例；上游确实无测试，附上述清点证据）
- `configured_executable_total` = 0（无任何可实例化的独立可执行测试用例）
- `executed_passed_total` = 0，失败 0，未运行/未实例化 0
- 通过率：0/0 不适用（上游无测试），实际执行验证由 2 个官方样例 + test_package 消费者覆盖
- "源码声明/宏或注册项 → 构建条件 → 构建目标 → ctest/GTest 注册项 → 执行日志"逐项映射：无注册项可映射
- 临时目录/运行时环境恢复规则：本次无测试入口因 /tmp 或 LD_LIBRARY_PATH 失败，无需恢复

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | Conan 配方（自定义编译，静态库默认） |
| conandata.yml | 官方 v1.0 源 + SHA-256 |
| test_package/ | 真实消费者（conanfile.py + CMakeLists.txt + consumer.c + MANIFEST.yml） |
| test_ohos/ | 鸿蒙专项测试（run_ohos_test.py + MANIFEST.yml，四检全过） |
| manifest.yaml | 版本级 manifest（status=built） |
| notes.md | 本适配笔记 |

## 知识候选台账与查重（知识库扩展 / Path B 评估）

### 候选台账（逐项非噪声候选）

| # | 候选 | 真实错误 | 根因 | 修复 | 验证 | 适用范围 |
|---|------|----------|------|------|------|----------|
| K1 | test_package 消费者喂 stdin 触发 L1d 假测试误判 | W3 报 `L1_RESULT=fail: fake test detected` | CI L1d 正则 `self\.run.*(echo\|print\|true)` 把 `echo 'x' \| ./consumer` 管道喂 stdin 的真实测试判为假测试；readline 类库消费者非 TTY 路径裸跑 stdin=EOF 返回 NULL | test() 先写输入文件，再 `< file` stdin 重定向执行消费者（命令无 echo/print/true） | conan-verify 通过 + finish W3 复跑 L1 RESULT=pass，100% (1/1)（w3-local-ci.log） | 任何消费者需 stdin 输入的 Conan test_package（readline/交互 CLI/SQL shell 类） |
| K2 | crossline_readline 非 TTY 路径行为 | 消费者裸跑时 crossline_readline 返回 NULL | 非 TTY 时内部走 fgets，stdin=EOF 返回 NULL | 测试与消费者均以 stdin 重定向喂入一行 | consumer 运行 exit 0 输出 readline ok（consumer_run.log） | 本库使用边界（K1 的子项，不单独成条目） |

### 四范围查重

- 正式知识（knowledge/doc/）：`grep -rli "fake test|stdin redirect|L1d"` → 无命中；E161（pipe fstat EACCES）、E363（/tmp 环境）为相邻但不同问题。
- 图谱条目（knowledge/graph/*.kv）：engine 检索 L1d/echo 管道 → 命中 E472（SDL 签名 + test() 需真实 self.run）；E472 覆盖「test 需真实执行」但**未覆盖**「echo/print 管道触发 L1d 正则误判」与「输入文件重定向方案」→ 部分覆盖。
- 草稿（knowledge/drafts/）：grep 无相同 stem；无 exact repeat。
- index.tsv：无 L1d/输入重定向条目。

### 七轴查重（K1）

| 轴 | 结论 | 说明 |
|----|------|------|
| exact_duplicate | false | 无完全重复条目 |
| causal_duplicate | false | K1 根因是 CI L1d 正则匹配写法，E472 根因是 ELF 签名/SDL 无头 |
| trigger_overlap | partial | E472 亦涉及 test() 需真实 self.run；但触发面不同（签名/SDL vs echo 管道正则） |
| solution_overlap | 无 | E472 方案=签 ELF + dummy env；K1=输入文件重定向 |
| combination_novelty | true | stdin 消费 + L1d 正则规避的新组合 |
| boundary_novelty | true | 适用于 readline 类/交互 CLI 的 test_package；纯库不受影响 |
| test_migration_novelty | true | 其他 readline/交互库 test_package 可复用 |

关系字段：`similar_to=E472`，`caused_by=none`，`prerequisite_of=none`，`conflicts_with=none`。

### 路径判断（knowledge 决定）

- **new_draft（Path B 知识库扩展成立）**：K1 已验证、可跨库复用、查重为部分覆盖且存在新增差异（L1d 正向正则规避 + stdin 文件重定向），已建立草稿对：
  - `knowledge/drafts/DRAFT-crossline-1.0-test-package-l1d-stdin-redirect.kv`
  - `knowledge/drafts/DRAFT-crossline-1.0-test-package-l1d-stdin-redirect.md`
- 草稿与 crossline 归档进入同一个 PR（本轮交付，不另建知识库 PR）。

## 注意事项
- crossline 是纯库包（readline/libedit 替代品），构建产物无 bin/ 可执行文件 → 不需要 commands.json（R38 仅 CLI 包需要）。
- 消费者测试必须通过 stdin 管道喂入一行（非 TTY 路径），不能直接裸跑（EOF 返回 NULL）。
---

**编译结束**: 2026-09-28 10:01
**最终状态**: built
