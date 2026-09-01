# mpegdemux 0.1.5 for HarmonyOS

## 概述

mpegdemux 在 HarmonyOS/OpenHarmony (aarch64) 上的编译指南和测试记录。

mpegdemux 是一个 MPEG1/MPEG2 系统流解复用器 (demultiplexer)，由 Hampa Hug 开发。
它可以将 MPEG 系统流中的基本流 (elementary streams) 分离出来，支持四种工作模式：
scan (扫描)、list (列表)、demux (解复用)、remux (重新复用)。

## 软件信息

| 项目 | 值 |
|------|-----|
| 名称 | mpegdemux |
| 版本 | 0.1.5 |
| 上游主页 | http://www.hampa.ch/mpegdemux/index.html |
| 下载地址 | http://www.hampa.ch/mpegdemux/mpegdemux-0.1.5.tar.gz |
| SHA256 | 05015755d45e50cbd3018baeaa8abcedc003b1162fa28237a72ab25c1bc00023 |
| License | GPL-2.0 (GPL-2.0-only) |
| 构建系统 | autotools (预生成 configure + 自定义 Makefile.in) |
| 产物类型 | CLI 工具 (单一可执行文件 mpegdemux) |

## 鸿蒙环境

| 项目 | 值 |
|------|-----|
| 系统版本 | HarmonyOS OpenHarmony (aarch64) |
| 架构 | aarch64 |
| target triplet | aarch64-unknown-linux-ohos |
| 动态链接器 | /lib/ld-musl-aarch64.so.1 |
| 编译器 | clang (LLVM) |
| 构建系统 | autotools (configure + make) |

## 上游测试情况

上游 mpegdemux 0.1.5 **没有正式测试套件**：

- 源码包中无 `tests/` 或 `regress/` 目录
- `Makefile.in` 中无 `check:` / `test:` 目标
- `configure.ac` 中无 `TESTS` / `check_PROGRAMS` 声明
- Debian 打包仅添加了一个只运行 `mpegdemux --help` 的 superficial autopkgtest

证据：
- `Makefile.in` 全部目标仅有：`all clean distclean man install dist dist-dist dist-contrib dist-extra`
- 源码树文件清单 (38 文件) 中无任何 test/regress/fixture 文件

因此 test_package 承担唯一的真实功能验证 (见 0.1.5/test_package/)。

## 编译步骤

```bash
# 1. 下载源码
curl -LO http://www.hampa.ch/mpegdemux/mpegdemux-0.1.5.tar.gz

# 2. 解压
tar xzf mpegdemux-0.1.5.tar.gz
cd mpegdemux-0.1.5

# 3. 配置 (零依赖)
./configure --prefix=$HOME/usr/local

# 4. 编译
make -j$(nproc)

# 5. 安装
make install
```

## 补丁说明

零 patch 构建。上游源码在 HarmonyOS/musl 下无需任何修改即可编译通过。

## 遇到的问题

无。mpegdemux 是纯 C 标准库程序，无系统依赖，musl 兼容性良好。

## 测试结果

详见 [test_package](./0.1.5/test_package/)

| 测试项 | 结果 |
|--------|------|
| scan 模式 (扫描 MPEG 流基本流) | ✅ |
| list 模式 (文本化列出包内容) | ✅ |
| demux 模式 (提取视频基本流) | ✅ |
| remux 模式 (保留系统流结构重复用) | ✅ |
| 输出确定性 (大小/结构) | ✅ |
| 负向测试 (空文件输入必须非零退出) | ✅ |

## 验证安装

```bash
# 检查产物 ELF 类型
file $(which mpegdemux)
# 期望: ELF 64-bit LSB executable, ARM aarch64, interpreter /lib/ld-musl-aarch64.so.1

# 检查版本
mpegdemux -V
# 期望: mpegdemux 0.1.5

# 功能验证
mpegdemux -c test.mpg        # scan 模式
mpegdemux -l -k -s all -p all test.mpg   # list 模式
```

## 经验总结

1. mpegdemux 零依赖纯 C 程序，musl/OHOS 兼容性优秀，零 patch 构建
2. 上游无正式测试套件，test_package 必须程序化生成 MPEG fixture 进行真实 demux 验证
3. 负向测试必须显式检查退出码，禁止 `|| true` 后无条件 PASS

## 参考资料

- http://www.hampa.ch/mpegdemux/index.html
- https://packages.debian.org/unstable/sound/mpegdemux
