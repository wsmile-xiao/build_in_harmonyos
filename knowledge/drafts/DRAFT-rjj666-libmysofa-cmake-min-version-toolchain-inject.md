# DRAFT-rjj666-libmysofa-cmake-min-version-toolchain-inject

## 基本信息
- **严重度**: 2
- **类别**: cmake | toolchain | conan | cross-compile
- **作者**: rjj666

## 错误特征
```
交叉 configure 期报编译器/系统名相关错误；toolchain 文件内容正确却"不生效"
```

## 根因分析
顶层 cmake_minimum_required(VERSION 2.8.12) 使 CMake 进入旧版兼容分支，
conan toolchain 文件在 project() 初始化阶段的变量注入被按旧语义处理，
交叉编译变量静默失效。

## 推荐方案
**方法**: bump-cmake-min-version-3.5（补丁升级最低版本声明）

**说明**: 提升到 3.5 官方兼容线后 project() 按现代语义消费 toolchain 变量。
排查顺序：toolchain 文件内容 → 顶层 min version → 最后才动生成逻辑。

## 验证
```bash
# 升级声明后同参数 conan create configure 直接通过（真机全绿）
```

## 来源
- 草稿: DRAFT-rjj666-libmysofa-cmake-min-version-toolchain-inject
- 关联: E103, E104, E187
- 提升日期: 待审核
