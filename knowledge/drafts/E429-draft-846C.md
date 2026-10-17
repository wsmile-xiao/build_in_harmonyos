# E429 — BSD make 项目在 OHOS(GNU make) 下的构建适配

> 状态：草稿（待知识库主编审核）｜来源：playumidi 0.8.3 适配（PR 待提交）

## 错误特征

```
$ make
Makefile:40: *** missing separator.  Stop.
```

改写语法后（第一次修复之后）出现的第二形态：

```
make: *** [Makefile:72: playumidi] Error 2
Usage: make [options] [target] ...      <- 递归子 make 打印 GNU make 帮助
```

第三形态（安装阶段）：

```
make: install: No such file or directory
make: *** [Makefile:56: install] Error 127
```

## 触发条件

- 构建系统：上游使用 **BSD make（bmake）** 语法，而目标环境只有 **GNU make**
- 阶段：`make`（configuration/build）、`make install`
- 典型来源：FreeBSD ports 生态、`*-port` 移植包、BSD 系工具（本项目 playumidi 来自 FreeBSD ports）

## 根因分析

三处语义差异，逐层暴露：

1. **条件语法不同**：BSD make 用 `.ifdef/.if/.else/.endif`，GNU make 用 `ifdef/if/else/endif`。
   GNU make 把 `.ifdef WITH_ICONV` 当普通文本行，因缺少 `:` 分隔符而报 `missing separator`。
2. **变量定义选项不同**：BSD make 中 `make -DWITH_ICONV` 是"定义变量"，GNU make 中 `-D` 未定义
   （GNU make 的 `-D` 不存在，实际是未识别选项），递归子 make 一旦收到 `-DWITH_X` 就打印 usage 并失败。
   因此上游 `BUILD_FLAGS += -DWITH_DEBUG` 这种写法在 GNU make 下会破坏递归 make 调用。
3. **`install(1)` 缺失**：上游 install 目标直接调用 coreutils/BSD 的 `install` 程序；OHOS 未提供
   该可执行文件（`Error 127`）。

## 解决方案

### 推荐方案（最小补丁，不引入平台宏）

```make
# 1) 条件语法：.ifdef/.else/.endif  ->  ifdef/else/endif
ifdef WITH_ICONV
BUILD_FLAGS += WITH_ICONV=1          # 2) 宏传递：-DWITH_ICONV -> 命令行变量
MAN_FILE = playumidi_iconv.1
else
MAN_FILE = playumidi.1
endif

# 3) 路径与安装
prefix ?= /usr/local
DESTDIR ?=
INSTALL_BIN_DIR = $(DESTDIR)$(prefix)/bin
INSTALL_MAN_DIR = $(DESTDIR)$(prefix)/share/man/man1

install:
	mkdir -p $(INSTALL_BIN_DIR) $(INSTALL_MAN_DIR)
	cp -f $(TARGET) $(INSTALL_BIN_DIR)/$(TARGET)
	chmod 755 $(INSTALL_BIN_DIR)/$(TARGET)
```

要点：
- 命令行变量（`make WITH_DEBUG=1`）会经 `MAKEFLAGS` **自动传给递归子 make**，等价于 BSD make 的 `-DWITH_X` 语义。
- 补丁保持通用性（GNU make 在 FreeBSD 上同样可用），**无需 `__OHOS__` 宏**（符合 R8）。
- `install` → `mkdir/cp/chmod` 是通用 POSIX 写法，不依赖 coreutils `install`。

### 禁止做法

- ❌ 仅把 `.ifdef` 注释掉/删掉：`WITH_*` 宏会丢失，多配置构建静默退化。
- ❌ 用 `-DWITH_X` 继续传递：递归 make 报错（见上）。
- ❌ 引入 `-D__OHOS__` 分支书写 Makefile：不必要（本问题是 make 方言差异，不是平台差异），且违反 R8 补丁策略。
- ❌ 绕过上游构建系统直接手写编译命令：丢掉上游 man/install 语义与可复现性。

## 验证

```bash
grep -nE '^\.(if|ifdef|else|endif)' Makefile src/Makefile   # 先确认是 BSD make 项目
make CC=clang -j1                                          # 应正常构建
make install DESTDIR=$PWD/_stage prefix=/usr/local          # 应产出 _stage/usr/local/bin/<tool>
```

## 实证（真实执行）

playumidi 0.8.3（FreeBSD ports `audio/playumidi`）适配：
- 首个错误 `Makefile:40: *** missing separator. Stop.`（E002 无关，纯 make 方言）
- 修复后 `make CC=clang -j1` → rc=0，产物 `playumidi`(ELF aarch64/musl) + `playumidi.1.gz`
- 上游测试入口 12 用例全通过（含 `-DWITH_VERIFY` 自校验 3/3）

## 关联条目

- 相关：install(1) 缺失 → OHOS 基础工具集裁剪类条目
- 相关：R8 补丁不得引入平台宏；R1 参数最少化
