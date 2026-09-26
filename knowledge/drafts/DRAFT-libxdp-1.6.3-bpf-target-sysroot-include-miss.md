# DRAFT-libxdp-1.6.3-bpf-target-sysroot-include-miss

**一类问题**：交叉/真机构建中，用 `clang -target bpf` 编译 eBPF 程序时，BPF 编译**不继承**
编译器驱动自身的默认 include/sysroot 搜索列表，导致 BPF 对象缺 `<linux/types.h>` 之类内核 uapi 头而失败；
宿主 x86_64 上常被宿主 `/usr/include` 掩盖，只有 crossover/真机才暴露。

## 使用说明（怎么判定 + 怎么修）

1. **判定**：报错出现在 `BPF_CFLAGS` 的编译（`clang -target bpf ... -c`）里，典型为
   `<...>/linux/bpf.h:NN: fatal error: 'linux/types.h' file not found`；而同一项目**宿主对象**（`cc -c`）编译正常。
2. **取证**：对比编译器自身搜索列表与构建脚本注入的 include：
   ```sh
   cc -E -Wp,-v -xc - 2>&1 | sed -n '/search starts here/,/End of search list/p'
   # 会列出 <sysroot>/usr/include 与 <sysroot>/usr/include/<arch>
   ```
   若构建脚本的 `ARCH_INCLUDES`/BPF flags 里**只有 arch 子目录**，即命中本类。
3. **修复**：在构建期解析上面的搜索列表，把所有真实存在的绝对目录以 `-I` 注入 BPF 编译参数：
   ```sh
   ARCH_INCLUDES="$(cc -E -Wp,-v -xc - 2>&1 \
     | awk '/search starts here/{f=1;next} /End of search list/{f=0} f && /^\//{printf "-I%s ",$1}')"
   make BPF_CFLAGS="$BPF_CFLAGS $ARCH_INCLUDES"
   ```
   （libxdp 配方在 `generate()` 期做等价注入，见 `conanfile.py::_default_includes`。）

## 适用范围

- 一切在 OHOS 上用 `clang -target bpf` 编 eBPF 程序的项目：xdp-tools/libxdp、bpftool、libbpf-bootstrap、bcc 等；
- 一切把“arch 子目录”当成 sysroot 全量、并且用自定义 configure/Makefile 组装 BPF flags 的构建；
- **不适用**：用 CMake/autotools 且其 toolchain 已把完整 sysroot include 传给 BPF 编译的场景。

## 输入输出定义

| | |
|---|---|
| 输入 | 编译器可执行文件路径 `CC`（其默认 target 的 sysroot 完整）；构建系统暴露的 BPF include/flag 变量（如 `ARCH_INCLUDES`/`BPF_CFLAGS`） |
| 输出 | 追加了完整默认 include 目录的 `-I` 列表；`clang -target bpf` 能解析 `<linux/types.h>` 与 `<asm/types.h>` |
| 成功判据 | BPF 对象（`.o`）编译退出码 0，且 `llvm-readelf -h` 显示 `EM_BPF`（`Machine: Linux BPF`） |

## 示例

libxdp 1.6.3（xdp-tools）在鸿蒙电脑原生构建：

- 失败：`CLANG xdp-dispatcher.o` → `../../headers/linux/bpf.h:11:10: fatal error: 'linux/types.h' file not found`
- 修复后：`xdp-dispatcher.o`、`xsk_def_xdp_prog.o`、`xsk_def_xdp_prog_5.3.o` 全部生成并嵌入 `libxdp.a`/`libxdp.so`。

## 查重差异表（与最相近的既有条目逐条比）

| 维度 | E334（fastnetmon 抓包后端门控） | 本条 |
|---|---|---|
| 问题轴 | **功能取舍**：首轮打包时关掉 AF_PACKET/AF_XDP/libpcap 后端 | **构建参数**：BPF 交叉编译缺 sysroot include 目录 |
| 触发点 | CMake 选项 `ENABLE_AF_XDP_SUPPORT=OFF` 等 | `clang -target bpf` 的 `-I` 搜索列表 |
| 解法 | 关闭依赖/后端 + 文档说明 | 注入编译器默认 include 列表 |
| 是否后者可被前者覆盖 | 否（即使开启 BPF 后端也会撞上本条） | — |

- `_TOOLS_LINUX_COMPILER_H_`/`compiler_types`/`target bpf` 词边界在 `knowledge/{graph,drafts,doc}` 均 **0 命中**（本次实测），无精确重复。

## 验证证据

```
# 真机（ohos-aarch64 原生）修复前
In file included from xdp-dispatcher.c:3:
../../headers/linux/bpf.h:11:10: fatal error: 'linux/types.h' file not found
1 error generated.
make[2]: *** [Makefile:141: xdp-dispatcher.o] Error 1

# 修复后（同真机）
CLANG xdp-dispatcher.o
CLANG xsk_def_xdp_prog.o
CLANG xsk_def_xdp_prog_5.3.o
LINK  libxdp.a
LINK  libxdp.so.1.6.0        # 退出码 0
```

- 日志：`/mnt/e/dsh working/tasks/libxdp-1.6.3-2026-09-21/logs/025e-conan-create-cross.log`（WSL 交叉 EXIT=0）、
  `logs/070-laptop-native-build-test-pass.png`（鸿蒙电脑原生 1/1 通过）。
- 配方：`archives/l/libxdp/1.6.3/conanfile.py`（`_default_includes`）。

## 平台侧修法建议（若有）

构建系统若直接给出“目标 sysroot 根”，应默认把 `<sysroot>/usr/include` 一并传给 BPF 目标编译；
当前 OHOS SDK 的 `clang -target bpf` 行为与 `-target aarch64-linux-ohos` 不一致，建议文档化。
