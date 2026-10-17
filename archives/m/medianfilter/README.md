# MedianFilter

## 是什么

Heap-free 滑动窗口中值滤波器（滑窗中位数），为嵌入式系统设计（ADC 读数、
传感器融合、DSP 管道）。无 malloc，O(n/2) 最坏插入复杂度（平均 ~n/4），
中值指针增量维护 O(1)。上游仓库：https://github.com/accabog/MedianFilter

## 功能概述

- C API：`MEDIANFILTER_Init` / `MEDIANFILTER_Insert`，调用方分配缓冲区
- C++ header-only 模板：`MedianFilter<type, N>`，编译期 static_assert
- 稳定重复值处理（地址决胜），24 字节/样本（64 位）恒定内存
- 上游自带三套测试：stress_test（140）/ circular_test（51）/ test_cpp（12）

## OHOS 适配

- 纯静态库无依赖，OHOS arm64 clang 直接编译通过，无源码修改、无补丁
- 类型名注意：v1.0.0 头文件实际类型为 `sMedianFilter_t`/`sMedianNode_t`
- warmup 语义：窗口未满时以 0 填充槽位，测试断言需对齐
- 交付：conanfile.py + conandata.yml + test_package + test_ohos + consumer

## 依赖关系

无编译/运行第三方依赖（仅标准头文件）。

## 参考资料

- 上游仓库: https://github.com/accabog/MedianFilter
- 版本归档: archives/m/medianfilter/