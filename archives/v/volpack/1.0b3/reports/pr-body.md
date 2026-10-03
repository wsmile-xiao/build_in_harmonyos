## PR 信息

- **三方库名称**：volpack
- **上游版本**：1.0b3
- **上游仓库地址**：https://graphics.stanford.edu/software/volpack/ （版本化 Debian 源码重打包物见 `conandata.yml`）
- **适配路径**：路径 A（原生库适配）+ 路径 B（知识库扩展，申请 10 分候选）
- **使用知识库**：复用 E007 的旧 GNU config 脚本识别思路；新增 `knowledge/drafts/E544-draft-7DD0.kv` 与同 stem `.md`，最终编号由主编确认

---

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------:|------|
| 单元测试 | 0 | 上游没有独立单元测试框架。 |
| 集成测试 | 4 | `examples/test.csh` 的原始、八叉树、分类、分类+八叉树四条渲染路径；每条与 `examples/check.ppm` 比对。 |
| 其他测试 | 0 | `make check` 没有可执行用例，不重复计数。 |
| **合计** | **4** | 清单见本 PR `reports/test-report.md` 与本机证据 `upstream-test-inventory.txt`。 |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|---------------:|------------|------|
| 单元测试 | 0 | 不变 | 未新增独立单元测试框架。 |
| 集成测试 | 4 | 不变 | 用可移植 `sh` 执行上游四条渲染路径，4/4 与 `check.ppm` 逐字节一致。 |
| 鸿蒙特有测试 | 5 | +5 | Conan 消费者通过公共 API 完成上下文生命周期及三维参数断言，5/5 通过；另有隐藏库/头文件后的负向依赖验证。 |
| **合计** | **9** | **+5** | 上游 4/4 + 新增消费者 5/5，均在 HarmonyOS PC/aarch64 实机运行。 |

---

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例
- [ ] **是**，存在对上游测试用例的修改（请在下方逐条说明）

`test_ohos/run_ohos_test.sh` 仅将上游 `examples/test.csh` 的四条命令移植为目标机可执行的 `sh` 驱动；上游测试数据 `brainsmall.den` 和参考图 `check.ppm` 未改动。GNU config 和 VPATH 补丁只涉及构建系统。

---

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [x] **否**，上游已有测试用例覆盖
- [ ] **是**，上游无测试用例，适配后补全了测试（请在下方说明）

上游虽未把用例挂入 `make check`，但 `examples/test.csh` 有四条真实渲染路径。我们没有将其误报为无测试；新增的 `test_package/test.c` 是包消费者覆盖，验证安装后的公开 API 和 Conan 链接关系。

---

## 验证结果

- 编译状态：通过
- 上游测试用例通过率：4/4（100%）
- 新增测试用例通过率：5/5（100%）

HarmonyOS PC/aarch64、Clang 15、Conan 2.29.1 上的清洁 `conan create` 通过。四条上游渲染路径在日志中给出 `4/4 PASS`，五项消费者 API 断言通过；移除包内 `lib/` 和 `include/` 后消费者构建按预期失败。目标机执行的 W3 本地 CI 模拟：L0、L1、L4、L5 通过，L2 因纯库无 `bin` 而跳过，包汇总 1/1 通过。完整证据与限制见 `archives/v/volpack/1.0b3/reports/test-report.md`。这些是目标机本地验证，不等于平台 PR CI 或 AI Review 已通过。

Stanford 官方包为 `.tar.Z`（SHA-256 `d7cfd5f6819cccf88363d2270377e547a07f35da6a0dac45845ecc1640e410fa`），目标机 Toybox `gzip` 不支持 LZW。配方改用 Debian 同版本 `.orig.tar.gz`（SHA-256 `dce3d892ad34b2810fc80b0592c7224a4606f8ebfb8206421e24288753f230d7`），此前逐字节核对 `vp_*.c`、`volpack.h`、测试输入及参考输出均与官方包一致。由于目标机无法直连 Debian，仅本地验证使用预下载且校验和相同的压缩包；提交配方仍指向正式 Debian URL。知识草稿限定了适用条件、禁止盲目改名和镜像未核验的情况。

---

## 补充说明

- 关联 Issue：#3534（路径 B 知识库扩展申请）
- 队伍名称：诶，云朵
- 申请人显示标识：2501_91199785
- 源分支：2501_91199785:feat/volpack-1.0b3
- 目标分支：OpenHarmonyPCDeveloper/build_in_harmonyos:main
- 其他说明：任务 #11740 已由本账号领取，难度 medium；仅本库配方、测试和配套知识草稿纳入 PR。`vprender` Tcl/Tk 演示为独立发行物，不在本次范围。平台 CI、AI Review、合并、制品仓发布均待真实回读，合并后才按 `/release` 发布。
