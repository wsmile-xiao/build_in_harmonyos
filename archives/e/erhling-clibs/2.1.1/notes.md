# erhling-clibs 2.1.1 适配笔记

## 编译环境
- 构建系统: cmake（上游 CMakeLists.txt；conan-init 按 URL 误判 autotools，已改用 CMake 配方）
- 编译日期: 2026-09-26
- 编译器: clang 15.0.4 / clang++
- 平台: HarmonyOS PC (aarch64-linux-ohos)，Conan profile ci/conan/profiles/ohos-aarch64
- 状态: built（conan-verify 8 门禁全过，未 upload）

## 编译步骤

1. 上游核验：https://github.com/ennorehling/clibs 无 tag、无 release，钉住 master HEAD `289f980277e9a568042257e4f6b919960adb2eb7`（`git ls-remote` 核验），源码归档 tarball sha256=`6fa11a94070d82b29b99144113d92293a9df82512420506340301015409f530d`。
2. 本地验证编译（native cmake 构建 + ctest）：
   ```bash
   cmake .. -DCMAKE_INSTALL_PREFIX=... && make -j2 && ctest
   ```
   ctest 1/1 通过；直接运行 test_clibs 输出 `OK (51 tests)`。
3. conan-init 生成配方 → 人工修正：
   - conanfile.py 从 autotools 模板改写为 CMake 模板（上游是 CMakeLists.txt）。
   - conandata.yml 填入真实 sha256。
   - test_package/test.c 从 print-only 空壳改为真实调用库 API（str_strlcpy/str_strlcat/str_hash/str_escape，R34/PF3）。
   - 补 export_sources() 与 apply_conandata_patches()（G1 要求）。
4. conan-verify 8 门禁全过（G1 配方完整 / G0 预扫描 / G2 conan create / G3 系统同名库隔离 / G4 产物完整 / L2 smoke / L4 checksec / L5 基线）。
5. finish（W2 结构 + R36 依赖 + W3 本地 CI）：W3 首次因其他库（cloog/kics）main 基线空文件触发 JC 拦截，按 ohpc-executor 规则做审计式临时 index 隔离 → W3 复验通过 → 无条件恢复（index blob 与 HEAD blob 一致 e69de29…）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build 下载 GitHub URL 返回 HTML | GitHub tarball 通道受限 | 用 `git clone --depth 1` 取得源码，放入 build 双轨目录后 `--no-download` 引导 |
| 2 | conan-init 生成 autotools 模板 | 按 URL 猜测构建系统，上游实际是 CMake | 改写 conanfile.py 为 CMake 模板 |
| 3 | G1 配方完整性 FAIL | 缺 export_sources()/补丁应用调用 | 补 export_conandata_patches/apply_conandata_patches |
| 4 | test_package 空壳测试 | 模板默认 print-only | 重写 test.c 真实调用库 API |
| 5 | W3/JC 拦截 | main 基线其他库（cloog/kics）空状态文件被 full-mode ls-files 命中 | 临时 index 隔离 → 复验 → 无条件恢复（审计记录于 ~/tmp/builds/baseline-isolation-audit.txt） |

## 源码修改

无需补丁（上游 CMakeLists.txt 可直接构建，无平台宏注入）。

## 依赖版本

- 无第三方依赖（单文件 C 库集合，仅依赖 libc/libm）

## 验证结果

```bash
# 上游测试（本机 native 构建）
ctest: 1/1 passed; test_clibs: OK (51 tests)
# Conan 交叉构建（ohos-aarch64 profile）
conan create: PASS (G2)
# 消费者测试（test_package）
test_erhling-clibs: str_strlcpy/str_strlcat/str_hash/str_escape 全部通过
```
---

**编译结束**: 2026-09-26 22:20
**最终状态**: built
