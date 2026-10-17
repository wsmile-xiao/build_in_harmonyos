# sparse 0.6.4 适配笔记

## 编译环境
- 构建系统: makefile (plain Makefile, no configure script)
- 编译日期: 2026-06-03
- 编译器: clang-wrapper (via clang-wrapper symlinked as gcc)
- 状态: built

## 编译步骤

1. **环境设置**: `ln -sf ~/tmp/bin/clang-wrapper ~/tmp/bin/gcc`, `umask 022`
2. **构建**: `cd ~/tmp/builds/sparse-0.6.4.work && PATH=$HOME/tmp/bin:$PATH make CC=clang-wrapper PREFIX=/storage/Users/currentUser/usr/local -j1 V=1`
3. **Staging安装**: `make install DESTDIR=/storage/Users/currentUser/tmp/test-install-sparse-0.6.4 PREFIX=/storage/Users/currentUser/usr/local`
4. **本地安装**: `make install PREFIX=/storage/Users/currentUser/usr/local`
5. **验证**: `/storage/Users/currentUser/usr/local/bin/sparse --version` → "0.6.4"

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 无 configure 脚本 | sparse 使用纯 Makefile | 直接用 `make CC=clang-wrapper PREFIX=...` 构建 |
| 2 | GCC_BASE 和 MULTIARCH_TRIPLET 检测 | Makefile 调用 `$(CC) --print-file-name=` 和 `-print-multiarch` | clang-wrapper 正确支持这些选项，无需修改 |
| 3 | 可选依赖缺失 | libxml、sqlite3、gtk、llvm 未安装 | 跳过不影响核心功能（c2xml、semind、test-inspect、sparse-llvm 被禁用） |
| 4 | make check 超时 | validation/test-suite 在 OHOS 上卡住 | 跳过并记录原因（per skill guidelines §3 Step 2） |

## 源码修改

无补丁，源码无需修改即可成功编译。

## 依赖版本

- clang: 15.0.4 (clang-wrapper)
- ar: LLVM (llvm-ar)
- make: GNU Make 4.4.1

## 验证结果

```bash
$ sparse --version
0.6.4

$ file /storage/Users/currentUser/usr/local/bin/sparse
ELF shared object, 64-bit LSB arm64, dynamic (/lib/ld-musl-aarch64.so.1), not stripped
```

### 程序级功能测试

- **sparse 静态分析**: ✅ 正确检测赋值条件警告和 static 声明警告
  ```
  test_simple.c:2:11: warning: assignment expression in conditional
  test_simple.c:1:5: warning: symbol 'foo' was not declared. Should it be static?
  ```
- **test-lexing**: ✅ 词法分析引擎正常（198 hits, 953 misses）
- **test-parsing**: ✅ 静默成功
- **test-linearize**: ✅ 静默成功
- **test-show-type**: ✅ 静默成功
- **test-unssa**: ✅ 静默成功
- **test-dissect**: ✅ 静默成功
- **cgcc**: ⚠️ 缺少 Perl 运行环境，部分可用

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| sparse-0.6.4-ohos-aarch64.tar.gz | TBD | 预编译包 |

## 注意事项

- sparse 是纯 Makefile 项目，不支持 configure，需直接用 `make CC=clang-wrapper` 构建
- libxml、sqlite3、gtk、llvm 是可选依赖，不影响核心 sparse 功能
- make check 在 OpenHarmony 上超时，需跳过
---

**编译结束**: 2026-07-15 17:00
**最终状态**: built
