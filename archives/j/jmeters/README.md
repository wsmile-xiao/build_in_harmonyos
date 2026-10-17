# jmeters — JACK 电平表（多标准刻度）

## 软件简介

jMeters 是 Fons Adriaensen（kokkinizita）编写的**音频电平计量表**：从文件或 JACK 端口取信号，
按 BBC / DIN / EBU / PPM / VU 等多种刻度显示峰值、短期与相关性计量，图形界面走 X11（clxclient）。
与同作者的 zita-* 系列共用构建方式（一个裸 `source/Makefile`，无 configure/autotools/CMake）。

**主要特征**:
- 多种计量刻度（share/ 下的 21 张 `*-meter*.png` / `*-scorr*.png` 皮肤，安装到 `share/jmeters/`）
- JACK 客户端（依赖 jack、libsndfile）
- X11 图形界面（clxclient / clthreads / cairo / libpng / libXft / libX11 / fontconfig）
- 上游主页 https://kokkinizita.linuxaudio.org/linuxaudio/

## 已编译版本

| 版本 | 状态 | 编译日期 | 补丁数 | 备注 |
|------|------|----------|--------|------|
| 0.4.5 | built ✅ | 2026-09-26 | 1 | 见 `0.4.5/manifest.yaml` 与 `0.4.5/notes.md` |

## 构建与安装（OHOS / Conan）

```bash
python3 scripts/ohc-run.py build jmeters 0.4.5
python3 scripts/ohc-run.py conan-verify jmeters 0.4.5
python3 scripts/ohc-run.py finish jmeters 0.4.5 built
```

配方为 `application` 包，`make install PREFIX=/` 把 `bin/jmeters` 与 `share/jmeters/*.png`
放进包目录；上游 `-march=native` 与裸 `install` 命令由
`0.4.5/patches/0001-source-Makefile.patch`（`+5/-5`，portability）处理。

## 运行边界（重要）

- 本包是 **GUI + JACK 客户端**：需要 X 显示服务与运行中的 JACK server 才有可见行为。
- 设备侧诊断性 `jmeters -h` 报 `Error loading shared library libXft.so.2`
  （musl loader 不认用户目录的 `LD_LIBRARY_PATH`，见 `knowledge/graph/E088.kv:2`），
  因此**归档只申报"编译 + 打包 + 消费者静态断言"通过，不申报可运行**。
- 交付证据口径见 `0.4.5/notes.md`：`conan-verify` 可用判决为 `G1/G2/G3 PASS`
  （`G4` 带「无法找到程序包 ID」、`L2/L4/L5` 为「跳过（无 cache 路径）」，不计为通过）；
  `W3 本地 CI 模拟通过`（`.ci-result.json` `exit_code=0`、`step=W3_local_ci`，`finish` 整体 rc=2 属收尾步骤常态）。
- 上游无任何测试资产（`make check` 报 `No rule to make target 'check'`，
  框架源码/语料目录/RUNTEST 脚本/示例目录四式读数均为 0），
  适配后为消费者用例 `test_package/test_jmeters.c` 1/1（4 检查点全过）。

## 使用（在有 X 与 JACK 的宿主上）

```bash
jmeters        # 默认刻度启动（需 X 显示服务 + 运行中的 JACK server）
jmeters -h     # 打印版本横幅后退出（设备侧该调用即报上面的 libXft 加载错误）
```

上游 README 未列出除帮助外的稳定选项面，本归档不申报其它调用形态。
