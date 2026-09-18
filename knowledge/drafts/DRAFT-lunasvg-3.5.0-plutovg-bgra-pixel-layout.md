# DRAFT — plutovg 渲染位图表面为 BGRA 小端字节序(little-endian)

## 问题概述

lunasvg 3.5.0 的消费者测试断言渲染结果时,按 RGBA 顺序读取
`Bitmap::data()` 导致误判。渲染一个 `fill="#ff0000"` 的矩形后,中心像素
读作 `(0,0,255,255)`,被断言为"蓝色",而实际渲染完全正确。

根因: plutovg_surface 的像素数据在 little-endian 平台上按 **premultiplied
BGRA** 存储,`data()` 返回的字节序是 `byte[0]=B, byte[1]=G, byte[2]=R,
byte[3]=A`。lunasvg 的 `Bitmap::data()` / `Bitmap::stride()` 直接透传
plutovg 表面数据,不做通道转换。

## 典型错误

```
FAIL: center pixel rgba=(0,0,255,255), expected (255,0,0,255)
Test #1: test_lunasvg ***Failed
```

触发条件:
- 平台: little-endian (arm64 aarch64 OHOS / x86_64)
- 阶段: test_package 消费者测试或渲染结果断言
- 库: 内嵌 plutovg 的图形库(lunasvg 内嵌 plutovg 1.3.x)

## 根因

1. plutovg_surface 内部以 premultiplied ARGB32 存储像素,在 little-endian
   内存中字节序为 B,G,R,A。
2. 按 RGBA 顺序解读 `data()` 会把正确的红色 (255,0,0) 读成 (0,0,255)。
3. 注意: `Bitmap::clear(uint32_t)` 接受 ARGB 整数语义,与 `data()` 的
   BGRA 字节序不同,两种 API 的通道语义不可混淆。

## 解决方案(已验证)

断言 plutovg 渲染结果时按 BGRA 映射读取:

```cpp
// i = y * stride + x * 4
r = data[i + 2];  // 红
g = data[i + 1];  // 绿
b = data[i + 0];  // 蓝
a = data[i + 3];  // Alpha
```

并在代码注释中写明字节序,防止后续按 RGBA 误读。验证结果: 修正映射后
conan-verify G2 消费者测试 1/1 PASS,鸿蒙专项测试(transform/gradient/text)
3/3 断言全 PASS,退出码 0。

回退/替代: 需要 ARGB 整数语义时使用 `Bitmap::clear(uint32_t)`,不要与
`data()` 字节序混用。

## 适用边界

- 适用: little-endian 平台上 plutovg 渲染位图;`Bitmap::data()` 逐字节
  断言;内嵌 plutovg 的图形库(lunasvg 及同类)的像素校验测试。
- 反例: 大端平台(字节序相反);未 premultiply 的 RGB 表面;通过
  `Bitmap::clear()` 构造 ARGB 整数的场景。

## 来源

- 库: lunasvg 3.5.0(task_id lunasvg-3.5.0-r01-pc4-22-20260916T132801Z)
- 首次发现: 消费者测试 G2 断言失败;根因定位后修正断言并全量复验
