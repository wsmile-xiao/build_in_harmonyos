# slurm 0.4.4 适配笔记

## 编译环境
- 构建系统: meson 1.11.1
- 编译日期: 2026-06-09
- 编译器: clang 15.0.4 / clang++ 15.0.4 (aarch64)
- 编译选项: CFLAGS="-fPIC -O2 -D__OHOS__"
- 运行时依赖: ncursesw 6.4.20221231（预编译包，静态链接）
- 状态: published

## 编译步骤

```bash
# 1. 下载源码（GitHub 超时，手动 curl）
curl -fsSL -o ~/tmp/slurm-0.4.4.tar.gz \
  https://github.com/mattthias/slurm/archive/refs/tags/upstream/0.4.4.tar.gz

# 2. 解压到 .orig 和 .work 目录
cd ~/tmp/builds
mkdir -p slurm-0.4.4.orig && cd slurm-0.4.4.orig
tar xf ~/tmp/slurm-0.4.4.tar.gz --strip-components=1
mkdir -p ../slurm-0.4.4.work && cp -a . ../slurm-0.4.4.work/

# 3. 初始化编译（--no-download，因为已有源码）
python3 $SKILL_ROOT/scripts/ohc-run.py init-build slurm 0.4.4 \
  --url=https://github.com/mattthias/slurm/archive/refs/tags/upstream/0.4.4.tar.gz \
  --no-download

# 4. 修改源码（修复 ethtool_cmd_speed 缺失）
#    在 src/if_media.c 的 #include <linux/ethtool.h> 之后
#    添加 #ifdef __OHOS__ 守卫块（详见补丁 0001-ethtool-ohos-compat.patch）

# 5. meson 配置与编译
export CFLAGS="-fPIC -O2 -D__OHOS__"
meson setup builddir --prefix=$DEFAULT_PREFIX
ninja -C builddir

# 6. DESTDIR 安装（R20 铁律）
DESTDIR=$TEST_PREFIX ninja -C builddir install

# 7. 本地安装验证
ninja -C builddir install

# 8. 用户验证（R7）
$DEFAULT_PREFIX/bin/slurm -h  # 确认版本 0.4.4

# 9. 打包（R19 铁律）
python3 $SKILL_ROOT/scripts/ohc-run.py package slurm 0.4.4

# 10. 收尾
python3 $SKILL_ROOT/scripts/ohc-run.py finish slurm 0.4.4 published
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `undefined symbol: ethtool_cmd_speed` 链接失败（make HANDOFF） | OpenHarmony SDK 的 `linux/ethtool.h`（源自 Android bionic 裁剪版）缺少 Linux 内核 3.x+ 引入的 `ethtool_cmd_speed()` inline 函数和 `SPEED_10/100/1000/2500/10000` 常量宏 | 在 `src/if_media.c` 中添加 `#ifdef __OHOS__` 守卫块，手动定义 `SPEED_*` 宏和 `ethtool_cmd_speed()` inline 函数（实现为 `(ep->speed_hi << 16) | ep->speed`），编译时传入 `-D__OHOS__` |
| 2 | GitHub 源码下载超时（init-build Step 1） | OpenHarmony 环境网络限制，直连 GitHub 超时 | 使用 `curl -fsSL` 手动下载源码包到 `~/tmp/`，然后手动创建 `.orig` 和 `.work` 目录，用 `init-build --no-download` 重新初始化 |
| 3 | 构建系统检测为 autotools（实际为 meson） | init-build 的构建系统检测逻辑优先检查 autotools 特征文件 | 手动使用 meson/ninja 编译，修正 manifest.yaml 中 `build_system: meson` |
| 4 | 首次 verify-build G4 门禁失败 | manifest.yaml 缺少顶级 `build_system:` 字段（仅有嵌套 `build.system:`） | 在 manifest.yaml 顶部添加 `build_system: meson` 顶级字段 |

## 源码修改

- `src/if_media.c`: 添加 `#ifdef __OHOS__` 守卫块（+24/-0 行），为 OpenHarmony 平台补充缺失的 ethtool API 定义
  - 补丁文件: `0001-ethtool-ohos-compat.patch`
  - 守卫宏: `__OHOS__`（通过 CFLAGS=-D__OHOS__ 传入）

## 依赖版本

| 依赖 | 版本 | 来源 | 说明 |
|------|------|------|------|
| ncursesw | 6.4.20221231 | 预编译包（cmd-pkgs） | 静态链接（libncursesw.a），提供 curses 终端界面支持 |
| meson | 1.11.1 | pip 安装 | 构建系统 |
| ninja | 1.13.1 | 系统预装 | 构建后端 |
| clang | 15.0.4 | 系统预装 | C 编译器 |

## 验证结果

```bash
# 帮助信息
$ slurm -h
slurm 0.4.4 - https://github.com/mattthias/slurm

# 实际运行测试（lo 接口，3秒超时）
$ timeout 3 slurm -i lo -z -d 1
# ncurses 界面正常显示 "slurm 0.4.4 on localhost"

# ELF 检查
$ readelf -d slurm | grep NEEDED
  (NEEDED) Shared library: [libc.so]
# 仅依赖 libc.so，ncursesw 已静态链接
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| slurm-0.4.4-ohos-aarch64.tar.gz | 322 KB | 预编译包（已 strip、已签名） |
| slurm-0.4.4-ohos-aarch64-debug.tar.gz | 109 KB | 调试符号包 |
| 0001-ethtool-ohos-compat.patch | 1.1 KB | OpenHarmony 平台兼容性补丁 |

## 注意事项

- slurm 是网络负载监控工具，运行需要指定 `-i interface` 参数
- 主题文件安装在 `$DEFAULT_PREFIX/share/slurm/themes/`（4 个主题文件）
- man page 安装在 `$DEFAULT_PREFIX/share/man/man1/slurm.1`（67 行）
- ncursesw 已静态链接到二进制中，运行时仅依赖 libc.so
- 当前 slurm 不支持 `--version` 参数，使用 `-h` 可查看版本信息

---

**编译结束**: 2026-06-09 22:14
**最终状态**: published