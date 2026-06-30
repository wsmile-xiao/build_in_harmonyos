# icoutils 0.32.3 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-05-27
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. configure：`CFLAGS="-fPIC -O2" CPPFLAGS="-I$DEFAULT_PREFIX/include" LDFLAGS="-L$DEFAULT_PREFIX/lib" ./configure --prefix=$DEFAULT_PREFIX`
2. 编译：`make -j2`
3. 安装staging：`make install DESTDIR=$TEST_PREFIX`
4. 安装本地：`make install`
5. 打包：`ohc-run.py package icoutils 0.32.3`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure报"cannot find required library png" | libpng16已安装但缺少libpng.so符号链接和PKG_CONFIG_PATH | 创建libpng.so→libpng16.so符号链接，设置PKG_CONFIG_PATH |
| 2 | 首次configure报"C compiler cannot create executables" | -Wuse-after-free=3不被clang15支持 | 用CFLAGS="-fPIC -O2"简化CFLAGS，避免触发有问题的警告标志测试 |
| 3 | "error: write on a pipe with no reader" | HMDFS pipe限制 | 非致命，不影响编译结果 |

## 源码修改

无源码修改，无需补丁。

## 依赖版本

- libpng: 1.6（已安装预编译包）

## 验证结果

```bash
icotool (icoutils) 0.32.3
wrestool (icoutils) 0.32.3
extresso / genresscript: 已安装
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| icoutils-0.32.3-ohos-aarch64.tar.gz | 870KB | 预编译包（含4个可执行文件） |
| icoutils-0.32.3-ohos-aarch64-debug.tar.gz | 225KB | 调试符号包 |

---

**编译结束**: 2026-05-27 18:37
**最终状态**: built