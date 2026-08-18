# eless 0.7 适配笔记

## 编译环境
- 构建系统: custom (pure bash script, no C/C++ compilation)
- 编译日期: 2026-08-14
- 编译器: N/A (bash script tool)
- 状态: built

## 编译步骤

eless 是一个纯 bash 脚本工具，使用 Emacs 作为分页器。无 configure/make 编译步骤。

安装方式：
1. 上游 Makefile 的 `install` 目标会先 `make all`（需要 emacs 来 tangle eless.org → eless），
   但发行版 tarball 中已包含生成好的 `eless` 脚本，无需重新 tangle。
2. 直接安装 `eless` 脚本到 `bin/` 即可：
   ```bash
   mkdir -p $DESTDIR/bin
   cp -f eless $DESTDIR/bin/eless
   chmod 755 $DESTDIR/bin/eless
   ```

DESTDIR 模式验证（L2 smoke test）：
```bash
# 安装到临时目录
mkdir -p $TEST_PREFIX/bin
cp -f eless $TEST_PREFIX/bin/eless
chmod 755 $TEST_PREFIX/bin/eless

# 验证可运行（L2 smoke test）
eless -V
# 输出: Eless version v0.7
# 注: debug 行会尝试调用 emacs/info，未安装时会输出到 stderr 但不影响 -V 功能
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `eless -V` 时出现 `emacs: command not found` 和 `info: command not found` | 脚本的 debug 行（line 158-161）尝试调用 emacs/perl/bash/info 获取版本信息 | 非致命：这些是 debug 输出到 stderr，不影响 `-V` 功能。eless 本身需要 emacs 作为运行时依赖（分页器），但打包时不需要 emacs |

## 源码修改

无补丁。使用上游 v0.7 原始源码。

## 依赖版本

无构建时依赖（纯 bash 脚本）。
运行时依赖：emacs（eless 是 emacs 的包装器，但不需要在打包时安装 emacs）。

## 验证结果

```bash
# L2 smoke test: eless -V
$ eless -V
Eless version v0.7
# (stderr: emacs/info not found warnings — non-fatal debug output)

# SHA256 of tarball
$ cat .tarball-sha256
de7a7891a20a5e7f25c0b5df812edaea87ab0d3336d41821a24e2d248aaf4abc
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| eless | 37265 bytes | 纯 bash 脚本，安装到 bin/ |

## 注意事项

- eless 是纯 bash 脚本工具，不是 C/C++ 库，不需要编译器。
- 上游 Makefile 的 install 目标需要 emacs 来重新生成脚本，但发行版 tarball 已包含生成好的脚本。
- Conan 配方中 build() 方法直接 copy 脚本，不调用 make。
- package_info() 中不需要 cpp_info.libs（无库文件），只需 cpp_info.bindirs 声明 bin 目录。
- commands.json 必须创建（R38：命令行工具必须声明）。
---

**编译结束**: 2026-08-14 09:32
**最终状态**: built
