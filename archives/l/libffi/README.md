# libffi

## 简介
libffi 是一个可移植的外部函数接口库，提供高级编程语言之间的可调用接口。

## OHOS 适配
- 构建系统为 autotools，需修改 config.guess 和 config.sub 支持 HarmonyOS
- 三元组格式：`aarch64-unknown-linux-ohos`
- FFI 核心功能（ffi_call/ffi_prep_cif）完全可用
- ffi_closure 闭包功能需要额外补丁：启用 FFI_EXEC_STATIC_TRAMP 并修复 HMDFS 路径回退
- HMDFS umask 077 问题需在 configure 中修复
- 3.5.2 新增版本 API（FFI_VERSION_STRING 等）

## 依赖
无外部依赖

## 功能验证
```bash
# 检查安装
ls $HOME/usr/local/lib/libffi*
pkg-config --modversion libffi

# 编译测试
clang -I$HOME/usr/local/include -L$HOME/usr/local/lib -lffi test.c -o test
```

## 参考
- 官方仓库：https://github.com/libffi/libffi
