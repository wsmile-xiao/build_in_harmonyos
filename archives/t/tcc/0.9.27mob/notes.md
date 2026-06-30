# tcc 0.9.27mob 适配笔记

## 编译环境
- 构建系统: autotools（configure + Makefile）
- 编译日期: 2026-05-26
- 编译器: clang 15.0.4
- 状态: built（编译成功，等待预编译包制作）

## 编译步骤

1. 配置：
   ```bash
   ./configure --prefix=$HOME/usr/local --cc=clang \
     --sysroot=/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/sysroot \
     --triplet=aarch64-linux-ohos
   ```

2. 编译 tcc 主程序：
   ```bash
   make -j2
   ```

3. 编译 libtcc1.a（使用 clang）：
   ```bash
   cd lib && make arm64-libtcc1-usegcc=yes
   ```

4. Staging 安装：
   ```bash
   make install DESTDIR=$TEST_PREFIX
   ```

5. ELF 签名：
   ```bash
   python3 $SKILL_ROOT/scripts/ohc-run.py sign-elf $TEST_PREFIX/$DEFAULT_PREFIX/bin/tcc
   ```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 报错 'gcc' not found | 系统无 gcc | --cc=clang |
| 2 | tcov.c 'stdio.h' not found | 缺 sysroot | --sysroot |
| 3 | stdio.h 'bits/alltypes.h' not found | 缺 triplet | --triplet=aarch64-linux-ohos |
| 4 | stdio.h 'invalid number' | tcc 不支持 OpenHarmony 属性 | arm64-libtcc1-usegcc=yes |
| 5 | 程序 Permission denied | ELF 签名要求 | sign-elf（平台限制） |

## 验证结果

```bash
$ tcc -v
tcc version 0.9.28rc (AArch64 Linux)

$ tcc -print-search-dirs
install: ~/usr/local/lib/tcc
include: sysroot/usr/include/aarch64-linux-ohos, sysroot/usr/include
libraries: ~/usr/local/lib/tcc, sysroot/usr/lib/aarch64-linux-ohos, sysroot/usr/lib
```

## 注意事项

1. ELF 签名限制：所有可执行文件必须签名
2. libtcc1.a 必须用 clang 编译
3. configure 参数必填：--cc=clang, --sysroot, --triplet
4. make test 会失败（测试程序需要签名）

---

**编译结束**: 2026-05-26
**最终状态**: built
---

**编译结束**: 2026-05-26 15:34
**最终状态**: built
