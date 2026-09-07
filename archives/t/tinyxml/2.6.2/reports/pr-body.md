## PR 信息

- 三方库名称：tinyxml
- 上游版本：v2.6.2
- 上游仓库地址：https://sourceforge.net/projects/tinyxml/
- 适配路径：路径 A（基础适配）+ 路径 B（贡献知识扩展）
- 使用知识库：openharmony-compile-agent；E554、E555
- 任务 Issue：待创建

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------:|------|
| 单元测试 | 1 | 官方 `xmltest.cpp` 可执行测试程序，运行 109 个断言 |
| 集成测试 | 0 | 上游未提供独立集成测试目标 |
| 其他测试 | 0 | 上游未提供其他测试目标 |
| **合计** | **1** | **1/1 可执行测试通过，109/109 断言通过** |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------:|------------|------|
| 单元测试 | 1 | 不变 | 独立主机运行官方 `xmltest`，109/109 断言通过 |
| 集成测试 | 0 | 不变 | 无 |
| 鸿蒙特有测试 | 1 | 新增 | `test_package/consumer.cpp` 在 OHOS/arm64 真机解析 XML，RC=0 |
| **合计** | **2** | **+1 个目标 consumer** | 上游分母与目标 consumer 分开记录 |

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例
- [ ] **是**，存在对上游测试用例的修改（请在下方逐条说明）

上游 `xmltest.cpp` 和实现源文件未修改；任务私有构建目录中的对象文件不进入候选 tree。

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [ ] **否**，上游已有测试用例覆盖
- [x] **是**，适配后补全了目标平台测试

- 补全的测试范围：新增 1 个 OHOS/arm64 test_package consumer。
- 补全原因：交叉编译的 AArch64 ELF 不能在 Windows 构建机执行，必须验证目标平台消费者闭包。
- 新增测试文件清单：`archives/t/tinyxml/2.6.2/test_package/consumer.cpp`，覆盖 XML 解析、属性/文本读取、实体展开和序列化。

## 验证结果

- 编译状态：通过
- 上游测试用例通过率：1/1（100%）
- 新增测试用例通过率：1/1（100%）
- 上游断言结果：109/109（100%）
- OHOS 真机：10.62.150.125:8022，W3 `tinyxml-2.6.2-w3-r003` PASS，目标 consumer RC=0，RELEASED/POSTRELEASE_PASS。

## 补充说明

- 关联 Issue：#2632
- 队伍名称：天天开心
- 申请人显示标识：2301_80739235
- 源分支：2301_80739235:feat/tinyxml-2.6.2
- 目标分支：OpenHarmonyPCDeveloper/build_in_harmonyos:main
- Conan OHOS/armv8 交叉构建生成 `libtinyxml.a` 和两个公共头文件；Windows host profile 消费者实际输出 `tinyxml consumer PASS`。
- 上游只有硬编码 GNU Makefile，配方提供任务私有 CMake install/export 入口，不改动上游实现。
- `r001` 因 transfer 回执的 boot_id 换行污染 fail closed 后清理；`r002` 因 CRLF shell 终态 RC127 fail closed 后清理；二者均未重放 launch。`r003` 使用 LF 脚本、native `binary-sign-tool selfSign=1` 唯一 launch 通过。
- 源码归档：Debian 官方镜像 `tinyxml_2.6.2.orig.tar.gz`，210124 bytes，SHA-256 `15bdfdcec58a7da30adc87ac2b078e4417dbe5392f3afb719f9ba6d062645593`。
