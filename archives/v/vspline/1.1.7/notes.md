# vspline 1.1.7 适配笔记

## 编译环境
- 构建系统: 无构建系统（header-only 库）
- 编译日期: 2026-09-25
- 编译器: clang/clang++ (OHOS NDK clang 15)
- 状态: published

## 编译步骤

vspline 是纯 header-only C++ 模板库（README 明确说明 "there are no shared or
static libraries"），无需 configure/make。适配方式：

1. 源码来自官方 bitbucket 上游 `https://bitbucket.org/kfj/vspline/get/1.1.7.tar.gz`
   （sha256: b127a14ae85edac1a495b7aa544c3975506395ecbea344e21b4f955913642c54）
2. 配方采用 header-only 模式：package() 仅复制根目录头文件 + opt/ 子目录到
   include/vspline/，无编译步骤
3. 依赖 vigra/1.12.4（已发布制品仓，conan download 验证通过）；SIMD 后端用默认
   'goading'（自转向量化），无需 Vc/highway 额外依赖
4. test_package 用上游 quickstart 示例改写：bspline → prefilter → evaluator →
   remap 实际调用链，断言常量场求值结果 == 42

## 上游测试清点（R51）

- 上游无自动化测试套件（无 Makefile/CMakeLists/ctest 注册）
- example/examples.sh 逐个编译运行 example/ 下 34 个示例程序，最接近测试的是
  self_test.cc（编译期静态断言为主）
- test_package 以消费者测试替代：6 处断言（eval 结果、remap 往返一致性）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | W3 首跑 JC1/JC5 拦截 | 本地未提交时 junk_check 落 full 模式，误扫出 main 上他人遗留的 .build-closed/.staging-verified 标记文件 | 提交 vspline 变更后重跑，CI 侧用 prdiff/incremental 模式只查 PR 变更文件，不受影响 |

## 依赖版本

- vigra/1.12.4（制品仓已发布）

## 验证结果

```bash
conan create archives/v/vspline/1.1.7 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing
# G2 PASS — 含 test_package 交叉编译 + 运行
# test_vspline 输出: vspline 1.1.7 test passed: eval(coordinate) == 42
```

## 注意事项

- vspline 需 C++17（CI profile 已设 compiler.cppstd=17）；若用户启用 std::simd
  后端（USE_STDSIMD）需注意 OHOS libcxx 对 <format>/<ranges> 的 stub 限制
  （knowledge/cxx20-stdlib-gap.yaml），默认 goading 后端不涉及
- package_info 声明 system_libs pthread（多线程求值用 std::thread）
