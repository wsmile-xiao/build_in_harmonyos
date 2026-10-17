# librist 0.2.18 适配笔记

## 编译环境

- 构建系统: Meson（上游唯一构建系统，`meson.build`＋`meson_options.txt`）
- 编译日期: 2026-09-16
- 编译器: clang/clang++（HarmonyOS PC 真机 `/data/service/hnp/bin` 工具链）
- 状态: prepared（待真机预检：`conan create`＋上游 `meson test`＋test_package）

## 上游信息

- 官方仓库: https://code.videolan.org/rist/librist
- 发布包: https://code.videolan.org/rist/librist/-/archive/v0.2.18/librist-v0.2.18.tar.gz
- sha256: `9a2d16dcdb9fb067b7ba4259a3976ff6f8df9a62dbec7f32f19a0b60ec0c114a`
  （取自 Homebrew homebrew-core `Formula/lib/librist.rb`；同一归档在 VLC
  contrib 记录的 SHA512 为 `f561e48b…`，算法不同、文件相同。CI 下载后
  以 `conandata.yml` 校验为准，若不匹配按 CI 日志修正。）
- 许可证: BSD-2-Clause
- 简介: RIST（可靠互联网流传输）协议 C 实现，低延迟音视频流传输库，
  FFmpeg/OBS 通过它收发 `rist://` 流。

## 依赖分析（W0）

| 上游依赖 | 状态 | 配方对策 |
|---|---|---|
| cJSON | 制品仓有 `cjson/1.7.19`，但 meson 侧找 `libcjson.pc`，存在 pc 名映射分歧风险 | 使用上游自带 `contrib/contrib_cJSON`（`-Dbuiltin_cjson=true`），零外部依赖，确定性最强 |
| mbedtls（AES/SRP 加密） | 制品仓仅 `mbedtls/4.1.0`（Conan 配方），与 0.2.18 所需 3.x API 不兼容 | 使用上游自带 `contrib/mbedtls`（`-Dbuiltin_mbedtls=true -Duse_mbedtls=true`） |
| libmicrohttpd（仅 tools 统计页） | 非库核心 | `-Dbuilt_tools=false -Duse_tun=false` 关闭工具，保持最小依赖面 |
| cmocka（仅 `srp_unit` 单元测试） | 制品仓有 `cmocka/2.0.2` | `test_requires("cmocka/2.0.2")`，不进入消费者依赖 |

结论：常规 `requires` 为空（library 自包含），测试期 `test_requires` 仅 cmocka。
无缺失依赖阻塞，不触发 R36 止损。

## 编译步骤

Meson 标准流程（`conanfile.py`）：

```bash
meson setup <build> <src> -Ddefault_library=shared \
  -Dbuiltin_cjson=true -Dbuiltin_mbedtls=true -Duse_mbedtls=true \
  -Duse_gnutls=false -Dbuilt_tools=false -Duse_tun=false \
  -Dfallback_builtin=true -Dstatic_analyze=false -Dtest=true
meson compile -C <build>
meson test -C <build> --print-errorlogs
meson install -C <build>
```

关键点：

1. `basic_layout(src_folder=".")` 分离源码/构建目录（Meson 带内构建拒绝）。
2. `PkgConfigDeps` 生成 `cmocka.pc`，供上游单元测试发现逻辑使用。
3. `test/rist/unit/meson.build` 上游用
   `meson.get_compiler('c').find_library('cmocka')` 探测，不走 pkg-config，
   Conan 包路径对其不可见会导致 `srp_unit` 被静默跳过。`build()` 内以
   Python 字符串替换改为优先 `dependency('cmocka', method: 'pkg-config')`，
   找不到时回退原逻辑（行为与上游一致：跳过注册，不报错）。幂等、可重入，
   无平台宏（PF5 安全），属构建集成微调而非平台适配，故未放入 `patches/`。
4. OHOS 下 meson 经 PATH 找不到 `llvm-ar` 时，向
   `conan_meson_native/cross.ini` 的 `[binaries]` 段注入绝对路径
   （zix/libsoup 先例，`_inject_meson_archiver`）。
5. `package_info`: `libs=["rist"]`，`pkg_config_name=librist`，
   系统库 `pthread/m/dl`（OHOS bionic 实际自带，声明无害，随 Linux 同列，
   R32 口径 `in ("Linux", "OHOS")`）。
6. `.so` 重签名为有守卫尝试：仅当 `llvm-objcopy` 与 `binary-sign-tool`
   同时在 PATH 时执行（libsoup 先例），缺失则 info 跳过、不阻断。

## 上游测试清点（供 PR 正文回填，真机实测为准）

来源：`test/rist/meson.build`、`test/rist/unit/meson.build`（deepin-community
镜像与上游同版本结构交叉核对；确切数字以真机 `meson test` 输出为准）：

