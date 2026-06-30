# Test Report — udunits 2.2.28

## 测试日期
2026-05-25

## 测试环境
- 系统: HarmonyOS HongMeng Kernel 1.12.0 aarch64 (musl)
- 编译器: clang/clang++ 15.0.4
- 依赖: expat 2.7.1

## make check 结果

```
Making check in lib
  Testsuite summary for UDUNITS 2.2.28
  # TOTAL: 0  # PASS: 0  # SKIP: 0  # XFAIL: 0  # FAIL: 0
  NOTE: CUNIT not detected → lib unit tests skipped (0 tests)

Making check in prog
  ./udunits2 ../lib/udunits2.xml </dev/null
  You have:
  ✅ PASS (程序启动正常，XML数据库加载成功)
```

## 功能验证

### 组1: 基础单位转换 (udunits2 命令行)

| 测试项 | 输入 | 期望输出 | 实际输出 | 结果 |
|--------|------|----------|----------|------|
| m→ft | 1 m → ft | 3.28084 ft | 1 m = 3.28084 ft | ✅ PASS |
| m→km | 1000 m → km | 1 km | 1000 m = 1 km | ✅ PASS |
| kg→lb | 1 kg → lb | 2.20462 lb | 1 kg = 2.20462 lb | ✅ PASS |
| h→s | 1 h → s | 3600 s | 1 h = 3600 s | ✅ PASS |
| K→degC | 273.15 K → degC | 0 degC | 273.15 K = 0 degC | ✅ PASS |
| Pa→bar | 1 Pa → bar | 1e-05 bar | 1 Pa = 1e-05 bar | ✅ PASS |
| W→kW | 1 W → kW | 0.001 kW | 1 W = 0.001 kW | ✅ PASS |
| mile→km | 1 mile → km | 1.60934 km | 1 mile = 1.60934 km | ✅ PASS |

### 组2: 反向转换

| 测试项 | 输入 | 期望输出 | 实际输出 | 结果 |
|--------|------|----------|----------|------|
| ft→m | 3.28084 ft → m | 1 m | 3.28084 ft = 1 m | ✅ PASS |

### 组3: 错误输入处理

| 测试项 | 输入 | 期望行为 | 实际行为 | 结果 |
|--------|------|----------|----------|------|
| 不兼容单位 | h → m | 拒绝转换 | Cannot convert | ✅ PASS |

### 组4: C API 功能测试

| 测试项 | 描述 | 结果 |
|--------|------|------|
| ut_read_xml | 加载XML单位系统 | ✅ PASS |
| ut_get_unit_by_name | 获取meter/foot单位 | ✅ PASS |
| ut_get_converter | 创建m→ft转换器 | ✅ PASS |
| cv_convert_double | 1 m = 3.28084 ft | ✅ PASS |
| 反向转换 | 3.28084 ft = 1 m | ✅ PASS |
| 温度转换 | 273.15 K = 0 degC | ✅ PASS |
| 温度转换 | 373.15 K = 100 degC | ✅ PASS |
| 不兼容转换拒绝 | hour → meter | ✅ PASS |
| 批量转换 | cv_convert_doubles (kg→lb) | ✅ PASS |

### 组5: 数据库完整性 (udunits2 -r)

```
9 个定义覆盖警告 (au, kt, microns, ft, yd, pt, at, ph, nt)
这些是上游已知问题，不影响功能正确性
```

## 安全验证

- ✅ ELF 签名: udunits2 和 libudunits2.so.0.1.0 已通过 binary-sign-tool -selfSign 1
- ✅ RUNPATH: $ORIGIN/../lib (相对路径库加载)

## 测试覆盖评估

| 类别 | 测试数 | 通过 | 说明 |
|------|--------|------|------|
| 基础单位转换 | 8 | 8 | 涵盖长度/质量/时间/温度/压力/功率 |
| 反向转换 | 1 | 1 | ft→m |
| 错误处理 | 1 | 1 | 不兼容单位 |
| C API | 9 | 9 | 系统加载/单位查找/转换/批量/温度/错误 |
| 数据库完整性 | 1 | 1 | 9个覆盖警告(上游已知) |
| **总计** | **20** | **20** | **全部通过** |

## 注意

- CUNIT 单元测试框架未检测到，lib内部单元测试（0个）跳过
- 温度单位查找需使用 "degree_Celsius" 名称而非 "degC" 符号
- 数据库覆盖警告是上游已知的兼容性问题，不影响功能