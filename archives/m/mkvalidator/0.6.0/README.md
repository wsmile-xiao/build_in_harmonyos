# mkvalidator 0.6.0 — OpenHarmony 预编译包

## 软件信息

| 属性 | 值 |
|------|------|
| 软件 | mkvalidator |
| 版本 | 0.6.0 |
| 状态 | built |
| 构建日期 | 2026-06-17 |
| 目标平台 | OpenHarmony aarch64 / musl libc |
| 编译器 | Clang 15.0.4 (OH native) |
| 构建系统 | CMake |

## 功能简介

mkvalidator 是 Matroska 容器格式验证工具，用于检查 MKV/WebM 文件的结构完整性。
它能检测 EBML 头部错误、段 UID 无效、轨道信息缺失等常见 Matroska 格式问题。

## 构建要点

- **必须传递 `-DCMAKE_SYSTEM_NAME=Linux`**: 否则 UNIX 宏未定义，corec 选择 str_linux.c 而非 str_os.c，产生 undefined reference
- **corec tests 子目录必须禁用**: 测试可执行文件依赖 tchar 符号在 musl 环境下不可用
- **原始源码缺少 install 规则**: 需手动添加 `install(TARGETS mkvalidator RUNTIME DESTINATION bin)`
- **所有依赖均为内置编译**: 无外部预编译依赖需求

## 补丁列表

| 补丁 | 说明 |
|------|------|
| 0001-disable-corec-tests.patch | 禁用 corec 测试子目录（注释 `add_subdirectory("tests")`） |
| 0002-add-mkvalidator-install-rule.patch | 添加 mkvalidator 的 `install(TARGETS)` 和 `GNUInstallDirs` 规则 |

## 安装与使用

```bash
# 通过 Conan 安装
conan install --requires=mkvalidator/0.6.0 -r=ohpcd

# 基本使用
mkvalidator --version          # 查看版本
mkvalidator --help             # 查看帮助
mkvalidator <mkv-file>         # 验证 MKV/WebM 文件
mkvalidator --details <file>   # 验证并显示详细信息
mkvalidator --quick <file>     # 快速模式，遇到第一个错误即退出
```

## 运行时依赖

仅依赖 `libc.so` (musl libc)，无其他运行时库依赖。

## 二进制安全特性

- ✅ PIE (Position-Independent Executable)
- ✅ BIND_NOW (全绑定，无延迟绑定)
- ✅ 最小动态依赖（仅 libc.so）
