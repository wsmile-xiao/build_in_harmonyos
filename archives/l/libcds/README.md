# libcds

## 简介
libcds 是 C++11 无锁并发数据结构库 (Treiber 栈、Michael&Scott 队列、散列映射、跳表等),
附带 Hazard Pointer / RCU 安全内存回收机制。库本体大部分为头文件,
仅 SMR 核心编译为小型动态/静态库。

## OHOS 适配
- CMake 构建, 库本体仅依赖 C++ 标准库与系统线程 (pthread/m), 无需 Boost。
- 上游单元测试 test/unit (gtest) 以 test_requires 引入本仓库 OHOS 适配版
  gtest/1.17.0.1, 在真机以 ctest 完整执行, 不进入消费方依赖链。Boost 为
  上游非 REQUIRED 可选依赖, 真机不引入。
- test/stress 为长耗时压测, 单核真机预算内无法完成, 以 ENABLE_STRESS_TEST=OFF 关闭并如实披露。
- 上游 cmake_minimum_required(3.0.2) 需 CMAKE_POLICY_VERSION_MINIMUM=3.5 兼容垫片。

## 依赖
- 无 (运行时)
- 测试期: gtest/1.17.0.1 (本仓库 OHOS 适配版, test_requires, 仅构建测试用)

## 功能验证
```bash
./test_libcds  # 期望输出: RESULT: 3 passed, 0 failed
```

## 参考
- 上游: https://github.com/khizmax/libcds
- 版本: v2.3.3 (2018-12-31 维护版本)
