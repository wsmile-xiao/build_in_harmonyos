# cpp-terminal 0.1.0 适配笔记

## 编译环境
- **类型**: header-only（无库编译）
- **编译日期**: 2026-08-28
- **编译器**: clang 15（OHOS 6.0 交叉工具链）
- **平台**: arm64-ohos（OpenHarmony PC）
- **状态**: built

## 编译步骤（conan create 全流程）

```bash
conan create archives/c/cpp-terminal/0.1.0 --build=missing
```

### 1. 源码获取（source()）
`get()` 下载 GitHub v0.1.0 tag tarball（73KB），`strip_root=True` 解压。

### 2. 打包（package()）
header-only——拷贝 `cpp-terminal/` 头文件（terminal.h + terminal_base.h）到 include。

### 3. 上游测试（build() 集成——rule 4 实测回填）
doctest 单元测试（test_terminal.cpp **自带 doctest.h——无需网络下载**；1 个
ctest 用例）+ tests.sh（examples/colors/keys）——`BUILD_TESTING=ON` 单独构建
+ ctest 运行：
```bash
cmake <src> -DBUILD_TESTING=ON \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_CXX_COMPILER=/data/service/hnp/bin/clang++ \
  -DCMAKE_CXX_FLAGS='-std=c++11'
cmake --build <bdir> -j4
ctest --test-dir <bdir>
```
- aarch64 OHOS 直接可编译（header-only）
- subprocess 调 cmake/ctest 用绝对路径（OHOS posix_spawn 不按 PATH 搜索
  相对名——与 rich/vc 同源教训）
- 注意：终端交互（键盘输入）需真实 tty——OHOS 沙箱无 tty，键盘相关测试
  受限（tests.sh 的 keys 部分未计——如实记录）

**实测结果：1 passed / 0 failed / 0 skipped（1 用例 = 100%，分母=全部用例）**

## 验证结果
- **构建**: `cpp-terminal/0.1.0: Package created`
- **上游测试**: 实测 **1/1 通过（100%）**——build() 集成回填（rule 4，分母=全部用例）
- **R34 消费者验证**: test_package——头文件存在 + Term::color(fg) 使用 smoke（1/1 = 100%）
