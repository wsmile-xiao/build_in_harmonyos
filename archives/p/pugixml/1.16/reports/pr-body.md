## PR 信息

- **三方库名称**：pugixml
- **上游版本**：v1.16
- **上游仓库地址**：https://github.com/zeux/pugixml
- **适配路径**：路径 A（基础适配）+ 路径 B（贡献知识扩展）
- **使用知识库**：openharmony-compile-agent；E552、E553

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 989 | tests/main.cpp，由官方 CTest 可执行文件执行 |
| 集成测试 | 0 | 上游未提供独立集成测试目标 |
| 其他测试 | 0 | 无 |
| **合计** | **989** | **989/989 断言通过** |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 989 | 不变 | 独立 host CTest，989/989 断言通过 |
| 集成测试 | 0 | 不变 | 无 |
| 鸿蒙特有测试 | 1 | 新增 | OHOS/arm64 consumer 解析 XML 并执行 XPath，真机 RC=0 |
| **合计** | **990** | **+1 个目标 consumer** | 上游分母与目标 consumer 分开记录 |

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例
- [ ] **是**，存在对上游测试用例的修改（请在下方逐条说明）

上游源码和 tests/main.cpp 未修改；Windows 解压产生的临时乱码文件名仅在任务私有源目录恢复为原始 UTF-8 名称，不进入候选 tree。

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [ ] **否**，上游已有测试用例覆盖
- [x] **是**，适配后补全了测试（目标平台运行闭包）

- 补全的测试范围：新增 1 个 OHOS/arm64 test_package consumer。
- 补全原因：上游 CTest 不能在 Windows 主机执行交叉编译的 AArch64 ELF，必须通过真实目标验证包可被消费者使用。
- 新增测试文件清单：
  1. `archives/p/pugixml/1.16/test_package/consumer.cpp` — 解析 XML、读取属性并执行 XPath。

## 验证结果

- 编译状态：通过
- 上游测试用例通过率：1/1（100%）
- 新增测试用例通过率：1/1（100%）
- OHOS 真机：10.62.150.125:8022，W3 `pugixml-1.16-w3-r002` PASS，目标 consumer RC=0，RELEASED/POSTRELEASE_PASS。

## 补充说明

- 关联 Issue：#2624
- 队伍名称：天天开心
- 申请人显示标识：2301_80739235
- 源分支：feat/pugixml-1.16
- 目标分支：OpenHarmonyPCDeveloper/build_in_harmonyos:main
- Conan 主包和 test_package 在 OHOS/arm64 交叉 profile 下编译、链接通过；交叉 ELF 不在 Windows 主机运行。
- r001 因 transfer 后 run-w3.sh 未恢复执行位而得到真实 RC126；该 run 未重放，已 RELEASED/POSTRELEASE_PASS。r002 重新冻结 payload 并在目标机用任务自有 native `binary-sign-tool` selfSign=1 后唯一 launch 通过。
- 归档源为 GitHub v1.16 官方 release archive，588574 bytes，SHA-256 `357bcab8877dc9943f355d3a72daba1b053238ba955f50fa81586afb65090219`。
