# libdynamite 0.1.1 适配笔记

## 编译环境

- 构建系统: autotools（上游**不含**生成态构建系统，仅 configure.ac.in + bootstrap 脚本）
- 平台任务: contrib-13139（libdynamite 0.1.1），claimer Ember5843，认领 2026-09-17T09:18Z
- 目标平台: HarmonyOS PC arm64（clang 15 / musl），本机原生构建
- 依赖: **无外部依赖**（纯 C99）
- 上游: https://github.com/twogood/dynamite （PKWARE DCL implode/explode 解压库）
- 源码 sha256: `e182395fd193e4591a9177cbf51aefc01d8bbc32b326ca233deed4311fd1a287`
- 版本锚点: 上游无 tag/release；0.1.1 = 官方提交 ccf573ad71cebbfe72f9fe2bead6b2954bb161c0 的树状态
- 语言实测（R47 lang-preflight）: 4 个源文件全部 C，主体 100%

## 源码面貌（摸底结论）

- 交付形态: `libdynamite.a`（静态库）+ `dynamite` 命令行工具 + `libdynamite.h`
- 接口: `DynamiteResult dynamite_explode(dynamite_reader, dynamite_writer, void* cookie)`
  —— 读者/写者回调 + 单一 cookie，流式解压
- **构建系统缺失**：仓库只有 `configure.ac.in`（版本号占位 YOU_DID_NOT_RUN_THE_BOOTSTRAP_SCRIPT）
  与 `bootstrap`（需要 aclocal/autoheader/libtoolize/automake/autoconf）；设备侧
  automake 与 libtoolize 缺失，Mac 侧缺 libtoolize（有 glibtoolize）

## 移植要点

1. **构建方式**：上游只发 `configure.ac.in` + `bootstrap`（需 automake/libtoolize，本平台皆缺）。
   先尝试「在完整 autotools 主机生成构建系统并作为补丁交付」——虽可行，但生成物
   有 4.7 万行，AI 检视直接跳过（"本次变更过大…已超出处理范围"），也给评审带来噪声。
   最终改为**配方自带 CMakeLists.txt**（上游源码不变，构建同一批产物）：
   `libdynamite.a` + `dynamite` + `queen_extract`。
2. 构建环境显式清空 LD_LIBRARY_PATH（lld/libxml2 防护，同 libodfgen 系）。
3. 消费者测试自建合法 PKWARE implode 流：**LSB-first 位流**
   （dynamite_read_bit 取 byte&1 后右移）——头 2 字节为原始字节（表示 0/1/2 + 字典位 4/5/6），
   之后是位流：字面量令牌 = 0 + 8 位（LSB first）；流结束令牌 = 控制位 1 +
   长度 519 的编码（0000000 + LE8(255)）。

## 状态

- [x] 配方四件套（CMake 构建）
- [ ] 设备实机 conan create + conan-verify + 消费者测试
- [ ] push / PR / 平台绑定 / 提审
