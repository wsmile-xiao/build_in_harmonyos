# W4 独立审计 r1 — trompeloeil-cpp/49（审计代号 z74-trompeloeil-w4）

- 绑定 HEAD：`fd547a140d188cd7580400cefcf82591129a8374`（本地 = 远端 `feat/trompeloeil-cpp-49`，实测一致）
- 坐标：B 机 `~/qzy/主理-74-trompeloeil-cpp-49`，归档 `archives/t/trompeloeil-cpp/49`，CONAN_HOME `~/tmp/ch/home-trompeloeil-cpp`
- **判决：FAIL**（P0=0 / **P1=2** / P2=2 / P3=2）
- 全程只读；未跑 build/create/verify/finish，未改任何 worktree 文件，未动登记表

---

## ★头号项：与已合入包 `trompeloeil/49` 并存 —— 判 **P1 真实缺陷**

**结论：会撞，且撞在 CMake config 文件上。**

| 比对项 | `trompeloeil/49`（已合入，7c2776cc50） | `trompeloeil-cpp/49`（本包） | 是否相同 |
|---|---|---|---|
| `cmake_file_name`（conanfile.py:190） | `trompeloeil` | `trompeloeil` | **逐字相同** |
| `cmake_target_name`（conanfile.py:191） | `trompeloeil::trompeloeil` | `trompeloeil::trompeloeil` | **逐字相同** |
| `namespaced_targets` / `aliases` | 未设置 | 未设置 | 同（grep `set_property` 各只命中 190/191） |
| `includedirs`（:195） | `["include"]` | `["include"]` | 相同 |
| 引用名 / `package_id` | `trompeloeil/49` | `trompeloeil-cpp/49` | 不同 ⇒ 两包各自独立落盘 |

- **配方实质差别 = 0**：`diff -u` 两 `conanfile.py` 全文只有 1 个 hunk（`@@ -30,7 +30,7 @@`），内容就是第 33 行 `name` 加 `-cpp`；其余 195 行逐字相同。`test_package/test_trompeloeil.cpp` 与已合入包 **diff 退出码 0**（同一份代码）。`tool_requires catch2/3.8.1`、`patches: {}`、`package_type=header-library` 全同。
- **撞的实物证据（不是推理）**：本包自己生成的 CMakeDeps 文件就是上游名 ——
  `test_package/build/clang-15-armv8-17-release/generators/` 下为
  `trompeloeil-config.cmake`、`trompeloeil-config-version.cmake`、`trompeloeilTargets.cmake`、`trompeloeil-Target-release.cmake`、`trompeloeil-release-armv8-data.cmake`。
  同一工程同时 `requires` 两包 ⇒ 5 个同名文件写进同一 generators 目录、后者覆盖前者，`find_package(trompeloeil)` 只解析到一个包，另一个的 imported target 缺失。⇒ **P1**。
- **头文件路径重合判「无害」**：两包 `package_id` 不同 ⇒ 各在自己的 `package_folder` 下装 `include/trompeloeil/…`（本包实构目录 `p/b/tromp7c289448ece0e/p`），绝对路径不同、不互相覆盖；消费者同时 `requires` 只是拿到两个 `-I`，上游 include guard 使重复包含不致重定义。⇒ 重合是真的，但缺陷不在此，缺陷在 config/target 同名。
- **处方（别名包让名，不动已合入包）**：本包 `package_info()` 改
  `cmake_file_name='trompeloeil-cpp'` + `cmake_target_name='trompeloeil-cpp::trompeloeil-cpp'`；
  **不要**用 `cmake_target_aliases` 复原 `trompeloeil::trompeloeil`（同名 alias 只是把冲突从文件名搬进 target 名，CMake 建 imported target 时直接重名报错）。配套 `test_package/CMakeLists.txt` 改 `find_package(trompeloeil-cpp CONFIG REQUIRED)` 与 `trompeloeil-cpp::trompeloeil-cpp`，并在 notes 加一段双包关系说明（同 upstream/tag/sha256，11301 已 done、11302 本窗，交付理由=Debian 侧别名，target 名刻意分开）。改后重跑 create + W3 并重新回填 `.ci-result.json`。
- **「值不值得单独成包」**：平台两个独立任务号 ⇒ 交付别名包本身有据（不否此点）。但本 PR 除包名外与已合入包无配方/测试/依赖差别，唯一增量是 notes/report 的一手清点与可达性披露 ⇒ 让名处方是「让并存无害」的最低要求，不是可选优化。

---

## A 取源诚实性 —— **合格**

