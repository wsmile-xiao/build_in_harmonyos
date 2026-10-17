# Test Report — enhex-generic_serialization 1.0.0 (r03 更新)

## 上游测试 (R51)
- v1.0.0 官方标签(src: https://github.com/Enhex/generic_serialization, commit 879b9a80b30fbd9deab3b6b0b18a7f636d9c1a2e)无独立 tests/ 目录, 无 ctest/pytest 注册。
- 唯一测试载体: 官方 test_package/example.cpp (序列化→文件→读回→断言往返, **8 条断言**)。
- 实测: 设备原生 clang++ -std=c++17 编译通过, 运行输出往返值一致 (x:5 y:7.5 z:ab vec3:1/2/3), 8 条断言全过, exit 0。
  - 命令: clang++ -std=c++17 -I include test_package/example.cpp -o example && ./example
  - 退出码: 0

## test_package 消费者测试 (OHOS 交叉, r03 修复后)
- conan create (profile ohos-aarch64, build_type=Release/-DNDEBUG) 内 test_package 编译+运行:
  - test_generic_serialization: 11 项无条件校验全过 (checks=11 failures=0), CTest Passed
  - harmony_platform_test: 11 项无条件校验全过 (checks=11 failures=0), CTest Passed
  - CTest 2/2 Passed, 退出码 0

## r03 Release/NDEBUG 修复对照
- 负向对照 (worktree 外注入 dst.x==999): -O3 -DNDEBUG 编译运行 exit 1, stderr 输出 FAIL: dst.x expected=999 actual=5
- 正向对照 (修复版): -O3 -DNDEBUG 编译运行 exit 0, 日志 checks=11 failures=0

## 结论
上游 8/8 断言(POD 往返), 适配后 2/2 测试入口 (22 项无条件校验), 通过率 100%。
