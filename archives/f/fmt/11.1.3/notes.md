# fmt 11.1.3 适配笔记（R01, executor pc2-2）

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-02
- 编译器: Clang 15.0.4 (HarmonyOS NDK)
- 状态: built

## 编译步骤

### 1. 配置（C++20 测试构建，最大化启用上游门控用例）
```bash
cmake .. -DCMAKE_BUILD_TYPE=Release -DCMAKE_CXX_STANDARD=20 \
  -DFMT_TEST=ON -DFMT_DOC=OFF -DFMT_PEDANTIC=OFF -DCMAKE_INSTALL_LIBDIR=lib
make -j$(nproc)
```

### 2. 上游测试
```bash
ctest --output-on-failure   # 21 目标，20 通过，1 失败（format_test.line_buffering，平台行为）
```

### 3. Conan 配方验证
```bash
python3 scripts/ohc-run.py conan-verify fmt 11.1.3   # G1-G4 + L2/L4/L5 全 PASS
```

### 4. HarmonyOS 专项测试（新增，真实可执行）
```bash
clang++ -std=c++20 -I include ohos-special-test.cc build-test/libfmt.a \
  -o ohos-special-test.bin && ./ohos-special-test.bin   # 10 组全过，exit 0
```
覆盖：FMT_VERSION / 基础与位置参数 / 浮点·进制·对齐 / format_to(memory_buffer) /
sprintf / join(ranges) / chrono 时间点 / fmt/std.h optional / to_wstring(xchar 宽字符) /
color 输出。预期值均 OHOS 工具链实测（11.x 八进制前缀 "0"；time_point 默认微秒精度）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | format_test.line_buffering 失败（Expected n=42, got n=0） | HarmonyOS 平台文件行缓冲语义与 POSIX 差异 | 接受为平台限制，记录在案；与历史归档 11.2.0-r1 `file_test.line_buffering` 同因 |
| 2 | lang-preflight 判 mixed（gradle/maven） | `support/build.gradle` 是 Android AAR 打包辅助脚本（externalNativeBuild 指向根 CMakeLists.txt），检测器全树匹配误当主 manifest | 按 R47"辅助脚本不算主体"边界规则复核：过滤辅助脚本后检测为 cpp/cmake，继续主线 |
| 3 | conan-init 生成 autotools 模板 | 模板按 Autotools 假设生成，fmt 实为 CMake 项目 | 按历史 12.2.0 验证配方重写为 CMake 配方（OHOS soname 修复 + FMT_INSTALL + 签名） |

## 源码修改

无源码补丁（0 patch，上游源码直接可用 OHOS 工具链构建）。

## 依赖版本

- CMake: 4.1.2
- Clang: 15.0.4 (OHOS NDK)
- Conan: 2.29.1（社区源 OHOS 适配版）
- 无外部第三方依赖

## 验证结果

```bash
# 上游测试（C++20）：全量 551/599 ≈ 92.0%（含上游设计的 module 测试不可运行项）
#   实际执行通过率 551/552 ≈ 99.8%，唯一失败为 line_buffering 平台行为
# ctest 目标级：21 目标 20 通过 / FMT_PEDANTIC=ON 25 目标 24 通过
# 专项测试：10 组全过；test_package 消费者 probe：11 组全过（conan create 实测）
# 详细台账: reports/upstream-test-ledger.md
```

## 交付物

| 文件 | 说明 |
|------|------|
| lib/libfmt.a / .so | 静态库 / 动态库（按 shared option） |
| include/fmt/*.h | 14 个头文件 |
| lib/cmake/fmt/ | CMake 配置文件 |
| lib/pkgconfig/fmt.pc | pkg-config 文件 |

## 注意事项

1. **平台限制**: file_test.line_buffering 因 HarmonyOS 文件缓冲行为差异失败，不影响核心格式化功能（11.2.0-r1 同样记录）。
2. **OHOS cmake 平台名**: recipe 中必须把 CMAKE_SYSTEM_NAME 设为 "OHOS"（而非 conan 默认 "HarmonyOS"），否则产物无 DT_SONAME（8.1.1/12.2.0 同因）。
3. **includedirs 不外扩**: include/fmt 含 locale.h，进 -isystem 会遮蔽 musl 头（8.1.1 实证）。
4. **C++ 标准**: 库本身 C++11 可编；测试用例（compile 系列）需 C++20 才全量启用。
5. **知识路径判断**: 无新错误模式（唯一失败为既有平台限制，11.2.0-r1 已记录），无新增知识草稿 → 按任务头【依赖项】路径，不升级【知识库扩展】。

---
**编译结束**: 2026-09-02 15:10
**最终状态**: built
---

**编译结束**: 2026-09-02 15:26
**最终状态**: built
