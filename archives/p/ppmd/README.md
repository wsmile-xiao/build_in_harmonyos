# ppmd

ppmd 是 Dmitry Shkarin 的 **PPMd variant I** 文件到文件压缩器（预测部分匹配，
prediction by partial matching），public domain 许可。它对文本类数据有很高的
压缩比与压缩/解压速度，上游为嵌入式场景设计，也提供完整的命令行入口。

本包源码是 Debian 打补丁、FreeBSD ports 重打包的 `ppmd-20050811.tar.gz`
（原始包为 compression.ru 系的 `ppmdi1.rar`），与 FreeBSD ports distinfo
逐字核对 SHA256。

## 功能

- `ppmd e <文件...>` 编码为 `.pmd` 档案，`ppmd d <档案>` 解码还原。
- `-oN` 模型阶数（2–16，默认 4）：阶数越高压缩比越好、内存与 CPU 消耗越大。
- `-mN` 子分配器内存（1–256 MB，默认 10）。
- `-r0/-r1/-r2` 内存不足时的模型恢复策略：重启 / 截断 / 冻结。
- `-fName` 自定义档案名，`-d` 处理后删除源文件，`-s` 静默，`*.txt` 通配符批量。
- 档案头保持 canonical ppmdi1 16 字节布局（magic `84ACAF8F` 小端 + 原始文件名）。

## HarmonyOS 适配

- 上游 port 标注 `ONLY_FOR_ARCHS=i386`，代码带有两处系统性 32 位假设，
  在 aarch64/LP64 上表现为**编码即段错误**与**解码首字节即失步**：
  - 子分配器粒度 `UNIT_SIZE=12` 假设 i386 的 4+4+4 结构布局，LP64 下上下文
    结构（20 字节）与空闲块头（24 字节）溢出单元边界 → 补丁 0002 按
    `__LP64__` 把粒度提到 24 字节，并保持「每单元 2 个 packed STATE」的寻址
    不变量。
  - carryless 区间编码器的 `low/code/range` 依赖 32 位回绕丢弃进位，LP64 下
    `range` 初值变成 2^64-1，首个符号即编解码失步 → 补丁 0003 把编码器状态
    钉死 `unsigned int`。
- 补丁 0001 修复 C++11 对 `"... "__DATE__` 的用户自定义字面量词法（新 clang
  上的确定性编译错误）。
- 补丁 0004 把档案头 `signature/attrib` 钉死 32 位，保持 canonical 16 字节
  ppmdi1 档案头不随宿主字长变化。
- 补丁 0005 把 FreeBSD pmake 专属 Makefile（`.for` 循环、`:C` 替换）改写为
  普通 GNU make Makefile，编译器与参数由 Conan 配方注入。
- 补丁 0006 让 `ppmd --version / --help / -V / -h`（旗标为唯一参数时）打印
  版本横幅或用法并退出 0，满足平台 smoke 探针契约；其余调用路径（包括无参
  用法错误退出 255）保持上游行为不变。
- 上游无测试设施（无 check 目标、无测试文件），包内 23 项消费者断言覆盖
  版本/用法旗标、退出码契约、文本与二进制通往返、开关矩阵、档案头布局与
  损坏档案优雅拒绝，全部通过。

## 依赖

无外部依赖：只需要 libc/libc++，标准 C/C++ 头文件。

## 参考

- https://packages.debian.org/unstable/utils/ppmd/
- FreeBSD ports archivers/ppmd（distinfo SHA256 交叉核对）
- 原始发布：ftp://ftp.elf.stuba.sk/pub/pc/pack/ppmdi1.rar（PPMd variant I，
  Dmitry Shkarin，public domain）
