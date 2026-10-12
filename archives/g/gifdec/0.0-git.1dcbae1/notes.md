# gifdec 0.0-git.1dcbae1 适配笔记

## 编译环境
- 构建系统: custom（上游无构建系统，conanfile.py 生成薄 CMakeLists.txt）
- 编译日期: 2026-10-04
- 编译器: clang 15.0.4（aarch64-unknown-linux-ohos 目标，OHOS aarch64 profile）
- 状态: built

## 上游形态

- 仓库: https://github.com/lecram/gifdec（master-only，无 tag 无 release）
- 版本号规则: 0.0-git.{master HEAD hash 前 7 位} → 本版本 = master @ 1dcbae19363597314f6623010cc80abad4e47f7c
- 源码包: 官方 GitHub master 分支 tarball（R39 官方源），ghfast.top 镜像 + 官方兜底
  列表格式（libgweather/libshumate 先例），双源下载 sha256 实测逐字节一致:
  96c68055b7e46bb04879c664724917214aae4614e2fd0bef9a0d4c146fd49c8a
  （git ls-remote 核验 master HEAD = 1dcbae193…，与版本号一致，无漂移）
- 许可证: public domain（README 明文声明）
- 交付形态: .c + .h 分离的两文件 C 库 —— gifdec.c(13,627B, 530 行) + gifdec.h(1,200B)，
  6 个公开函数（gd_open_gif/gd_get_frame/gd_render_frame/gd_is_bgcolor/gd_rewind/gd_close_gif）
- 上游构建: 无 CMake/Makefile；README 记载的用法是消费者直接 `cc gifdec.c example.c`（example.c
  为 SDL2 交互播放器演示，非测试）

## 编译步骤

1. conan create -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=…（CI 同款命令）
2. source(): 镜像列表下载官方 tarball（strip_root）
3. build(): save() 生成薄 CMakeLists.txt（add_library(gifdec gifdec.c) + install 规则）
4. cmake configure + build（clang 15 / c99 / 静态库，-Wall -Wextra 零警告）
5. 无上游测试可跑（上游无测试套件）——消费者验证全部在 test_package 阶段

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游无构建系统 | 仓库仅 gifdec.c/gifdec.h/example.c/README，无任何构建文件 | conanfile.py save() 生成薄 CMakeLists.txt，未修改上游 gifdec.c 一行（无补丁） |
| 2 | 上游无测试套件，CI L1 无测试痕迹 | example.c 是 SDL2 交互播放器演示（需 GUI + 真实 GIF 文件），非测试程序 | test_package 程序化合成最小 GIF89a 字节流（写临时文件→gd_open_gif→断言），零文件资产全 API 实测 |
| 3 | 合成 GIF 的 LZW 码流构造 | LZW 是 LSB-first 变长位打包，手工构造易错 | 按解码器语义逐位推演 + 独立锚点程序在未修改上游 gifdec.c 上实测校准后冻结：min code size=2 时 [clear=4][code0]→0x04；[clear][code0][code1]→0x44 0x00 |
| 4 | LCT 场景 packed 字节易错 | LCT size 字段在 packed 字节低 3 位，0x81 表示 2^(1+1)=4 项（12 字节），不是 2 项 | LCT 2 项应写 0x80（低 3 位=0 → 2^(0+1)=2 项）——实测校准后冻结 |

## 源码修改

无补丁。conanfile.py build() 中 save() 生成的 CMakeLists.txt 为增量打包层，
上游 gifdec.c / gifdec.h / example.c 零修改。

## 依赖版本

W0 依赖审计: 零第三方依赖。
- gifdec.c: 纯 libc（open/read/lseek/close POSIX fd I/O + memset/memcpy/memcmp），
  stdio（fprintf/stderr）——musl/OHOS 直接可用，无 libm 依赖
- gifdec.h: 仅 stdint.h + sys/types.h

## 验证结果

```bash
# 独立锚点校准程序（未修改上游 gifdec.c 原样编译, OHOS aarch64 clang 15 -O2）:
#   49/49 CHECK 全过（头部/LSD/GCT 解析、LZW 单码/多码解码、GCE 延时/透明度、
#   NETSCAPE 循环数、局部色表覆盖、双帧默认处置 canvas 累积、gd_is_bgcolor、
#   gd_rewind 重解码、错误契约 5 项）
# conan create test_package 阶段: test_gifdec 49 条消费者断言全过
# （详见 PR 正文"验证结果"段 conan create 原始输出）
```

## 注意事项

- 消费者用法: `#include "gifdec.h"` + 链接 libgifdec.a（符号 gd_*_gif 全在库内，
  与 minimp3 的实现宏形态不同——gifdec 是 .c+.h 分离形态，无需定义任何宏）
- gd_get_frame 返回值语义: 1=取到帧 / 0=trailer 结束 / -1=错误
- gd_render_frame 输出画布为 RGB 三字节/像素（width*height*3 缓冲）
- 上游不支持无全局色表的 GIF（gd_open_gif 直接失败，README 明示的限制）
- 上游 master 分支无版本 tag：引用本包固定用 gifdec/0.0-git.1dcbae1，
  后续上游演进需按 0.0-git.{新 hash7} 递增新版本目录
