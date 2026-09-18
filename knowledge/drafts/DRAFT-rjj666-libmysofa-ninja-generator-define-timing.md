# DRAFT-rjj666-libmysofa-ninja-generator-define-timing

## 基本信息
- **严重度**: 1
- **类别**: conan | cmake | generator | environment | silent-failure
- **作者**: rjj666

## 错误特征
```
clang 无声 exit 1（无任何编译诊断）；make recipe Error 127；
同一配方 conan 进程树内必挂、交互 shell / 树外脚本全过
```

## 根因分析
1) 本机 conan 进程树内 make recipe 的 /bin/sh→clang exec 存在环境回归
   （shim 捕获 Permission denied）。conan 默认无 ninja 时回退
   "Unix Makefiles" → 撞上回归 → 静默失败。ninja 直接 fork/exec，
   不经 /bin/sh -c 包装，不受影响。
2) 时机语义：CMakeToolchain 构造时即读取 generator conf；
   test_package 属性式 generators 更是在 generate() 之前实例化。

## 推荐方案
**方法**: explicit-ninja-generator-plus-define-before-toolchain

**说明**: 配方 generate() 中 conf.define("tools.cmake.cmaketoolchain:generator",
"Ninja") 必须放在 CMakeToolchain 构造之前；test_package 属性式生成器
则放 configure()。判定路径：树内挂树外过 → 显式 Ninja；
命令行 -c 注入成功而配方 define 无效 → 时机问题。

## 验证
```bash
conan create archives/l/libmysofa-tools/1.3.2 -pr:h ohos-aarch64 -pr:b ohos-aarch64
# 修复后 RC=0，test_package 3/3
```

## 来源
- 草稿: DRAFT-rjj666-libmysofa-ninja-generator-define-timing
- 关联: E099, E123, E153, E286
- 提升日期: 待审核
