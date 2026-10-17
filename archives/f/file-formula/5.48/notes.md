# file-formula 5.48 适配笔记

## 编译环境

- 构建系统：Autotools
- 编译日期：2026-07-30
- 目标：OpenHarmony 6.0 / arm64
- 编译器：Clang，目标三元组 `aarch64-linux-ohos`
- 状态：built

## 包身份与依赖决策

比赛任务名是 Homebrew 的 `file-formula`。该名称并非另一份上游源码：
Homebrew 因 Ruby 中 `File` 是保留类名而使用此名称，并把 `file(1)` CLI
与 `libmagic` 拆包。

仓库已有 `file/5.48`，且 W0 使用以下命令确认其 OHOS/armv8 recipe 和
binary 均已发布：

```bash
conan download "file/5.48" -r=ohpcd --only-recipe
conan download "file/5.48" -r=ohpcd
```

`libmagic/5.48` 并不存在，因此本配方显式依赖 `file/5.48`，使用其
`magic.h`、`libmagic.a` 和 `magic.mgc`。新包只安装自身构建的 `file`
CLI，不复制依赖包中的同名二进制。

## 编译流程

1. 从 Astron 官方站点下载 `file-5.48.tar.gz` 并校验 SHA256。
2. 应用 GNU config 和 HMDFS 临时目录补丁。
3. `AutotoolsDeps` 注入 `file/5.48` 的头文件和静态库路径。
4. OHOS 配置缓存指定 `ac_cv_func_fmtcheck=no`，使用上游随源码提供且
   有正确声明的替代实现。
5. 配置时关闭不属于该公式依赖闭包的压缩库、seccomp 和 landlock。
6. 用 `file_DEPENDENCIES=`、依赖包中 `libmagic.a` 的绝对路径以及
   libtool `-all-static` 构建 CLI。
7. 可运行构建执行上游 `make check` 后，再次链接公式 CLI。
8. 上游 `install-exec` 与 `install-binPROGRAMS` 均会拉起内建
   libmagic，因此打包时直接复制已经外链的 `src/file`，再生成手册页。

## OpenHarmony 适配

| 问题 | 根因 | 处理 |
|---|---|---|
| `config.sub` 拒绝 linux-ohos | 上游 GNU config 快照缺少 OHOS 枚举 | 增加 `ohos*` 和 `linux-ohos*` |
| 原生 OHOS 无法由 config.guess 识别 | 缺少 HarmonyOS uname 分支 | 输出 `aarch64-unknown-linux-ohos` |
| HMDFS 上 configure 临时文件不可读 | `umask 077` 与挂载权限组合 | 仅将相关临时目录 umask 改为 022 |
| `softmagic.c` 将 `fmtcheck()` 返回值当作 `int` | `AutotoolsDeps` 注入的 `file/5.48` 静态库导出私有符号但无公共原型，`AC_REPLACE_FUNCS` 仅链接探测后误定义 `HAVE_FMTCHECK` | 注入 `ac_cv_func_fmtcheck=no`，编译上游 `src/fmtcheck.c` 并保留 `file.h` 原型 |
| 公式 CLI 与依赖均提供 `file` | PATH 测试可能误跑依赖包 | 消费者测试使用新包 package folder 下的绝对路径 |
| `install-binPROGRAMS` 仍编译内建库 | 上游显式依赖 `install-libLTLIBRARIES` | 不调用安装目标，直接复制已验证的 CLI |

## 测试边界

- 上游 `tests/Makefile.am` 的 `check-local` 使用 `set -e` 遍历精确的
  83 个 `tests/*.testfile`；`tests/test.c` 是这些用例共用的驱动程序，
  不另计为第 84 个测试。本地可执行环境运行 `make -j1 check`，结果
  83/83 通过、0 失败。
- Homebrew `file-formula` 官方公式的 `test do` 另有 1 项下游集成冒烟：
  使用官方 `test.mp3` 夹具执行 `file`。本地可执行环境已按原命令执行，
  结果 1/1 通过；夹具 SHA256 为
  `ed6179bca746797a903a8ea92174a7babeffc9a0d257fe6b504573f82c8f4408`。
- `build()` 在 build/host 可直接执行时运行上游 `make check`。前一已验证
  HEAD `e084d09de` 的 OHPCD Build #11606（CI 12282）通过；本次提交新增
  `UPSTREAM_FILE_TESTS_RESULT` 的 expected/executed/passed/failed 精确日志，
  以新 HEAD 的 CI 回执作为最终远程证据。
- 最终包是静态 `ELF64 AArch64 EXEC`，无解释器且无 `DT_NEEDED`。
- `test_package` 使用新包 `bin/file` 的绝对路径，并通过 qemu-user
  10.2.1 实际执行 `--version`、MIME、编码和文本描述 4 项断言，结果
  4/4 通过。
- QEMU 结果覆盖 arm64 指令、静态 ABI 和 CLI 行为，不替代真机系统
  集成验证。

## 仓库验证与 Worker 边界

- 直接 Linux → OHOS 交叉 `conan create` 已成功，完整包引用为
  `file-formula/5.48#ae60f8163f882990af1ae8c868fb8782:d41b1c5df0bdbe502fa58a09ed9efc774ee160a6#412b1228d38ad981f74037bfa7d98339`。
- R34 负向验证临时移除了上述精确包的 `bin/file`。消费者测试以
  `FileNotFoundError: packaged file CLI not found` 按预期失败；恢复同一文件后
  SHA256 保持不变，消费者测试再次通过。
- 当前证据包括：上游回归套件 83/83、Homebrew 公式集成冒烟 1/1、
  包内静态 OHOS CLI 的 QEMU 消费者断言 4/4，以及 OHPCD CI 12282
  通过。真机 OpenHarmony PC 系统集成验收仍是外部边界。

---

**编译结束**: 2026-07-30 02:35
**最终状态**: built
