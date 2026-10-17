# aghermann

> Aghermann — 睡眠研究实验管理器（GTK+3，EDF/EEG 信号处理与评分）

## 简介

Aghermann 是一个面向睡眠研究的实验管理器：以 EDF/EDF+ 格式处理多夜多通道
EEG/PSG 记录，提供评分、谱分析（FFT 的慢波/纺锤波检测）与统计工具。命令行
工具 `edfcat`（修剪/转换 EDF）、`edfhed`（EDF 头查看/编辑）与 GUI
`aghermann` 构成完整工作流。

本归档为 HarmonyOS PC (aarch64) 适配版本：autotools 构建，GTK+3 栈全部来自
ohpcd 制品仓，编译与功能验证通过。

## OHOS 适配要点

- 构建环境为 musl + clang 15，上游两处 glibc 私有 API 已替换：
  `canonicalize_file_name()` → `realpath(path, NULL)`；`<sys/time.h>` 显式引入。
- OHOS 无 glibc argp，依赖 `argp-standalone` 提供 `argp_parse`。
- C++17 编译：上游 8 处动态异常规范（`throw(...)`）与 `std::mem_fun_ref` 已移除
  /替换为 `std::mem_fn`（clang 15 报错）。
- 上游 bug 修复：CEDFFile 写构造器 mmap 用 `MAP_PRIVATE` 导致 edfcat prune 输出
  全零，已改 `MAP_SHARED`。
- 系统 `/data/service/hnp/bin/glib-compile-resources` 为坏二进制（ffi 符号缺失），
  构建时使用 conan glib 包的 wrapper。

## 排除与替代

- GUI（`aghermann`/`edfhed-gtk`）依赖 X11/GTK 显示环境；无显示器时请使用命令行
  工具 `edfcat`/`edfhed`/`agh-profile-gen`。

## 依赖

| 依赖 | 版本 | 说明 |
|------|------|------|
| gtk | 3.24.43 | GUI 框架 |
| glib | 2.84.0.1 | 基础库（glib-compile-resources 等） |
| cairo | 1.18.4 | 2D 渲染 |
| vte | 0.74.2 | 终端部件 |
| fftw | 3.3.11 | FFT 谱分析 |
| gsl | 2.8 | 数值计算 |
| libconfig | 1.7.3 | 配置解析 |
| itpp | 4.3.1 | 信号处理 |
| libsamplerate | 0.2.2 | 重采样 |
| lua | 5.5.0 | 脚本 |
| argp-standalone | 1.5.0 | glibc argp 替代 |

## 功能验证

```bash
edfhed --help                    # 用法输出
edfhed minimal.edf               # 解析 2 通道 EDF → "# of channels : 2"
edfcat prune 往返                # 修剪读改写一致（验证 MAP_SHARED 修复）
aghermann --version              # 版本号
```

上游无自动化测试套件（0/0 已清点，R51 如实申报）；功能替代验证 8/8 通过，
conan-verify 8 道门禁全绿。

## 参考

- 上游官网: https://johnhommer.com/academic/code/aghermann
- 源码包: https://johnhommer.com/academic/code/aghermann/source/aghermann-1.1.2.tar.xz
