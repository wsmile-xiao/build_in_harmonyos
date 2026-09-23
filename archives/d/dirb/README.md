# dirb

DIRB 是一个 Web 内容字典爆破扫描工具：通过基于词表的暴力枚举，发现 Web 服务器上隐藏的目录、文件与对象。

## 功能概述

- 基于词表（wordlist）对目标 URL 做目录/文件暴力发现（HTTP/HTTPS）
- 可选扩展名拼接（-X/-x）、递归扫描（-r/-R）、静默模式（-S）、请求延迟（-z）
- HTTP 认证（-u）、自定义 User-Agent、NOT_FOUND 页面容错（自动学习 404 特征）
- 附带 gendict（自定义词表生成）与 html2dic（HTML 转词表）两个辅助工具
- 自带多类别词表（common.txt、big.txt、small.txt、vulns/、mutations/ 等，约 1.6MB）

## OHOS 适配

- 唯一外部依赖 libcurl：configure 经 `curl-config` 探测，配方把依赖 curl 包的 bin 目录前置到 conanbuild PATH
- tarball 自带预生成 configure/Makefile.in（automake 1.9.6/autoconf 2.69），无需 autoreconf；configure.ac 无 AC_CANONICAL_HOST，无 config.guess/sub 需求
- clang 默认 `-fno-common` 与上游头文件全局变量定义冲突（variables.h 被 8 个翻译单元包含，链接报 multiple definition）：patch 0001 改 extern + 新增 `src/variables.c` 单点定义
- 默认词表路径 `/usr/share/dirb/...` 在 OHOS 不存在：patch 0002 运行期按可执行文件位置（/proc/self/exe）解析 `<exe_dir>/../share/dirb/wordlists/`；词表装入包内 `share/dirb/wordlists`
- man 页安装：配方内 install shim 覆盖 INSTALL/INSTALL_DATA，不依赖平台 install(1) 的模式位语义
- 上游无任何自动化测试套件；功能性验证由 test_package 承担（本地 loopback HTTP 服务真实扫描）

## 依赖关系

- 编译依赖：curl/8.15.0（conan）
- 运行依赖：libcurl（conan 运行环境注入）

## 参考资料

- 官方主页：https://sourceforge.net/projects/dirb/
- 源码归档：https://downloads.sourceforge.net/project/dirb/dirb/2.22/dirb222.tar.gz
