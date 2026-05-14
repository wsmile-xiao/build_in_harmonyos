# miniupnpc 2.3.3 — OpenHarmony 编译记录

## 基本信息
- **软件名称**: miniupnpc
- **版本**: 2.3.3
- **构建系统**: Makefile（非 autotools，无 configure 脚本）
- **编译平台**: HarmonyOS aarch64 (HongMeng Kernel 1.12.0)
- **编译日期**: 2026-05-06

## 编译指导

### 源码获取
```bash
# 下载源码
wget 'https://miniupnp.tuxfamily.org/files/download.php?file=miniupnpc-2.3.3.tar.gz'
tar xzf miniupnpc-2.3.3.tar.gz
cd miniupnpc-2.3.3
```

### 编译命令
miniupnpc 使用 Makefile 构建，无 configure 脚本。使用 `INSTALLPREFIX` 参数指定安装路径：

```bash
# 编译
make -j$(nproc) INSTALLPREFIX=$HOME/usr/local

# 安装到 staging 目录（打包用）
make install DESTDIR=$HOME/test-install-miniupnpc-2.3.3 INSTALLPREFIX=$HOME/usr/local

# 安装到本地（验证用）
make install INSTALLPREFIX=$HOME/usr/local
```

### 测试验证
```bash
# 运行测试套件
make check

# 测试二进制功能
export LD_LIBRARY_PATH=$HOME/usr/local/lib:$LD_LIBRARY_PATH
$HOME/usr/local/bin/upnpc --help
$HOME/usr/local/bin/upnp-listdevices --help
```

### 注意事项
1. **构建系统**: 该项目使用 Makefile，而非 autotools，无 configure 脚本
2. **安装参数**: 使用 `INSTALLPREFIX` 而非 `--prefix`
3. **动态库运行**: 需设置 `LD_LIBRARY_PATH` 或在 install.sh 中配置
4. **OS 自动识别**: 源码会自动检测为 "HarmonyOS/HongMeng Kernel 1.12.0"

## 补丁清单
本次编译**无需任何补丁**，源码在 HarmonyOS 上直接编译通过。

## 已知限制
1. 动态链接的二进制文件（upnpc、upnp-listdevices）运行时需要设置 `LD_LIBRARY_PATH=$HOME/usr/local/lib`
2. 静态链接的二进制文件（upnpc-static、upnp-listdevices-static）可独立运行

## 功能验证

### 安装产物
- **静态库**: `libminiupnpc.a` (82KB)
- **动态库**: `libminiupnpc.so.21` (64KB) + 软链接 `libminiupnpc.so`
- **头文件**: 10 个（igd_desc_parse.h, miniupnpc.h 等）
- **二进制**: upnpc, upnp-listdevices, external-ip
- **pkg-config**: miniupnpc.pc

### 验证命令
```bash
# 检查 pkg-config
pkg-config --exists miniupnpc && echo "已安装" || echo "未找到"
pkg-config --cflags miniupnpc
pkg-config --libs miniupnpc

# 检查库文件
ls -la $HOME/usr/local/lib/libminiupnpc.*

# 检查二进制
file $HOME/usr/local/bin/upnpc
```

### 测试结果
全部 6 个测试通过：
- validateminixml: XML 解析验证 ✅
- validateminiwget: HTTP wget 功能测试 ✅
- validateupnpreplyparse: UPnP 回复解析测试 ✅
- validateportlistingparse: 端口列表解析测试 ✅
- validateigddescparse: IGD 描述解析测试 ✅
- validateaddr_is_reserved: 地址保留测试 ✅

## 依赖关系
- **编译依赖**: 无（仅需标准 C 库和 socket API）
- **运行依赖**: 无

## 预编译包
- **主包**: miniupnpc-2.3.3-ohos-aarch64.tar.gz (492KB)
- **调试包**: miniupnpc-2.3.3-ohos-aarch64-debug.tar.gz (126KB)
- **安装脚本**: install-miniupnpc-2.3.3.sh