# advancecomp 2.6 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-05-21
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 解压源码：`tar xf advancecomp-2.6.tar.gz`
2. 应用补丁：
   - 0001-config.guess.patch - 添加 HarmonyOS 平台检测
   - 0002-config.sub.patch - 更新 config.sub 支持 HarmonyOS
   - 0003-configure.patch - 修复 umask 077 → umask 022
3. Configure：`CXX=clang++ ./configure --prefix=/storage/Users/currentUser/usr/local`
4. Build：`make -j$(nproc)`
5. Test：`make check` - 全部通过
6. Install：`make install DESTDIR=/storage/Users/currentUser/test-install-advancecomp-2.6`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure umask 077 | 临时目录权限过严 | 修改 configure 第 6971、6976 行：umask 022 |
| 2 | config.guess 无法识别 HarmonyOS | heredoc 权限限制 | 修改 config.guess 第 170-178 行，添加 HarmonyOS 分支 exit |

## 源码修改

### config.guess (0001)
修改 HarmonyOS 检测分支，添加正确的架构映射和 exit：
```bash
*:HarmonyOS:*:*)
    case "$UNAME_MACHINE" in
        aarch64|arm64) MACHINE=aarch64 ;;
        armv7*|armv8*) MACHINE=arm ;;
        x86_64|amd64)  MACHINE=x86_64 ;;
        i?86)         MACHINE=i686 ;;
        *)            MACHINE="$UNAME_MACHINE" ;;
    esac
    GUESS=${MACHINE}-unknown-linux-ohos
    ;;
```

### config.sub (0002)
添加 HarmonyOS 目标支持：
- aarch64-unknown-linux-ohos
- arm-unknown-linux-ohos
- x86_64-unknown-linux-ohos
- i686-unknown-linux-ohos

### configure (0003)
修复 umask 设置：
- 第 6971 行：umask 077 → umask 022
- 第 6976 行：umask 077 → umask 022

## 依赖版本

- clang/clang++ (HarmonyOS 默认编译器)
- zlib (系统库)
- libdeflate (内嵌)
- zopfli (内嵌)
- 7z SDK (内嵌)

## 验证结果

```bash
$ ./config.guess
aarch64-unknown-linux-ohos

$ make check
PASS: advzip
PASS: advpng
PASS: advmng
PASS: advdef
Success!

$ ls -la ~/usr/local/bin/
advdef    1.1M
advmng    1.2M
advpng    1.1M
advzip    1.0M
```

## G0 干净构建验证

```
verified_at: 2026-05-21T15:53:30
tarball: advancecomp-2.6.tar.gz
patches: 3
状态: PASS
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| advdef | 1.1M | PNG/MNG/ZIP 重新压缩工具 |
| advmng | 1.2M | MNG 动画优化工具 |
| advpng | 1.1M | PNG 优化工具 |
| advzip | 1.0M | ZIP 优化工具 |

## 注意事项

1. HarmonyOS 环境下 heredoc 权限受限，config.guess 需要特殊处理
2. 必须使用 CXX=clang++，默认 CC=g++ 会链接失败
3. TMPDIR 需要设置为用户可写目录

---
**编译结束**: 2026-05-21 15:52
**最终状态**: built
**G0验证**: PASS