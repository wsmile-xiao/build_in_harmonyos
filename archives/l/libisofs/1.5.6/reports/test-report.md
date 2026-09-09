# libisofs 1.5.6 测试报告

## 上游测试（R51 三步法）

1. **清点**：上游 tarball 无 test/、tests/ 目录；Makefile.am 中单元测试（check_PROGRAMS = test/test 等）被上游注释禁用（ticket 147: "The test code does not use the API"）；无 ctest/pytest 注册；`make check` 无注册目标（Nothing to be done for 'check'）。
2. **实测**：`make check` 实际运行，exit 0（无测试目标，无失败项）。
3. **结论**：上游未提供可运行测试；以 demo 编译链接成功 + test_package 消费者测试作为适配验证。

## 消费者测试（test_package）

- test.c 实际调用 libisofs API：iso_lib_version() / iso_init() / iso_finish()
- 断言：运行时版本号与头文件 iso_lib_header_version_major/minor 一致；iso_init() 返回 >= 0
- 实测结果（conan create test_package，来自 conan-create.log）：

```
[100%] Built target test_libisofs
    Start 1: test_libisofs
1/1 Test #1: test_libisofs ....................   Passed    0.03 sec
```

- 通过率：1/1（100%）

## 构建验证

- configure exit 0（--build=aarch64-linux-ohos --host=aarch64-linux-ohos，config.sub OHOS 补丁）
- make exit 0（libisofs 静态库 + demo 链接成功，仅 4 个上游 -Wstrict-prototypes 警告）
- make install DESTDIR exit 0（staging 隔离）
- conan-verify G0-G4 全部 PASS
- W3 本地 CI 模拟（build_and_test.sh）100% 通过（1/1）
