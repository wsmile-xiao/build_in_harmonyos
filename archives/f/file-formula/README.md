# file-formula

`file-formula` 是 Homebrew 为 `file(1)` 命令使用的特殊公式名（Ruby 中
`File` 是保留类名）。它从官方 `file` 源码构建命令行工具，并使用
`libmagic` 根据文件内容识别文件类型。

## 功能

- 通过 magic 数据库识别文本、可执行文件、归档和多媒体等文件类型。
- 输出 MIME 类型、字符编码和人类可读的文件描述。
- 提供 `file --version`、`file --mime-type` 等标准命令行接口。

## OpenHarmony 适配

- Conan 包名保持为比赛任务名 `file-formula`，避免与已有的
  `file/5.48` 配方混淆。
- 对齐 Homebrew 官方公式：只交付 `file` 命令，`libmagic` 由已发布的
  `file/5.48` Conan 包提供。
- `file/5.48` 的静态 `libmagic.a` 被链接进命令，最终 CLI 不依赖额外
  的 `libmagic.so`。
- CLI 通过 libtool `-all-static` 生成无 ELF 解释器、无 `DT_NEEDED`
  项的 OpenHarmony arm64 可执行文件。
- 补丁使 GNU config 脚本识别 `aarch64-unknown-linux-ohos`，并修复
  HMDFS 上 Autoconf 临时目录的权限问题。

## 依赖

- `file/5.48`：构建时提供 `magic.h`、`libmagic.a`，运行时提供
  `magic.mgc`。
- OpenHarmony NDK：提供静态 libc、libm 和 arm64 交叉工具链。

## 参考

- 上游主页：https://www.darwinsys.com/file/
- 上游源码：https://github.com/file/file
- 官方发布包：https://astron.com/pub/file/file-5.48.tar.gz
- Homebrew 公式：https://formulae.brew.sh/formula/file-formula
