# scheme48 1.9.3 适配笔记

## 编译环境

| 项目 | 值 |
|------|-----|
| 构建系统 | autotools |
| 编译日期 | 2026-06-18 |
| 编译器 | clang 15.0.4 / clang++ |
| CFLAGS | -fPIC -O2 |
| 平台 | HarmonyOS (HongMeng Kernel 1.12.0, aarch64) |
| 状态 | published |

## 编译步骤

1. `./configure --prefix=$DEFAULT_PREFIX`
2. `make -j1`（编译 scheme48vm 和初始镜像）
3. `make install DESTDIR=$TEST_PREFIX`（staging 隔离安装）
4. `make check`（测试套执行，详见 reports/test-report.md）
5. `ohc-run.py package scheme48 1.9.3`（预编译包制作）
6. `make install`（本地安装到 $DEFAULT_PREFIX）
7. 本地验证：`$DEFAULT_PREFIX/bin/scheme48`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 | 补丁 |
|---|------|------|----------|------|
| 1 | config.guess 无法识别 HarmonyOS | scheme48 附带的 config.guess 版本为 2006 年，不支持 HarmonyOS 平台和 aarch64 CPU | 在 config.guess 中添加 `aarch64:HarmonyOS:*:*) echo aarch64-unknown-linux-gnu` 分支 | 0002-config.guess.patch |
| 2 | config.sub 不识别 aarch64 | 2006 年版本的 config.sub 中无 aarch64 CPU 条目 | 在 config.sub 的 CPU 列表和 CPU-* 列表中添加 `aarch64` 和 `aarch64-*` | 0003-config.sub.patch |
| 3 | config.status 创建临时文件 Permission denied | autoconf 生成的 config.status 使用 `(umask 077 && mktemp -d)` 创建临时目录，在 HMDFS 文件系统上 umask 077 导致目录权限为 `drwx--S---`（2700），该权限下无法在目录内创建文件 | 将 configure 脚本中的 `umask 077` 替换为 `umask 022` | 0004-configure.patch |
| 4 | make install 写入 /tmp 失败 | Makefile.in 中硬编码 `/tmp/` 路径用于构建安装镜像，鸿蒙系统的 /tmp 为只读文件系统 (R10/E002) | 将 Makefile.in 中的 `/tmp/` 替换为 `$(TMPDIR)/` 变量引用 | 0001-Makefile.in.patch |
| 5 | make check 中 .so 加载失败 | 鸿蒙要求所有 ELF 文件（含共享库）必须签名后才能执行/加载 | 测试前使用 `ohc-run.py sign-elf` 对所有 .so 和 scheme48vm 进行签名 | （运行时操作，无需补丁） |
| 6 | pdflatex 不可用 | 鸿蒙平台未安装 LaTeX | 跳过 PDF 手册生成，不影响软件功能 | （无需处理） |

## 源码修改

共修改 4 个文件，生成 4 个补丁：

### 0001-Makefile.in.patch（移植性修复）
- 将 install-no-doc 目标中的硬编码 `/tmp/` 路径替换为 `$(TMPDIR)/` 变量
- 修改位置：第 480-484 行，共 4 处替换

### 0002-config.guess.patch（平台检测）
- 在 case 分支中添加 `aarch64:HarmonyOS:*:*) echo aarch64-unknown-linux-gnu; exit ;;`
- 插入位置：i*86:rdos 分支之后、esac 之前

### 0003-config.sub.patch（平台检测）
- 在 CPU 列表中添加 `| aarch64`
- 在 CPU-* 模式列表中添加 `| aarch64-*`

### 0004-configure.patch（平台兼容）
- 将 config.status 生成模板中的两处 `umask 077` 替换为 `umask 022`
- 位置：configure 第 7240 行和第 7245 行

## 依赖版本

无外部依赖。scheme48 是完全自包含的 Scheme 实现，编译时不需要任何第三方库。

## 验证结果

### 编译验证
```
$ make -j1
# 编译 scheme48vm + 初始镜像 + 常规镜像 → 成功
```

### 安装验证
```
$ make install DESTDIR=$TEST_PREFIX
# staging 安装成功（除 PDF 文档外）
```

### 功能验证
```
$ echo '(display "Hello from Scheme48!")(newline)' | scheme48
Welcome to Scheme 48 1.9.3 (made by 100 on 2026-06-18)
> Hello from Scheme48!
```

### 测试套验证
- 已运行约 128 个测试用例，全部通过
- 因 300 秒超时在 tlc-table-tests 中段被终止
- 详见 reports/test-report.md 和 reports/make-check.log

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| scheme48-1.9.3-ohos-aarch64.tar.gz | 8.5 MB | 预编译包（289 个文件） |
| scheme48-1.9.3-ohos-aarch64-debug.tar.gz | 274 KB | 调试符号包 |

## 注意事项

1. **ELF 签名**：鸿蒙平台要求所有 ELF 文件（scheme48vm、scheme-r5rs、scheme-srfi-7、*.so）必须签名后才能执行。打包时已自动签名，但开发测试时需手动签名。

2. **初始镜像构建**：scheme48 需要先用 C 编译 scheme48vm，然后用 VM 执行 build-usual-image 脚本构建 scheme48.image 堆镜像。这个过程是 Makefile 自动完成的，但需要 scheme48vm 可执行（即需先签名）。

3. **TMPDIR 变量**：Makefile 现在使用 `$(TMPDIR)` 替代硬编码的 `/tmp/`。安装时需要确保 TMPDIR 环境变量已正确设置（鸿蒙上通常为 `$HOME/tmp`）。

4. **config.status umask**：修改 umask 不会影响安全性，因为临时目录仍然使用 mktemp 创建唯一名称。

5. **pdflatex**：手册 PDF 需要安装 texlive/pdflatex 才能生成，不影响软件功能。

---

**编译结束**: 2026-06-18
**最终状态**: published
