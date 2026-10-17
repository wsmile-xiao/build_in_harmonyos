# newLISP

newLISP 是一个 Lisp 风格、通用目的的脚本语言解释器。纯 C 实现，单一静态可执行文件，无第三方运行时依赖，内建网络、正则(PCRE)、XML/JSON、数据库访问、并发原语等大量内建函数。

## 版本信息

- 当前版本: 10.7.5
- 官方网站: http://www.newlisp.org
- 源码地址: https://www.newlisp.org/downloads/newlisp-10.7.5.tgz

## 功能特性

- Lisp 系函数式/命令式脚本语言（内建 300+ 内建函数）
- 内置 PCRE 正则、FFI（可关）、网络 socket（IPv4/IPv6）、XML/JSON、MySQL/SQLite 模块
- UTF-8 多语言支持（arm64/aarch64 已验证）
- 上游自带 qa 测试套件（make check）

## 平台适配说明

- 构建路线：`configure-alt`（非交互）→ 生成 makefile_build → make
- HarmonyOS 适配要点：
  - `configure-alt` 的 uname 识别需补丁增加 HarmonyOS 分支（0001 补丁）
  - 必须静态链接（`--enable-static`）+ 禁用 strip：设备 exec 沙箱只接受静态且未 strip 的 ELF
  - 关闭 readline 与 ffi（无第三方运行时依赖）
  - `p_pipe()` 写端 fdopen 误用读端句柄的真实上游 bug 修复（0002 补丁）
- 平台限制：System V IPC（semaphore 函数）被设备沙箱 SIGSYS 拦截，qa-dot 相关测试项记录为平台限制失败

## 构建命令（conan）

```bash
conan create . --build=missing -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

## 冒烟验证

```bash
newlisp -e '(+ 1 2)'   # → 3
newlisp -v             # → newLISP v.10.7.5 64-bit on Linux IPv4/6 UTF-8.
```