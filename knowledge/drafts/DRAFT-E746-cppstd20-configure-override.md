# DRAFT-E746 — C++20 包在 cppstd=17 profile 下的 configure() 覆盖

- 取号：`knowledge_id.py --claim --task snitch-1.2.3` → **E746**（2026-09-25，回查未占用）
- 适用：一切 validate/上游构建要求 C++20（或更高）而 profile 钉 17 的 conan 配方
- 状态：UNMATCHED（草稿，待审核提升为 E 条目）

## 一句话

统一 profile 固定 `compiler.cppstd=17`，要求 C++20 的包（直移 CCI 配方高危）在
graph/validate 阶段就会被判 `Invalid: Current cppstd (17) is lower than the required
C++ standard (20)`（rc=6，构建前即拦）——正解是 recipe `configure()` 首行
`self.settings.compiler.cppstd = "20"`（settings 可写时机先于 validate/package_id），
test_package 同样覆盖；不改 profile、不删 validate。

## 证据链（snitch 1.2.3 反证探针，2026-09-25）

- 正向：配方含覆盖 → `conan create` 日志 settings 行
  `compiler=clang compiler.cppstd=20`，rc=0，test_package 3/3 过。
- 反证：从 `configure()` 删除覆盖一行（探针副本 `$TASK_DIR/cppstd-probe`）→
  `snitch/1.2.3: Invalid: Current cppstd (17) is lower than the required C++ standard (20).`
  `ERROR: There are invalid packages`，**rc=6**，构建前即拦。
- 仓库先例：apache-arrow、abseil、kirigami、baloo、libarrow（configure 覆盖）；
  knighttime、kholidays（`tc.blocks.remove("cppstd")` + cache_variables 20 两路写法）。
- package_id 含 cppstd=20 语义正确；conan compatibility 会为 17 消费者匹配
  （create 日志 `Checking 3 compatible configurations`：gnu20/23），无需各建二进制。

## 判定与处置（详见 .kv 的 rec_approach / solution）

1. 判定：`Current cppstd (N) is lower than the required C++ standard (M)` 或
   validate 报 `requires C++M` → 命中（不是编译器不支持，设备 clang15 支持 C++20）。
2. 处置：`configure()` 首行覆盖 + 注释 profile 默认值与先例；test_package 同款。
3. 自证：create 日志 `compiler.cppstd=20` 行 + 消费编译通过。
4. 判级：配方正确性修复，验证后才发现须按 delta 分级重验。

## 复现命令

见 .kv 的 `solution`（探针与判据全部落 `$HOME/tmp/snitch-1.2.3/`，设备可直接执行）。
