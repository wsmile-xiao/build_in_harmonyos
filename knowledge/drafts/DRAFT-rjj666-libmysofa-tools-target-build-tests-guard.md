# DRAFT-rjj666-libmysofa-tools-target-build-tests-guard

## 基本信息
- **严重度**: 2
- **类别**: cmake | packaging | conan | tools-package
- **作者**: rjj666

## 错误特征
```
conan 包 bin/ 为空；test_package 调 mysofa2json 报 command not found
```

## 根因分析
上游 src/CMakeLists.txt 把 mysofa2json 的 add_executable 与
install(TARGETS) 放在 if(BUILD_TESTS) 块内。-tools 适配包关闭
BUILD_TESTS 后工具目标整体消失——"工具与测试开关耦合"的上游
CMake 结构缺陷。

## 推荐方案
**方法**: unguard-tool-install-target（补丁将工具目标与 install 移出测试守卫）

**说明**: 将 add_executable 与 install(TARGETS) 移到守卫外并保留依赖接线，
BUILD_TESTS=OFF 时工具照常交付；配方 package_info() 声明 bindirs=["bin"]。
判定要点：适配 -tools 包先查工具目标的守卫归属，再定开关。

## 验证
```bash
conan create archives/l/libmysofa-tools/1.3.2  # test_package 3/3
```

## 来源
- 草稿: DRAFT-rjj666-libmysofa-tools-target-build-tests-guard
- 关联: E235, E321, E322, E476
- 提升日期: 待审核
