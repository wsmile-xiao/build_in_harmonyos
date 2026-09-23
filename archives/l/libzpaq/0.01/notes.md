# libzpaq 0.01 适配笔记

## 编译环境
- 构建系统: none（上游无构建系统——手动单文件编译，binn/cssc 式源清单）
- 编译日期: 2026-09-15
- 编译器: clang/clang++ 15 (aarch64-linux-ohos)
- 状态: built

## 上游形态

zpaq 0.01（2009-02-15，Matt Mahoney，Ocarina Networks）是 ZPAQ 开放压缩
标准的 level 0 实验性参考实现。发布物极小：

- `zpaq.cpp`（58KB，单文件自包含 C++，仅依赖 C 标准库头
  stdio/stdlib/string/ctype/time/math/assert）
- `min.cfg` / `max.cfg`（压缩模型配置——压缩时必需的数据文件）
- `readme.txt`
- 无任何构建系统（无 Makefile/configure/CMakeLists），readme 记载的
  构建命令即 `g++ -O3 -s -DNDEBUG zpaq.cpp -o zpaq`

注意：libzpaq 0.01 是 zpaq 生态在 zpaq/zpaq 仓库 tag 0.01 的库形态
（上游不存在独立的 zpaq/libzpaq 仓库——git ls-remote 验证过认证失败/
不存在），按任务指定从 zpaq/zpaq tag 0.01 打包，包名 libzpaq。

## 编译步骤

```bash
# 等价于上游 readme 的 g++ -O3 -s -DNDEBUG zpaq.cpp -o zpaq
clang++ -O2 -DNDEBUG -static-libstdc++ zpaq.cpp -o zpaq
```

- `-O2 -DNDEBUG`：对齐上游 release 构建（关闭 assert）
- `-static-libstdc++`：静态链接 libc++。原因：SDK sysroot 的
  libc++_shared.so 是链接器脚本 INPUT(-lc++_shared)，运行期 musl 加载器
  无法解析；动态链接的二进制在设备上直接报
  `Error loading shared library libc++_shared.so`。烘焙静态 libc++ 后
  二进制仅依赖 libc.so，任何 OHOS 环境可运行（boost1.84-* 测试可执行
  文件同款处理）。设备实测验证过。
- 零补丁：源码纯 ISO C++ 标准库，无平台敏感 API（无 syscall/dirent/
  stat/mkdir），对 OHOS 完全可移植。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 动态链接的 zpaq 运行报 `Error loading shared library libc++_shared.so` | SDK 的 libc++_shared.so 是链接器脚本，musl 加载器不认 | 加 `-static-libstdc++` 烘焙 libc++ |
| 2 | zpaq x 解压时报 `No such file or directory` | 上游设计：zpaq 不自动创建目录（readme 明示） | 测试脚本先 mkdir 再解压 |

## 验证结果（设备 aarch64 OHOS 本机实测）

```bash
# 1) 压缩（min.cfg 模型）
$ ./zpaq cmin.cfg test.zpaq src/readme.txt src/min.cfg src/max.cfg
rtest2/src/readme.txt 5964 -> 3297
rtest2/src/min.cfg 191 -> 139
rtest2/src/max.cfg 1023 -> 543

# 2) 列表
$ ./zpaq l test.zpaq
Block 1: requires 4.195 MB memory
  rtest2/src/readme.txt  5964 -> 3297
  ...

# 3) 解压 + 字节级比对
$ zpaq x test.zpaq   # 3 file(s) extracted
$ cmp 逐文件比对 → 全部一致（ROUNDTRIP OK）

# 4) test.sh 完整往返（随机二进制/数字序列/文本 3 类文件）
   → ALL TESTS PASSED（压缩/列表/解压/字节级 cmp）
```

## 依赖版本

零依赖（纯 C++ 标准库，conanfile requirements 为空）。

## 注意事项

- 上游无测试套件：tag 0.01 tarball 仅 5 个文件，无 tests/、无构建
  系统、readme 无任何测试说明——测试由 test_package 补全（3 类文件
  压缩→列表→解压→字节级 cmp 往返）。
- `zpaq --version` 非标准选项：usage() 输出帮助后 exit(0)，L2 冒烟
  可通过（实测 exit=0）。
- min.cfg/max.cfg 安装到 share/libzpaq/（压缩操作必需的模型配置）。
---

**编译结束**: 2026-09-15 03:16
**最终状态**: built
