# RetroArch

> libretro API 的官方参考前端（模拟器 / 游戏前端），支持大量 libretro 核心、着色器、
> 回放（runahead）、存档状态与 RetroAchievements。

## 简介

RetroArch 是 libretro API 的参考实现，本身是一个前端：它加载各平台/主机的
libretro「核心」（core，.so 动态库）来运行内容。项目规模庞大——约 1763 个
`.c`/`.cpp` 翻译单元，自带 `libretro-common` 运行时与一批内置第三方依赖
（zlib、libFLAC、libchdr/lzma、7zip、rcheevos、glslang/SPIRV、switchres 等），
使用自研的 quickbuild（`configure` + `Makefile` + `qb/*.sh`）构建系统。

## OHOS 适配要点

- **平台识别**：quickbuild 以 `uname -s` 判平台，OHOS 返回 `HarmonyOS`，原本落到
  Win32 分支并因缺 `windres` 中止；补丁并入 Linux（musl/bionic 用户态）分支。
- **bionic 缺 pthread 取消**：可选 IIO 光照传感器线程与内置 glslang 清理路径用
  `HAVE_PTHREAD_CANCEL` / 既有 `__ANDROID__` 分支守卫。
- **单字符十六进制解析**：回移上游 1.22.2 之后的 `string_hex_to_unsigned` 修复。
- **上游单测修复**：`libretro-common/test/` 的 libcheck 套件上游从未构建、已腐化，
  按上游后续修复方式修好，并把临时文件改走 `TEMP`/`TMPDIR`（OHOS 无可写 `/tmp`）。
- **无头最小 profile**：关闭全部桌面/GPU/音频/网络后端，构建可运行的无头前端。

## 依赖

| 依赖 | 版本 | 说明 |
| --- | --- | --- |
| check | 0.15.2 | 仅用于构建并执行上游 libretro-common 单测（不链接进产物） |

## 功能验证

```bash
retroarch --version     # RetroArch - Frontend for libretro / Version: 1.22.2
retroarch --help        # 用法与全部命令行选项
retroarch --features    # 打印编译进程序的特性列表
```

上游 127 项 libretro-common 单元测试（5 个 libcheck 套件）全部通过。

## 参考

- [源码仓库](https://github.com/libretro/RetroArch)
- [官网](https://www.retroarch.com)
- [libretro 文档](https://docs.libretro.com/)
