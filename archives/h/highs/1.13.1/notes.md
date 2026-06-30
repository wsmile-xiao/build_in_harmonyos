# highs 1.13.1 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-05-28
- 编译器: clang 15.0.4 (OpenHarmony 交叉编译工具链, Target: aarch64-unknown-linux-ohos)
- 状态: built

## 编译步骤

1. **初始化构建**: `python3 ohc-run.py init-build highs 1.13.1 --url=https://github.com/ERGO-Code/HiGHS/archive/refs/tags/v1.13.1.tar.gz`
2. **手动下载源码**: 因 SSL 证书问题无法自动下载，使用 `curl -k` 手动下载到 ~/tmp/builds/
3. **CMake 配置**: `cmake -S . -B build -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX -DCMAKE_BUILD_TYPE=Release < /dev/null`
4. **编译**: `make -j4` (使用4线程加速)
5. **DESTDIR 安装**: `make install DESTDIR=$TEST_PREFIX`
6. **测试**: `make test` → 2/2 PASS
7. **打包**: `python3 ohc-run.py package highs 1.13.1`
8. **本地安装**: `make install` (安装到 ~/usr/local)
9. **G0 验证**: `python3 ohc-run.py clean-verify highs 1.13.1` → PASS
10. **收尾**: `python3 ohc-run.py finish highs 1.13.1 built`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | SSL 证书验证失败，无法下载源码 | HMDFS 文件系统 SSL 证书库不完整 | 使用 `curl -k` 手动下载 |
| 2 | HiGHS 无 configure 脚本，G0 clean-verify 硬编码运行 `bash ./configure` | HiGHS 是纯 CMake 项目，不提供 autotools configure 脚本 | 创建 configure wrapper，将 `--prefix=` 转为 cmake `-D` 参数 |
| 3 | `bash ./configure` 导致 cmake 编译器识别为 unknown | bash 5.3.0 的 stdin 处理在 HMDFS 上引发 seek 错误，cmake TryCompile 中 `head` 命令失败 | 在 configure wrapper 中添加 `< /dev/null` stdin 重定向；使用 `cmake -S/-B` 替代 `cd + cmake ..` |
| 4 | G0 `make` 失败 (No makefile found) | G0 在源码目录执行 `make`，但 cmake 构建文件在 `build` 子目录 | 创建 Makefile wrapper，转发 make 命令到 build 子目录 |
| 5 | `cd build && cmake ..` 模式失败 | bash 子进程 cd 后 cmake 仍然受 HMDFS stdin 影响 | 改用 `cmake -S . -B build`（源目录外构建）|
| 6 | manifest configure_options YAML 列表格式导致 G0 解析错误 | G0 用正则匹配单行值，但 manifest 配了 YAML 列表格式 | 清空 configure_options，由 configure wrapper 内部处理 |

## 源码修改

### 补丁: 0001-ohc-wrapper.patch

该补丁创建了两个新文件（原始源码不存在这些文件）:

**1. configure** — autotools → cmake 转换 wrapper:
```sh
#!/bin/sh
PREFIX=""
EXTRA_OPTS=""
for arg in "$@"; do
    case "$arg" in
        --prefix=*) PREFIX="${arg#--prefix=}" ;;
        *) EXTRA_OPTS="$EXTRA_OPTS $arg" ;;
    esac
done
if [ -z "$PREFIX" ]; then PREFIX="$HOME/usr/local"; fi
cmake -S . -B build -DCMAKE_INSTALL_PREFIX="$PREFIX" -DCMAKE_BUILD_TYPE=Release $EXTRA_OPTS < /dev/null
```

**2. Makefile** — make 命令转发 wrapper:
```makefile
BUILD_DIR = build
.PHONY: all install test check clean
all:
	$(MAKE) -C $(BUILD_DIR) all
install:
	$(MAKE) -C $(BUILD_DIR) install DESTDIR=$(DESTDIR)
test:
	$(MAKE) -C $(BUILD_DIR) test
check: test
clean:
	$(MAKE) -C $(BUILD_DIR) clean
```

**关键设计决策**:
- `< /dev/null` 防止 HMDFS stdin pipe seek 错误
- `cmake -S/-B` 避免 cd 子进程中的 HMDFS 问题
- Makefile wrapper 使 G0 的 `make install DESTDIR=` 模式可正常工作

## 依赖版本

| 依赖 | 版本 | 说明 |
|------|------|------|
| zlib | 1.3.1 | 已预编译安装到 ~/usr/local |
| pthread | 系统库 | musl libc 提供 |

## 验证结果

```bash
$ ~/usr/local/bin/highs --version
HiGHS version 1.13.1 Githash n/a. Copyright (c) 2026 under MIT licence terms

$ make test
100% tests passed, 0 tests failed out of 2
Total Test time (real) = 0.32 sec

$ python3 ohc-run.py clean-verify highs 1.13.1
✅ ✅ G0 干净构建验证通过
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| highs-1.13.1-ohos-aarch64.tar.gz | 17MB | Release 预编译包 |
| highs-1.13.1-ohos-aarch64-debug.tar.gz | 870KB | Debug 符号包 |
| 0001-ohc-wrapper.patch | 1.5KB | configure + Makefile wrapper 补丁 |

## 注意事项

1. **HMDFS stdin 问题**: bash 5.3.0 在 HMDFS 上运行 cmake 时，stdin 管道不支持 seek，导致 TryCompile 失败。必须使用 `< /dev/null` 重定向
2. **G0 clean-verify 兼容**: 纯 CMake 项目需要创建 configure + Makefile wrapper 才能通过 G0 的 `bash ./configure && make && make install DESTDIR=` 流程
3. **refresh-patch 限制**: finish 流程中的 refresh-patch 步骤可能无法正确生成含 tab 的 Makefile 补丁，建议使用合并补丁 (0001-ohc-wrapper.patch)
4. **musl 兼容警告**: zstr 库输出 `#warning "broken strerror_r()"` 警告，不影响功能

---
**编译结束**: 2026-05-28 14:02
**最终状态**: built