# libtasn1 4.20.0 适配笔记

## 编译环境
- 构建系统: autotools (configure + make)
- 编译日期: 2026-09-08
- 编译器: clang 15.0.4 / clang++
- 状态: built

## 编译步骤

```bash
# 源码: https://ftp.gnu.org/gnu/libtasn1/libtasn1-4.20.0.tar.gz
# sha256: 92e0e3bd4c02d4aeee76036b2ddd83f0c732ba4cda5cb71d583272b23587a76c
./configure --prefix=/storage/Users/currentUser/usr/local --disable-doc
make -j1
make check          # 31/31 PASS
make install DESTDIR=<staging>
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 不识别 HarmonyOS 平台 | config.guess 无 aarch64:HarmonyOS 分支 | 补丁 0001：添加 `aarch64:HarmonyOS:*:*` → `aarch64-unknown-linux-ohos` |
| 2 | configure 临时目录权限失败 | HMDFS 上 umask 077 + setgid 导致 `drwx--S---` | 补丁 0002：umask 077 → 007 |
| 3 | 文档构建失败 | 系统无 texinfo/makeinfo | configure 加 `--disable-doc` |

## 源码修改

- `patches/0001-build-aux-config.guess.patch`：config.guess 增加 HarmonyOS 平台检测
- `patches/0002-configure.patch`：configure umask 077 → 007（HMDFS setgid 兼容）

## 依赖版本

- 无第三方依赖（纯 autotools 库）

## 验证结果

```bash
# 上游测试: make check → 31/31 PASS (TOTAL:31 PASS:31 FAIL:0)
# Conan 验证: conan-verify G0-G4/L2/L4/L5 全部 PASS
# W3 本地 CI: build_and_test.sh → L0/L1/L2/L4/L5 全部 PASS (1/1, 100%)
# test_package: ASN.1 INTEGER schema 解析/编码/解码往返测试通过
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | Conan 配方（autotools，--disable-doc，静态库） |
| conandata.yml | 源码声明 + 2 个补丁 |
| test_package/ | 消费者测试（真实调用 libtasn1 API） |
| patches/ | 2 个适配补丁 |

## 注意事项

- 系统同名库 libtasn1 非系统库，配方默认静态编译（shared=False），避免污染系统目录
- `cpp_info.libs = ["tasn1"]`（产物为 libtasn1.a/.so，SONAME 为 libtasn1.so.6）
- 历史 4.21.0 归档（2026-07-15，published）为本版本适配提供了相同补丁方案，本版本独立完成并复验

---

**编译结束**: 2026-09-08 21:39
**最终状态**: built
