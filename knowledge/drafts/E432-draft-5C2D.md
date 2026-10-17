# E432 — 上游测试链接内部静态库可用私有符号，消费者移植断言须先 nm -D 过滤

## 错误特征
把上游测试断言 1:1 移植到 conan test_package（消费者上下文）后链接失败：
`ld.lld: error: undefined symbol: adw_accent_color_nearest_from_rgba`
（libadwaita 1.8.8 实测，2026-10-01）。

## 触发条件
- 场景: 上游测试断言移植（E471 无显示 API 探针方法的一部分）
- 阶段: test_package 链接
- 特征: 同一编译单元内的兄弟函数（`adw_accent_color_to_rgba` /
  `adw_accent_color_to_standalone_rgba` / `adw_rgba_to_standalone`）正常
  导出，仅**私有头**（`src/adw-accent-color-private.h`）声明的函数缺失——
  公共头 `adwaita/` 目录无该函数声明

## 根因分析
上游 meson 将测试二进制链接到库的**内部静态库**
（`libadwaita-1-internal.a`，全部符号、无可见性过滤），因此上游测试可
引用私有 API。conan 消费者只能链接**已安装的 .so**，其导出符号面窄于
内部 .a——`adw_accent_color_nearest_from_rgba` 未出现在
`nm -D libadwaita-1.so.0` 中。这是符号可见性差异，**不是库缺陷**：
符号在公共接口中确实不存在。

## 解决方案

### 推荐方案
移植上游测试断言前**逐符号验证可见性**：
```bash
nm -D --defined-only <安装目录>/lib/libadwaita-1.so.0 | grep <函数名>
# 空 = 私有，不可移植；同文件兄弟函数应能列出
```
将断言集二分，如实申报（libadwaita 1.8.8 实测口径）：

| 上游测试 | 公共 API 断言 | 私有 API 断言 |
|---|---|---|
| test-easing（35 值 × 2 端点） | 70（1:1 移植，100% PASS） | 0 |
| test-accent-color | 35（to_rgba 9 + standalone 18 + rgba_to_standalone 8，1:1 移植） | 137（nearest_from_rgba roundtrip 10 + 调色板 127） |

私有 API 部分不入探针，按 E471 口径分类留证（函数名 + 私有头路径 +
nm -D 为空 + "上游为何可用 = 链接内部 .a"）。

### 禁止做法
- ❌ test_package 链接 `libadwaita-1-internal.a`——消费者场景无效，
  内部 .a 符号面不代表公共接口，R34 实质验证失真
- ❌ 把私有 API 断言计入"移植执行通过数"（数字失真，评审可复核实证）

## 验证
```bash
nm -D --defined-only lib/libadwaita-1.so.0 | grep nearest   # 空
nm -D --defined-only lib/libadwaita-1.so.0 | grep accent    # 4 个公共函数
# test_package 移植后: checks=124 PASS (105/105 upstream-ported)
```

## 关联条目
- 相似: E471（display 测试分类与无显示 API 探针——本条是其"可移植性"维度的补充）
