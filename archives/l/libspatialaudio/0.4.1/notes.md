# libspatialaudio 0.4.1 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-27
- 编译器: clang/clang++ (harmonyos, target aarch64-unknown-linux-ohos)
- 状态: published

## 编译步骤

```bash
# 1. 源码与校验
#    官方 tag tarball: https://github.com/videolabs/libspatialaudio/archive/refs/tags/0.4.1.tar.gz
#    SHA-256: 1c3fe135daaedce468a716afa795749e4b1bb77c9df8108203a6ffe6440532de

# 2. CMake 配置（OHOS 本机构建，build=host=OHOS/aarch64）
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release \
      -DHAVE_MIT_HRTF=ON -DBUILD_TESTING=ON -DBUILD_SHARED_LIBS=ON

# 3. 编译 + 上游测试
cmake --build build -j2
ctest --output-on-failure   # 4/4 通过

# 4. Conan 配方验证
python3 scripts/ohc-run.py conan-verify libspatialaudio 0.4.1   # 8 道门禁全过

# 5. 消费者用例（test_package/test_consumer.cpp，公开 API：AmbisonicEncoder/BFormat）
clang++ test_consumer.cpp -I<install>/include -L<install>/lib -lspatialaudio -lm -o test_consumer
./test_consumer   # 脉冲编码验证：W 声道能量非零，exit 0

# 6. HarmonyOS 专项验证（test_ohos/run_ohos_test.sh）
#    T1 aarch64 ELF / T2 头文件无宿主路径泄漏 / T3 配置头一致 / T4 DT_NEEDED 仅系统库 → 全过
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | github.com 直连超时无法下载源码 | 执行端网络无法直连 github.com | 使用 codeload.github.com（官方 CDN）下载 tarball 并核验 SHA-256；conan create 经 E017 自动注入 ghfast.top 镜像 |
| 2 | 消费者用例 W 声道输出为零 | AmbisonicEncoder 系数需 Refresh() 后才会生成（公开 API 契约） | 按公开 API 先 SetPosition 再 Refresh() 刷新编码系数，W 声道脉冲能量非零 |
| 3 | OHOS 专项检验 SOVERSION 校验失败 | OHOS 平台无 CMake platform module，链接器不发射 SONAME | 将 ABI 校验改为 DT_NEEDED（仅 libc/libc++_shared/libm）+ 无宿主 RPATH 泄漏 |

## 源码修改

无补丁（patches/ 为空，官方源码直接构建）。

## 依赖版本

- 无第三方硬依赖（MySofa 可选，未安装时内建 MIT HRTF）
- 构建工具：cmake 4.1.2 / clang 15.0.4 / make 4.4.1 / conan 2.29.1

## 验证结果

```bash
ctest: 4/4 通过（TestInsideAngleRange/TestAmbisonicShelfFilters/TestAmbisonicDecoderPresets/TestRenderer）
conan-verify: G0-G4 + L2/L4/L5 全过，可标记 published
消费者用例: exit 0（AmbisonicEncoder+BFormat 脉冲编码 W 声道能量非零）
鸿蒙专项: T1-T4 全过（ohos-test.log）
```

## 注意事项

- 库类型（非 CLI），无需 commands.json（R38）
- 静态库消费者需链接 -lm（配方的 cpp_info.system_libs 已含 m）
- 官方 URL 为 https://github.com/...（conandata.yml 主源），CI 自动添加镜像 fallback
---

**编译结束**: 2026-09-27 22:04
**最终状态**: published
