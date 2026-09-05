## PR 信息

- **三方库名称**：pkgconf
- **上游版本**：3.0.6
- **上游仓库地址**：https://github.com/pkgconf/pkgconf
- **适配路径**：路径 A（基础适配） / 路径 B（贡献创新）
- **使用知识库**：openharmony-compile-agent；E077、E369、E490；本 PR 新增 E543（OHOS 原生 self-sign signer 闭包与目标执行边界）

---

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------:|------|
| 单元测试 | 16 | Meson upstream validation：api-audit 至 api-oom-spdxtool |
| 集成测试 | 0 | 上游没有独立集成测试入口 |
| 其他测试 | 17 | fuzz replay、basic/cli、solver、SBOM、工具和 symlink 组 |
| **合计** | **33** | `pre-pr/upstream-inventory.txt`，33 项完整执行 |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|---------------:|------------|------|
| 单元测试 | 16 | 不变 | 上游 API 测试全部构建并执行 |
| 集成测试 | 0 | 不变 | 无独立集成入口 |
| 鸿蒙特有测试 | 1 | 新增 | AArch64 真机 consumer/CLI/fixture/BOM/SPDX/pccritic 组 |
| **合计** | **34** | **+1** | 真机组见任务证据目录的 `pre-pr/target-consumer.log` |

---

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [ ] **否**，未修改上游任何测试用例
- [x] **是**，存在对上游测试用例的修改（请在下方逐条说明）

> 0002/0004 将 parser/solver replay 临时文件绑定到 TMPDIR 并在失败时 fail closed；0003 绑定 replay 计数；0005 为 Windows 测试可执行文件提供溢出安全 shim；0006 固定 wrap/OOM/replay 回归；0007 使用 TMPDIR-backed anonymous streams；0008 提供 Windows 测试专用 strndup。所有修改均由 8 个补丁在干净源码上通过应用检查。

---

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [ ] **否**，上游已有测试用例覆盖
- [x] **是**，上游无测试用例，适配后补全了测试（请在下方说明）

> 补全范围：新增 Conan `test_package` consumer 和真机目标组，覆盖静态链接 API、CLI、fixture 查询及 OHOS ELF 执行/签名边界。补全原因：上游 Meson 测试不覆盖 Conan package export、consumer link 或 OpenHarmony 目标信任。

---

## 验证结果

- 编译状态：通过
- 上游测试用例通过率：33/33（100%）
- 新增测试用例通过率：1/1（100%）

> Windows native upstream log：33/33（32 OK + 1 EXPECTEDFAIL，Fail=0）。OHOS 交叉构建 `125/125`，consumer compile/link `1/1`；真机 `run-004` 在 `10.62.195.15:8022` 返回 `W3_RESULT=PASS`，并完成 `POSTRELEASE_PASS`。目标事务使用官方 native `binary-sign-tool` `selfSign=1`，未重放已消费 launch。

---

## 补充说明

- **关联 Issue**：#2613
- **队伍名称**：天天开心
- **申请人显示标识**：2301_80739235
- **源分支**：OpenHarmonyPCDeveloper:feat/pkgconf-3.0.6
- **目标分支**：OpenHarmonyPCDeveloper/build_in_harmonyos:main
- **其他说明**：递归依赖闭包为空，按简单依赖门禁继续；若后续领取的依赖展开为 GUI/平台框架或大规模目标闭包，将立即放弃并释放，不递归继续。W3 证据位于 `F:\\HarmonyPC\\contrib-claim-af-20260903-pkgconf-3.0.6\\w3-run-004`；知识查重结果为 `NO_EQUIVALENT_REUSABLE_KNOWLEDGE`，新增 E543 草稿对。
