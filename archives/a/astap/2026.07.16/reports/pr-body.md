- **三方库名称**：astap
- **上游版本**：v2026.07.16
- **上游仓库地址**：https://github.com/CanardConfit/ASTAP
- **适配路径**：路径 A（基础适配）
- **使用知识库**：openharmony-compile-agent

## 测试用例对比

### 上游库测试用例统计

已检查上游 `v2026.07.16` 完整源码、Lazarus/FPC 工程文件及 `command-line_version/` 目录。上游未提供自动化测试目录、测试工程或测试目标。

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------:|------|
| 单元测试 | 0 | 上游源码无单元测试目录或测试目标 |
| 集成测试 | 0 | 上游源码无集成测试工程 |
| 其他测试 | 0 | 上游未提供可自动执行的测试脚本 |
| **合计** | **0** | **上游无可执行测试用例** |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------:|-----------|------|
| 单元测试 | 0 | 不变 | 上游无单元测试，本适配未修改上游源码测试 |
| 集成测试 | 0 | 不变 | 上游无集成测试 |
| 鸿蒙特有测试 | 9 | +9 | 对 Conan 制品执行版本、帮助、错误路径和真实 FITS 分析验证 |
| **合计** | **9** | **+9** | **9/9（100%）通过** |

鸿蒙特有测试明细：

| 编号 | 测试内容 | 实际结果 |
|---:|---|---|
| 1 | 精确验证运行时版本身份 | `ASTAP astrometric solver version CLI-2026.07.16` |
| 2 | 验证帮助信息包含 `Usage:` | PASS |
| 3 | 验证帮助信息包含输入文件选项 `-f` | PASS |
| 4 | 验证帮助信息包含图像分析选项 `-analyse` | PASS |
| 5 | 验证无参数调用输出用法 | PASS |
| 6 | 验证缺失输入文件输出访问错误 | `Error, accessing the file!` |
| 7 | 验证缺失输入文件输出文件不存在错误 | `File not found.` |
| 8 | 对确定性 256×256 FITS 星场执行真实分析并验证 HFD | `HFD_MEDIAN=3.7` |
| 9 | 验证真实 FITS 分析检测到非零星点 | `STARS=23` |

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例
- [ ] **是**，存在对上游测试用例的修改（请在下方逐条说明）

上游没有测试用例，因此不存在对上游测试的删除、跳过或修改。本适配仅新增 Conan 消费者测试。

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [ ] **否**，上游已有测试用例覆盖
- [x] **是**，上游无测试用例，适配后补全了测试（请在下方说明）

- **补全的测试范围**：为 ASTAP 命令行制品补全 9 项测试，覆盖精确版本身份、帮助和参数接口、无参数调用、缺失文件诊断，以及有效 FITS 图像的核心分析流程。
- **补全原因**：上游仅提供 Lazarus/FPC 应用源码和工程文件，没有正式自动化测试框架；仅验证帮助输出不足以证明图像分析核心功能可用，因此额外生成确定性 FITS 星场并执行真实 `-analyse`。
- **新增测试文件清单**：
  1. `archives/a/astap/2026.07.16/test_package/conanfile.py` — Conan 制品测试入口，加载打包后的 `astap_cli` 运行环境。
  2. `archives/a/astap/2026.07.16/test_package/test_astap.sh` — 执行并断言 9 项命令行和 FITS 分析结果。
  3. `archives/a/astap/2026.07.16/test_package/generate_test_fits.py` — 生成包含 23 颗确定性高斯星点的 256×256 FITS 测试图像。
  4. `archives/a/astap/2026.07.16/test_package/MANIFEST.yml` — 记录测试来源、执行命令和断言数量。

## 验证结果

- 编译状态：通过
- 上游测试用例通过率：`0/0`（N/A，上游无测试用例）
- 新增测试用例通过率：`9/9`（100%）

验证环境：HarmonyOS PC arm64（`os=OHOS`、`arch=armv8`），Conan 2.29.1，Free Pascal Compiler 3.2.2。

验证命令：

```bash
conan create archives/a/astap/2026.07.16 \
  -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=astap/*

python3 scripts/ohc-run.py conan-verify astap 2026.07.16
python3 scripts/ohc-run.py finish astap 2026.07.16 built
```

门禁结果：

- `conan create`：通过
- `conan-verify` G1–G4：通过
- W3 本地 CI：通过
- 独立终审：PASS，无 P0/P1

## 补充说明

- ASTAP 是 Lazarus/Object Pascal 应用，不是 Autotools C/C++ 库。本适配采用 custom Conan 构建，直接编译 `command-line_version/astap_command_line.lpr`。
- 上游标签 `v2026.07.16` 中 CLI 版本常量仍为 `2026.07.13`，使用最小补丁同步为 `2026.07.16`，并通过整行精确断言验证运行时身份。
- 使用官方 AArch64 FPC 3.2.2 静态发行包；在线源码和 W3 本地缓存均执行 SHA-256 校验。
- FPC 构建工具和最终 `astap_cli` ELF 均完成 HarmonyOS 签名。
- 本次交付命令行求解器，不包含 Lazarus GUI、GTK/Qt 依赖和大型外部星表数据库。
