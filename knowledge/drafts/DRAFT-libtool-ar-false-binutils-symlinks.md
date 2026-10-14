# DRAFT: libtool 链接行出现 `false cr`——configure 的 AR 探测回退值，纯 llvm 工具链设备需补 binutils 名称符号链接

> 配套条目：`DRAFT-libtool-ar-false-binutils-symlinks.kv`（本 md 与 kv 成对）
> 状态：pending-editor-review（拟提升编号 E7xx，最终由主编确认）
> 首发实现：fftw3f 3.3.10 真机预构建（补 ar/ranlib/nm/strip/objdump → llvm-* 符号链接后通过）
> 同场景先例：ld 符号链接（configure "no acceptable ld found"）——同一设备环境问题族

## 1. 错误特征（可机器匹配）

```
libtool: link: false cr .libs/libkernel.a .libs/align.o ...
make[2]: *** [Makefile:418: libkernel.la] Error 1
```

- error_signature：`libtool: link: false cr |libtool: link: false .*\.a`
- **识别要点**：编译全部通过、挂在第一个 libtool 归档链接；链接命令的第一个词是字面量 `false`。

## 2. 根因

autoconf 的 `AC_CHECK_TOOL([AR], [ar], [false])` 找不到 `ar` 时以 `false` 作为回退值（让后续步骤"显式失败"）。真机工具链只带 llvm 前缀二进制（llvm-ar/llvm-ranlib/llvm-nm/llvm-strip/llvm-objdump），无裸名 binutils。configure 探测发生在 conan 注入环境之前或探测路径不含符号链接时即命中回退。同一问题族：`ld` 缺失时 configure 报 "no acceptable ld found in $PATH"。

## 3. 修法（设备环境侧一次性修复，不是配方问题）

```bash
B=/storage/Users/currentUser/usr/local/bin
for t in ar ranlib nm strip objdump ld; do ln -sf $B/llvm-$t $B/$t; done
# ld 若无 llvm-ld 则链到 ld.lld
```

修复后无需改配方，重跑 conan create 即过。CI worker 环境（/data/service/hnp/bin）自带裸名工具，不受影响——本条目主要服务真机预构建场景。

## 4. 佐证

fftw3f 3.3.10：首轮 `libtool: link: false cr` 红灯；补五连符号链接后 conan create 全链路 exit 0，消费探针（1D DFT 往返）真机 PASS（worst |err|=1.19e-07，float 精度极限）。

## 5. 适用范围

所有在纯 llvm 工具链环境做 autotools 真机预构建的场景（libtool 归档链接、configure 工具探测）。排查口诀：链接行首词是 `false` = 工具探测回退，补符号链接而非改配方。
