# ired 0.6 适配笔记

## 编译环境
- 构建系统: makefile（纯 Makefile，无 configure/CMake）
- 编译日期: 2026-09-16
- 编译器: clang 15（Conan tools.build:compiler_executables）
- 目标: OHOS aarch64 (os=OHOS, arch=armv8)
- 状态: built

## 编译步骤

```bash
# 源码核验
# 官方 tag: https://github.com/radare/ired  tag 0.6 (default branch: master)
# tarball: https://github.com/radare/ired/archive/refs/tags/0.6.tar.gz
# sha256: c15d37b96b1a25c44435d824bd7ef1f9aea9dc191be14c78b689d3156312d58a

# 上游直编译验证（work 目录）
make CC=clang -j1        # 产物: ired bdiff (ELF arm64, musl)

# 上游测试（bash + jot/seq shim + md5sum）
export PATH=$HOME/tmp/bin:$PATH   # jot → seq shim, md5 → md5sum shim
cd t && bash test.sh              # 16 个 bdiff→ired -n 往返用例, 16/16 通过

# Conan 配方
python3 scripts/ohc-run.py conan-verify ired 0.6
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游 t/test.sh 的 `jot 1` 探测失败后 else 分支把 `seq` 结果赋给 `md5` 而非 `SEQ`，导致用例循环为空 | 上游脚本假设 BSD jot；无 jot 环境下 fallback 有 bug | 不改上游测试：提供 jot→seq、md5→md5sum 兼容 shim 于 PATH，使 16 个用例真实执行 |
| 2 | conan-init 误判 build_system=autotools | init 按 URL 猜测，ired 实际是纯 Makefile | 手写 raw Makefile CLI 配方（参考 conanfile-makefile.py.tmpl 与 cronutils 1.1 配方） |
| 3 | /tmp 磁盘 100% 满导致 tarball 写入失败 | 环境 /tmp 容量耗尽 | 使用 TMPDIR=$HOME/tmp 下载（SKILL §7 /tmp 陷阱对策） |
| 4 | OHOS 未签名 ELF 运行时被拒（PermissionError） | 无 .codesign 段 | package() 阶段 llvm-objcopy 移除旧段 + binary-sign-tool 自签名（cronutils 同型） |

## 源码修改

无（未修改上游源码；无补丁）。

## 依赖版本

无外部依赖（仅 libc）。

## 验证结果

```bash
# 上游测试（16/16 通过）
$ cd t && PATH=$HOME/tmp/bin:$PATH bash test.sh
0 file1 file1 … 0 file4 file4   # 16 行全部 ret=0

# 消费者测试（test_package）: 安装后执行 ired 写/读/搜索 + bdiff diff，8 断言
```

## 交付物

| 文件 | 说明 |
|------|------|
| archives/i/ired/commands.json | R38 CLI 声明（ired/bdiff 工具） |
| archives/i/ired/0.6/conanfile.py | raw Makefile CLI 配方（含 OHOS 签名） |
| archives/i/ired/0.6/conandata.yml | 官方 tag 源码 + SHA256 |
| archives/i/ired/0.6/test_package/ | explicit test_type 消费者测试（test_ired.py，8 断言） |

## 注意事项

- ired 是 CLI 工具包（非库），package_info 无 libs，仅 bindirs/PATH。
- 上游测试依赖 bsdtools jot/md5sum，平台已提供 /usr/bin/seq 与 /usr/bin/md5sum，shim 可复现。
- t/test.sh 也支持 `$1 $2` 单对参数模式（btest 直接调用）。
---

**编译结束**: 2026-09-16 22:12
**最终状态**: built
