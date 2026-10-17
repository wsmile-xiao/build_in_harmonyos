## PR 信息
- **三方库名称**：qt5-qtsvgv
- **上游版本**：5.15.2.2（源码对应 Qt 5.15.2 官方 tarball）
- **上游仓库地址**：https://code.qt.io/cgit/qt/qtsvg.git
- **适配路径**：路径 A（基础适配）+ 路径 B（贡献创新）
- **使用知识库**：openharmony-compile-agent；E345（本 PR 配套草稿）

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 5 组（92 个断言） | tests/auto/qsvgdevice、qsvggenerator、qsvgplugin、qicon_svg、qsvgrenderer |
| 集成测试 | 0 | 上游模块未单列集成组 |
| 其他测试 | 29 | qsvgdevice 的目标能力跳过，非失败 |
| **合计** | **5 组（92 个断言）** | 五组均执行并通过 |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 5 组（92 个断言） | 不变 | r13 目标平台执行 |
| 集成测试 | 0 | 不变 | 无单列集成组 |
| 鸿蒙特有测试 | 1 | 新增 | QSvgRenderer 安装包消费者 smoke |
| **合计** | **6 组** | **+1** | 上游五组加消费者验证 |

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例
- [ ] **是**，存在对上游测试用例的修改（请在下方逐条说明）

上游测试源码未修改；qsvgdevice 的 29 个跳过来自目标能力判定，已在 r13 结果中单独记录。

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [ ] **否**，上游已有测试用例覆盖
- [x] **是**，适配后补全了测试（为安装包消费增加验证）

补全范围：新增 1 个 QSvgRenderer 消费者 smoke，调用真实安装包 API 并断言合法 SVG 的 `isValid()`。
补全原因：上游模块测试不能证明 Conan package_info、生成 target 和安装后元数据在消费者侧可用。
新增测试文件：任务证据 `w3-r13-consumer.cpp`（对应 test_package 的实质消费路径）。

## 验证结果

- 编译状态：通过
- 上游测试用例通过率：5/5（100%）
- 新增测试用例通过率：1/1（100%）

### 编译验证
- 目标平台：OHOS aarch64，endpoint `10.62.195.15:8022`
- r13 唯一 launch，qmake 构建与五组上游测试通过，结果 SHA-256：`474e9e6bcb6eda4c5f6a8c2065722705b5913ffc5ea257b6a8276c09e7569535`
- 本机 Windows `conan create` 失败于 provider 内 AArch64 qmake/Posix 激活脚本不可由 Windows 执行；该环境边界不产生 `.ci-result.json`，正式 CI 以 PR 后平台 Buildbot 为准。

### 目标测试结果

| 测试组 | 结果 |
|--------|------|
| qsvgdevice | 2 passed, 0 failed, 29 skipped |
| qsvggenerator | 13/13 |
| qsvgplugin | 15/15 |
| qicon_svg | 7/7 |
| qsvgrenderer | 55/55 |
| QSvgRenderer consumer | PASS |

### 依赖与元数据修复

- 依赖：`qt5-qtbase/5.15.2.2`（W0 已由 `conan download --only-recipe` 确认发布）
- `conanfile.py` 对 provider 的 `.pri`、`.prl`、`.la`、`.pc`、`.cmake` 元数据同时处理 Unix/Windows Conan 路径。
- r9-r11 失败均保留为不可重放历史，r13 使用新的唯一 run_id 和完整 transfer/readback。

### 验证命令

```text
W3 r13: 唯一 launch -> 五组上游测试 -> QSvgRenderer consumer -> AArch64 ELF -> 进程清零
结果：PASS；run_id=qt5-qtsvgv-5.15.2.2-w3-r13-20260903
```

## 补充说明

- 关联 Issue：#2568（创建 PR 后回写真实编号并建立双向关联）
- 队伍名称：天天开心
- 申请人显示标识：2301_80739235
- 源分支：fix/qt5-qtsvgv-5.15.2.2
- 目标分支：OpenHarmonyPCDeveloper/build_in_harmonyos:main
