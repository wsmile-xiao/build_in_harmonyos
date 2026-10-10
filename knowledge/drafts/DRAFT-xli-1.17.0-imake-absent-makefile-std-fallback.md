# xli 1.17.0:Imake 遗产 X11 库在 OHOS 无 imake/xmkmf 下的适配——优先走自带的 Makefile.std

> 草稿(DRAFT)— 来自 xli 1.17.0-20061110 HarmonyOS PC (aarch64) 适配的真实实践。
> 与 `.kv` 同 stem 配对。

## 问题

xli 是 1990s-2000s 的 X11 图像查看/转换工具，构建系统是 **Imake**：

```
$ ls
Imakefile  Makefile.std  Makefile.noimake  ddxli.h  window.c  xli.c ... 
$ make
make: *** No targets specified and no makefile found.  Stop.
```

`Makefile` 由 `xmkmf`（imake 前端）现场生成；而 OHOS SDK native 工具链
（clang/llvm）**不含 imake/xmkmf**，实测：

```
$ command -v imake xmkmf
(空)
```

上游本身也已停更：xli 官网 2006 年后下线（HTTP 404），只能取发行快照 tarball
（本样例取 openSUSE fork 保存的 2006-11-10 原始发行快照，
sha256 固定于 `conandata.yml`）。

## 关键事实与最小解

发行快照**自带非 Imake 的构建路径** `Makefile.std`（BSD/SYSV 直编，不依赖 imake
生成任何东西）。最小解两步：

1. **构建入口换成 `Makefile.std`**，把 Imake 的 `INCLUDES`/`LIBS` 自动解析替换为
   **Conan 依赖注入**——展开 `self.dependencies[*].cpp_info`
   （includedirs / libdirs / libs）拼出 `-I` / `-L` / `-l`：

```python
def _dependency_flags(self):
    inc, lib, names = [], [], []
    for dep in self.dependencies.values():
        for d in dep.cpp_info.aggregated_components().includedirs:
            short = self._relocatable(d)
            if short: inc.append("-I" + short)
        ...
```

2. **补齐 musl 缺口**（见配对条目
   `DRAFT-xli-1.17.0-ohos-musl-missing-rindex-bsd-legacy`）：编译期注入
   `-Drindex=strrchr`，**不要**启用上游 `-DSYSV`。

验证：`conan create archives/x/xli/1.17.0-20061110` 全绿（G0-G4 + L2/L4/L5，
含 `test_package/` 消费者用例：`xlito` 往返转换 + `xli` 启动）。

## 为什么不用 imake 工具链

- OHOS SDK 无 imake/xmkmf，制品仓也无对应 `tool_requires`；
- 即使存在，Imakefile 的生成语义要求完整 X11 宿主环境（Imake.rules 体系），
  在 CI 干净环境里不可复现；
- 源码已自带直编路径，**0 补丁**即可完成构建——最小侵入。

## 同族范围与边界

适用于 1990s-2000s 的 X11 系包（源码树含 `Imakefile`、无现代构建系统），
尤其是发行 tarball 自带 `Makefile.std` / `Makefile.noimake` / `Buildfile` 者；
无回退构建文件时需按 Imakefile 语义手工重建最小 Makefile（次选，逐包成立）。
检测脚本 + 复现脚本 + 完整文档见 `knowledge/drafts/imake-legacy-x11/`。

## 覆盖判断

- 不复用 `-Werror` 类条目（`knowledge/drafts/werror-autotools/`）：那是告警升级问题，
  本条是**构建系统缺失**问题，二者可同时命中同一包。
- 不复用 musl syscall 缺口条目（E051/P008）：那是运行时不可用接口，本条是构建入口缺失。
