# libitl (Islamic Tools and Libraries)

## 简介
ITL 提供伊斯兰常用计算：希吉来历与公历互转、礼拜时间与朝拜方向（Qibla）。

## OHOS 适配
- CMake 构建；应用 Debian 补丁以产出 `libitl.so` 并将头文件装到 `include/itl/`
- C99 前向声明补丁避免隐式声明问题
- 无外部依赖（链接 `libm`）

## 依赖
- 编译：cmake ≥ 3.5、C 编译器
- 运行：libc、libm

## 功能验证
```bash
# 头文件与库
ls $HOME/usr/local/include/itl/
ls $HOME/usr/local/lib/libitl*
```

## 参考
- 源码：https://github.com/arabeyes-org/ITL
- Debian：https://packages.debian.org/source/sid/libitl
