# ceres-solver 2.2.0 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-08-06
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 从 GitHub 下载 ceres-solver-2.2.0.tar.gz 源码包
2. 解压并创建 build 目录
3. 配置 CMake（关键选项）:
   ```bash
   cmake .. \
     -DCMAKE_BUILD_TYPE=Release \
     -DBUILD_EXAMPLES=OFF \
     -DBUILD_TESTING=OFF \
     -DMINIGLOG=ON \
     -DGFLAGS=OFF
   ```
4. 并行编译: `make -j6`
5. 安装: `make install DESTDIR=$TEST_PREFIX`
6. Conan 配方生成与验证

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Bazel BUILD 文件冲突 | 源码包含 Bazel BUILD 文件，与 CMake build 目录冲突 | 在 source() 中删除 BUILD 文件 |
| 2 | Eigen/Core 头文件找不到 | cpp_info 未声明传递依赖 | 添加 cpp_info.requires = ["eigen::eigen"] |
| 3 | glog/logging.h 找不到 | MINIGLOG 头文件路径未声明 | 添加 include/ceres/internal/miniglog 到 includedirs |
| 4 | cmake.build(args=...) API 不兼容 | Conan 2.29.1 不支持 args 参数 | 改用 build_tool_args 参数 |
| 5 | CI stub_test_method 门禁 | test() 方法缺少 self.run() 调用 | 在 test() 中使用 self.run() 运行测试二进制 |

## 源码修改

无补丁，源码无需修改即可编译。
在 source() 中删除 Bazel BUILD 文件以避免目录冲突。

## 依赖版本

| 依赖 | 版本 | 来源 |
|------|------|------|
| eigen | 3.4.0 | Conan 制品仓 (ohpcd) |

## 注意事项

1. 使用 MINIGLOG=ON 替代外部 glog（glog 未在 OHOS Conan 仓库中发布）
2. 使用 `find_package(ceres-solver)` 在 CMake 项目中引用
3. 链接时只需要 `-lceres`（glog 已内置为 miniglog）
4. 并行编译 -j6 可正常工作

---

**编译结束**: 2026-08-06
**最终状态**: built
