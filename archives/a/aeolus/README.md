# aeolus — Synthesised Pipe Organ

## 软件简介

Aeolus 是 Fons Adriaensen 编写的**合成（非采样）管风琴合成器**：它不加载采样，而是用物理建模/加性合成算法实时生成管风琴音色，配合 JACK 或 ALSA 音频后端输出。适合对管风琴音色有研究的音频爱好者与音乐家。

**主要功能**:
- 多采样率（44.1k/48k/88.2k/96k）、多通道输出
- JACK 音频后端（默认）与 ALSA 后端（`-A`）
- MIDI 输入、注册表（stops）管理
- 文字模式界面（`aeolus_txt.so`，`-t`）与 X11 图形界面（`aeolus_x11.so`）

## 已编译版本

| 版本 | 状态 | 编译日期 | 补丁数 |
|------|------|----------|--------|
| 0.10.4 | built ✅ | 2026-08-25 | 1 |

## 使用方法

```bash
# 帮助（打印版本横幅 Aeolus 0.10.4；上游 help() 退出码为 1，test_package 断言横幅文本）
aeolus -h

# 文字模式界面 + JACK 输出
aeolus -t

# 使用 ALSA 输出
aeolus -A -d default
```

## 平台适配说明

### 鸿蒙系统适配

**编译补丁**（`0.10.4/patches/0001-source-Makefile.patch`）:
1. 移除 `CXXFLAGS += -march=native`（容器/交叉环境不可移植，编译器由 conan profile 提供）
2. `INSTALL ?= /bin/install` 参数化，install 目标去掉 `ldconfig`（OHOS 无裸 install/ldconfig）
3. install 只构建/安装 `aeolus` + `aeolus_txt.so`，剔除 `aeolus_x11.so`
4. `aeolus_txt.so` LDLIBS 追加 `-lncursesw`（readline 静态库的 termcap 符号）

**编译依赖**:
- zita-alsa-pcmi/0.6.1、clthreads/2.4.0、jack/1.9.22、alsa-lib/1.2.16
- readline/8.3、ncurses/6.6（text-mode 界面）

**构建系统**: makefile（无 configure 脚本；源码位于 tarball `source/` 子目录）

### 已知平台限制（R40 评估）

`aeolus_x11.so`（X11 图形界面）**未构建**：
- 制品仓无 X11 相关配方：`conan download xft/libxft/clxclient -r=ohpcd --only-recipe` → 0 recipes
- 本机与 OHOS SDK 均无 X11/Xft 头文件（实测 find 无结果）
- 影响范围：仅图形界面不可用；核心合成器 + JACK/ALSA 音频 + 文字模式界面（`aeolus_txt.so`）完整可用

## 验证结果

| 测试项 | 结果 |
|--------|------|
| `aeolus -h`（打印 Aeolus 0.10.4 版本横幅，test_package 断言横幅文本） | ✅ 通过 |
| dlopen `aeolus_txt.so` + 解析 `create_iface` | ✅ 通过 |
| conan create + test_package | ✅ 通过 |

## 源码信息

- **源码地址**: https://kokkinizita.linuxaudio.org/linuxaudio/downloads/aeolus-0.10.4.tar.bz2
- **官方主页**: https://kokkinizita.linuxaudio.org/linuxaudio/
- **许可证**: GPL-3.0-or-later
- **作者**: Fons Adriaensen <fons@linuxaudio.org>

## 相关资源

- [编译详情](./0.10.4/notes.md)
- [验证报告](./0.10.4/reports/test-report.md)
