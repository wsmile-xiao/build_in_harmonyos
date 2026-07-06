# zlib

## 简介
广泛使用的数据压缩库，实现 DEFLATE/inflate 压缩算法，是 gzip、PNG、HTTP 等的基础依赖。

## OHOS 适配
- configure shell 脚本在 HarmonyOS 上原生支持，无需补丁
- 编译简单，无兼容性问题
- Makefile 和 zconf.h 是 configure 生成文件，不应补丁 (R6)
- 编译器路径从 Conan conf 获取 (R33)

## 依赖
- 无

## 功能验证
```bash
# 通过链接库验证
```

## 参考
- 官网: https://zlib.net/
