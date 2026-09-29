# divsufsort 2.0.1 适配笔记

## 编译环境
- 构建系统: cmake（上游 CMake 工程，Conan CMakeToolchain 驱动）
- 编译日期: 2026-09-23
- 编译器: clang/clang++（OHOS 6.0 交叉工具链，aarch64-linux-ohos）
- 状态: built（conan-verify 通过；制品仓未上传 —— ohpcd 中已有另一协作者发布的 libdivsufsort/2.0.1，同库不同包名，本配方未重复上传）

## 编译步骤

conan create 全流程（CI 与本地一致）：

```bash
conan create archives/d/divsufsort/2.0.1 --build=missing -pr:h ohos-aarch64 -pr:b default
```

关键 CMake 缓存变量（generate() 注入）：

| 变量 | 值 | 说明 |
|------|-----|------|
| CMAKE_POLICY_VERSION_MINIMUM | 3.5 | 上游 cmake_minimum_required(2.4) 与 CMake 4+ 不兼容，提升策略下限 |
| BUILD_SHARED_LIBS | option | 默认静态 |
| BUILD_EXAMPLES | ON | 编译上游 5 个 examples，build() 中实际执行验证 |
| BUILD_DIVSUFSORT64 | ON | 同时交付 64 位索引变体（divsufsort64） |
| USE_OPENMP | OFF | 鸿蒙工具链未验证 libomp，关闭保证可移植 |
| WITH_LFS | ON | 大文件支持 |

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CMake 配置阶段报 cmake_minimum_required 兼容错误 | 上游声明 minimum 2.4，CMake 4.x 移除 <3.5 兼容 | tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"]="3.5"，无需改上游源码 |

无其他阻塞：上游 CMake 原生支持 OHOS 交叉编译，为无补丁适配（patches_applied: []）。

## 源码修改

无补丁。全部适配通过配方层注入（见上表），上游源码零修改。

## 依赖版本

无外部依赖。纯 C 库，仅依赖标准 C 头文件（静态链接 libm）。

## 验证结果

```bash
# 1) build() 内执行上游 5 个 examples（输入 "banana_bandana"，15 字节无尾换行）
#    suftest    : divsufsort() + sufcheck() 退出 0            → PASS
#    bwt        : divbwt() 生成 framed BWT 文件               → PASS
#    unbwt      : inverse_bw_transform() 字节级还原原文       → PASS
#    mksary     : 生成非空二进制后缀数组文件                  → PASS
#    sasearch   : sa_search("ana") 结果 = [1, 3, 11]          → PASS
#    汇总: Upstream examples: 5/5 PASS

# 2) test_package（消费者用例，"banana"）: 14 个验证点全部通过
#    SA=[5,3,1,0,4,2] / sufcheck / BWT="annbaa" / 逆 BWT 还原 /
#    divsufsort64 + sufcheck64 / divsufsort_version() 非空
```

产物：libdivsufsort.a + libdivsufsort64.a（aarch64 静态库，双组件）。

## 注意事项

1. **同库不同包名**：ohpcd 制品仓与 main 已有 libdivsufsort/2.0.1（另一协作者，PR !6575）。本配方按工单分支命名 feat/divsufsort-2.0.1 使用上游项目名 divsufsort 作为 Conan 包名，两者指向同一上游 y-256/libdivsufsort tag 2.0.1。
2. 上游不生成 `*-config.cmake`：消费者需经 Conan CMakeDeps 生成的 config 做 find_package（components: divsufsort / divsufsort64）。
3. 上游 VERSION 文件内容为 "2.0.0" 而 tag 为 2.0.1，属上游已知状态，不影响功能与符号。
4. OpenMP 关闭（USE_OPENMP=OFF）；如需多线程可在鸿蒙工具链验证 libomp 后重开。
