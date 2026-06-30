# bonnie++ 2.00a 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-06-18
- 编译器: clang 15.0.4 / clang++
- 状态: published

## 编译步骤

```bash
cd $BUILD_SRC_DIR
./configure --prefix=$DEFAULT_PREFIX
make -j2
make install DESTDIR=$TEST_PREFIX  # R20 DESTDIR 模式
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 | 知识图谱 |
|---|------|------|----------|----------|
| 1 | config.status: can't create ./confdQaQR6/subs1.awk: Permission denied | autoconf 使用 `umask 077` 创建临时目录，HMDFS 不兼容 | `sed -i 's/umask 077/umask 022/g' configure` | E011（已知） |
| 2 | make install DESTDIR= 安装到错误路径 | Makefile.in 不支持 DESTDIR | 补丁 install 目标添加 `$(DESTDIR)` 前缀 | L3 本版笔记 |
| 3 | 二进制执行提示 Operation not permitted | ELF 未签名 | `ohc-run.py sign-elf` 签名 | 平台要求 |
| 4 | bon_csv2txt 无法执行 | Perl 脚本，平台无 Perl | 已知限制，不影响核心功能 | L3 本版笔记 |

## 源码修改

1. **configure** — `umask 077` → `umask 022`（2处）：HMDFS 文件系统不兼容 umask 077 创建的目录（E011）
2. **Makefile.in** — install-bin 和 install 目标添加 `$(DESTDIR)` 前缀（R20 DESTDIR 模式）
3. **Makefile** — 同 Makefile.in，生成文件同步修改

## 依赖版本

无外部依赖（仅需 libc 的 pthread 支持）

## 功能验证结果（真实执行）

| 工具 | 命令 | 结果 |
|------|------|------|
| bonnie++ 文件IO | `bonnie++ -s 64 -r 32 -n 5 -m ohos-aarch64 -f -q` | ✅ 退出码 0，CSV 输出正常 |
| bonnie++ 元数据 | `bonnie++ -s 0 -n 10 -m test-ohos -f -q` | ✅ 退出码 0，CSV 输出正常 |
| zcav | `zcav -b 1 -c 1 <10MB文件>` | ✅ 4117 MB/s 读取速度 |
| getc_putc | `getc_putc -s 64 -m getc-test` | ✅ 8 种 I/O 模式全部完成 |
| generate_randfile | `generate_randfile -f file 1000` | ✅ 生成 8000 字节随机数据 |
| bon_csv2html | `echo CSV | bon_csv2html` | ✅ 生成完整 HTML 表格 |
| bon_csv2txt | `echo CSV | bon_csv2txt` | ⚠️ Perl 脚本，平台无解释器 |

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| bonnie++-2.00a-ohos-aarch64.tar.gz | 311KB | 预编译包（含 ELF 签名） |
| bonnie++-2.00a-ohos-aarch64-debug.tar.gz | 96KB | 调试符号包 |

## 注意事项

- bonnie++ 是文件系统基准测试工具，没有 `make check` 目标
- 二进制需要 ELF 签名才能在鸿蒙系统上执行
- zcav 默认块大小 64MiB，测试小文件需用 `-b 1` 降低块大小
- bon_csv2txt 为 Perl 脚本，鸿蒙平台默认无 Perl 解释器（已知限制）
- 7 个可执行文件中 6 个完全通过功能测试

---

**编译结束**: 2026-06-18 11:30
**最终状态**: published
