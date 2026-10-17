# mp3check

mp3check 检查音频 MPEG layer 1、2、3 (*.mp3) 文件的一致性 (头部与 CRC)
与异常, 并能以多种格式列出逐文件参数。它是纯命令行工具, 不提供库接口。

## OHOS 适配

- 构建官方 0.8.7 发布的 tarball, 不修改源码。
- 构建系统为 plain Makefile (上游 `configure` 仅 echo TARGET, 为空操作, 跳过)。
- 通过命令行 `make CXX="clang++"` 覆盖 Makefile 硬编码的 `g++` (**不传 `CC`**, 令 Makefile 第 11 行 `CC = $(CXX)` 别名生效; 隐式链接规则用 `$(CC)` 链接, 走 C++ 驱动 `clang++` 自动加 `-lc++`/`-lc++abi`; 若传 `CC=clang` 会破坏别名, 致 libc++ EH 符号未定义), 无需打补丁。
- 使用 `-std=c++98` 降级语言标准, 解决 `tstring.cc` 中 placement-new 常量表达式模式
  在现代 clang C++17 默认下的硬错误。
- 使用 `make -j1` 串行构建, 避免首次构建时依赖生成规则 (`.dep.*` include) 的竞态。
- 上游无测试套件 (Makefile 无 check 目标, 源码树无 test 文件); 消费者侧功能测试
  由 `test_package` 提供: CLI 可运行、正常/可解析输入、非法输入、非法路径, 全部验证
  exit code 与关键输出。
- 测试 fixture 从文档化的 MPEG 头部字节 `0xFF 0xFB 0x90 0x00` 合成 6 帧最小流
  (满足上游 MIN_VALID=6 连续头阈值), 不提交未知二进制。

## 依赖

无依赖 (独立 C++ 程序, 仅 libc/libm)。

## License

GPL-2.0-or-later (COPYING 为 GPLv2 文本; 版权声明含 "version 2 or (at your
option) any later version", 与 Debian copyright 文件一致)。

## 参考

- https://code.google.com/archive/p/mp3check/
- https://storage.googleapis.com/google-code-archive-downloads/v2/code.google.com/mp3check/mp3check-0.8.7.tgz
