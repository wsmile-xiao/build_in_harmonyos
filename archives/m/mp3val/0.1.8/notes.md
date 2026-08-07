# mp3val 0.1.8 适配笔记

## 编译环境
- 构建系统: makefile
- 编译日期: 2026-08-07
- 编译器: clang/clang++
- 状态: published

## 编译步骤

mp3val 没有 configure 脚本，使用 Makefile 直接编译：
1. `make -j1 PREFIX=$DEFAULT_PREFIX` （使用新增的 Makefile）
2. `make install DESTDIR=$TEST_PREFIX PREFIX=$DEFAULT_PREFIX` （staging 安装）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | crossapi.cpp 硦编码 /tmp 路径 | 原始代码硬编码 `/tmp/mp3val.XXXXXX` | 修改为使用 `getenv("TMPDIR")` 环境变量，默认值 `/tmp` |
| 2 | 原始 Makefile.linux 无 install 目标 | 原始项目无 DESTDIR/PREFIX 支持 | 新建 Makefile 包含 install 目标和 DESTDIR/PREFIX 支持 |
| 3 | clean-verify (G0) configure 失败 | mp3val 无 configure 脚本 | mp3val 为 makefile 类型，G0 跳过 configure 步骤 |
| 4 | 源码使用 CRLF 行尾 | 原始 tarball 为 Windows 源码风格 | 补丁使用 --binary 选项应用 |

## 源码修改

1. `0001-fix-hardcoded-tmp-path-for-R10.patch` — crossapi.cpp: 替换硬编码 `/tmp` 为 `getenv("TMPDIR")` (R10)
2. `0002-add-makefile-with-install-target.patch` — 新增 Makefile: 包含 install 目标、DESTDIR/PREFIX 支持、编译规则

## Conan 适配 (2026-08-07)

- 生成 conanfile.py: application 类型 (CLI 工具, 非库)
- 生成 conandata.yml: 含正确 sha256 和 SourceForge URL (含 %20 编码)
- 生成 test_package/: VirtualRunEnv 方式运行 `mp3val -v` 验证二进制
- 创建 commands.json: 声明命令行工具 (R38)
- 修复 SourceForge 下载: SourceForge 阻止 Python urllib, 使用 curl 下载
- 修复补丁 CRLF: 补丁文件转为 LF 格式, build() 中先 sed 转换源码 CRLF→LF
- 修复补丁格式: 补充缺失的尾部上下文行 (7 行匹配 hunk header)
- conan-verify 全部通过: G1✅ G2✅ G3✅ G4✅ L2✅ L4✅ L5✅

## 依赖版本

无外部依赖（纯 C++ 项目，仅依赖标准库）

## 验证结果

```bash
$ mp3val --version
MP3val 0.1.8
$ mp3val -v
0.1.8
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| mp3val-0.1.8-ohos-aarch64.tar.gz | 102KB | 预编译包（stripped, ELF签名） |
| mp3val-0.1.8-ohos-aarch64-debug.tar.gz | 51KB | debug 符号包 |

## 注意事项

- 源码为 Windows 风格（CRLF 行尾），补丁需使用 `--binary` 选项应用
- mp3val 为命令行工具，无共享库
- 跳过 make check（mp3val 无测试套）

---

**编译结束**: 2026-08-07
**最终状态**: published
