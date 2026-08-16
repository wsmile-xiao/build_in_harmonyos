# palp 2.21 编译笔记（HarmonyOS PC · 手写 GNU Makefile）

## 定位
- 产 25 个命令行程序（`{poly,class,cws,nef,mori}` × `{默认,4d,5d,6d,11d}`），**无库无头**。
- 直接消费方：`passagemath-palp` 的 wheel —— 它把 `bin/{class,cws,mori,nef,poly}*.x`
  整组塞进 wheel 的 `sage_wheels/bin/`，少一个即少一项功能。

## 关键适配
- **按维度分别编译不可省**：`POLY_Dmax` 是编译期常量，同一份 `.o` 不能跨维度复用。
  上游 GNUmakefile 的 `all-dims` 目标已展开这套矩阵，不必照 sage 的 spkg-install
  自己 sed `Global.h` 循环 5 遍。
- **CFLAGS 不得含 `-DNDEBUG`**：PALP 在 `assert()` 里写了有副作用的表达式，
  NDEBUG 会把整条预处理掉，程序语义随之改变（上游 spkg-install.in 专门 sed 掉它）。
- **需要 GNU make ≥ 3.82**：`define VAR =` 是该版本起的语法，老 make 会报
  "No rule to make target 'poly-d.x'"，措辞完全看不出真因。build() 里先打印 make 版本。
- **`package()` 逐个核对 25 个可执行文件**：`copy(*.x)` 少拷了不会报错，
  硬核对才能把"构建静默退化"变成当场失败。
- 产可执行文件的包必须签 bin 下的 ELF（XPM），否则设备上 exec 报 Permission denied。

## 状态
built —— 2026-08-16 在 HUAWEI MateBook（OHOS aarch64）真机验证通过。

真机 `conan create -pr ohos-native` 通过；test_package 用上游 tests/2.1 的例子跑 poly.x 与 poly-11d.x，输出均为 `M:6 3 F:3`。
