# miniupnpc — HarmonyOS aarch64 预编译包

## 快速安装

### 方式一：使用 install.sh
```bash
curl -fsSL <url>/install.sh | sh -s -- 2.3.3
```

### 方式二：手动安装
```bash
tar xzf miniupnpc-2.3.3-ohos-aarch64.tar.gz -C ~/usr/local
cd ~/usr/local && sh install-miniupnpc-2.3.3.sh
```

安装后需要设置 LD_LIBRARY_PATH：
```bash
export LD_LIBRARY_PATH=$HOME/usr/local/lib:$LD_LIBRARY_PATH
```

## 可用版本

| 版本 | 状态 | 补丁数 | 测试通过 |
|------|------|--------|----------|
| 2.3.3 | success | 0 | 6/6 ✅ |

## 当前版本 (2.3.3) 详情

### 包内容
```
miniupnpc-2.3.3-ohos-aarch64/
├── bin/
│   ├── upnpc              (39KB, UPnP 客户端)
│   ├── upnp-listdevices   (23KB, 设备发现工具)
│   └── external-ip        (脚本, 获取外部 IP)
├── lib/
│   ├── libminiupnpc.a     (82KB, 静态库)
│   ├── libminiupnpc.so.21 (64KB, 动态库)
│   └── libminiupnpc.so    (软链接)
│   └── pkgconfig/
│       └── miniupnpc.pc
├── include/
│   └── miniupnpc/
│       ├── miniupnpc.h
│       ├── miniwget.h
│       ├── upnpcommands.h
│       └── ... (共 10 个头文件)
└── share/
    └── man/
        └── man3/
            └── miniupnpc.3.gz
```

### 包大小
- **主包**: 492KB (miniupnpc-2.3.3-ohos-aarch64.tar.gz)
- **调试包**: 126KB (miniupnpc-2.3.3-ohos-aarch64-debug.tar.gz)

### 编译信息
- **构建系统**: Makefile（无 configure）
- **目标平台**: HarmonyOS aarch64 (HongMeng Kernel 1.12.0)
- **编译器**: clang 15.0.4
- **质量门禁**: PASS ✅
- **补丁数**: 0（无需补丁）

### 测试结果
全部 6 个测试通过：
1. validateminixml ✅
2. validateminiwget ✅
3. validateupnpreplyparse ✅
4. validateportlistingparse ✅
5. validateigddescparse ✅
6. validateaddr_is_reserved ✅

## 环境要求
- HarmonyOS/OpenHarmony aarch64
- 设置 LD_LIBRARY_PATH 或运行 install.sh 自动配置

## 使用示例

### 获取外部 IP 地址
```bash
upnpc -s
# 或使用脚本
external-ip
```

### 添加端口映射
```bash
# 添加 TCP 端口映射
upnpc -a 192.168.1.100 8080 8080 TCP

# 删除端口映射
upnpc -d 8080 TCP

# 列出所有端口映射
upnpc -l
```

### 发现 UPnP 设备
```bash
upnp-listdevices
```

### 编译链接（开发使用）
```bash
# 使用 pkg-config
pkg-config --cflags --libs miniupnpc

# 编译示例
gcc -o myapp myapp.c $(pkg-config --cflags --libs miniupnpc)
```

## 已知限制
1. 动态链接的二进制文件需要设置 LD_LIBRARY_PATH
2. 静态链接版本（upnpc-static）可独立运行

## 更新日志
- **2026-05-06**: 首次编译 2.3.3 版本，全部测试通过