# ccmaker 1.0.0 适配笔记

## 编译环境
- 构建系统: cmake
- 编译器: clang 15
- 状态: published

## 编译步骤
```bash
cmake -B build -DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=OFF
cmake --build build -j1
ctest --test-dir build --output-on-failure
cmake --install build --prefix /data/service/hnp
```

## 源码修改
无补丁，源码来自 https://gitcode.com/gyccc/ccmaker。

## 上游测试
- 上游测试框架: ctest
- 测试用例: 1 个 (ccmaker_test)
- 执行方式: build() 末尾 `ctest --output-on-failure` 并输出 HMBS_UPSTREAM_TEST_RESULT
- 结果: 1/1 通过

## 验证结果
- conan create 通过
- test_package 2 个用例通过
- 产物: libccmaker.a, include/ccmaker.h
