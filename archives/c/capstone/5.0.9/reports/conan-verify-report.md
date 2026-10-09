# Conan Verify Report — capstone 5.0.9

**Verdict**: FAIL
**Reference**: `capstone/5.0.9@ohpcd/stable`
**Profile**: ohos-aarch64
**Date**: 2026-09-28T08:16:48.628086

## G0: ✅ PASS
  📦 构建系统: cmake
  ✅ 已知风险 E092 已在配方中处理
     CMake 不认识 HarmonyOS 作为目标平台，
没有对应的 platform module。
当 CMake 检测到系统名称为 harmonyos/ohos 时，
无法匹配任何已知平台（Lin

## G1: ✅ PASS
  ✅ name 声明
  ✅ version 声明
  ✅ source() 方法
  ✅ build() 方法
  ✅ package() 方法
  ✅ package_info() 方法
  ✅ export_sources() 方法
  ✅ 补丁应用调用
  ✅ R26: 系统同名库静态链接配置存在
  ✅ conandata.yml 完整
  ✅ test_package/ 存在 (R28)
  ✅ test_package/MANIFEST.yml 存在

## G2: ❌ FAIL
**Knowledge hit**: E540
  ❌ conan create 失败:
     Error relocating ./test_probe: cs_strerror: symbol not found
     ERROR: capstone/5.0.9@ohpcd/stable (test package): Error in test() method, line 41
  📄 日志: archives/c/capstone/5.0.9/reports/conan-create.log
    🧠 知识图谱命中: E540 (评分:9608)
     根因: The OHOS Conan profile can point CC/CXX to /data/service/hnp/bin/clang, so configure succeeds, while later recipe comman
     方案: runner-path-prepend
     命令: EXTRA_PATH=/data/service/hnp/bin:/data/service/hnp/cmake.org/cmake_4.1.2/bin:$HOME/usr/local/bin:$HOME/.local/bin:$HOME/
     文档: knowledge/drafts/zlib-shadow-ci-hnp-tool-path.md
