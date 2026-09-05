# xxd 9.1.0 适配笔记

## 编译环境
- 构建系统: makefile (纯 Makefile，非 autotools)
- 编译日期: 2026-08-30
- 编译器: clang (LLVM)
- 链接器: GNU ld (/data/service/hnp/bin/ld.bfd) - 条件性使用
- 状态: built
- 源码嵌套: vim 仓库内 src/xxd/ 子目录（build_subdir=src/xxd）

## 编译步骤

1. 下载 vim v9.1.0 源码 (xxd 在 src/xxd/ 子目录中)
2. 使用 Conan 配方构建:
   ```
   conan create archives/x/xxd/9.1.0/conanfile.py -pr ci/conan/profiles/ohos-aarch64 --build=missing
   ```
3. Makefile 自动添加 -DUNIX 宏，无需额外配置
4. 传递 CC=clang 和 CFLAGS="-fPIC -O2"
5. LDFLAGS 条件性使用: 仅当 /data/service/hnp/bin/ld.bfd 存在时才使用 -fuse-ld=ld.bfd
6. ELF 签名: 仅当 binary-sign-tool 可用时执行
7. 安装 xxd 二进制到 bin/

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 源码嵌套在 vim 仓库中 | xxd 是 vim 的子目录 (src/xxd/) | conanfile.py 中使用 os.path.join(source_folder, "src", "xxd") 定位 |
| 2 | LDFLAGS 在 CI 中失败 | CI 环境无 /data/service/hnp/bin/ld.bfd | 改为条件性使用: os.path.isfile(ld_bfd) 判断 |
| 3 | gh-proxy.com 镜像 URL 违反 PF7 | conandata.yml 中使用了非官方镜像 | 仅保留 GitHub 官方 URL |
| 4 | test_package 硬编码 bash 路径 | /data/service/hnp/bin/bash 在 CI 不可用 | 改用 shutil.which("bash") 从 PATH 查找 |
| 5 | test_xxd.sh shebang 不便携 | 硬编码 /data/service/hnp/bin/bash | 改为 #!/bin/bash |
| 6 | manifest.yaml 有重复 software 键和 typo | 旧版本生成时错误 | 修复重复键和 systm→system 拼写 |

## 源码修改

- 无需修改源码 (patches: [])
- xxd 是纯 C 单文件 (xxd.c)，仅依赖标准库

## 依赖版本

- 无额外依赖（纯 C 实现，仅依赖 libc）
- musl 动态链接 (/lib/ld-musl-aarch64.so.1)

## 实际执行的验证命令

```bash
# 版本检查
$ xxd -v
xxd 2022-01-14 by Juergen Weigert et al.

# 十六进制转储
$ printf "hello" | xxd
00000000: 6865 6c6c 6f                        hello

# 纯十六进制输出
$ printf "hello" | xxd -ps
68656c6c6f

# C 语言数组输出
$ printf "hello" | xxd -i
  unsigned char buf[] = {
    0x68, 0x65, 0x6c, 0x6c, 0x6f
  };
  unsigned int buf_len = 5;

# 反向操作
$ printf "hello" | xxd -ps | xxd -r -ps
hello
```

## 质量门禁结果

| 门禁 | 结果 | 备注 |
|------|------|------|
| G0 干净构建验证 | PASS | 无补丁，源码自包含 |
| G1 二进制完整性 | PASS | ELF 64-bit LSB arm64 |
| G2 功能可用性 | PASS | xxd -v 输出版本信息 |
| G3 可移植性 | PASS | 无 RPATH、ELF 签名通过 |
| G4 档案完整性 | PASS | manifest, notes, patches 完整 |

## 注意事项

- xxd 是 vim 编辑器项目的一部分，源码在 vim 仓库的 src/xxd/ 目录
- Makefile 自动添加 -DUNIX 宏，无需手动传递
- LDFLAGS 使用 ld.bfd 是条件性的，仅在本地 OHOS 设备上有效
- CI 环境使用默认链接器 (lld)
- conandata.yml 仅包含 GitHub 官方 URL，不使用任何镜像代理 (PF7/R39 合规)

---
**编译结束**: 2026-08-30
**最终状态**: built
---

**编译结束**: 2026-09-05 06:24
**最终状态**: built
