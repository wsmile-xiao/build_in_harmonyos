# editorconfig-core-c

## 简介
EditorConfig Core C 是 EditorConfig 文件规范的 C 语言实现，提供命令行工具和共享库，帮助开发者在不同编辑器和 IDE 间保持一致的编码风格。

## OHOS 适配要点

### 平台识别
- **问题**：源码缺少 HarmonyOS 平台检测（misc.c 报错 "Either UNIX or WIN32 must be defined"）
- **解决**：添加 `#ifdef __OHOS__` 宏，将 OHOS 视为 UNIX 系统
- **补丁**：0001-src-lib-misc.c.patch

### 构建系统
- **问题**：CMake 构建产生的动态库使用相对路径 RPATH（../../lib/libeditorconfig.so）
- **解决**：使用静态链接 `-DBUILD_STATICALLY_LINKED_EXE=ON`
- **G0 验证**：clean_verify.py 只支持 autotools，创建 configure wrapper 桥接
- **补丁**：0002-cmake-configure-wrapper.patch

### 依赖
- **pcre2/10.40**：正则表达式库，需显式指定路径参数

## 功能验证
```bash
editorconfig --version
# 输出: EditorConfig C Core Version 0.12.9
```

## 参考
- 官网: https://editorconfig.org/
- 源码: https://github.com/editorconfig/editorconfig-core-c