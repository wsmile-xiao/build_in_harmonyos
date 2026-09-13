# Test Report — udunits 2.2.28.1

## 测试日期
2026-09-09（conan 配方适配）

## 测试环境
- 系统: HarmonyOS PC (aarch64, os=OHOS, armv8, clang/LLVM 15)
- 依赖: expat/2.8.2.1（conan）

## 上游测试（make check，实际执行）

```
Making check in lib
  Testsuite summary for UDUNITS 2.2.28.1
  # TOTAL: 0  # PASS: 0  # SKIP: 0  # XFAIL: 0  # FAIL: 0
  NOTE: CUNIT not detected → lib 内部单元测试未注册（0 用例）

Making check in prog
  ./udunits2 ../lib/udunits2.xml </dev/null
  You have:            # udunits2 启动正常、XML 数据库加载成功（smoke test）
```

上游注册用例数：0（CUnit 未检测，lib 测试未注册）+ prog smoke test 正常。

## test_package 自研断言（test.c，R34 实质调用库 API）

| 组 | 覆盖 | 断言点 | 结果 |
|----|------|--------|------|
| XML 数据库加载 | ut_read_xml(NULL) 非空 | 1 | ✅ |
| 单位查找 | meter/foot/hour/second/kelvin/degree_Celsius 全部非空 | 6 | ✅ |
| 转换器创建 | m→ft / ft→m / h→s / K→degC 转换器全部非空 | 4 | ✅ |
| 数值转换 | 1 m = 3.28084 ft；1000 m = 3280.84 ft | 2 | ✅ |
| 反向转换 | 3.28084 ft = 1 m | 1 | ✅ |
| 时间转换 | 1 h = 3600 s | 1 | ✅ |
| 温度换算 | 273.15 K = 0 degC；373.15 K = 100 degC | 2 | ✅ |
| 不兼容拒绝 | hour→meter 转换器为 NULL | 1 | ✅ |
| 可转换性 | meter↔foot=1；hour↔meter=0 | 2 | ✅ |

**总计 20 断言点（14 CHECK + 6 near_eq）全部通过**（运行输出：`test_udunits: all assertions passed`）。

## 验证结果汇总

| 项 | 结果 |
|----|------|
| 上游 make check | lib 0 注册用例 + prog smoke 启动正常 |
| test_package 断言 | 20/20 通过 |
| conan-verify | PASS (G1-G4) |
| W3 本地 CI（build_and_test.sh） | PASS（1/1 package，exit 0，L0/L1/L4/L5 全绿） |

## 注意

- CUnit 单元测试框架未检测到，上游 lib 内部注册测试为 0；test_package 以公共 C API 断言补足功能覆盖
- 温度单位查找使用 "degree_Celsius" 名称
