# commoncpp2

## 软件描述
GNU Common C++ 2 是一个可移植的 C++ 框架，提供线程、套接字、实时网络开发等基础能力。本项目将其适配到 HarmonyOS PC（OHOS）平台。

## 功能概述
- **线程与同步**：Thread、Mutex、Semaphore 等线程原语封装
- **网络编程**：TCP/UDP 套接字、网络地址解析
- **实时支持**：定时器、事件循环、信号处理
- **通用工具**：字符串处理、配置文件解析、管道通信

## OHOS 适配

### 构建方式
- **构建系统**：autotools（configure + make）
- **交叉编译**：`--build=aarch64-unknown-linux-ohos --prefix=/usr --disable-shared`
- **编译器**：clang 15（C++98 老代码——`-std=c++98 -fpermissive`）

### 关键攻坚点
1. **旧版 config.guess/config.sub（2007 年）不识别 ohos**：config.guess 插 `linux-ohos` 分支、config.sub 加 `linux-ohos*`（实测识别 aarch64-unknown-linux-ohos）
2. **C++98 兼容**：`-fpermissive` + `string.h` friend 声明默认参数 patch（现代 clang 报错）
3. **鸿蒙 libc 差异**：无 `pthread_testcancel`（stub 头 + `-include` 注入）、timespec 无 `tv_usec`（改 `tv_nsec`）、netfilter 头链触发 sockaddr_storage 重定义（注释 include）
4. **config.status mktemp 沙箱限制**：TMPDIR 指可写目录 + mktemp 模板改 `${TMPDIR}`（同 dpkg——见 SKILL `autotools-config-status-mktemp-sandbox`）

### 与 Linux 的差异
- 静态库打包（--disable-shared）
- 取消点检测为 stub 空实现（鸿蒙 libc 无 pthread_testcancel）

## 依赖关系
| 依赖 | 版本 | 用途 |
|------|------|------|
| zlib | 1.3.1 | 压缩数据 |
| openssl | 1.1.1w | 加密/TLS |

## 版本记录
| 版本 | 状态 | 编译日期 | 备注 |
|------|------|---------|------|
| 1.8.1 | built | 2026-08-27 | Conan 配方适配 |

## 参考资料
- 官网: https://www.gnu.org/software/commoncpp/
- 源码: https://ftp.gnu.org/gnu/commoncpp/
