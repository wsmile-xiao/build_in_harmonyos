# libcorrect

libcorrect 是一个 BSD 许可的 C 语言前向纠错（FEC）库：Reed-Solomon 块码（编码/译码，支持擦除译码）与卷积码（软判决 Viterbi 译码），目标是作为 libfec 的 BSD 许可替代品（上游还内置可选的 libfec API 兼容 shim）。

## 功能概述

两类 FEC API（头文件 `correct.h`，扁平布局）：
- **Reed-Solomon**：`correct_reed_solomon_create/encode/decode/decode_with_erasures/destroy`，255 字节块 8-bit 符号，CCSDS 等本原多项式
- **卷积码**：`correct_convolutional_create/encode_len/encode/decode/decode_soft/destroy`，rate 1/2..1/3 × order 6..9 预置多项式

## OHOS 适配

- 构建系统为 CMake（C99），无平台相关代码，Linux/OHOS 同源构建，**零补丁**。
- W0 依赖核验：仅依赖 libc（`nm -D` 实证），无第三方依赖；上游测试为手写 C main + CTest 注册，**不用 check 框架**，无测试框架供给需求。
- `CMAKE_SYSTEM_NAME=OHOS` 显式注入（E092/libaec 先例）；aarch64 顺带跳过上游 `-march=native` SSE4.1 探测。
- 上游 4 个无条件注册 ctest 条目在 `conan create` 内真实运行（显式构建 `test_runners` 聚合目标 + tests/ 子目录 ctest）；SSE4.1 与 libfec 互操作测试受上游 HAVE_SSE/HAVE_LIBFEC 平台门控不注册（与上游 GitHub CI runner 行为一致）。
- libfec API-compat shim 不随包发布（避免遮蔽真 libfec 包）；上游 .so 无 SONAME，默认 static 规避（E077 家族）。

## 依赖关系

- 无（纯 libc）

## 参考资料

- 上游仓库：https://github.com/quiet/libcorrect
- 本包版本：master 快照 ee82e6673a806dfdf0a969b975ab36596ecc5401（2026-02-05，无正式 release）