- HEAD 实物（非 `git show 8a7c`）：`conandata.yml:14` 单一官方 URL `https://github.com/rollbear/trompeloeil/archive/refs/tags/v49.tar.gz`，`:15` 官方 `sha256=2523571f…5593`。
- `git log -- conandata.yml` 只有 `8a7c7714c3` + `fd547a140d` ⇒ **只此一次翻转**；`8a7c` 的 `:12` 确为被注入的 `https://ghfast.top/https://github.com/...`，`fd547a` 已复原。
- tracked 全包扫 `ghfast|gh-proxy|file://|mirrors`：命中 2 条，均为披露性注释（`conandata.yml:11`、`notes.md:92`），无申报源。
- tag 形态与双哈希：`notes.md:13-14` 实测 `refs/tags/v49` 存在、`refs/tags/49.tar.gz` HTTP 404；官方件 `.build-cache/predl_cache/{320623c7,7cef7f42}_v49.tar.gz` 实算均 = `2523571f…`、336774B；Debian 池件 `dl/t49.orig.tar.xz` 实算 = `5213c194…`、291284B。两哈希分属两文件，`notes.md:15-21` 如实分开，**未拿池件哈希冒充官方件**。

## B 可达性披露 —— 披露在，**取证落盘缺 ⇒ P1（W4-02）**

- 探针**脚本**在盘：`~/tmp/uc2/z74-trompeloeil/s2.sh`（`:20` 就是 `curl --connect-timeout 20 -m 90 -w "http=… size=… time=…"`，`:25` 是 `git clone --depth 1 --branch v49`）。
- 但目录顶层只有 `diffreport.txt / finish.log / s1.sh / s2.sh / s3.* / s4.sh / s6.* / w3-verify.log`，**没有任何 s2 输出件**；跨 `~/tmp/uc2` 与 `.ci_logs` 扫 `curl: (28)|Empty reply|2756/7908|http_code` 命中的全属别的包。⇒ 四条读数按本轮「指不到=申报无来源」口径判 P1。
- 结论方向本身另有独立盘证：`w3-verify.log:20`、`finish.log:47` 显示取源需临时注入 ghfast.top 镜像；`w3-local-ci.log:99-103` 显示实构走 `gh-proxy.com` 后转 `file://` ⇒ **本地绿确实不证明 CI 绿**，此判断成立。
- notes/正文披露：`notes.md:22-27`、`:89-94`、`test-report.md:34-35` 三处均如实写出限制，未粉饰。

## C W3 证据自洽 —— **合格**

`.ci-result.json` `exit_code=0`、`integrity_hash=3f3c5817aa8bcc0b`、`log_sha256=99571f7b…4df4`；`sha256sum reports/w3-local-ci.log` 实算**逐字相等**。真编译真运行：`:180 Building from source`、`:229` 真 `cmake --build self_test thread_terror custom_recursive_mutex`、`:236-241` 编译链接行、`:243/249/253` 三个二进制真 RUN、`:425 L1_RESULT=pass: test_package executed` 名副其实。`:426 L2_RESULT=skip: no bin/ dir`、`:428 L5_RESULT=warn: no artifacts found` 对 `package_type=header-library` + `bindirs/libdirs=[]` 成立，属良性，不是拿 skip 当通过。

## D 测试质量 —— 数字全真，**两处口径/引用问题**

- 出处于 `w3-local-ci.log`：246=1361/604（C++14）、311=1394/615（C++20）、314=负向 68/executed 50/excluded 18、315=68/68/excluded 0、407 与 `conan-create.log:150`=消费者 5/4；静态 3 目标=w3:229；测试源码 `cat test/*.cpp test/*.hpp | wc -l` 实算 **14736** ✓。
- **W4-03（P2）**：`notes.md:55-66` 把这 7 条的来源件写成 `reports/conan-create.log` 并给出行号 211/214/215/307 —— 该文件**实只有 152 行**，只含消费者那一行（`:150`）。`test-report.md:5-6` 又称其「309 行」。数字未虚构，但「正文数字与证据同源」不成立 ⇒ 四件套③不过。
- **W4-05（P3）**：`test-report.md:13`「可执行数」里填 50（实测执行数）而非 68（静态可执行总数），`notes.md:73-74` 把 1219 运行时用例也塞进该行 ⇒ 静态/实测口径混用（rule4 家族方向）。
- **18 excluded 归因合格**：`compilation_errors/*.cpp` 实数 68，含 `// exception` 的 24 个；上游 `verify_compilation_error.sh:31 EXCEPTION_RE=get_rule "exception"`、`:34` 匹配 `{$RUNNER_OS} ${COMPILER}` 即 `exit 0`（不打印 PASS/FAIL）⇒ 配方把「既非 PASS 也非 FAIL」计为 excluded，**非本窗裁剪用例**。
- **鸿蒙特有面 ≥1 且非「头文件存在即通过」**：`test_trompeloeil.cpp` 4 用例 5 断言，真用 `MAKE_MOCK0/1`、`REQUIRE_CALL().RETURN(42)`、`gt(0)` 匹配器、`TIMES(2)`、`LR_SIDE_EFFECT`、并 `catch (trompeloeil::expectation_violation)` 校验 `e.what()`；OHOS 特有维度=整份上游套件在 OHOS clang 15/libc++ 下跑 C++14+C++20 两轮 + 负向编译 `TMPDIR`（`/tmp` 只读）改造。
- **0 ctest 与「有测试」并存自洽**：`notes.md:32-33`、`:70-72` 明说 0 ctest 注册、测试实体是 3 个可执行目标 + 68 个 expect-to-fail 单元，表述不矛盾。

