# hopscotch-map 2.4.0 适配笔记

## 编译环境
- **类型**: header-only C++17（无库编译）
- **编译日期**: 2026-08-28
- **编译器**: clang 15（OHOS 6.0 交叉工具链）
- **平台**: arm64-ohos（OpenHarmony PC）
- **状态**: built

## 编译步骤（conan create 全流程）

```bash
conan create archives/h/hopscotch-map/2.4.0 --build=missing
```

### 1. 源码获取（source()）
`download()` 下载 GitHub v2.4.0 tag tarball（72KB——6 个 tsl/ 头文件 +
tests/），`strip_root` 后解压。

### 2. 打包（package()）
header-only——拷贝 `include/tsl/` 头文件（hopscotch_map.h + hopscotch_set.h +
bhopscotch_map.h + bhopscotch_set.h + hopscotch_hash.h +
hopscotch_growth_policy.h）到 include。

### 3. 上游测试（build() 集成——rule 4 实测回填）
Boost.Test 单元测试（tests/——main.cpp + custom_allocator_tests +
hopscotch_map_tests + hopscotch_set_tests + policy_tests——179 用例）——
编译并运行：
```bash
clang++ -std=c++17 -Iinclude -I<boost>/include -include pthread_stub.h \
  tests/*.cpp -o unit_tests -pthread
./unit_tests
```

**实测结果：Running 179 test cases... *** No errors detected（179 用例 = 100%，分母=全部用例）**

关键处理（缺依赖就装上 / 环境差异修复）：
1. **Boost.Test 无编译库**：ohpcd boost 包无 libboost_unit_test_framework
   编译库（只有头文件）——用 header-only 模式（included/unit_test.hpp——
   main.cpp 的 include 替换为 included 版）——tool_requires boost/1.84.0
2. **pthread_setcancelstate/pthread_cancel**：OHOS libc 缺失（Boost 内部
   sp_thread_sleep.hpp 使用实测）——写 stub 头 + `-include` 注入（同
   CLI11 pthread_testcancel 教训）

## 验证结果
- **构建**: `hopscotch-map/2.4.0: Package created`
- **上游测试**: 实测 **179/179 通过（100%）**——build() 集成回填（rule 4，分母=全部用例）
- **R34 消费者验证**: test_package——头文件存在 + tsl::hopscotch_map insert/find/erase 真实 API（1/1 = 100%）
