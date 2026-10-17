- **三方库名称**：sluice
- **上游版本**：0.03.01（上游 tag `V0.03.01`）
- **上游仓库地址**：https://github.com/ColinIanKing/sluice
- **适配路径**：路径 A（基础适配）
- **使用知识库**：openharmony-compile-agent（ohc-run 流水线：W0 → init-build → conan-init → conan-verify → finish → submit）

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 0 | 来源：上游无测试框架，tarball 无 tests/ 目录，Makefile 无 test/check 目标（grep 退出码 1） |
| 集成测试 | 0 | 来源：无 |
| 其他测试 | 1 | 来源：上游 CI（.travis.yml）`make -j2 PEDANTIC=$PEDANTIC` 编译门禁，非功能测试 |
| **合计** | **1** | 功能性自动化测试用例为 0 |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 0 | 不变 | 工具类单二进制 CLI，无库接口可做单元测试 |
| 集成测试 | 0 | 不变 | 上游亦无 |
| 鸿蒙特有测试 | 3 | 新增 | test_package 消费者用例（见下） |
| **合计** | **3** | **+3** | |

鸿蒙特有消费者用例（`test_package/test.sh`，随 conan create 在 OHOS arm64 musl 真机环境实际执行）：

1. **版本横幅用例**：`sluice -h` 输出 `sluice, version 0.03.01` — 验证二进制在 OHOS musl/libc 下正常启动；
2. **直通完整性用例**：1048576 字节（256 页对齐）经 `sluice -n` 管道转发，断言 1048576/1048576 字节零丢失；
3. **限速节奏用例（OHOS 平台特性）**：8000000 字节 @ 2MB/s 限速转发，断言 8000000/8000000 字节完整且耗时 ≥3s（实测 4s）— 验证 OHOS 管道 + 定时限速协同可行；脚本内含 OHOS 适配（`/data/service/hnp/bin/bash` 解释器、OHOS `/tmp` 只读规避、页对齐大小选择）。

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例
- [ ] **是**，存在对上游测试用例的修改（请在下方逐条说明）

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [ ] **否**，上游已有测试用例覆盖
- [x] **是**，上游无测试用例，适配后补全了测试（请在下方说明）

- **补全的测试范围**：为核心功能（版本输出、管道直通完整性、限速转发节奏）新增 3 个端到端消费者用例，其中限速节奏用例为鸿蒙平台特有可行性验证
- **补全原因**：上游库仅含单文件 C 工具（sluice.c + Makefile），无任何测试框架与功能测试；上游 CI 仅做 PEDANTIC 编译门禁
- **新增测试文件清单**：
  1. `archives/s/sluice/0.03.01/test_package/test.sh` — 3 个消费者用例（版本横幅 / 直通完整性 / 限速节奏），含 OHOS 平台适配
  2. `archives/s/sluice/0.03.01/test_package/conanfile.py` — VirtualRunEnv 消费者测试入口
  3. `archives/s/sluice/0.03.01/test_package/MANIFEST.yml` — 测试包清单

## 验证结果

- 编译状态：通过（本地 `make -j2 CC=clang` 与 `PEDANTIC=1` 均零警告；conan create 于 ohos-aarch64 profile 下 clang 15 交叉构建成功，产出 arm64 musl ELF）
- 上游测试用例通过率：1/1（100%，上游唯一测试入口为 CI 编译门禁，已在 OHOS 环境复现通过；上游无功能性自动化测试）
- 新增测试用例通过率：3/3（100%，conan create 日志 `ALL OK`，含 L1e 破坏性负测试确认用例真实依赖被测产物）

## 补充说明

- 上游存在 EOF 尾部行为：流末尾不足一个 io_size 的尾部缓冲在 EOF 时被丢弃（`-n` 模式转发 `floor(N/4096)×4096` 字节）。经与上游 master 分支源码逐字节比对（42719 字节、行号一致），确认为**上游既有行为**而非 OHOS 适配缺陷，本次不篡改上游逻辑；新增测试用例选用页对齐大小规避该尾部 quirk（详见 `notes.md`）。
- 零第三方依赖：sluice 仅依赖 libc，W0 依赖检查无外部依赖需 conan download 验证。
- 适配知识沉淀：知识库新增草稿 E429（make 命令行 CFLAGS 覆盖 `+=` 导致 -DVERSION 丢失）、E430（Conan conf 嵌套子键寻址报错）。
- 本地门禁：conan-verify 8 道（G0-G4 + L2/L4/L5）全 PASS；W3 本地 CI（prdiff 模式 17 文件）L0/L1/L4/L5 pass；finish step10 就绪项全过。
