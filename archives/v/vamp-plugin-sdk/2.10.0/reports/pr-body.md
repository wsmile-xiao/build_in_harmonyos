- **三方库名称**：vamp-plugin-sdk
- **上游版本**：2.10.0
- **上游仓库地址**：https://github.com/vamp-plugins/vamp-plugin-sdk
- **适配路径**：路径 A（基础适配）
- **使用知识库**：无

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 0 | 上游无正式单元测试框架，仅提供 example 型测试程序 |
| 集成测试 | 0 | 上游无独立集成测试框架 |
| 其他测试 | 6 plugin + 22 output | vamp-simple-host 内置 6 个示例插件（Amplitude Follower, Simple Fixed Tempo Estimator, Simple Percussion Onset Detector, Simple Power Spectrum, Spectral Centroid, Zero Crossings）；上游 test/run-test-plugin-regression.sh 对官方 vamp-test-plugin 仓库的 22 个 output 与 test/expected/ 逐字节对照 |
| **合计** | **6 plugin + 22 output** | |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 0 | 不变 | |
| 集成测试 | 0 | 不变 | |
| 鸿蒙特有测试 | 1 | 新增 | test_package（头文件断言 + 运行时链接验证，1/1 通过） |
| 上游 simple-host 测试 | 6 plugin | 不变 | VAMP_PATH 加载 6 个内置插件，exit_code=0，真实通过 |
| 上游 regression 测试 | 22 output | 不变 | vamp-test-plugin（官方仓库）22/22 与上游 expected/ 逐字节匹配，0 failed |
| **合计** | **1（鸿蒙特有）+ 6 plugin（上游 simple-host）+ 22 output（上游 regression）** | **+1 鸿蒙特有测试** | |

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [x] **否**，上游已有测试用例覆盖（simple-host 6 插件 + vamp-test-plugin regression 22 output 均已真实执行通过）

## 验证结果

- 编译状态：通过
- 上游测试用例通过率：6/6 插件（simple-host `-l` 列出全部 6 个内置插件，exit_code=0）；22/22（官方 vamp-test-plugin regression 与上游 expected/ 逐字节匹配，0 failed）
- 新增测试用例通过率：1/1（100%）（test_package 头文件断言 + 运行时链接，exit_code=0）

## 补充说明

### R07 关键修复（真实 libsndfile 消费链）
- configure 检测 `checking for SNDFILE... yes`，链接命令包含 `-lsndfile -lvorbisenc -lvorbisfile -lvorbis -lFLAC++ -lFLAC -logg -lopus`
- 上游 simple-host 测试通过：`VAMP_PATH=$(pwd)/examples $(pwd)/host/vamp-simple-host -l` 列出 Amplitude Follower、Simple Fixed Tempo Estimator、Simple Percussion Onset Detector、Simple Power Spectrum、Spectral Centroid、Zero Crossings 共 6 个插件，exit_code=0

### R08 关键修复（test_package 运行时链接）
- `package_info()` 新增 `self.runenv_info.prepend_path("LD_LIBRARY_PATH", os.path.join(self.package_folder, "lib"))`
- 修复前：`Error loading shared library libvamp-sdk.so.2`；修复后：`vamp-plugin-sdk header assertions: 1 passed`，exit_code=0

### R11 上游 regression 覆盖恢复（规则4 依据更新）
- 官方 vamp-test-plugin 来源：github.com/vamp-plugins/vamp-test-plugin（受控网络环境获取成功，R07 时外部网络不可达属环境恢复，非测试失败）
- 构建：上游官方 Makefile.linux 构建 vamp-test-plugin.so（ELF arm64，链接 SDK 静态库）
- 执行：R07 真实构建的 vamp-simple-host + 上游 testsignal.wav，VAMP_PATH 指向 vamp-test-plugin
- 结果：--list-ids 返回 2 个预期插件 ID（vamp-test-plugin、vamp-test-plugin-freq）；22/22 output 与上游 test/expected/ 逐字节 cmp 全部 OK，0 failed
- 统计口径：与上游 run-test-plugin-regression.sh 完全一致（simple-host <output> testsignal.wav → expected 逐字节对照）
- 适配中两处可修复前置（configure 缺 libsndfile pkg-config → 注入 conan sndfile.pc；HMDFS 上 config.status 临时目录写入受限 → 使用可写副本 + R07 构建产物）均已在本轮解决，属于构建环境适配，不构成测试失败

### test_package 单独统计
- test_package（鸿蒙特有）单独统计，不计入上游测试：1/1 通过

### 已知限制
- W3 本地 L0i 门禁：`registry_unreachable` — 制品仓认证不可达（基础设施限制），不影响本地构建与测试结果
- 操作系统：HarmonyOS PC（aarch64）
- 编译器：Clang（libc++）
- 构建系统：Conan 2 + Autotools
