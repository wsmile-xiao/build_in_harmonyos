# msdl

msdl（Media Stream DownLoader）是多媒体流下载命令行工具，支持
HTTP/FTP/RTSP/MMS/MMST/MMSH/SDP 协议。2010 年的纯 C 实现，仅依赖
libc 与 POSIX socket，无任何第三方库依赖。

## HarmonyOS 适配

- 版本 `1.2.7-r2` 以 application 形式打包，面向 OHOS `armv8`（native
  编译，不传交叉三元组）。
- Autotools 构建；configure 的 umask 077 → 022 内联修复（E129 复用
  方案，零补丁文件）。
- 2010 年代码语义兼容：`-fcommon`（头文件 tentative definitions）+
  `-fgnu89-inline`（url.h 内联函数无 extern 分离定义）。
- 许可证 GPL-2.0-or-later（以 src/*.c 文件头为准；顶层 COPYING 误放
  GPLv3 全文，为上游打包错误）。

## 依赖关系

- 编译期/运行期均无第三方库依赖（libc + POSIX socket 自足）。
- 产物仅 `bin/msdl` 与 man 手册页。

## 参考资料

- 上游主页: <http://msdl.sourceforge.net/>
