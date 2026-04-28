# FriBidi

## 简介
GNU FriBidi 是 Unicode 双向算法 (Bidirectional Algorithm) 的实现库，用于正确处理阿拉伯语、希伯来语等从右到左（RTL）文本与从左到右（LTR）文本的混合排版。

## OHOS 适配
- **构建系统**: 使用 meson（非 autotools）
- **meson 安装**: 需要手动安装 `pip install --user meson`
- **编译器设置**: 需显式设置 CC, CXX, AR 等环境变量
- **符号链接**: meson 在 OHOS 上无法创建符号链接，需手动创建

## 依赖
- 编译工具: clang, meson
- 无额外库依赖

## 功能验证
```bash
fribidi --version
fribidi --help
```

## 参考
- GitHub: https://github.com/fribidi/fribidi
