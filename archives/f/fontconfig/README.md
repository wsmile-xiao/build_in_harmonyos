# fontconfig

## 简介
fontconfig 是一个字体配置和自定义库，提供统一的字体访问接口。它允许应用程序查询系统上安装的字体，并根据名称、风格、语言等属性选择合适的字体。

## OHOS 适配
- **依赖关系**: 依赖 freetype 和 expat，需要先安装这两个库
- **环境变量**: 需要设置 `FONTCONFIG_PATH` 环境变量指定配置文件路径
- 使用 autotools 构建系统

## 依赖
- freetype（必须）
- expat（必须）
- 编译工具: clang, make

## 功能验证
```bash
fc-list              # 列出可用字体
fc-match sans        # 匹配字体
fc-cache --version   # 查看版本
```

## 参考
- 官网: https://www.freedesktop.org/wiki/Software/fontconfig/
- 源码: https://www.freedesktop.org/software/fontconfig/release/
