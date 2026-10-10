# 【知识库扩展】feat(metacam): 1.2 鸿蒙 PC 原生适配与 EXIF 扫描回归测试

## PR 信息

- **三方库名称**：`metacam`
- **上游版本**：`1.2`
- **上游仓库地址**：Debian [源码维护仓库](https://salsa.debian.org/pkg-security-team/metacam)；本配方使用 [官方 Debian 原始发布包](https://deb.debian.org/debian/pool/main/m/metacam/metacam_1.2.orig.tar.gz)，未把 Debian 包装仓库冒称为软件作者的原始 Git 仓库
- **适配路径**：路径 A + 路径 B（知识库扩展）候选；HD1–HD4 已逐项复判为不匹配，最终等级、积分及验收以维护者为准
- **使用知识库**：本仓库 `knowledge/drafts/E13539-draft-tank_you.{kv,md}`；本地既有鸿蒙 PC 旧 C++ 图像扫描器经验用于回归测试设计
- **看板任务**：`@tank_you` 已认领 `metacam/1.2`，指定分支 `feat/metacam-1.2`

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------:|------|
| 单元测试 | 0 | 官方 1.2 原始发布包无自动化单元测试 |
| 集成测试 | 0 | Makefile 无 `check`/`test` 目标 |
| 其他测试 | 0 | 发布包无测试脚本或测试目录，详见上游清单 |
| **合计** | **0** | 上游测试 0/0，不虚报通过率 |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------:|------------|------|
| 单元测试 | 0 | 不变 | 未虚构上游或新增单元测试 |
| 集成测试 | 1 | +1 | `test_package` 调用最终安装包的 CLI，覆盖 TIFF、延后、短文件及跨缓冲区 EXIF，11 项断言 |
| 鸿蒙特有测试 | 1 | 同一用例 | 上述消费者场景在 HarmonyOS PC 真机运行，属于交叉分类，不另计一个用例 |
| **合计** | **1** | **+1** | 1/1 场景、11/11 断言；鸿蒙特有行不重复加总 |

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，上游发布包无自动化用例，也未删减任何上游测试
- [ ] **是**，存在对上游测试用例的修改

仅修复生产代码 `metacam.cc` 的两个独立扫描状态错误：初始 `found_exif`
改为 `false`；扫描结束后清除阻断 `seekg` 的流错误状态。前者修复
EXIF 位于第二缓冲区时提前终止，后者修复短文件的 `failbit`。

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [ ] **否**，上游已有测试用例覆盖
- [x] **是**，上游无自动化用例；补全 1 个已安装包消费者场景，共 11 项断言

- **补全的测试范围**：CLI 帮助与无参退出状态、TIFF `Make` 字段、
  EXIF 位于第二缓冲区、短 JPEG、标记跨 1024 字节边界。
- **补全原因**：原版在真机对延后 EXIF 静默漏检，仍返回 0；仅检查
  编译或退出码不足以验证核心功能。
- **新增测试文件清单**：
  1. `archives/m/metacam/1.2/test_package/test_metacam.py` — 黑盒生成
     确定性 TIFF/JPEG 夹具，实际启动已安装程序并检查内容与返回码。

## 验证结果

- 编译状态：通过
- 上游测试用例通过率：0/0（不适用）
- 新增测试用例通过率：1/1（100%）

HarmonyOS PC AArch64 真机上的隔离 Conan 2.29.1 `conan create` 返回 0，
新增消费者场景中的 11/11 项断言通过。原始发布包没有自动化测试入口。
官方发布包 33,657 字节，SHA-256
`3fb1e19e7a32d7bdf6a9ef5a75027a885239f35488035cd066839c175d8ed3a7`；
真机上传、远端核验、独立回读一致。原版对延后 EXIF 输出
`No EXIF/TIFF data found`；修复后已安装 Conan 包消费者输出
`PASS: installed metacam reads TIFF, late, short and split JPEG EXIF`。
后续将以最终候选代码 SHA 核对正式 W3 事务和平台 CI，不能拿探索性运行
冒充 CI 通过。

## 补充说明

- 关联 Issue：[GitCode #3606](https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/issues/3606)；创建后按编号、OPEN 状态和正文散列回读
- 队伍名称：看板组织字段为空，未擅自填写
- 申请人显示标识：`@tank_you`
- 源分支：tank_you:feat/metacam-1.2
- 目标分支：`OpenHarmonyPCDeveloper/build_in_harmonyos:main`
- 适配边界：仅验证所列 EXIF/TIFF 输入、CLI 行为和包构建；不声称完整
  JPEG 规范、所有相机厂商私有字段或平台发布流程均已验证。
