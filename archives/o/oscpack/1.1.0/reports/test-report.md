# test-report.md — oscpack/1.1.0（OHOS PC aarch64）

- 日期: 2026-09-29
- 环境: OpenHarmony PC, aarch64, clang/clang++ 15.0.4, CMake 4.1.2, Conan 2.29.1
- Profile: ci/conan/profiles/ohos-aarch64（绝对路径）

## 1. 上游官方单元测试 OscUnitTests

```bash
cmake .. -DCMAKE_BUILD_TYPE=Release -DCMAKE_POLICY_VERSION_MINIMUM=3.5 && cmake --build . -j4
./OscUnitTests
```

结果: **91 tests run, 91 passed, 0 failed**（exit 0）

## 2. 上游 UDP 回环收发测试（OscSendTests + OscReceiveTest）

```bash
./OscReceiveTest &   # 接收端
./OscSendTests       # 发送端, exit 0
```

结果: 接收端完整收到 /an_int64、/a_time_tag、/a_double、/a_string 等全部消息；
发送端 exit 0。（"wrong argument type" 输出为上游用例故意注入的健壮性测试）

## 3. test_package 端到端消费者测试（test_oscpack.cpp）

打包 bundle(time=1234)+消息(int32/float/string/bool) → 按网络字节流解析回 →
逐字段断言，另含 LP64 类型修复校验（sizeof(osc::int32)==4）、字节序往返
（int32 0x01020304）与错误类型访问抛 osc::Exception 校验。

结果: **23 checks run, 23 passed, 0 failed**（conan create 全链路含此测试，exit 0）

## 4. conan-verify 门禁

G0/G1/G2/G3/G4 + L2/L4/L5 全部 PASS（conan-verify-report.md verdict=pass）

## 汇总

| 测试 | 数量 | 通过 | 失败 |
|------|------|------|------|
| OscUnitTests（上游用例） | 91 | 91 | 0 |
| OscSendTests/ReceiveTest（回环） | 全部消息 | ✅ | 0 |
| test_oscpack.cpp（消费者断言） | 23 | 23 | 0 |
