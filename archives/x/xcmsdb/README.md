# xcmsdb — OpenHarmony 预编译包

## 软件简介
xcmsdb 是 X.Org 的 X 颜色数据库客户端：把 ICC / RGB 颜色特性（`SCREEN_VERSION` 属性）
写入、查询、列出或删除 X server 上的颜色数据库，走 libX11 的 Xcms API。

## 基本信息
- 软件名称: xcmsdb
- 适配版本: 1.0.7
- 构建系统: autotools（上游 tarball 已内置生成的 `configure`）
- 目标平台: ohos-aarch64
- 源码地址: https://xorg.freedesktop.org/archive/individual/app/xcmsdb-1.0.7.tar.gz
- 上游主页: https://gitlab.freedesktop.org/xorg/app/xcmsdb
- 许可: MIT

## 使用方式
```bash
# 通过 conan 消费本配方（在 build_in_harmonyos 仓库内）
conan install --requires=xcmsdb/1.0.7@ohpcd/stable -r=ohpcd \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
# 产物为 bin/xcmsdb
xcmsdb -version
xcmsdb -query            # 需要可访问的 X server
xcmsdb datafiles/sample1.dcc
```

## 可用版本

| 版本 | 状态 | 说明 |
|---|---|---|
| 1.0.7 | built | HarmonyOS PC 上 `conan create` 通过，`test_package` 5 条无头断言全过；真实写入 X server 的功能路径需 X 会话，未验证（详见 1.0.7/notes.md） |

## 适配要点
- `config.guess` / `config.sub` 补丁识别 HarmonyOS 与 `ohos` 三元组（不写死 `--build/--host`，
  `config.log` 中 `host='aarch64-unknown-linux-ohos'` 即补丁真实生效的证据）
- HMDFS 补丁：`configure` 在 `pwd`（`getcwd`）失败时回退 `$PWD`，`config.status` 临时目录
  `umask 077 → 022`
- pkg-config 视图：`tool_requires(util-macros)` + `PkgConfigDeps` + `VirtualBuildEnv`
- OHOS 下把 Makefile 的 `INSTALL` 重定向到 cp/mkdir shim（HMFS 上带 `-c` 的 install 会失败）
