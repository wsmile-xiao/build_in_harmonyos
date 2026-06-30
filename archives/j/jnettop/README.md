# jnettop

## 简介

jnettop是一个网络流量监控工具，使用ncurses提供实时文本界面，显示各网络连接的带宽使用情况。类似于top命令的网络版。

## 功能概述

- 实时显示网络连接流量
- 按源/目的地址、端口分类统计
- 显示带宽使用（bytes/packets per second）
- 支持自定义显示格式（CSV/TSV）
- 支持内容过滤和地址解析
- ncurses文本界面，适合终端环境

## OHOS 适配

### 适配要点

1. **libpcap依赖问题**
   - cmd-pkgs的预编译libpcap来自Alpine Linux（musl libc）
   - musl编译的静态库缺少`ether_hostton`符号
   - **解决方案**：手动编译libpcap 1.10.5
   - 需要添加平台适配补丁处理sockaddr_storage重复定义

2. **HMDFS临时文件限制**
   - autotools的configure脚本使用`mktemp -d ./confXXXXXX`
   - 鸿蒙HMDFS文件系统不允许此类临时文件操作
   - **解决方案**：
     - 在`~/tmp`目录编译（避开HMDFS）
     - 修改configure的umask：`sed -i 's/umask 077/umask 022/g' configure`

3. **运行时库路径**
   - 动态链接libpcap.so需要设置库路径
   - **解决方案**：`export LD_LIBRARY_PATH=$HOME/usr/local/lib`

4. **网络权限**
   - 需要CAP_NET_RAW权限捕获网络流量
   - 使用root或`setcap cap_net_raw+ep`设置权限

### 已知问题

| 问题 | 状态 | 说明 |
|------|------|------|
| HMDFS临时文件限制 | 已解决 | 在~/tmp目录编译 |
| libpcap musl兼容性 | 已解决 | 手动编译libpcap |
| G0干净构建验证 | 待验证 | 需在标准Linux环境重跑 |

## 依赖

### 编译依赖
- **libpcap** ≥ 1.10（网络捕获库，需要手动编译）
- **ncurses** ≥ 6.0（终端显示库）
- **glib-2.0** ≥ 2.0（工具库，系统预装）

### 运行依赖
- libpcap.so（动态库）
- libncurses.so
- glib-2.0相关库

## 功能验证

```bash
# 设置库路径
export LD_LIBRARY_PATH=$HOME/usr/local/lib

# 查看版本
jnettop --version

# 查看帮助
jnettop --help

# 监控指定网卡（需要root权限）
sudo jnettop -i eth0

# 使用文本输出模式
jnettop --display text -t 10
```

## 编译示例（0.13.0）

```bash
# 1. 准备编译目录（避开HMDFS）
mkdir -p ~/tmp/jnettop-build
cd ~/tmp/jnettop-build
cp -r ~/builds/jnettop-0.13.0/* .

# 2. 修改umask设置
sed -i 's/umask 077/umask 022/g' configure

# 3. 设置环境变量
export PKG_CONFIG_PATH="$HOME/usr/local/lib/pkgconfig"
export CFLAGS="-I$HOME/usr/local/include"
export LDFLAGS="-L$HOME/usr/local/lib"
export LD_LIBRARY_PATH="$HOME/usr/local/lib"

# 4. Configure
./configure --prefix=$HOME/usr/local

# 5. Make
make -j2

# 6. Install
make install
```

## 参考

- **项目主页**: https://sourceforge.net/projects/jnettop/
- **源码下载**: https://downloads.sourceforge.net/project/jnettop/jnettop/0.13/jnettop-0.13.0.tar.gz
- **手册页**: jnettop(8)
- **HMDFS解决方案**: `/storage/Users/currentUser/Documents/hmdfs.txt`
- **libpcap适配**: `archives/j/jnettop/0.13.0/notes.md`

---

*文档更新: 2026-06-12*
*版本: 0.13.0*