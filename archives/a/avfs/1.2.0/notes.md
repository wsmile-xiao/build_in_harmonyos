# avfs 1.2.0 适配笔记

## 编译环境
- 构建系统: autotools (configure + make)
- 编译日期: 2026-07-02
- 编译器: clang 15.0.4 / clang++
- 状态: built

## 编译步骤

1. 下载源码: `https://downloads.sourceforge.net/project/avf/avfs/1.2.0/avfs-1.2.0.tar.bz2`
2. 解压源码到工作目录
3. 打补丁:
   - 0001-config.guess.patch: 添加 OHOS/HarmonyOS 检测到 config.guess
   - 0002-config.sub.patch: 添加 ohos-linux triplet 支持到 config.sub
   - 0003-configure-mktemp-fix.patch: 修复 HMDFS 上 mktemp 失败 (E125)
4. 设置环境变量: `export CC=clang CXX=clang++`
5. 执行 configure: `./configure --prefix=$DEFAULT_PREFIX`
6. 执行 make: `make -j1`
7. 执行 make install: `make install DESTDIR=$TEST_PREFIX`
8. 执行 make check (通过，avfs 没有正式测试套件)
9. 功能测试: 自定义测试验证库链接和虚拟文件系统操作

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 不识别 HarmonyOS | GNU config.guess 不包含 __OHOS__ 检测分支 (E007) | 补丁 0001: 添加 OHOS 检测到 config.guess |
| 2 | config.sub 不识别 ohos-linux triplet | GNU config.sub 不包含 ohos-linux 和 linux-ohos 支持 (E007) | 补丁 0002: 添加 ohos-linux triplet 到 config.sub |
| 3 | configure 失败: mktemp 不工作 | HMDFS 上 mktemp -d "./confXXXXXX" 失败 (E125) | 补丁 0003: 将 mktemp 替换为 TMPDIR 固定路径 |
| 4 | configure 失败: cc 不存在 | OHOS 上没有 cc/c++ 软链接，只有 clang (E001) | 设置 CC=clang CXX=clang++ 环境变量 |
| 5 | test_package 运行时找不到 libavfs.so.1 | OHOS 共享库不在标准路径，LD_LIBRARY_PATH 未设置 | test_package 手动设置 LD_LIBRARY_PATH 指向包 lib 目录 |
| 6 | runtest 失败: /tmp 只读 | runtest 使用 TESTDIR="/tmp/avfstest"，OHOS /tmp 只读 (E002) | 功能测试改为使用 $TMPDIR 目录 |

## 源码修改

- `config.guess`: 添加 `__OHOS__` 宏检测分支，返回 `aarch64-unknown-linux-ohos`
- `config.sub`: 添加 `ohos-linux` triplet 支持和 `linux-ohos*` kernel-OS case
- `configure`: 将 `mktemp -d "./confXXXXXX"` 替换为 `${TMPDIR:-/tmp}/avfs-conf-$$` + `mkdir -p`

## 依赖版本

- 无外部 Conan 依赖 (zlib 和 bzip2 为内嵌版本)
- 系统库: pthread, dl

## 验证结果

```
conan-verify: G1 PASS, G0 PASS, G2 PASS, G3 PASS, G4/L2/L4/L5 PASS
make check: exit code 0 (avfs 无正式测试套件)
功能测试: PASS (库链接、virt_stat、virt_open/virt_read 均通过)
```

## 交付物

| 文件 | 说明 |
|------|------|
| libavfs.a | 静态库 |
| libavfs.so.1.0.0 | 共享库 |
| libavfs.so.1 | 共享库 soname 符号链接 |
| libavfs.so | 共享库开发符号链接 |
| avfs.h | 公共头文件 |
| extfs/ | 扩展文件系统脚本 |

## 注意事项

- OHOS 上必须设置 CC=clang CXX=clang++ (E001)
- HMDFS 上 mktemp 不可用，configure 中的 mktemp 需替换为 TMPDIR 路径 (E125)
- test_package 需要手动设置 LD_LIBRARY_PATH 以解析共享库依赖
- runtest 使用 /tmp 目录，在 OHOS 上只读，功能测试改用 $TMPDIR

---

**编译结束**: 2026-07-02 15:48
**最终状态**: built
