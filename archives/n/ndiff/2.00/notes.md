# ndiff 2.00 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-06-13
- 编译器: clang 15.0.4 / clang++
- 平台: OpenHarmony ARM64 (musl libc)
- 状态: built ✅

## 编译步骤

1. 初始化: `python3 ohc-run.py init-build ndiff 2.00 --url=https://ftp.math.utah.edu/pub/misc/ndiff-2.00.tar.gz`
   - 源码已缓存（225KB tarball），无需重新下载
   - 历史归档: published（复用已有参数）
   - 依赖检查: 无外部依赖
   - 环境检查: clang/make/autoconf/pkg-config 均就绪

2. 配置: `cd $BUILD_SRC_DIR && ./configure --prefix=$DEFAULT_PREFIX`
   - 成功完成，检测到 clang 编译器
   - GMP库未检测到（可选依赖），使用 long double 精度替代
   - gawk 路径: /data/service/hnp/bin/gawk

3. 编译: `make -j1`
   - 生成二进制: ndiff (87KB, 4个目标文件: ndiff.o, awklib.o, regexp.o, store.o)

4. 安装（staging）: `make install DESTDIR=$TEST_PREFIX`
   - 成功安装到 staging 目录
   - 安装文件: bin/ndiff, bin/ndiff-2.00, man/man1/ndiff.1, share/lib/ndiff/ndiff-2.00/ndiff.awk

5. 安装（本地）: `make install`
   - bin/ndiff 和 bin/ndiff-2.00 已安装到 ~/usr/local/bin/
   - scp -p 命令对已存在文件操作受限（Operation not permitted），但不阻塞

6. 打包: `python3 ohc-run.py package ndiff 2.00`
   - 生成预编译包: ndiff-2.00-ohos-aarch64.tar.gz (211KB)
   - 生成debug包: ndiff-2.00-ohos-aarch64-debug.tar.gz (118KB)
   - ELF签名 + strip + 权限修复完成

7. 收尾: `python3 ohc-run.py finish ndiff 2.00 built`
   - 补丁生成: refresh-patch 无新变更，保留现有补丁
   - 归档关闭: status=built
   - G0验证: 平台限制（硬链接），手动验证通过
   - G1-G4质量门禁: 全部PASS

8. 验证: `python3 ohc-run.py verify-build ndiff 2.00`
   - G1-G4: PASS

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | tar 解压硬链接失败 | HMDFS不支持硬链接（Gotchas） | 手动 cp 复制缺失的测试文件（check008-022.in1/in2） |
| 2 | `make install DESTDIR` 硬链接失败 | `LN = ln` 在HMDFS上不支持 | 修改 Makefile.in: `LN = @LN@` → `LN = cp -p` |
| 3 | `make install DESTDIR` 不支持 DESTDIR | 旧版 Makefile 无 DESTDIR 变量 | 修改 Makefile.in: 添加 `DESTDIR =` 行，install/uninstall 规则中所有路径前加 `$(DESTDIR)` |
| 4 | install 目标依赖 uninstall（会先删除 DESTDIR 中不存在的文件） | install-exe: uninstall-exe 依赖 | 移除 uninstall 前置依赖，增加 `mkdir` 确保目录存在 |
| 5 | make check 无法运行 | `/tmp` 只读（E002），check-install-tmp 需要安装到 /tmp/ndiff | 手动逐个运行26个测试用例，全部通过 |

## 源码修改

修改文件: `Makefile.in`（详见补丁 0001-Makefile.in.patch）

核心修改:
- `LN = @LN@` → `LN = cp -p` (避免HMDFS硬链接限制)
- 添加 `DESTDIR =` 变量
- install-exe/install-man/install-shrlib/install-show 规则: 所有路径加 `$(DESTDIR)` 前缀
- uninstall-exe/uninstall-man/uninstall-shrlib 规则: 所有路径加 `$(DESTDIR)` 前缀
- install-exe 移除 `uninstall-exe` 前置依赖，增加 `mkdir $(DESTDIR)$(bindir)` 确保目录存在
- install-man 移除 `uninstall-man` 前置依赖，增加 `mkdir $(DESTDIR)$(mandir)`
- install-shrlib 移除 `uninstall-shrlib` 前置依赖

## 依赖版本

- gawk: /data/service/hnp/bin/gawk（ndiff.awk 库需要）
- 无外部库依赖（GMP可选，缺失不影响编译，使用 long double 精度替代）

## 测试结果

### 源码测试套件（26个用例）

全部 26 个测试用例（check001 ~ check026）通过：
- 精度模式: long double (epsilon = 1.93e-34)
- 参考输出: okay-ldb
- 输出文件和错误日志均与参考完全一致

### 功能验证

| 功能 | 结果 |
|------|------|
| `ndiff --version` | ✅ 输出 Version 2.00 |
| 基础数值比较 | ✅ 正确检测差异和计算误差 |
| 相同文件比较 | ✅ 无差异时不输出 |
| -abserr 绝对误差阈值 | ✅ 正确生效 |
| -relerr 相对误差阈值 | ✅ 正确生效 |
| 大阈值忽略小差异 | ✅ 仅输出最大误差统计 |
| `ndiff --help` | ✅ 正常输出用法信息 |

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| ndiff-2.00-ohos-aarch64.tar.gz | 211KB | 预编译包（ELF签名+strip） |
| ndiff-2.00-ohos-aarch64-debug.tar.gz | 118KB | debug符号包 |
| 0001-Makefile.in.patch | 5.4KB | 平台适配补丁 |

## 注意事项

- ndiff 是数值比较工具（compare files of numerical values），不是 nmap 的组成部分
- `scp -p` 作为 CP 命令用于本地文件复制可以正常工作
- GMP库可选但未安装，影响精度但不影响功能（long double epsilon = 1.93e-34 vs GMP可达到更高精度）
- HMDFS不支持硬链接，所有 `ln` 命令需改为 `cp -p`
- `/tmp` 为只读文件系统（E002），make check 需手动替代
---

**编译结束**: 2026-06-13 15:40
**最终状态**: built
