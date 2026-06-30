# Chez Scheme 10.3.0 适配笔记

## 编译环境
- 构建系统: 自定义（自举编译系统，非标准autotools）
- 编译日期: 2026-05-21
- 编译器: clang/llvm (aarch64)
- 目标平台: tpb64l (threaded pb 64-bit LE, unknown OS)
- 状态: built

## 编译步骤

1. **源码获取**: 从 GitHub 下载 v10.3.0 tarball（不含子模块）
2. **子模块补全**: 通过 GitHub API 获取 v10.3.0 tree，提取5个子模块的精确 commit SHA，从 codeload.github.com 逐个下载并放置到正确目录
   - zuo → 063f82c381d871f2d8300e857a33c194ea054d35
   - nanopass → f3100cedaf9ed7fb89647a770d855997b32cf17e
   - lz4 → 5ff839680134437dbf4678f3d0c7b371d84f4964
   - zlib → 51b7f2abdade71cd9bb0e7a373ef2610ec6f9daf
   - stex → 5e4f0ca67bac448e19a24c09f12fc16d24cd6b6d
3. **配置**: `./configure --pbarch --disable-curses --disable-x11 --as-is --installprefix=$PREFIX CC=clang CFLAGS="-fPIC -O2" LDFLAGS="-fPIC"`
4. **构建**: `make`（约389秒，包含3轮自举编译 + fixpoint验证）
5. **安装**: 手动安装（因硬链接问题，修改install.zuo用cp替代ln -f）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 子模块目录为空 | GitHub tarball不含子模块 | 通过GitHub API获取tree，从codeload逐个下载精确commit |
| 2 | nanopass v1.9编译失败 | tagged release与v10.3.0不兼容 | 使用精确commit f3100ced |
| 3 | `ln -f`硬链接失败 | HMDFS不支持硬链接 | 修改install.zuo，ln -f改为cp |

## 源码修改

- `makefiles/install.zuo`: 将 `ln -f` 和 `ln -s` 硬链接改为 `cp` 拷贝（1个补丁）

## 依赖版本

- 无外部依赖（自带zlib/lz4/zuo/nanopass/stex子模块）
- 编译器: clang (aarch64)

## 验证结果

```scheme
;; 10项功能测试全部通过
=== T1: 版本 === Chez Scheme Version 10.3.0
=== T2: 算术 === (+ 1 2)=3, (* 6 7)=42, (/ 22 7)=22/7, sqrt(2)=1.4142...
=== T3: 列表 === list/length/reverse/map 均正确
=== T4: 字符串 === string-length/append/->number 均正确
=== T5: 递归 === fact(10)=3628800, fib(10)=55
=== T6: bytevector/utf8 === utf8->string正确输出"Hello!"
=== T7: 文件IO === 读写文件正确
=== T8: 宏 === swap!宏正确交换变量
=== T9: 条件 === cond分类正确
=== T10: compile-file === Scheme源码编译为.so并加载执行正确
```

## 交付物

### 预编译包

| 文件 | 大小 | SHA256 |
|------|------|--------|
| chezscheme-10.3.0-aarch64-tpb64l.tar.gz | 9.3M | 22658fad333fe078888b94b5eadd78db3bce0423ab378a12f707d706040e6698 |

### 包内核心文件

| 文件 | 大小 | 说明 |
|------|------|------|
| bin/scheme | ~914KB | Chez Scheme 主二进制 (ELF aarch64) |
| bin/petite | ~914KB | Petite Scheme（与scheme相同二进制） |
| bin/scheme-script | ~914KB | scheme-script wrapper（与scheme相同） |
| lib/csv10.3.0/tpb64l/scheme | ~914KB | 主二进制 |
| lib/csv10.3.0/tpb64l/scheme.boot | ~929KB | Scheme boot文件 |
| lib/csv10.3.0/tpb64l/petite.boot | ~1.8MB | Petite boot文件 |
| lib/csv10.3.0/tpb64l/scheme-script.boot | ~929KB | scheme-script boot文件 |
| lib/csv10.3.0/examples/ | ~400KB | 示例程序 |
| man1/scheme.1 | ~44KB | man手册 |

## 注意事项

- Chez Scheme为自举编译器，构建采用--pbarch（portable bytecode petit bootstrap）方式
- tunknown平台标记意味着无平台特定汇编优化，仅bytecode解释器模式
- Fixpoint验证通过（"unchanged after rebuild"），表明自举结果稳定
- GitHub连接不稳定，子模块需提前准备或通过API+codeload逐步下载
- 不支持硬链接的文件系统需修改install.zuo

---

**编译结束**: 2026-05-21 21:54
**最终状态**: built