- **三方库名称**：openbabel（Open Babel，C++ 化学信息学工具箱）
- **上游版本**：v3.1.1
- **上游仓库地址**：https://github.com/openbabel/openbabel
- **适配路径**：路径 A（基础适配）+ 路径 B（贡献创新：新增知识库条目 E545/E546/E547）
- **使用知识库**：本次新增沉淀知识草稿 E545（CMake>=4 兼容：CMAKE_POLICY_VERSION_MINIMUM 须命令行传入 + 显式 policy OLD 需补丁改 NEW）、E546（conan CMakeToolchain 强制 CONFIG 优先后上游 Module 风格全大写 <PKG>_FOUND 判断失效 → 静默回退错误分支）、E547（静态配方 + 制品仓 shared-only 依赖：FIND_LIBRARY_SUFFIXES 钉 .a 与全静态链接的双重冲突）；复用既有清单 #24（HMDFS symlink 实体化）、E092（CMAKE_SYSTEM_NAME 强制 Linux）。

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 164 | 来源：test/test_runner（obtest.h 新式 CTest，29 模块 159 例 + align(Eigen3) 5 例），ctest 注册口径 |
| 集成测试 | 48 | 来源：test/test_runner 旧式 30 源 44 例 + cmlreadfile 1 例（静态+WITH_STATIC_LIBXML 下注册）+ test_inchiwrite 3 例 |
| 其他测试 | 1 | 来源：test/test_depiction.sh（TEST_DEPICTION 默认 OFF，依赖 ImageMagick，未计入运行） |
| **合计** | **212** | `ctest -N` 口径（本适配配置：静态构建 + Eigen3 + LibXml2 + InChI） |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 164 | 不变 | 上游测试源码未修改，注册条件随 Eigen3/LibXml2 大小写兼容补丁保持完整 |
| 集成测试 | 48 | 不变 | 同上 |
| 鸿蒙特有测试 | 1 | 新增 | test_package 消费者端到端测试（test_openbabel.cpp：SMILES 解析→规范化/分子式→MOL 往返→InChI 生成→MW 描述符，11 项断言，真机实跑） |
| **合计** | **213** | **+1** | |

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例
- [ ] **是**，存在对上游测试用例的修改（请在下方逐条说明）

> 说明：patches/0005-test-CMakeLists.txt.patch 仅调整 test/CMakeLists.txt 的**构建/注册条件**（CONFIG 模式 found 变量大小写兼容、OHOS 部分静态链接开关），不修改任何测试用例的源码与断言。

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [ ] **否**，上游已有测试用例覆盖
- [x] **是**，上游无测试用例，适配后补全了测试（请在下方说明）

> - **补全的测试范围**：新增 1 个鸿蒙特有消费者端到端测试（11 项断言），验证打包库在 OHOS 真机上的完整消费链路
> - **补全原因**：上游 CTest 用例为库内测试；本项从消费者视角验证包配置（头文件路径/链接闭包/运行期数据文件 BABEL_DATADIR/共享依赖加载）在鸿蒙 PC 上真实可用
> - **新增测试文件清单**：
>   1. `test_package/test_openbabel.cpp` — OBConversion/OBMol/InChI/OBDescriptor 全链路消费者测试

## 验证结果

- 编译状态：通过（conan create 全绿；conan-verify G0–G4 + L2/L4/L5 全 PASS；W3 本地 CI 模拟通过）
- 上游测试用例通过率：28/28（100%，代表性子集真机实跑；全量 212 项中长耗时数值套件未执行，未执行原因逐类记录于 conanfile.py HMBS_UPSTREAM_TEST_RESULT.gaps 与 test_package/MANIFEST.yml）
- 新增测试用例通过率：1/1（100%，test_package 真机实跑 11/11 断言通过）

## 补充说明

- 构建配置：静态库（BUILD_SHARED=OFF，格式全部编译进 libopenbabel.a，规避 HMDFS 运行期 dlopen 插件波动）+ bundled inchi/rapidjson；maeparser/coordgen（Maestro 格式）显式关闭——需 boost 且属可选格式插件，上游原生支持 graceful degrade。
- 依赖：zlib/1.3.1（静态）、libxml2/2.15.3（共享，制品仓仅有共享二进制，与仓内 abiword 系消费先例一致）、eigen/3.4.0（header-only）。静态 libopenbabel.a 引用 libxml2 符号，cpp_info.requires 已声明传递闭包。
- OHOS 适配补丁 5 个（全部 patch_type=portability）：CMake>=4 策略兼容、CMAKE_FIND_LIBRARY_SUFFIXES 放宽、CONFIG 模式 found 变量大小写兼容（Eigen3/LibXml2）、musl pthread 在 libc（无独立 libpthread）、test_runner/obabel 部分静态链接开关。
- obabel 命令行工具随包交付（软件级 commands.json 已登记，type=tool）。
- 已知限制：Maestro（maeparser/coordgen）格式不可用；TEST_DEPICTION 依赖 ImageMagick 未启用；上游 184 项 CTest 长耗时用例未在真机执行（原因与分类见 gaps 申报）。
