# DRAFT-ncurses-widec-bridge: ncurses widec 库名桥接

## 基本信息
- **严重度**: 2（configure 静默跳过 curses 支持，功能缺失）
- **类别**: build-system, autotools, linking, dependency
- **作者**: AtomCode (qwen38) <noreply@atomgit.com>
- **来源 PR**: 11418（tina 0.1.14 OHOS 适配）

## 错误特征

```
checking for initscr in -lcurses... no
```

或 configure 静默跳过 curses 支持，最终编译无终端功能。

## 根因分析

ncurses `--enable-widec` 编译后库名为 `libncursesw.a`（`w` = wide char），
而多数上游 `configure.ac` 通过 `AC_CHECK_LIB(curses, initscr)` 探测 `-lcurses`。
两者文件名不匹配，`-lcurses` 找不到，configure 判定 curses 不可用。

## 推荐方案

**方法**: `ncurses-widec-symlink-bridge`

**说明**: 在 conanfile `build()` 入口（`autotools.configure()` 之前）创建
`libcurses.a → libncursesw.a` 符号链接；同时在 `generate()` 中注入
`-I<ncurses_include> -L<ncurses_libdir>` 到 CPPFLAGS/LDFLAGS。

**验证/命令**:
```python
# conanfile.py build()
import os
nc = self.dependencies["ncurses"].cpp_info.aggregated_components()
libdir = nc.libdirs[0]
link = os.path.join(libdir, "libcurses.a")
if not os.path.exists(link):
    os.symlink(os.path.join(libdir, "libncursesw.a"), link)
```
```python
# conanfile.py generate()
from conan.tools.env import Environment
nc = self.dependencies["ncurses"].cpp_info.aggregated_components()
env = Environment()
env.append("CPPFLAGS", f"-I{nc.includedirs[0]}")
env.append("LDFLAGS", f"-L{nc.libdirs[0]}")
env.vars(self).save_script("ncurses_flags")
```

**修复前后对比**:
- 修复前: `checking for initscr in -lcurses... no`
- 修复后: `checking for initscr in -lcurses... yes`

## 禁止策略

| 禁止做法 | 原因 | 后果 |
|---------|------|------|
| `--without-ncurses` | 绕过探测，功能缺失 | CI L0 功能验证失败 |
| 假设 CI worker 有系统 ncurses | OHOS 目标环境无系统 ncurses | 链接失败 |

## 影响范围

所有使用 autotools + `AC_CHECK_LIB(curses, ...)` 的终端/编辑器类库：
readline、joe、nano、mutt、irssi、slang、tmate、tina、mcabber 等。

## 与相邻条目的差异

| 相邻条目 | 差异 |
|---------|------|
| E033（add-cflags） | E033 修的是宽字符**头文件暴露**（CFLAGS 加 `_XOPEN_SOURCE_EXTENDED`），本条修的是**库文件名不匹配**（符号链接）；`grep -c "libncursesw" E033.kv` = 0 |
| E028（configure-static-only） | E028 修的是共享库劫持系统 `.so`，本条修的是库名探测不匹配 |