## E R51 清点复核 —— **合格**（台账「101 个头文件」被正确否定）

源树一手实算：`find . -type f`=**123**、`find include -type f`=**24**、`find -name '*.hpp'`=**27**。`notes.md:30-31` 逐字按实测申报并写明「台账『101 个头文件』**不成立**」。
Catch2 构建期 `file(DOWNLOAD)`：**不会**在 CI 沙箱因联网而红 —— 配方 `conanfile.py:94-102` 在 tool_requires 未给包目录时直接 `raise ConanException`，无网络回落；实构日志 `catch2/3.8.1` 全程走 Cache（w3:173/348 `Already installed`），preflight `w3:32 [ok] dependency in registry: catch2/3.8.1`，日志内无 `catch.hpp` 下载行。真正风险只剩取源那一条（见 B）。

## F manifest/harness 回写 —— **合格**

tracked 扫 `pending|TODO|占位|xxxx|FIXME` 命中 **1 条** = `notes.md:85` 抄录门禁判决行「[OK] KC2: 模板占位符残留检测通过」，非未完成标记（执行棒申报一致）。`49/manifest.yaml` `status: built`、`patches_applied: []` 与实物一致（`conandata patches: {}`、两包 diff 无补丁）；软件级 manifest `display: "trompeloeil"` 正确标出别名关系。
**W4-06（P3）**：配方目录内残留未跟踪产物 —— `conandata.yml.orig`、`__pycache__/conanfile.cpython-314.pyc`、`test_package/CMakeUserPresets.json`、`test_package/build/**`、`.build-closed/.conan-verified/.handoff.json/.ci-result.json`、`reports/*.log`。均被 .gitignore 覆盖不入 PR，但 `__pycache__` 可能被 `conan export` 卷入 ⇒ 提审前清。

## 另判 **P2（W4-04）**：「树级 diff 0 行差异」不成立

`notes.md:20-21` 申报官方树与 Debian 池件树 `diff -rq` **0 行差异**。唯一取证件 `~/tmp/uc2/z74-trompeloeil/diffreport.txt` 实有 **18 行**，全是 `Only in x/trompeloeil-cpp-49: <顶层条目>`（`.github`、`CMakeLists.txt`、`include`、`test`… 逐个 Only in），且官方侧目录 `gt` **不存在**（`ls: No such file or directory`）⇒ `git clone` 失败后拿空目录参与比较，该交叉核验从未真正执行。哈希侧不受影响（见 A）。修法：删该结论或改为「树级 diff 未取得（官方 clone 失败）」，或改用已入库的官方 tarball 解包树重做并落盘。

---

## 收口前最欠的 3 件（按优先级）

1. **W4-01 让名**（P1）：`cmake_file_name/cmake_target_name` 改成 `trompeloeil-cpp*`，配套 test_package 与 notes 双包说明，然后**重跑 create + W3 并回填 log_sha256**（这是唯一会真正伤到他人的缺陷）。
2. **W4-02 落盘补证**（P1）：把 `s2.sh` 输出 tee 成文件并被 notes 引用；否则从正文撤掉具体数字，只保留 `w3-verify.log:20` / `w3-local-ci.log:99-103` 两条盘上事实 + 「本地绿不代表 CI 绿」。
3. **W4-03 + W4-04 同源修复**（P2）：测试读数来源件/行号改为 `w3-local-ci.log` 实号、`309 行`→`152 行`；撤掉「diff -rq 0 行差异」。

（W4-05/06 顺手改即可，不阻塞提审。）
