# E081: OHOS 不支持 utmpx API

## 错误特征

链接阶段失败，报错：
```
ld.lld: error: undefined symbol: setutxent
>>> referenced by pty.c
>>> did you mean: setutent
>>> defined in: libc.so

ld.lld: error: undefined symbol: pututxline
>>> referenced by pty.c
>>> did you mean: pututline

ld.lld: error: undefined symbol: endutxent
>>> referenced by pty.c
>>> did you mean: endutent
```

## 根因分析

OHOS 系统只提供 POSIX utmp API（setutent/pututline/endutent），不提供 utmpx 扩展 API（setutxent/pututxline/endutxent）。utmpx 是 utmp 的扩展版本，提供了更好的 API 设计，但 OHOS 未实现这些函数。

链接器提示 "did you mean: setutent" 表明系统有 utmp 版本的替代函数。

## 影响范围

使用 utmp 记录功能的程序：
- SSH 服务器（如 psusan、sshd）
- 终端工具（如 pterm）
- 包含 pty.c 的程序

## 解决方案

### 推荐方案（优先级 1）：禁用 utmp 功能

大多数终端/SSH 服务器的核心功能不依赖 utmp 记录，可安全禁用。

**CMake 项目**：
```cmake
target_compile_definitions(psusan PRIVATE OMIT_UTMP)
```

**Autotools 项目**：
```bash
CPPFLAGS="-DOMIT_UTMP" ./configure ...
```

### 回退方案（优先级 2）：替换 API

如果 utmp 记录功能必需，将 utmpx API 替换为 utmp API：
```bash
sed -i 's/setutxent/setutent/;s/pututxline/pututline/;s/endutxent/endutent/' pty.c
```

注意：utmp 和 utmpx API 参数类型可能不同，需检查代码适配。

## 验证方法

```bash
# 检查是否使用 utmpx API
grep -r "setutxent|pututxline|endutxent" *.c

# 验证修复后编译成功
make clean && make
```

## 注意事项

1. OMIT_UTMP 宏通常已在源码中预定义（通过 #ifndef OMIT_UTMP 守卫）
2. 禁用 utmp 记录不影响 SSH 连接/传输等核心功能
3. utmp 记录主要用于 `who`/`w` 等命令显示登录用户信息

## 相关原则

- **R6**: 只改源文件，不改生成文件
- **R1**: 参数最少化（编译定义比修改源码更简单）

## 案例

- **putty 0.84**: psusan/uppity 使用 pty.c，添加 OMIT_UTMP 定义成功编译
- **openssh**: 可能需要类似处理（待验证）

---

**创建日期**: 2026-05-28
**来源**: putty 0.84 编译
**贡献者**: 42FF