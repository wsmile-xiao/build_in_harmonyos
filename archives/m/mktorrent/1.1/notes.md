# mktorrent 1.1 适配笔记

## 编译环境
- 构建系统: makefile（GNU Make，无 configure）
- 编译日期: 2026-07-14
- 编译器: clang 15（/data/service/hnp/bin/clang）
- 状态: built（配方验证通过，待 CI 真机验证后发布）

## 源码
- 上游: https://github.com/Rudde/mktorrent
- 版本: git tag v1.1
- 源码包: https://github.com/Rudde/mktorrent/archive/refs/tags/v1.1.tar.gz
- sha256: d0f47500192605d01b5a2569c605e51ed319f557d24cfcbcb23a26d51d6138c9
- 许可证: GPL-2.0-or-later

## 构建说明

mktorrent 是纯 Makefile 项目（GNUmakefile + Makefile + rules.mk）。默认构建（不开启
USE_PTHREADS / USE_OPENSSL）产出单一 `mktorrent` 可执行文件，使用内置 SHA1，仅依赖 libc。

构建命令：
```
make CC=<clang> USE_LONG_OPTIONS=1 OFFPRFX=l -j1
```

无源码补丁；所有适配通过 make 变量与 conanfile.py 的 package() 完成。

## 关键适配点

| # | 事项 | 根因 | 处理 |
|---|------|------|------|
| 1 | 跳过构建期运行 `./prefix` | 上游 Makefile 用 `$(shell ./prefix)` 运行一个临时编译的辅助程序来探测 off_t 的 printf 宽度；OHOS 上未签名的新构建 ELF 无法在构建期执行 | 命令行传入 `OFFPRFX=l`。aarch64 下 `off_t == long`（8 字节），`./prefix` 本应输出 `l`，直接给出等价值，避免运行 |
| 2 | 无 install(1) | HarmonyOS 不带 `install` 命令，`make install` 会失败 | package() 用 `copy()` 把 `mktorrent` 放入 `bin/` |
| 3 | ELF 签名 | OHOS 执行二进制前必须有代码签名，否则 test_package 运行报权限错误 | package() 用 `llvm-objcopy` 去除旧 `.codesign` 段后，用 `binary-sign-tool -selfSign 1` 自签名 |
| 4 | 长选项 | 默认构建仅支持短选项（getopt）；CI L2 冒烟调用 `--help` | 传入 `USE_LONG_OPTIONS=1`（musl 提供 getopt_long） |

## 编译器与链接器
- CC 显式传 `make CC=clang`（字面量，非 shell `${CC}`，满足 R33）。OHOS clang 在 PATH 上。
- 不使用 `self.conf.get("tools.build:compiler_executables:c", check_type=str)`：该 conf 在 OHOS 适配版 Conan 2.29.1 中未注册，会抛 ConanException（CI #1816 首次失败根因）。
- 链接使用 clang 默认链接器；mktorrent 仅链接 libc，无第三方库。

## 依赖
- 无第三方库依赖（不使用 OpenSSL / pthreads）。
- 运行时仅依赖 musl libc。

## test_package
- test.sh 实际驱动 mktorrent：用样本文件生成 `out.torrent`，校验产物非空且以 bencode 字典起始符 `d` 开头。
- 不联网：`-a` 指定的 tracker URL 只写入 metainfo，不会被访问。

## 验证（配方层面）
- conanfile.py 不含 `${CC}` 等 shell 变量自引用（L0h）。
- test_package 实质调用被测二进制（R34 / L1e）。
- 软件级 commands.json 已声明 tool 类型（L0k）。
- 真机编译/运行由 CI（真实鸿蒙 worker）验证。

## 注意事项
- 本机无鸿蒙构建环境，未本地 conan create；上述结论基于源码审查与同模式（lz4/ripmime）已合入配方。
