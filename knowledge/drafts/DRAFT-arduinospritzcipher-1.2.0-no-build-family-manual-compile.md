# 无构建系统纯 C 源文件库（Arduino 生态布局）的 Conan 手动编译配方

> 知识草稿（DRAFT-arduinospritzcipher-1.2.0-no-build-family-manual-compile）
> 来源库：arduinospritzcipher 1.2.0（Abderraouf Adjal / ArduinoSpritzCipher）

## 问题

Arduino/嵌入式生态库常以「源码包」形态发布：`src/*.c(+.h)` + `examples/*.ino` +
`library.properties`，不附带任何构建系统（无 configure、无 Makefile、无
CMakeLists.txt）。`conan-init` 的构建系统猜测器按 URL/关键字推断为 autotools，
生成的 autotools 模板 `Autotools.configure()` 因无 configure 脚本必然失败。

## 根因

无构建族（no-build-family）库被构建系统猜测器误判为 autotools；模板与库实际
形态（纯 C 源文件、无任何构建入口）不匹配。G1 配方完整性门禁同时要求
`build()` 内显式调用 `apply_conandata_patches()`（静态结构检查必填）。

## 方案

`conanfile.py` 采用无构建族手动编译模式：

1. `build()` 内从 `self.conf.get("tools.build:compiler_executables", default={},
   check_type=dict)` 取 c 编译器（R33，禁止裸 shell 环境变量）：
   `cc -c SpritzCipher.c -o SpritzCipher.o -I<src>`；静态库用
   `llvm-ar rcs libSpritzCipher.a SpritzCipher.o`（ar 从 conf / llvm-ar / ar
   依次取）；shared 用 `cc -shared`。
2. `package()` 安装 `libSpritzCipher.a → lib/`、`SpritzCipher.h → include/`、
   `LICENSE → licenses/`。
3. `package_info()` 设 `cpp_info.libs = ["SpritzCipher"]`。
4. `build()` 首行必须 `apply_conandata_patches(self)`（G1 结构门禁必填）。
5. 测试三件套：
   - `test_package/test.c`：用真实公开 API 断言（RS14 hash 向量、crypt
     roundtrip、mac 确定性、PRNG 种子确定性）；
   - `test_ohos/run_ohos_test.py`：移植上游样例内测试向量为原生 C 测试实际
     运行（T1 ELF64 AArch64 / T2 musl / T3 .codesign / T4 路径泄漏 /
     T5 密码学向量），独立于上游与 test_package 计数；
   - `consumer/consumer_vault.c`：模拟业务上层组件，仅用公开头文件/API/
     正常链接目标。
6. 无 CLI 产物 → 不创建 `commands.json`（R38 仅 tool 类型需要）。

## 验证

- `conan-verify`：G1（配方完整性）、G2（conan create 干净构建）、G3（系统
  同名库隔离）、G4（产物完整性）、L2/L4/L5 全部 PASS（EXIT:0）。
- `test_package`：ALL_PASS。
- `test_ohos`：TEST_OHOS_ALL_PASS（T1-T5 全过，含 RS14 hash('ABC') 向量）。
- `consumer`：CONSUMER_VAULT_PASS。
- 官方 tarball SHA-256：
  `7446c8af872ebe7e0f22af3cb3b38051af33dec76030b05653cfc6e1a803fb0b`。
- 上游测试双口径：source_declared_total=0（官方 tag 无独立测试框架；
  8 个 .ino 为 Arduino 样例，依赖 Serial/pinMode，按规则计入台账不计入
  独立用例），全量通过率 0/0；样例内测试向量已移植为鸿蒙专项测试实际运行。

## 适用边界

- 适用：无任何构建系统但含需编译 `.c/.cpp` 翻译单元的库（Arduino 生态
  library.properties 布局、嵌入式单文件库等）。
- 反例：header-only 库走 E257（no-op build()）；含 Makefile 的 raw makefile
  库走 E392（raw-makefile-conan-recipe-pattern）；纯资源/数据包走
  E305/E536。本模式仅覆盖「无构建系统但有 .c 需编译」的空白带。

## 关系

- similar_to：E392（raw makefile 配方模式）、E257（header-only G1 门禁）
- caused_by：conan-init 构建系统猜测器将无构建族误判为 autotools
- prerequisite_of：无
- conflicts_with：无

## 查重差异（vs 既有条目）

- E392 覆盖「有 Makefile」的 raw makefile（BadZipFile 编码器误选 /
  compiler_executables dict / make cwd 三陷阱）；本候选为「无 Makefile 也
  无 configure/CMake」的纯源文件库，手动 cc -c + llvm-ar，且含 Arduino
  生态布局与样例测试向量移植的测试迁移新增（test_migration_novelty=true）。
- E257 覆盖 header-only（无需编译）；本候选需编译 .c，边界不同
  （boundary_novelty=true）。
- 七轴查重：exact=false、causal=false、trigger=partial、solution=partial、
  combination_novelty=true、boundary_novelty=true、test_migration_novelty=true。
