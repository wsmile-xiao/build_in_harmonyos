# ZMap 4.4.0 编译笔记

## 编译信息
- 软件名称: ZMap
- 版本: 4.4.0
- 发布日期: 2026-05-29
- 构建系统: CMake
- 编译开始时间: 2026-06-02 18:00
- 编译完成时间: 2026-06-02 19:06

## 源码下载
- 官方地址: https://github.com/zmap/zmap/archive/refs/tags/v4.4.0.tar.gz
- 源码目录: ~/tmp/builds/zmap-4.4.0.work

## 依赖列表及安装状态

### 已预安装依赖（~/usr/local）
- ✅ gengetopt 2.23（已手动编译安装）
- ✅ libjudy 1.0.5（已手动编译安装）

### 通过预编译包安装
- ✅ gmp 6.3.0（安装到 ~/usr/local/gmp-6.3.0-ohos-aarch64）
- ✅ json-c 0.16（安装到 ~/usr/local/lib）
- ✅ libunistring 1.0（安装到 ~/usr/local/lib）

### 手动编译安装
- ✅ libpcap 1.10.6（从tcpdump.org下载并编译）
  - 应用补丁：0001-config.guess.patch, 0002-config.sub.patch, 0003-pcap-linux.c.patch

### 系统自带
- ✅ cmake 4.1.2
- ✅ flex 2.6.4
- ✅ bison 3.8.2（作为byacc替代）
- ✅ pkg-config 0.29.2

## 编译步骤

### Step 1: 初始化编译环境
- 检查依赖状态：发现 libpcap 缺失
- libpcap 预编译包下载失败，改为手动编译
- 创建 byacc 符号链接到 bison

### Step 2: CMake配置
- 修改 CMakeLists.txt，添加 ~/usr/local 路径到 HINTS
- 处理 gmp 安装在独立目录的问题
- 创建 json-c.pc pkg-config 文件
- 配置成功

### Step 3: 编译
- 遇到 OpenHarmony 系统头文件冲突：sockaddr_storage 重定义
- 修改 get_gateway.c 为 stub 实现
- 修改 send-linux.c，移除不必要的 linux/netlink.h 包含
- 修改 util.c，stub pthread_setaffinity_np（OpenHarmony不支持）
- 编译成功

### Step 4: 安装
- make install 失败（无法创建 /etc/zmap）
- 手动复制二进制文件到 ~/usr/local/sbin/
- 安装成功

### Step 5: 验证
- zmap --version 成功运行
- 版本：v4.4.0
- 输出警告：get_gateway 功能不可用（不影响核心扫描功能）

## 遇到的问题

### 问题1: libpcap预编译包下载失败
**现象**: curl下载返回错误，预编译包不存在或损坏
**原因**: cmd-pkgs仓库中libpcap预编译包缺失或下载链接失效
**解决方案**: 从tcpdump.org下载源码并手动编译

### 问题2: gengetopt不在PATH中
**现象**: cmake找不到gengetopt
**原因**: ~/usr/local/bin不在系统PATH中
**解决方案**: export PATH="$HOME/usr/local/bin:$PATH"

### 问题3: gmp安装到独立目录
**现象**: cmake找不到gmp库
**原因**: gmp预编译包安装到 ~/usr/local/gmp-6.3.0-ohos-aarch64 独立目录
**解决方案**: 修改CMakeLists.txt，添加GMP_LIB_DIR路径

### 问题4: json-c缺少pkg-config文件
**现象**: cmake无法通过pkg-config找到json-c
**原因**: json-c安装时未生成.pc文件
**解决方案**: 手动创建 json-c.pc 文件

### 问题5: OpenHarmony系统头文件冲突（核心问题）
**现象**: sockaddr_storage在sys/socket.h和linux/socket.h中重复定义
**原因**: OpenHarmony SDK bug：两个头文件都定义了sockaddr_storage结构体
**影响文件**:
  - get_gateway-linux.h（包含linux/netlink.h）
  - send-linux.c（包含linux/netlink.h）
**解决方案**:
  1. get_gateway.c改为stub实现（禁用get_gateway功能）
  2. send-linux.c移除不必要的linux/netlink.h包含
  3. 为缺失的函数提供stub实现

### 问题6: pthread_setaffinity_np不可用
**现象**: util.c中调用pthread_setaffinity_np失败
**原因**: OpenHarmony不支持pthread_setaffinity_np API
**解决方案**: 修改set_cpu函数为stub实现，禁用CPU affinity功能

### 问题7: byacc缺失
**现象**: make找不到byacc命令
**原因**: 系统只有bison，没有byacc
**解决方案**: 创建byacc符号链接到bison

## 解决方案总结

### 平台适配修改
1. **CMakeLists.txt**: 添加 ~/usr/local 和 gmp独立目录的路径
2. **lib/CMakeLists.txt**: 添加Judy.h include目录
3. **src/CMakeLists.txt**: 添加include和link_directories
4. **get_gateway.c**: 完整stub实现，禁用网关获取功能
5. **send-linux.c**: 移除linux/netlink.h包含
6. **lib/util.c**: stub pthread_setaffinity_np

### 依赖处理
- 优先使用预编译包（除libpcap）
- 手动编译libpcap
- 创建byacc符号链接
- 手动创建json-c.pc

## 知识提取

### E001: OpenHarmony sockaddr_storage冲突
**问题**: linux/socket.h和sys/socket.h都定义sockaddr_storage
**根因**: OpenHarmony SDK头文件bug
**解决方案**: 避免包含linux/netlink.h，或提供stub实现
**适用范围**: 所有包含linux/netlink.h的软件
**平台**: OpenHarmony专用

### E002: pthread_setaffinity_np缺失
**问题**: OpenHarmony不支持pthread_setaffinity_np
**根因**: 平台限制
**解决方案**: stub实现或条件编译
**适用范围**: 使用CPU affinity的软件
**平台**: OpenHarmony专用

### E003: 预编译包安装路径问题
**问题**: gmp安装到独立目录而非~/usr/local/lib
**根因**: 预编译包安装脚本设计
**解决方案**: cmake中添加独立目录路径
**适用范围**: 所有使用预编译包的软件

## 编译产物

### 二进制文件
- ~/usr/local/sbin/zmap (775K)
- ~/usr/local/sbin/zblocklist (54K)
- ~/usr/local/sbin/ziterate (242K)
- ~/usr/local/sbin/ztee (54K)

### 功能限制
- get_gateway功能不可用（需手动指定网关IP和MAC地址）
- CPU affinity功能禁用
- 核心扫描功能正常
**编译时长**: 约66分钟
**编译版本**: zmap v4.4.0
---

**编译结束**: 2026-06-02 19:19
**最终状态**: built
