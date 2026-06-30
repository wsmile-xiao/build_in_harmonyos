# picolisp 26.3 适配笔记

## 编译环境
- 构建系统: makefile (LLVM-based)
- 编译日期: 2026-05-26
- 编译器: clang/clang++ with LLVM 15.0.4
- 状态: built

## 编译步骤

PicoLisp 使用 LLVM 作为后端，需要预生成的 .ll 文件进行引导编译。

1. 从 tarball 解压源码到正确的目录结构 (`pil21/src/`)
2. 修改 Makefile 以适配 OpenHarmony 环境：
   - 添加 PKG_CONFIG_PATH 环境变量支持
   - 添加 CFLAGS_EXTRA 和 LDFLAGS_EXTRA 变量
   - 修改 pkg-config 调用，将 `libffi` 改为 `ffi`
   - 禁用 bootstrap 规则（避免清空预生成的 .ll 文件）
   - 为 ssl/httpGate 添加 OpenSSL 头文件路径
3. 创建 libffi 头文件软链接（`ffi/ffi.h` -> `ffi.h`）
4. 执行 `make` 编译所有组件

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | pkg-config 找不到 libffi | 包名是 `ffi` 不是 `libffi` | 修改 Makefile 中 pkg-config 调用 |
| 2 | ffi.h 头文件路径错误 | ffi.h 在 `ffi/` 子目录中 | 创建软链接 `ln -s ffi/ffi.h ffi.h` |
| 3 | base.ll 被清空 | Makefile bootstrap 规则执行 `touch *.ll` | 注释掉 bootstrap 规则 |
| 4 | readline/ssl 头文件找不到 | 缺少 include 路径 | 添加 CFLAGS_EXTRA 变量 |
| 5 | OpenSSL 库找不到 | 缺少 lib 路径 | 添加 LDFLAGS_EXTRA 变量 |

## 源码修改

- Makefile: 修改了 8 处以适配 OpenHarmony 环境
  - 添加 PKG_CONFIG_PATH/CFLAGS_EXTRA/LDFLAGS_EXTRA
  - 修改 pkg-config 包名 `libffi` -> `ffi`
  - 注释掉 bootstrap 规则
  - 为 ssl/httpGate 添加 OpenSSL 链接

## 依赖版本

- LLVM: 15.0.4 (系统自带)
- readline: 8.2 (预编译包)
- libffi: 3.4.6 (预编译包)
- openssl: 1.1.1w (预编译包)

## 验证结果

编译产物已生成，但由于 ELF 签名问题，需要在打包阶段进行签名后才能在鸿蒙系统上执行。

```bash
ls -la pil21/bin/
# picolisp: 378KB ELF executable
# balance: 14KB
# ssl: 22KB
# httpGate: 26KB
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| bin/picolisp | 378KB | PicoLisp 解释器 |
| bin/balance | 14KB | 平衡工具 |
| bin/ssl | 22KB | SSL 工具 |
| bin/httpGate | 26KB | HTTP 网关 |
| lib/ext.so | 14KB | 扩展库 |
| lib/ht.so | 18KB | HTTP 库 |
| lib/sysdefs | 1KB | 系统定义 |

## 注意事项

1. PicoLisp 是引导编译器，需要预生成的 .ll 文件（已在 tarball 中提供）
2. 编译不需要 configure，直接 `cd src && make`
3. 需要正确设置 PKG_CONFIG_PATH 以找到预编译依赖
4. OpenSSL 和 readline 需要显式指定 include/lib 路径
5. 打包前必须进行 ELF 签名
---

**编译结束**: 2026-05-26 14:29
**最终状态**: built
---

**编译结束**: 2026-05-26 14:29
**最终状态**: built
