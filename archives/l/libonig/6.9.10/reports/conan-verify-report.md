# Conan Verify Report — libonig 6.9.10

**Verdict**: FAIL
**Reference**: `libonig/6.9.10@ohpcd/stable`
**Profile**: ohos-aarch64
**Date**: 2026-09-19T12:41:12.962378

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
**Knowledge hit**: E422
  ❌ conan create 失败 (RC=1)
  📄 失败摘要已保留在本报告；原始日志未随 PR 入库。
    🧠 知识图谱命中: E422 (评分:86)
     根因: Windows 特有的错误码或 API 调用在非 Windows 平台编译失败
     方案: 添加平台条件编译宏，隔离 Windows 特有代码
     命令: 在受影响的源文件中添加条件编译宏，或在 CMakeLists.txt 中使用 if(WIN32) 控制源文件编译
     文档: doc/E422.md
