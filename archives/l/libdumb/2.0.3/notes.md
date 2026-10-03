# libdumb 2.0.3 — 适配笔记

## 基本信息
| 项目 | 值 |
|------|-----|
| 软件 | libdumb(Dynamic Universal Music Bibliotheque,IT/XM/S3M/MOD 解码) |
| 版本 | 2.0.3(kode54/dumb tag 2.0.3) |
| 状态 | built |
| 构建系统 | cmake |
| 源码 | https://github.com/kode54/dumb/archive/refs/tags/2.0.3.tar.gz |
| sha256 | 99bfac926aeb8d476562303312d9f47fd05b43803050cd889b44da34a9b2a4f9 |

## 上游选源说明
- 原始上游 katajakasa 的 dumb 仓库已消失(GitHub 404),IRC 引用为准的历史项目;
- **de facto 维护 fork = kode54/dumb**(CMake 构建,dsda-doom 等大量下游使用,
  openSUSE/Fedora 发行包 2.0.3 均出自此 fork)——与本库 7.1-1.10.1 条目
  (ctasada→ctabin 迁移)同模式:原上游死即切事实维护 fork。

## 配方设计
1. **CMake 链路**(上游 CMakeLists cmake_minimum_required=3.1,CMake 4 拒绝):
   `-DCMAKE_POLICY_VERSION_MINIMUM=3.5`(libzippp 同款)。
2. **三个上游 option 全关**(均为 aarch64/CI 不需要或引依赖):
   - `BUILD_ALLEGRO4=OFF`(allegro4 集成,引 allegro 头/库);
   - `BUILD_EXAMPLES=OFF`(examples 查找 argtable2/SDL2);
   - `USE_SSE=OFF`(x86 SSE 旗标,aarch64 无意义)。
3. **零外部依赖**:仅 libc/libm(关闭 allegro/examples 后无第三方查找)。
4. **产物**:lib/libdumb.so.2 + include/dumb.h(+internal 头)+ lib/pkgconfig/dumb.pc。
5. **license = Unlicense**(dumb 2.0 起重授权,非早期 GPL;LICENSE 文件已随包)。

## test_package(C 消费者探针)
- 正向:`dumbfile_open_memory` 打开内存缓冲 → `dumbfile_getc` 逐字节读回断言
  (DUMBFILE 抽象层主链路);
- 错误路径:`dumb_load_xm("/nonexistent-probe.xm")` 期望返回 NULL(库加载/API
  可调用/错误码语义);
- `dumb_exit()` 清理。

## 依赖
- 无(关闭 allegro/examples 后仅 libc/libm)。

## 【知识库扩展】
- 见 knowledge/drafts/DRAFT-libdumb-2.0.3-dead-upstream-de-facto-fork.kv/.md:
  上游消亡项目的事实维护 fork 选源判据(404 探测 + 下游引用面验证)。
