# DRAFT-irsim-9.7.104-ohos-nographics-null-srcs

> 对应 .kv: DRAFT-irsim-9.7.104-ohos-nographics-null-srcs.kv
> 状态: draft（待主编审核）

## 错误特征

```
thread.c:9:10: fatal error: 'X11/Xlib.h' file not found
ld.lld: error: undefined symbol: EnableInput
>>> referenced by rsim.c:513 ... ../base/libbase.o:(input)
ld.lld: error: undefined symbol: OffsetNode
>>> referenced by rsim.c:0 ... ../base/libbase.o:(analyzer)
```

## 根因

autotools 图形软件（irsim 及同作者 magic 系）的 configure 依据
`usingTcl`/`usingX11` 选择图形后端源码列表（`TK_SRCS`/`X11_SRCS`），但
"非 Tcl 且非 X11" 分支**未回退 `NULL_SRCS`**（无图形桩），导致 `gr_srcs`
残留依赖 X11 头文件的 `thread.c`（编译期 `X11/Xlib.h not found`）；
且 `noana.c`（`NULL_SRCS` 桩）缺 `EnableInput`/`DisableInput`/
`OffsetNode`/`OffsetVector` 四个符号，基础模块（base/rsim.c）仍引用，
链接报 undefined symbol。HarmonyOS PC 无 X11/Tcl 环境，必然命中此路径。

## 方案

1. configure（及 configure.in）在非 Tcl 非 X11 分支补
   `gr_srcs="${NULL_SRCS}"`、`gr_libs=""`（消除 thread.c 编译失败）
2. noana.c 补全 `OffsetNode`/`OffsetVector`/`EnableInput`/`DisableInput`，
   语义与上游 analyzer.c 一致（no-op return 1 / 空体）
3. 若保留图形路径，可提供最小 X11 头桩——不推荐，与 R8/R40 冲突

## 验证

- 修复前 `make -j1`：analyzer/thread.c 编译失败 + 链接 undefined symbol
- 修复后 configure/make 全绿，`irsim <prm> <sim>` 真实仿真 exit 0
- conan create 干净构建 + L0-L5 + test_ohos 12/12 通过

## 适用边界

- irsim 及同作者 magic 系工具（magic/netgen 等，"图形可选"的 autotools C 软件）
- 无 X11/Tcl 的 OHOS PC 环境必然触发；有限 X 环境走 X11_SRCS 不受影响
- 反例：真实需要图形界面的库不应回退 NULL_SRCS（会失去图形能力），
  应适配 X11/Tcl 依赖而非禁用

## 查重差异

- 引擎查询 "analyzer noana NULL_SRCS no graphics" 命中 E463（GTK/Broadway
  无显示环境消费者探针）——对象是 GTK 系 Meson 工程，irsim 是 magic 系
  autotools C 工程，根因/方案/适用边界不同，仅"无图形环境"背景重叠
- E007（config.guess HarmonyOS 补丁）：前置平台层，本条目是其后
  图形源码列表层，caused_by 关系

## 来源

- 触发事件: irsim/9.7.104 适配 HarmonyOS PC 编译记录（2026-09-16）