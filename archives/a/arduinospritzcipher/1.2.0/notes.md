# arduinospritzcipher 1.2.0 适配笔记

## 编译环境
- 构建系统: custom（无构建族：纯 C 源文件 src/SpritzCipher.c + src/SpritzCipher.h，无 configure/Makefile/CMake）
- 编译日期: 2026-09-22
- 编译器: clang 15（aarch64-unknown-linux-ohos，OHOS 交叉工具链）
- 状态: published（conan-verify G1-G4 + L2/L4/L5 全部通过）

## 编译步骤

1. 官方源下载：`https://github.com/abderraouf-adjal/ArduinoSpritzCipher/archive/refs/tags/v1.2.0.tar.gz`
   SHA-256 = `7446c8af872ebe7e0f22af3cb3b38051af33dec76030b05653cfc6e1a803fb0b`
2. init-build 初始化归档骨架与 .build-context
3. lang-preflight：task=cpp，detected=c（c↔cpp 兼容族，通过）
4. conan-init 生成配方骨架 → 按无构建族改写 conanfile.py：
   - build() 内用 Conan conf `tools.build:compiler_executables` 的 c 编译器
     执行 `cc -c SpritzCipher.c -o SpritzCipher.o` + `llvm-ar rcs libSpritzCipher.a`
     （R33：编译器取自 conf，不用裸 shell 环境变量）
   - package() 安装 libSpritzCipher.a → lib/、SpritzCipher.h → include/、LICENSE → licenses/
5. conan-verify：G1 配方完整性 → G2 conan create 干净构建 → G3 系统同名库隔离 →
   G4 产物完整性 → L2 smoke → L4 checksec → L5 基线，全部 PASS
6. 鸿蒙专项测试 test_ohos/run_ohos_test.py：T1 ELF64 AArch64、T2 musl（无 glibc）、
   T3 .codesign 段、T4 无宿主路径泄漏、T5 RS14 测试向量真实运行 → TEST_OHOS_ALL_PASS
7. 消费者验证 consumer/consumer_vault.c：仅公开头文件/API 链接最终静态库，
   口令哈希确定性 + 加密/解密 roundtrip + MAC → CONSUMER_VAULT_PASS

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build 直连 GitHub 下载超时 | 网络对 github.com 直连不稳定 | 用 curl 下载官方归档并核验 SHA-256 后放入 $TMPDIR/builds 预期路径，init-build 复用已有 tarball |
| 2 | conan-verify G1 失败 | 配方缺补丁应用调用 | conanfile.py build() 补 `apply_conandata_patches(self)` |
| 3 | conan-verify G2 链接失败 undefined symbol: spritz_random | test_package/test.c 误用不存在的 `spritz_random()` API | 核对头文件实际 API 为 `spritz_random8()`，修正 test.c |
| 4 | 生成配方为 autotools 模板 | 库无 configure/make 构建系统 | 按无构建族手动编译配方重写（参考 2048.c/headeronly 模式） |

## 源码修改

无补丁（上游源码原样编译，patches/ 为空）

## 依赖版本

- 无第三方依赖（库本身为纯 C 单翻译单元，仅依赖标准 C 头文件）

## 验证结果

```bash
# 上游测试：官方 tag 无独立测试框架/无 TEST_CASE（8 个 .ino 为 Arduino 样例，
# 按规则计入台账不计入独立用例；source_declared_total=0，全量通过率 0/0）
# 鸿蒙专项测试：
python3 test_ohos/run_ohos_test.py <pkg>   # → TEST_OHOS_ALL_PASS（T1-T5 全过）
# 消费者验证：
<clang> -O2 -I <pkg>/include consumer_vault.c -L <pkg>/lib -lSpritzCipher
./consumer_vault                              # → CONSUMER_VAULT_PASS
```

## 注意事项

- 本库为 Arduino 生态库但核心为纯 C，OHOS 直接可用；样例 .ino 依赖 Arduino 框架
  （Serial/pinMode），无法在 OHOS 直接运行，其 RS14 测试向量已移植到
  test_package/test.c 与 test_ohos/run_ohos_test.py 中实际运行验证。
- 无 commands.json：产物仅静态库（.a）+ 头文件，非 CLI 工具（R38 库类型无需声明）。
---

**编译结束**: 2026-09-22 13:22
**最终状态**: built
