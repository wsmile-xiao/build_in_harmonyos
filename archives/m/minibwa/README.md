# minibwa

lh3 的轻量级 BWA 短序列比对工具。

## 版本列表

- `0.4`：本分支 OHOS PC aarch64 适配（v0.4，版本串 `0.4-r400`）。application
  包：只产出 `minibwa` 可执行文件。mimalloc 禁用（知识 E210），串行 make
  （知识 E074），上游 api-test + chrM index/map 在 build() 内验证。
- `0.7`：upstream 正式适配（v0.7，r421）。同时提供静态库 `libminibwa.a` 与
  公共头 `minibwa.h`，含 `--meth` 甲基化模式与 `fa2bit`/`genraw`/`genbwt`
  子命令。

## 简介（0.4）

minibwa 是一个面向短读段比对的轻量级 BWA 重实现（v0.4，版本串
`0.4-r400`），保留 BWA-MEM 风格的映射算法核心，代码量远小于完整 BWA。
主要命令：
- `index`：构建参考索引
- `map`：短读段比对（支持 paired-end）
- `version`：输出版本串（无 `--version` 选项）

包类型为 application：只产出 `minibwa` 可执行文件；`libminibwa.a` 为构建
中间产物，不随包发布。需要 C API 的消费者参考上游 `api-test/` 示例
（`mb_idx_load`/`mb_map`，由配方在 build() 内编译验证）。

## 技术信息（0.4）

- **许可证**：主体 MIT；`bwtgen.c` GPL-2.0-or-later、`QSufSort.c` 自定义
  许可（配方标注 `MIT AND GPL-2.0-or-later`；`gpl=0` 可关但会砍掉
  `genraw` 命令与低内存索引路径，故保持默认 `gpl=1`）
- **编程语言**：C
- **构建系统**：Makefile（纯 Makefile，无 configure、无 install 目标）
- **依赖**：zlib/1.3.1（gzip 输入）、pthread、m；OpenMP 运行时由 OHOS
  clang 工具链自带
- **补丁**：无（仅命令行变量驱动构建，源码零改动）

## 构建配置（0.4）

在 OHOS aarch64 上通过 Conan 配方构建（raw Makefile：INCLUDES/LDFLAGS
注入 zlib 路径，CPPFLAGS/LIBS 被上游 Makefile 语义锁定不可覆盖）：

```
conan create . --build=missing \
  -pr:h ci/conan/profiles/ohos-aarch64 \
  -pr:b ci/conan/profiles/ohos-aarch64
```

要点：
- `mimalloc=0` 必须使用：mimalloc 的 malloc override 在 OHOS 上启动即
  SIGSEGV（知识 E210）；`mimalloc=0` 是上游官方开关，回退 kalloc 分配器
- 串行 make（`make -j1`）：HMDFS 工作区无法承载 GNU make jobserver FIFO
  （知识 E074）
- 配方对 `tools.build:compiler_executables` 做存在性校验：conf 路径在本机
  不存在时回退从 PATH 解析 clang/llvm-ar/llvm-ranlib（保持 CI 语义）
- 上游测试（`make -C api-test` + chrM 数据 index/map/api-test 断言）在
  build() 内执行；test_package 另做消费者级端到端冒烟

## 简介（0.7）

minibwa 是一个面向短读段比对的轻量级 BWA 重实现（v0.7, r421），保留
BWA-MEM 风格的映射算法核心，代码量远小于完整 BWA。主要命令：
- `index`：构建参考索引（默认 libsais + QSufSort/bwtgen 组件）
- `map`：短读段比对（支持 paired-end、甲基化 `--meth` 模式）
- `fa2bit`/`genraw`/`genbwt`：索引内部构建流程的子命令

同时提供静态库 `libminibwa.a` 与公共头 `minibwa.h`，C API 与上游
api-test 示例（`mb_idx_load`/`mb_map`/`mb_opt_init`）配合使用。

## 技术信息（0.7）

- **许可证**：MIT（含可选 GPL 组件 QSufSort/bwtgen，默认启用，`gpl=0` 可关）
- **编程语言**：C99
- **构建系统**：Makefile（纯 Makefile，无 configure）
- **依赖**：zlib/1.3.1.1（gzip 输入）、pthread、m
- **SIMD 支持**：aarch64 由 ksw2 内置 s2n-lite.h NEON 翻译层原生支持

## 构建配置（0.7）

在 aarch64/OHOS 平台上应使用以下参数构建：
```
make -j1 ARCH=aarch64 CC=clang AR=llvm-ar \
     INCLUDES="-I<zlib>/include" LDFLAGS="-L<zlib>/lib" \
     gpl=1 mimalloc=0
```

要点：
- `ARCH=aarch64` 显式传递（Makefile 默认取 `uname -m`，交叉场景不可靠）
- `mimalloc=0` 必须使用：mimalloc 的 malloc override 在 OHOS emulated
  TLS bootstrap 阶段于 `__emutls_get_address` 递归栈溢出（知识 E210）；
  `mimalloc=0` 是上游官方开关，回退 kalloc 分配器
- 串行 make：HMDFS 工作区无法承载 GNU make jobserver FIFO（知识 E074）

## 已知限制（0.4）

- 无 `--version` 选项（exit 1）；版本查询用 `minibwa version` 子命令
  （exit 0，输出 `0.4-r400`）
- 无参数调用 exit 0（打印 usage）；未知子命令 exit 1
