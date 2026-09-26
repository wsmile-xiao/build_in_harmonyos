- **三方库名称**：zrc
- **上游版本**：v2.7
- **上游仓库地址**：https://github.com/Edd12321/zrc
- **适配路径**：路径 A（基础适配）
- **使用知识库**：ohos-worker-env-triage（编译环境分诊）、仓库 docs/ADAPTATION_GUIDE.md、参考包 jpnevulator 2.3.6（CLI application 模板）

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 0 | 上游无测试套件（Makefile 仅 release/debug/clean/install 目标，无 tests/ 目录） |
| 集成测试 | 0 | 同上 |
| **合计** | **0** | |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 0 | 不变 | 上游无测试框架可迁移 |
| 集成测试 | 0 | 不变 | 同上 |
| 鸿蒙特有测试 | 8 | 新增 | test_package 消费者测试（test_zrc.sh），实测执行打包产物 bin/zrc |
| **合计** | **8** | **+8** | |

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例
- [ ] **是**，存在对上游测试用例的修改（请在下方逐条说明）

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [x] **是**，上游无测试用例，适配后补全了测试（请在下方说明）
- [ ] **否**，上游已有测试用例覆盖

> - **补全的测试范围**：为 zrc CLI 补全 8 项消费者测试断言（版本探测、
>   -c 单行求值、命令替换 + expr 算术、真实脚本文件的 do/while 控制流
>   与退出码语义）
> - **补全原因**：上游为单人维护的 shell/脚本语言项目，Makefile 无
>   check/test 目标，无任何测试框架
> - **新增测试文件清单**：
>   1. `archives/z/zrc/2.7/test_package/test_zrc.sh` — 消费者测试脚本，
>      实际执行打包产物 bin/zrc（脚本主体改编自上游示例
>      examples/99bottles.zrc）

## 验证结果

- 编译状态：通过（conan create RC=0；W3 本地 CI：L0/L1/L4/L5 全 pass，
  L2 skip 原因：zrc `--version` 按上游语义恒以退出码 1 结束，属上游
  定义行为，非产物缺陷，详见 reports/test-report.md）
- 上游测试用例通过率：0/0（上游无测试套件，如实申报）
- 新增测试用例通过率：8/8（100%）

## 补充说明

1. **包类型为 application**（CLI shell/脚本语言，纯可执行文件，无库产物），
   含软件级与版本级 commands.json；conanfile `package_type="application"`。
2. **CXXFLAGS 覆盖**：去掉上游默认的 `-flto`（OHOS 系统链接器 LTO 风险），
   追加 `-fsigned-char`（AArch64 char 默认无符号，zrc 做逐字符处理，
   恢复上游 x86 有符号语义）。
3. **不使用上游 `make install`**：该目标会向 /etc/shells 追加行，
   package() 直接从 bin/zrc 拷贝（同 jpnevulator 先例）。
4. **零外部依赖**：仅依赖系统 libc/libc++，无 conan requires。
5. 构建/打包自检文件（reports/、packaging/、.staging-verified、
   manifest.yaml、notes.md）齐备，证据见 reports/test-report.md。
