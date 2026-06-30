# facad 2.20.16 适配笔记

## 编译环境
- 构建系统: meson
- 编译日期: 2026-06-13
- 编译器: clang 15.0.4 / clang++
- 目标平台: OpenHarmony aarch64 (musl libc)
- 状态: published

## 编译步骤

1. 初始化: `ohc-run.py init-build facad 2.20.16 --url=https://github.com/yellow-footed-honeyguide/facad/archive/refs/tags/v2.20.16.tar.gz`
2. meson 配置: `meson setup builddir --prefix=$DEFAULT_PREFIX`
3. ninja 构建: `ninja -C builddir`（13 个编译单元，1 个链接目标）
4. DESTDIR 安装: `DESTDIR=$TEST_PREFIX ninja -C builddir install`
5. 安全弹窗验证: `facad --version` → "facad version 2.20.16"
6. 质量门禁验证: `ohc-run.py verify-build facad 2.20.16` → G1-G4 PASS
7. 预编译包制作: `ohc-run.py package facad 2.20.16` → 93KB tar.gz
8. 本地安装: `ninja -C builddir install`（不带 DESTDIR）
9. 本地验证: `$DEFAULT_PREFIX/bin/facad --version` → "facad version 2.20.16"
10. 收尾: `ohc-run.py finish facad 2.20.16 published`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | meson 命令无法执行（libpython3.12.so.1.0 缺失） | LD_LIBRARY_PATH 未包含 Python3.12 lib 路径 | 设置 `LD_LIBRARY_PATH=/data/service/hnp/python.org/python_3.12/lib:...` |
| 2 | meson install 子进程无法启动（PYTHONHOME 缺失） | meson 调用 python3-fixed 需要 PYTHONHOME | 设置 `PYTHONHOME=/data/service/hnp/python.org/python_3.12` |
| 3 | G4 manifest 缺少 build_system 字段 | init-build 默认生成 autotools 模板 | 手动添加 `build_system: meson` |
| 4 | G0 clean-verify 使用 autotools ./configure | meson 项目没有 ./configure | 创建 hints/clean-verify-hints.yaml |

## 源码修改

无补丁，源码无需修改即可编译成功。仅产生 2 个非阻塞编译警告：
- `git_integration.h:12:28: warning: no newline at end of file [-Wnewline-eof]`

## 依赖版本

无外部依赖，仅依赖 libc 和 libm（系统自带）。

## 功能验证测试

详细测试报告见 `reports/test-report.md`。此处摘录关键结果：

### 版本验证
```bash
$ facad --version
facad version 2.20.16
```

### 帮助信息
```bash
$ facad --help
Usage: facad [OPTION] [DIRECTORY]
List directory contents with colorful emojis.
Options:
  -h, --help      display this help and exit
  -v, --version   output version information and exit
  -l, --long      display detailed directory listing
  -a, --analytics display directory analytics
```

### 默认列表功能
```bash
$ facad /storage/Users/currentUser/tmp
📁 abduco        📁 builds        📦 aalib-1.4rc5.tar.gz
...（彩色 emoji 目录列表正常输出）
```

### 长格式列表 (-l)
```bash
$ facad -l /storage/Users/currentUser/usr/local/bin
  26.7M  4d ago  👑:20001006 📜:👀✏️🚀  💾 prodigal
...（文件大小、时间、权限信息正确显示）
```

### 分析模式 (-a)
```bash
$ facad -a /storage/Users/currentUser/usr/local/bin
🧮 Total Size    : 250.5M
🗃️  Files         : 710
🐘 Largest File  : prodigal [26.7M]
...（目录分析统计信息正确）
```

### 单元测试
```bash
$ ninja -C builddir test
No tests defined.
```
项目无单元测试套件。功能验证通过 6/6 = 100%。

### 二进制文件属性
```bash
$ file facad
ELF shared object, 64-bit LSB arm64, dynamic (/lib/ld-musl-aarch64.so.1), not stripped
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| facad-2.20.16-ohos-aarch64.tar.gz | 93KB | 预编译包（ELF 签名，strip 后） |
| facad-2.20.16-ohos-aarch64-debug.tar.gz | 103KB | 调试符号包 |
| facad (二进制) | 151KB | 本地安装的可执行文件 |
| facad.1 (man page) | 5156 | 手册页 |

## 预编译包内容

```
bin/facad                — 主可执行文件（ELF 签名 + strip）
share/man/man1/facad.1   — 手册页
lib/external/            — 外部依赖目录（空，无外部依赖）
```

## 注意事项

- meson 项目，需设置 `LD_LIBRARY_PATH` 和 `PYTHONHOME` 以正确运行 meson 命令
- DESTDIR install 需环境变量 `DESTDIR=$TEST_PREFIX`（meson 用环境变量而非参数传递）
- 编译仅有 2 个无害警告（git_integration.h 缺少文件末尾换行符），不影响功能
- G0 clean-verify 需 hints/clean-verify-hints.yaml 为 meson 项目提供自定义构建命令

## 关键修复记录

### 1. meson 运行环境修复
**问题**：meson 二进制文件链接到 python3-fixed，需要 PYTHONHOME 环境变量才能正常工作。
**方案**：设置 `PYTHONHOME=/data/service/hnp/python.org/python_3.12` 或使用 `python3 -m mesonbuild.mesonmain` 替代直接调用 meson。

### 2. G0 clean-verify hints 配置
**问题**：clean-verify 默认使用 autotools `./configure`，meson 项目不适用。
**方案**：创建 `hints/clean-verify-hints.yaml`：
```yaml
build_system: meson
configure_command: "PYTHONHOME=/data/service/hnp/python.org/python_3.12 python3 -m mesonbuild.mesonmain setup build --prefix=$DEFAULT_PREFIX"
build_command: "ninja -C build -j1"
install_command: "PYTHONHOME=/data/service/hnp/python.org/python_3.12 DESTDIR=__DESTDIR__ ninja -C build install"
```

### 3. DESTDIR install 环境修复
**问题**：ninja install 调用 meson 内部命令时使用 python3-fixed（无 PYTHONHOME）。
**方案**：运行 DESTDIR install 时需设置 `PYTHONHOME=/data/service/hnp/python.org/python_3.12`。

---

**编译结束**: 2026-06-13
**最终状态**: published
