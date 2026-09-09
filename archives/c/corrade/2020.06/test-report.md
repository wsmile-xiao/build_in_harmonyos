# corrade 2020.06 功能测试报告

**测试日期:** 2026-09-06
**测试环境:** HarmonyOS (HongMeng Kernel 1.12.0, aarch64)
**编译器:** clang 15.0.4 (OHOS SDK 26.0.0.18, target aarch64-linux-ohos)
**构建系统:** CMake 4.1.2

## 1. 编译测试

### 1.1 编译状态
✅ 完整构建成功(库 + 87 个测试目标)

### 1.2 源码修改
- 11+2 个适配补丁(平台识别、插件 SHARED 链接、C++20 标准注入),详见 `patches/` 与 `conandata.yml`

## 2. 上游测试

### 2.1 运行方式
```bash
cd build && ctest   # 87 个测试目标
```

### 2.2 结果
- 86/87 通过
- 1 个失败: UtilityDirectoryTest(7 检查项,均为 OHOS 平台环境差异: `/tmp` 只读、无 sysfs cpufreq、OHOS 配置目录布局、corrade-rc 未部署测试 bin)
- 全量通过率: 1564/1571 (99.55%) — 完整双口径台账见 `notes.md`

## 3. 鸿蒙专项测试 (test_package)

### 3.1 用例
`test_package/test.cpp` — 6 项断言:
1. CORRADE_TARGET_OHOS 宏已定义
2. CORRADE_TARGET_UNIX 宏已定义
3. Utility::String::join 输出正确
4. Utility::String::split 输出正确
5. Containers::Array 求和正确
6. Containers::Optional 解引用正确

### 3.2 运行结果
```
PASS: CORRADE_TARGET_OHOS is defined
PASS: CORRADE_TARGET_UNIX is defined
PASS: String::join -> a,b,c
PASS: String::split -> 3 parts
PASS: Containers::Array sum = 49
PASS: Containers::Optional = 5
corrade OHOS consumer test: ALL PASSED   (exit 0)
```

## 4. 消费者验证 (conan create)
✅ conan-verify 全部通过 (G0-G4), 配方 `corrade/2020.06@ohpcd/stable` 可复现构建

## 5. 结论
- 库本体 + 全部模块在 HarmonyOS aarch64 上编译运行正常
- 6 项鸿蒙专项断言全部通过
- 7 项上游测试平台差异已记录为 quality_warnings(非库缺陷)
