## PR 信息

- **三方库名称**：liblouis
- **上游版本**：3.38.0
- **上游仓库地址**：https://github.com/liblouis/liblouis；官方发布包 https://github.com/liblouis/liblouis/releases/download/v3.38.0/liblouis-3.38.0.tar.gz
- **适配路径**：路径 A（基础适配）+ 路径 B（贡献创新，待官方审核）；任务 #8260
- **使用知识库**：复用 E228、E259；新增 `knowledge/drafts/E2166-draft-A6F2.kv` / `.md`，主题为混合语言 Automake 测试的有效驱动入口选择

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|---|---:|---|
| 单元测试 | 209 | 官方发布包的 Automake `parallel-tests`，包括 C、Perl 和 YAML 测试；详见 `test_package/MANIFEST.yml` 与实机逐项清单 |
| 集成测试 | 0 | 无另列独立上游集成测试入口，避免与 209 项重复计数 |
| 其他测试 | 0 | 无另列其他上游测试入口 |
| **合计** | **209** | 原生 `make check -j1` 实测 209/209 PASS，0 SKIP，0 FAIL |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|---|---:|---|---|
| 单元测试 | 209 | 不变 | 保留原 TESTS 集，调整测试启动入口与必要的测试源码移植点 |
| 集成测试 | 0 | 不变 | 未虚增上游集成测试 |
| 鸿蒙特有测试 | 1 | +1 | Conan 安装包消费者程序在 OpenHarmony PC 上编译、链接并运行，输出 `LIBLOUIS_CONSUMER_PASS` |
| **合计** | **210** | **+1** | 上游 209/209，新增消费者 1/1；两者分开统计 |

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [ ] **否**，未修改上游任何测试用例
- [x] **是**，存在对上游测试启动及测试工具源码的最小移植修改

`patches/0001-test-runtime-portability.patch` 将 Autoconf `config.status` 的 0700 临时目录放在 `TMPDIR` 下；配方命令局部固定 OHOS 的 `TMPDIR=/data/storage/el2/base/cache`，避免 CI 的 Conan profile 把它重设到 HMDFS。补丁还将 Perl 测试内部直接执行的 Libtool wrapper 显式交给 shell；在 YAML 测试工具中把 `yaml_parser_initialize` 从可能被 `NDEBUG` 省略的 `assert` 表达式移出，随后仍断言返回值。没有删减、跳过测试或放宽预期。配方另分别配置生成规则实际读取的 `LOG_COMPILE` 与 `YAML_LOG_COMPILER`，对 wrapper 与真实 ELF 条件分流。

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [x] **否**，上游已有 209 项测试用例覆盖
- [ ] **是**，上游无测试用例，适配后补全了测试

另新增 1 项 Conan 已安装包消费者验证，不计入上游 209 项，也不声称上游无测试。

## 验证结果

- 编译状态：通过
- 上游测试用例通过率：209/209（100%）
- 新增测试用例通过率：1/1（100%）

唯一最终实机事务 `liblouis-w3-20260925T152815Z`：`conan create` 返回 0，`make check -j1` 的 `test-suite.log` 为 209 PASS / 0 SKIP / 0 FAIL，消费者输出 `LIBLOUIS_CONSUMER_PASS`，事务与释放后回读通过 `W3_VALIDATOR_PASS`。构建日志 SHA-256 `b146b9be2d6670dde25675a408c6bb8394388ffa806af2581593a17283c1ea65`；测试汇总 SHA-256 `f6a527b328554088262be7cd8875237747805527373e2c2fc3235b663bfae213`。平台 CI 与 AI Review 尚待 PR 创建后触发和回读。

## 补充说明

- **关联 Issue**：#3420（https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/issues/3420）
- **队伍名称**：诶，云朵
- **申请人显示标识**：2501_91199785
- **源分支**：2501_91199785:feat/liblouis-3.38.0
- **目标分支**：OpenHarmonyPCDeveloper/build_in_harmonyos:main
- **其他说明**：上游官方 tarball SHA-256 `afb26096b18b17f43e6055e6a79ce0058eb9dbdcdcc4597522dcd7f11915ec16`；依赖 `libyaml/0.2.5` 已预检；知识查重结论为相对 E228/E259 仍有多驱动入口诊断增量，是否计入路径 B 由官方审核。HD1–HD4 均无充分证据，不申请路径 C。合并后的发布动作才运行 `/release`，本 PR 不上传制品。
