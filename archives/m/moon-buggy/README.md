# moon-buggy

## 简介
moon-buggy 是一个简单的字符图形游戏，玩家驾驶月球车在月球表面行驶，需要跳跃躲避危险的陨石坑。游戏使用 ncurses 库在终端中渲染画面，操作简单但富有挑战性。

## OHOS 适配
- **构建系统**: 使用 autotools（configure + make）
- **shebang 修复 (E165)**: configure 脚本使用 `#! /bin/sh`，OHOS 无 /bin/sh，替换为 `#!/system/bin/sh`
- **交叉编译**: 使用 `--host=aarch64-unknown-linux-ohos` 指定目标平台，`--build=aarch64-unknown-linux-gnu` 绕过 config.guess
- **ncurses 依赖**: 使用 Conan 源码依赖 `ncurses/6.4` 提供头文件和静态库
- **静态链接 (R26)**: 使用依赖包内 `libncursesw.a` 的绝对路径指定静态链接
- **预生成文件**: Release tarball 已包含预生成的 configure 和 Makefile.in，无需 bootstrap

## 依赖
- 编译工具: clang, autotools
- 编译依赖: ncurses/6.4（Conan 源码构建，静态库）

## 安装产物
- bin/moon-buggy — 游戏主二进制
- share/man/man6/moon-buggy.6 — man page
- share/info/moon-buggy.info — info 文档

## 功能验证
```bash
moon-buggy -V
# 预期输出: Moon-Buggy 1.1.0
```

## 参考
- Homepage: https://www.seehuhn.de/programs/moon-buggy
- GitHub: https://github.com/seehuhn/moon-buggy
- Homebrew formula: https://github.com/Homebrew/homebrew-core/blob/master/Formula/m/moon-buggy.rb