- `test_send_receive`（simple profile，单播）: 3 项
- `test_send_receive`（simple profile，组播，非 darwin 注册，OHOS 会注册）: 3 项
- `test_send_receive`（main profile NPD/主备收发/加密/SRP）: 约 20 项，
  其中 8 项为 `should_fail:true` 反向用例（单侧加密错配、SRP 口令错配，
  期望失败，meson 计为 Expected Fail）
- `srp_unit_test`（cmocka）: 1 项（cmocka 缺失时上游自动不注册）
- 预计总量约 27 项；组播在受限沙箱可能失败（Gentoo ebuild 有
  `meson_src_test --no-suite multicast` 规避 network-sandbox 的先例），
  真机若复现则如实上报、再议 `--no-suite multicast` 豁免，绝不预先阉割。

证伪安排（真机 evidence 轮执行，不在本轮猜测）：

1. 检查 `meson test` 原始摘要行非空且各项计数之和等于 discovered；
2. `should_fail` 反向用例必须出现在 Expected Fail 中（证明 harness 能
   区分成功/失败，而非空跑报喜）；
3. `srp_unit_test` 必须出现在注册列表（`meson test --list`），否则视为
   静默跳过、不计通过。

## test_package 设计（R34）

两个真实调用 API 的消费者程序（均只走本地逻辑，不绑定端口，沙箱可跑）：

- `test_sender.c`: `librist_version/api_version` 非空断言 →
  `rist_logging_set` → `rist_sender_create(RIST_PROFILE_MAIN)` →
  `rist_destroy`。
- `test_receiver.c`: `rist_receiver_create` →
  `rist_parse_address2("rist://@127.0.0.1:19680")` 解析断言 →
  `rist_peer_config_free2` → `rist_destroy`。

`test()` 内 `clang -I/-L… -lrist` 逐个编译运行，全部退出 0 后打印
`HMBS_TEST_PACKAGE_RESULT`（discovered=2/passedCount=2）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|---|---|---|
| 1 | Windows 检出后 `archives/l/libXext` 误报 dirty | 上游同时存在 `libXext` 与 `libxext`（仅大小写差异），Windows 大小写不敏感文件系统碰撞 | 非本任务文件，不碰；真机（Linux）无此问题，后端以 Linux 树为准 |
| 2 | mbedtls 外部依赖无兼容版本 | 制品仓仅 4.1.0 Conan 配方，0.2.18 需 3.x API | 用上游内嵌 `contrib/mbedtls`，零外部依赖 |
| 3 | `srp_unit` 可能静默跳过 | 上游 `find_library('cmocka')` 不走 pkg-config | `build()` 内改优先 `dependency('cmocka')`＋回退，`test_requires` 引入 cmocka |
| 4 | CI `meson.build:177 clock_gettime not found`（构建 #48637） | CI 上 `host_machine.system()` 非 linux（`linux/if_alg.h` 检查行缺失为证），`linux/android` 分支未执行 → 无 `-D_GNU_SOURCE`，c_std=c99 下 OHOS libc 不声明 `clock_gettime`，plain 与 `-lrt` 两次检查均为 NO；且 OHOS 下 `platform_files` 为空会导致后续 `rist_tun_read/write` 链接缺符号 | `patches/0001-ohos-clock-gettime-tun.patch`：① `ohos`/`harmonyos` 并入 `_GNU_SOURCE` 分支；② `clock_gettime` 失败时用 `threads` 依赖重试、仅 `lib_rt.found()` 才链接 `-lrt`；③ OHOS 用新增 `src/tun_ohos.c` 桩（全返回 -1/ENOSYS，对标 `tun_win.c`，TUN 数据面在 OHOS 无 `/dev/net/tun`，本来就不可用）。补丁行已在官方 0.2.18 源码树逐行验字（3 删行＋16 上下文行原文命中），待 CI/真机验证 |

## 验证结果

```bash
# 待 HMBS 真机预检回填（conan create 全量日志）：
# - meson test 摘要（Ok/Expected Fail/Fail/Skipped/Timeout）
# - HMBS_UPSTREAM_TEST_RESULT 行
# - HMBS_TEST_PACKAGE_RESULT 行（discovered=2）
```

## 交付物

| 文件 | 说明 |
|---|---|
| `conanfile.py` | Meson 主配方（含上游测试执行与双 HMBS 标记） |
| `conandata.yml` | 官方源 URL＋sha256 |
| `manifest.yaml` | 版本级清单（status=prepared，待真机翻绿） |
| `test_package/` | 双 API 实测程序＋MANIFEST.yml |
| `notes.md` | 本文件 |

## 注意事项

- 本库非系统同名库，默认动态链接（R26 不适用）。
- 纯库（`built_tools=false` 关闭 CLI），无需 `commands.json`（R38 不适用）。
- 适配路径为路径 A（基础适配）：标准 Meson 构建＋内嵌依赖＋测试全量执行，
  无平台补丁、无创新封装。
- 中文文件均以 Python UTF-8 无 BOM 写入；本轮未执行 commit/push/PR 写接口。
