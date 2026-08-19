# enchive 3.5 适配笔记

## 编译环境
- 构建系统: makefile (plain Makefile, no configure)
- 编译日期: 2026-08-19
- 编译器: clang 15.0.4 (aarch64-unknown-linux-ohos target)
- 状态: built

## 编译步骤

1. `ohc-run.py init-build enchive 3.5 --url=https://github.com/skeeto/enchive/releases/download/3.5/enchive-3.5.tar.xz` — 下载、解压、骨架、环境检查全部通过
2. 编写 conanfile.py（Makefile 模式，package_type=application）+ conandata.yml + test_package/
3. `make CC="clang" CFLAGS="-fPIC -O2" LDFLAGS="" -j2` — 编译成功，产出 aarch64 OHOS ELF
4. 手动安装：`cp enchive $TEST_PREFIX/bin/`（OHOS 缺 install 命令）
5. 功能验证：keygen → archive(encrypt) → extract(decrypt) 往返测试通过

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | make install 失败 | OHOS 缺 `install` coreutil | package() 中用 conan.tools.files.copy 直接复制二进制 |
| 2 | make -j2 jobserver fifo 警告 | HMDFS 不支持 mkfifo | 非致命，编译仍成功；conanfile 用 -j1 规避 |
| 3 | enchive keygen 默认访问 ~/.enchive/ | 需要 /data 权限 | 测试用 -p/-s 显式指定密钥路径 |
| 4 | init-build 误判 BUILD_SYSTEM=autotools | enchive 无 configure 但有 Makefile | 手动修正 conanfile.py 为 Makefile 模式 |

## 源码修改

无补丁。enchive 3.5 源码零修改即可在 OHOS 上编译。conandata.yml `patches: {}`。

## 依赖版本

无外部依赖。enchive 是纯 C 实现，仅依赖 libc（OHOS musl libc）。
- ChaCha20: src/chacha.c (自实现)
- Curve25519: src/curve25519-donna.c (自实现)
- SHA256: src/sha256.c (自实现)

## 验证结果

```bash
# 二进制类型验证
file enchive
# → ELF shared object, 64-bit LSB arm64, dynamic (/lib/ld-musl-aarch64.so.1), not stripped

# 安全属性
llvm-readelf -d enchive | grep FLAGS_1
# → NOW PIE (PIE + Full RELRO enabled)
llvm-readelf -l enchive | grep GNU_STACK
# → RW (NX stack, non-executable)

# 版本验证
./enchive --version
# → enchive 3.5

# 加解密往返测试
printf '\n' | enchive -p pubkey -s seckey keygen
echo "test" > plaintext.txt
printf '\n' | enchive -p pubkey -s seckey archive plaintext.txt
printf '\n' | enchive -p pubkey -s seckey extract plaintext.txt.enchive decrypted.txt
diff plaintext.txt decrypted.txt
# → MATCH (round-trip verified)
```

## 交付物

| 文件 | 说明 |
|------|------|
| archives/e/enchive/3.5/conanfile.py | Conan 配方 (Makefile, application) |
| archives/e/enchive/3.5/conandata.yml | 源码 + SHA256 |
| archives/e/enchive/3.5/test_package/test.sh | 功能测试脚本 (R34) |
| archives/e/enchive/3.5/test_package/conanfile.py | 测试包配方 |
| archives/e/enchive/3.5/test_package/MANIFEST.yml | 上游测试声明 |
| archives/e/enchive/3.5/manifest.yaml | 版本级 manifest |
| archives/e/enchive/commands.json | 软件级命令声明 (R38) |

## 注意事项

- enchive Makefile 默认 CFLAGS (`-ansi -pedantic -Wall -Wextra -O3 -g3`) 是 GCC 导向的，OHOS clang 用 `-O2` 即可编译通过
- enchive 是命令行工具（package_type=application），非库；package_info 使用 bindirs=["bin"]，libs=[]
- enchive 无 make check 目标，功能验证通过 keygen→archive→extract 加解密往返测试
- OHOS `/tmp` 只读，测试临时文件需用 `$TMPDIR`
---

**编译结束**: 2026-08-19 09:41
**最终状态**: built
