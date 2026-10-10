# DRAFT：tag archive autotools 包引导——autoreconf -f 保留 OHOS config 脚本

> 草稿（pending-editor-review），配套 .kv 同名成对。拟提升编号由主编确认。

## 错误特征（error_signature）

- `libtoolize: copying file 'aux-build/config.guess'` / `config.sub`（autoreconf -i 日志）
- `config.guess: unable to guess system type`（configure 阶段）
- `Invalid configuration 'aarch64-unknown-linux-ohos': OS 'ohos' not recognized`

## 根因（root_cause）

上游只发 git tag archive（无 release tarball 资产）时源码树没有预生成
configure/Makefile.in，必须 autoreconf 引导。`-i`（安装模式）会让
libtoolize/automake 用 stock 版覆盖 `AC_CONFIG_AUX_DIR` 下的
config.guess/config.sub——stock 版不认识 HarmonyOS，E007 补丁被打回原形。

## 解法（solution）

`autoreconf -f`（不带 -i）+ 源内 E007 补丁先行 + tool_requires
automake/libtool + 生成 configure 的 umask 077 文本修复（E114）。
代码级方案见 .kv `solution` 字段（可复制片段）。

## 降级（fallback）

个别 libtoolize 在 -f 下仍覆盖：autoreconf 后对 config 脚本二次打补丁，
或备份-还原（abiword-plugin-* 的 -fi + 重打路线可对照）。

## 红线

- 禁 `--build=`/`--host=` 传参绕过（E007：误判交叉编译，级联 E064/E061 等）
- conan create 必须同时传 `-pr:h` 与 `-pr:b`（tool_requires 走 build profile）

## 验证（verify_builds）

- 本地 conan create -pr ohos-aarch64 全绿：上游 tinytest 16/16、ctest 1/1、
  消费者脚本断言 9/9
- 线上 CI：见关联 PR（知识库扩展 issue 内链接）
