# normalize

`normalize` 是一个音频音量电平归一化命令行工具：测量音频文件的响度并把
音量调整到目标电平，支持 WAV/AIFF/AU/MP3 等格式（经 audiofile 库读多格式）。

## 功能概述

- `normalize`：测量并对音频文件做音量归一化（支持 -qn 仅测量、-q 就地调整）
- `normalize-mp3` / `normalize-ogg`：调用外部转换工具链的辅助脚本（madplay/lame/flac/oggenc）
- 8/16/24-bit PCM 的测试与校验（上游 `make check`，3 个测试用例全通过）

## OHOS 适配

- 2005 版 `config.guess` 不认识 `aarch64:HarmonyOS:*:*`，补丁让其输出
  `aarch64-unknown-linux-gnu`，保证 configure 以 native（非 cross）模式运行，
  从而实测字节序（小端）与类型长度（LP64，long=8）。
- `config.status` 在 HMDFS 上创建临时目录的 `umask 077` 会因属主不同导致
  "Permission denied"，改为 `umask 000`。
- 静态链接的 audiofile 含 C++ 目标文件，C 链接驱动缺 `-lc++`，在 LIBS 末尾注入。
- audiofile 通过老式 `audiofile-config` 脚本被发现（AM_PATH_AUDIOFILE 宏），
  配方在 build 目录生成私有 shim 脚本并注入 PATH/AUDIOFILE_CONFIG。

## 依赖关系

- 编译/运行依赖：`audiofile/0.3.6`（制品仓已发布，提供多格式音频 I/O）
- libmad（MP3 解码）与 xmms 插件为可选，未打包故自动禁用

## 参考资料

- 上游原站（SourceForge projects/normalize，下载不可达）
- 权威源码镜像：https://deb.debian.org/debian/pool/main/n/normalize-audio/
- Homepage: https://savannah.nongnu.org/projects/normalize/
