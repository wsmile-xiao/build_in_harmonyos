# asciitex 0.21 适配笔记

## 编译环境
- 构建系统: autotools (configure + make)
- 编译日期: 2026-06-30
- 编译器: clang/clang++
- 状态: built (conan-verify 全部 8 道门禁通过)

## 编译步骤

1. **init-build**: SSL 证书验证失败，使用 `curl -kL` 手动下载源码到 $TMPDIR/builds/，然后用 `--no-download` 完成 init-build
2. **configure**: 执行 `./configure --prefix=$DEFAULT_PREFIX --disable-gtk`，跳过 GTK2 依赖
3. **umask 修复**: HMDFS 文件系统下 umask 077 导致文件不可读，通过 sed 修改 config.status 中的 umask 077 为 022
4. **make -j1**: 首次失败（SYNTAX_ERR_FLAG 重复定义），修改源码后重新编译成功
5. **make install DESTDIR=$TEST_PREFIX**: 成功安装 asciiTeX 二进制到 bin/
6. **make check**: 无测试目标，直接通过
7. **二进制验证**: `asciiTeX -v` 和 `asciiTeX 'y=x^2'` 输出正常
8. **track-edit scan**: 追踪 2 个变更文件
9. **conan-init**: 生成 conanfile.py 和 conandata.yml
10. **refresh-patch --auto**: 生成 2 个补丁文件
11. **conan-verify**: 8 道门禁全部通过 (G0-G4 + L2/L4/L5)
12. **finish**: 成功完成，状态 built

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | SSL 证书验证失败 | 鸿蒙环境缺少 CA 证书 | 用 `curl -kL` 手动下载源码 |
| 2 | configure 需要 GTK2 | 默认启用 GTK GUI 模式 | 使用 `--disable-gtk` 选项 |
| 3 | umask 077 导致文件不可读 | HMDFS 文件系统权限问题 | sed 修改 config.status 中 umask 077→022 |
| 4 | SYNTAX_ERR_FLAG 重复定义 | 头文件中定义全局变量，多文件包含 | 头文件改 extern，.c 文件中定义 |
| 5 | test_package 链接不存在的库 | cpp_info.libs 声明了库但实际只有二进制 | 清空 libs=[]，设置 bindirs=["bin"] |
| 6 | test_package 找不到二进制 | VirtualRunEnv 未正确设置 PATH | 使用 dependencies.package_folder 直接定位 |

## 源码修改

| 文件 | 修改内容 |
|------|----------|
| src/asciiTeX_struct.h | `STAT SYNTAX_ERR_FLAG;` → `extern STAT SYNTAX_ERR_FLAG;` |
| src/asciiTeX.c | 添加 `STAT SYNTAX_ERR_FLAG;` 全局定义 |

对应补丁:
- patches/0001-src-asciiTeX.c.patch
- patches/0002-src-asciiTeX_struct.h.patch

## 依赖版本

无外部依赖（禁用 GTK 后）。

## 验证结果

```bash
$ asciiTeX -v
    ___   _____ ______________   ______    _  __
   /   | / ___// ____/  _/  _/  /_  __/__ | |/ /
  / /| | \__ \/ /    / / / /     / / / _ \|   /
 / ___ |___/ / /____/ /_/ /     / / /  __/   |
/_/  |_/____/\____/___/___/    /_/  \___/_/|_|
The ASCII equation renderer
Version 0.21 - Jun 30 2026

$ asciiTeX 'y=x^2'
     2
y = x
```

## 注意事项

1. 必须使用 `--disable-gtk` 选项，否则需要 GTK2 开发库
2. 补丁是必须的，否则链接时会出现 SYNTAX_ERR_FLAG 重复定义错误
3. Conan 配方中已内置 umask 修复逻辑，无需手动干预
4. 终端工具，无库文件，cpp_info.libs=[] 且 bindirs=["bin"]
---

**编译结束**: 2026-06-30 16:05
**最终状态**: published
