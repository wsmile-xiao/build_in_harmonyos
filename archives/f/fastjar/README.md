# fastjar

## 简介
fastjar 是一个快速的 Java Archive (JAR) 文件操作工具，提供 `fastjar` 和 `grepjar` 命令，用于创建、提取和搜索 JAR 文件。

## OHOS 适配
- 需要更新 `config.guess`/`config.sub` 添加 OHOS 平台识别
- 需要修补 `configure.ac` 和 `configure` 脚本以正确识别平台
- 使用 autotools 构建系统

## 依赖
- 编译工具: clang, make
- 无额外库依赖

## 功能验证
```bash
fastjar --version
grepjar --help
```

## 参考
- 官网: https://savannah.nongnu.org/projects/fastjar/
