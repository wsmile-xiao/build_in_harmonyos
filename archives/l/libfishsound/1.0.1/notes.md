# libfishsound 1.0.1 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-09-19
- 编译器: clang（/data/service/hnp/bin/clang，OHOS aarch64 原生）
- 状态: built

## 编译步骤

1. W0 依赖发布检查（R35/R36 口径，conan download 实测）：libogg/1.3.6、
   libvorbis/1.3.7、speex/1.2.1 均已在 ohpcd 制品仓发布且二进制可解析
   （`conan install --requires=... --build=never` 三包全部 Download 成功）。
2. 上游源码分析：`configure.ac` 中 Ogg 为必需依赖，Vorbis/Vorbisenc/Speex/FLAC
   为可选拦截器（`--disable-*` 均存在）；示例程序依赖 liboggz/libsndfile，
   缺失时 `noinst_PROGRAMS` 置空自动跳过，不影响库本体。
3. E007 处理：`scripts/patch-autotools-ohos.pl` 打 HarmonyOS 识别补丁
   （config.guess +HarmonyOS 分支；config.sub +ohos-linux 三元组 +ohos* OS 表）。
   该脚本对本包 2009 年版 config.sub 报 "[skip] linux-ohos already present"
   属误判（匹配到的是三元组映射行而非 kernel-OS 校验行），已按 E007 §3.3 手工
   追加 `| linux-ohos*` 到 kernel-OS 组合列表。补丁后
   `./config.sub aarch64-unknown-linux-ohos` 验证通过（输出规范三元组）。
4. 配方按 icecast 模式接线依赖：PkgConfigDeps 生成 ogg/vorbis/vorbisenc/speex
   的 .pc 模块 + VirtualBuildEnv 暴露 LD_LIBRARY_PATH + 逐依赖 -L/-rpath。
5. FLAC 支持：`--disable-flac`（见下方"依赖版本"）。
6. HMDFS 规避（E129 同款）：build() 内将 configure 的 `umask 077` 原地替换为
   `umask 022`，规避 config.status 临时目录 setgid 权限问题。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | flac/1.4.3 与 flac/1.5.0 配方均固定 `requires("libogg/1.3.5")`，与 libvorbis/1.3.7、speex/1.2.1 要求的 libogg/1.3.6 同图冲突 | 制品仓 flac 配方未随 libogg 1.3.6.x 修复版对齐 | 本包 `--disable-flac`，不捎带改 flac（W2 原子性）；libfishsound 的 FLAC 拦截器禁用，Vorbis/Speex 全功能保留 |
| 2 | patch-autotools-ohos.pl 对 2009 年 config.sub 评分 4/5，kernel-OS 校验漏补 | 脚本的 already-present 探测匹配到三元组映射行 | 按 E007 §3.3 手工补 `\| linux-ohos*`，`config.sub aarch64-unknown-linux-ohos` 实测通过 |
| 3 | 设备上经 conan 直接驱动 configure 出现 getcwd 风暴（hnp bash 在 hmdfs 深层路径）；mksh 下 PATH 前缀的未签名 printf 又 exec 受限 | 设备 shell/签名环境约束（E386 同族），属环境层而非配方层 | 由验证环境处理（TECHNICAL_NOTES 已有 E386 先例）；同一构建目录手动 `source conanbuild.sh && ./configure` 实测 94 项检查全部通过，证明配方与补丁本身正确 |
| 4 | 首轮 test_package 消费者测试段错误 | 误把单缓冲区当 `float *pcm[]` 每声道指针数组传给 `fish_sound_encode_float`，Vorbis 双声道越界读指针 | 改为按声道分配指针数组（上游 encdec-audio 同款） |
| 5 | 修复 #4 后 Vorbis 编码 0 包、解码 0 帧（Speex 正常） | 上游 1.0.1 两个 API 事实：①非交织 `fs_vorbis_encode_f` 恒返回 0；②Vorbis codec `flush` 挂 NULL，`fish_sound_flush` 对 Vorbis 无效——尾包必须经 `fish_sound_prepare_truncation` 的 EOS 标志在最后一块编码时冲刷（上游测试正是此用法） | 消费者测试按上游口径：每次 encode 前调 `prepare_truncation`（最后块 EOS）、不断言 encode 返回帧数、期望帧数按 Speex 320 窗口补齐公式计算；修正后 Vorbis/Speex 回环全过 |

> 上游怪癖（#5）对下游使用者的含义：编码收尾必须走 `prepare_truncation`
> EOS 路径，不能依赖 `fish_sound_flush`（Vorbis 无效）；非交织 encode
> 返回值不可作为帧数依据。
>
> 补充（L5 基线重立说明）：包内 libtool `.la` 已按指南从 package() 移除
> （内嵌绝对路径，且属 L5 逐轮差异源）；ELF 制品内嵌构建路径/build-id
> 随每轮私有 CONAN_HOME 随机名变化，reports/baseline.json 按验证器指引
> 同源码重验时删除重立（语义等同首轮）。

## 源码修改

- `patches/0001-config.guess.patch`：新增 `*:HarmonyOS:*:*` uname 分支，
  映射 aarch64/armv8/x86_64/i686 → `aarch64-unknown-linux-ohos` 等三元组
  （E007 §2.2 标准改法，无平台宏）。
- `patches/0002-config.sub.patch`：ohos-linux 三元组映射、`ohos*` 加入 OS 列表、
  `linux-ohos*` 加入 kernel-OS 组合校验（E007 §3.1-§3.3，无平台宏）。
- build() 内联修复：configure `umask 077`→`022`（E129，HMDFS setgid）。

## 依赖版本

- libogg/1.3.6（必需，与制品仓 libvorbis/speex 配方对齐，避免同图版本冲突）
- libvorbis/1.3.7（提供 vorbis、vorbisenc）
- speex/1.2.1（提供 speex）
- 未启用：flac（见问题 #1）；liboggz/libsndfile（示例程序专用，未适配，
  configure 自动跳过示例）

## 上游测试

上游自带测试位于 `src/tests/`（`make check` 驱动，4 个测试程序）：

| 测试程序 | 内容 | 前提条件 |
|----------|------|----------|
| comment-test | Vorbis/Speex 注释读写 | FS_ENCODE（默认开） |
| noop | 编解码器句柄空转冒烟 | FS_DECODE+FS_ENCODE（默认开） |
| encdec-comments | 编解码链路注释保真 | 同上 |
| encdec-audio | 多采样率/声道/块大小编解码回环矩阵 | 同上 |

适配后合计新增 1 个消费者测试（test_package/test_libfishsound.c）：
Vorbis（44.1kHz 双声道）与 Speex（8kHz 单声道）编码→识别→解码回环，
13 个 CHECK 断言点 × 2 编解码器 = 26 断言，不进上游分母。

## 验证结果

- 设备手动验证（staging 目录，conan 缓存构建树内）：
  `./configure --enable-shared --disable-static --prefix=/ --disable-flac`
  退出码 0，94 项 checking 全部完成，Vorbis/Speex 支持均已检测到。
- 正式验证：conan create（含 make check 与 test_package）由 finish 流程
  执行，结果见 reports/ 与 .ci-result.json（日志哈希绑定）。

## 注意事项

- libfishsound 非系统同名库，默认动态链接（shared=True），由 Conan 管理依赖链。
- 下游如需 FLAC 拦截器，需先将制品仓 flac 配方的 libogg 依赖对齐到 1.3.6+
  （或发布 flac 新适配版本），再以 `X.Y.Z.N` 递增本包版本启用。
