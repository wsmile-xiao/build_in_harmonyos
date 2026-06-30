# libsass

## 简介
libsass 是一个用 C/C++ 编写的 Sass/SCSS 编译器，是 Ruby Sass 的官方替代品。它提供高性能的 Sass 到 CSS 转换功能，广泛用于前端构建流程中。

## OHOS 适配
- 使用简单 Makefile，不需要 configure 脚本
- 只生成静态库 libsass.a，无可执行文件
- 需要设置 CC=clang CXX=clang++（系统缺少 cc/c++ 符号链接）
- 缺少 GNU install 命令时可用 cp -a 手动安装
- 测试需要 sassc CLI 工具和 sass-spec 测试套件（纯库无法直接测试）

## 依赖
- 无编译依赖

## 功能验证
```bash
# 验证静态库可用
ls -lh ~/usr/local/lib/libsass.a
# 验证头文件安装
ls ~/usr/local/include/sass/
```

## 参考
- 官网: https://sass-lang.com/libsass
- 源码: https://github.com/sass/libsass