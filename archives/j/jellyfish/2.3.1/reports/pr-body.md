- **三方库名称**：jellyfish
- **上游版本**：2.3.1
- **上游仓库地址**：https://github.com/gmarcais/Jellyfish
- **适配路径**：路径 A（基础适配）
- **使用知识库**：E160（config.guess 识别 HarmonyOS）、E011/E114（HMDFS umask 权限）、E002（/tmp 只读）、新增草稿 DRAFT-7605（mkfifo 不可用 → 运行期能力探测）

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 51313 | 来源：`unit_tests/` 内置 googletest（54 个 test case，51313 个 gtest 实例），由 `unit_tests/unit_tests.sh` 驱动 |
| 集成测试 | 11 | 来源：`tests/*.sh`（automake parallel-tests：generate_sequence / parallel_hashing / merge / bloom_filter / big / subset_hashing / multi_file / bloom_counter / large_key / sam / small_mers） |
| 其他测试 | 3 | SWIG 绑定脚本 `tests/swig_{python,ruby,perl}.sh`（未启用绑定，上游设计 exit 77 skip） |
| **合计** | **51327** | automake `make check` 注册 15 个 TESTS；gtest 实例 51313 个 |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 51310 执行（51310 通过） | -3 | 3 个依赖命名管道（mkfifo）的用例（`TmpPipes.CreateDestroy`、`TmpPipes.Discard`、`GeneratorManager.OneLiners`）在 HarmonyOS 上按运行期能力探测排除，日志声明原因；其余全部通过 |
| 集成测试 | 11 脚本（9 通过 + 2 跳过） | 不变 | `big.sh` 需 `BIG=1`（上游默认 skip，与平台无关）；`sam.sh` 未启用可选 htslib，按上游逻辑 exit 77；其余 9 个脚本 0 失败 |
| SWIG 绑定测试 | 3（全部跳过） | 不变 | 未启用 SWIG 绑定（上游默认），3 个脚本按上游逻辑 exit 77 |
| 鸿蒙特有测试 | 11 | 新增 | `test_package/test.sh` 消费者测试：对**已安装的** `jellyfish` CLI 做 11 条断言（版本/计数/直方图/dump/query/info + 2 条负例） |
| **合计** | **51324 执行**（另新增 11 条消费者断言） | **-3（平台能力排除，逐条披露）** | automake TESTS：15（10 PASS / 5 SKIP / 0 FAIL）；gtest：51310/51310 通过 |

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [ ] **否**，未修改上游任何测试用例
- [x] **是**，存在对上游测试用例的修改（请在下方逐条说明）

> 修改均为「平台能力运行期探测 + 等价回退/跳过」，未弱化或删除任何断言；未修改任何库源码的计数逻辑。

1. **修改的测试文件**：`tests/bloom_counter.sh`
   - **修改原因**：HarmonyOS 全局拒绝 `mkfifo(2)`（EPERM），generator 命令装载输入不可用。
   - **修改内容**：加入 `mkfifo` 运行期能力探测；FIFO 可用时保持上游原样（`-g` 命令文件），不可用时改用文件参数装载**同一份重复输入**（`seq1m_0.fa seq1m_0.fa`），布隆计数器内容与直方图 md5 不变。
2. **修改的测试文件**：`tests/multi_file.sh`
   - **修改原因**：同上（generator 子测试依赖 FIFO）。
   - **修改内容**：FIFO 不可用时跳过 generator 子测试（含 generator 失败负例）并复用普通多文件直方图；保留"打不开文件必须失败"负例。
3. **修改的测试文件**：`unit_tests/unit_tests.sh`
   - **修改原因**：gtest 中 `TmpPipes.*` 与 `GeneratorManager.OneLiners` 直接调用 `mkfifo` 建管道。
   - **修改内容**：FIFO 不可用时追加 `--gtest_filter=-TmpPipes.*:GeneratorManager.OneLiners`（日志打印原因）；FIFO 可用的平台上命令不变。
4. **修改的测试文件**：`unit_tests/test_stream_iterator.cc`
   - **修改原因**：用例硬编码 `/tmp/stream_iterator_XXXXXX`，HarmonyOS 的 `/tmp` 只读（EROFS，E002）。
   - **修改内容**：临时目录依次尝试 `TMPDIR` → `/tmp` → `.`（不改变测试逻辑与断言）。
5. **修改的构建脚本**：`configure`（非测试用例，随 0002 补丁）
   - **修改原因**：toybox `unix2dos` 不支持测试使用的 `-n <in> <out>`；`configure` 无脑命中该命令导致 `generate_sequence.sh`/`parallel_hashing.sh` 误失败。
   - **修改内容**：为 `UNIX2DOS` 增加功能探测；不支持时置空，上游测试中相应步骤自行跳过（`parallel_hashing.sh` 走上游自带的 `cp` 回退分支）。

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [x] **否**，上游已有测试用例覆盖（`make check` 完整运行）
- [ ] **是**，上游无测试用例，适配后补全了测试

> 说明：上游测试覆盖充分，本适配未删除/新增上游用例；另按仓库规范新增了消费者视角测试 `test_package/test.sh`（11 条断言，计入上方"鸿蒙特有测试"行）。

## 验证结果

- 编译状态：通过（`conan create`，OHOS aarch64 clang 15.0.4；产物 `bin/jellyfish`、`libjellyfish-2.0.a`、头文件、`jellyfish-2.0.pc`）
- 上游测试用例通过率：automake `make check` **10/15 通过、5 跳过、0 失败**；gtest 单元 **51310/51313 通过**（3 例平台能力排除，逐条见上）
- 新增测试用例通过率：**11/11（100%）**

## 补充说明

- **命名管道平台限制（如实披露）**：HarmonyOS 沙箱对普通用户域进程的 `mkfifo(2)` 一律返回 EPERM（实测 HMDFS 用户目录、构建目录、`/dev/shm` 全部拒绝，toybox 亦无 mkfifo 命令）。因此 jellyfish 的 **generator 输入（`-g`/`-G`）在本平台不可用**；核心的文件输入 k-mer 计数路径不受影响，并已被上游集成测试与消费者测试覆盖。测试层使用运行期能力探测（非平台宏、非 uname 硬编码），FIFO 可用平台上与上游行为完全一致。若需该功能，需将 `generator_manager` 从"命名管道 + shell 重定向"重构为匿名管道（`pipe()`/`socketpair()` + `dup2`），属独立增强，不在本次基础适配范围。
- **htslib 可选依赖**：本配方显式 `--disable-htslib`（保证构建可复现、避免构建机系统 htslib 意外命中）；`tests/sam.sh` 按上游设计检查 `HAVE_HTSLIB` 后 exit 77。制品仓已有 `htslib/1.24-r0`，后续可按需启用。
- **补丁可向上游提交**：6 个补丁均无平台宏（无 `__OHOS__`）、无硬编码绝对路径，为通用可移植性修复（config.guess 新系统识别、临时目录权限、命令功能探测、TMPDIR 支持），详见 `patches/` 与 `notes.md`。
