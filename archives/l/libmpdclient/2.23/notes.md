# libmpdclient 2.23 适配笔记

## 编译环境

- 构建系统: Meson
- 适配日期: 2026-08-07
- 状态: 前置适配完成，待真机或 shadow CI 单包验证

## 源码

- URL: https://www.musicpd.org/download/libmpdclient/2/libmpdclient-2.23.tar.xz
- sha256: `4a1b6c7f783d8cac3d3b8e4cbe9ad021c45491e383de3b893ea4eedefbc71607`

## 依赖版本

- 默认构建依赖: 无三方库依赖。
- 可选测试依赖: `check`。上游 `-Dtest=true` 会构建 `t_iso8601` 和 `t_commands`，但仓库中 `check/0.15.2` 当前只有旧式构建记录，未纳入本轮 PR。

## 编译策略

- 使用 Conan `MesonToolchain`。
- 默认构建 shared library。
- 显式关闭 `documentation` 与 `test`，保留 `tcp=true`。
- OHOS runner 中 Meson 找不到 `ar` 时，recipe 会向 Meson native file 注入 `/data/service/hnp/binutils.org/binutils_2.45/bin/ar` 等可用 archiver 候选。
- OHOS 不支持 Meson 安装阶段的 symlink 创建，recipe 会物化 `libmpdclient.so.2` 与 `libmpdclient.so`，保证消费者可用 `-lmpdclient` 链接。
- 无 OHOS 补丁。

## 测试策略

- `build()` 中保留 `meson.test()`；当前 `-Dtest=false` 下不启用依赖 `check` 的上游测试。
- `test_package` 直接使用 Conan profile 中的 C 编译器，编译并运行 `test_libmpdclient.c`，不依赖真机是否安装 `cmake`。
- 消费者测试验证版本宏、tag 名称解析 API 和 `mpd_audio_format` 公开结构体，不需要运行 MPD 服务。

## 本机验证结果

```bash
# 已完成
Get-FileHash -Algorithm SHA256 libmpdclient-2.23.tar.xz
# 4A1B6C7F783D8CAC3D3B8E4CBE9AD021C45491E383DE3B893EA4EEDEFBC71607
```

## Shadow CI 验证结果

- 真机: `currentUser@10.62.189.79:2222`
- 隔离 job: `/storage/Users/currentUser/ohos-users/codex/libmpdclient-2.23-1910-shadow-20260807-110329`
- 成功 run: `/storage/Users/currentUser/ohos-test-runs/codex-libmpdclient-libmpdclient-2.23-1910-shadow-ci-r3-20260807-111233-14825`
- 命令: `CI_PACKAGES="archives/l/libmpdclient/2.23" zsh ci/conan/build_and_test.sh`
- 结果:
  - `L0_RESULT=pass`
  - `L1_RESULT=pass`
  - `L2_RESULT=skip: no bin/ dir`
  - `L4_RESULT=pass: no patches`
  - `L5_RESULT=pass`
  - `Build Summary: Total 1, Success 1, Failed 0`
- 消费者测试输出: `libmpdclient API smoke passed`

## 下一步

```sh
CI_PACKAGES="archives/l/libmpdclient/2.23" zsh ci/conan/build_and_test.sh
```

或进入 shadow CI 队列:

```sh
/path/to/run-ohos-shadow-ci.sh archives/l/libmpdclient/2.23
```
