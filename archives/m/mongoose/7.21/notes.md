# mongoose 7.21 适配笔记

## 编译环境
- 构建系统: makefile
- 编译日期: 2026-06-12
- 编译器: clang 15.0.4
- 状态: built

## 编译步骤
```bash
# 1. 下载源码
wget https://github.com/cesanta/mongoose/archive/refs/tags/7.21.tar.gz
tar -xzf 7.21.tar.gz
cd mongoose-7.21

# 2. 编译静态库
make libmongoose.a CC=clang CFLAGS="-O2 -fPIC"

# 3. 编译共享库
make libmongoose.so CC=clang CFLAGS="-O2 -fPIC"

# 4. 安装
cp mongoose.h $HOME/usr/local/include/
cp libmongoose.a $HOME/usr/local/lib/
cp libmongoose.so.7.21 $HOME/usr/local/lib/
ln -sf libmongoose.so.7.21 $HOME/usr/local/lib/libmongoose.so

# 5. ELF 签名（共享库）
python3 $SKILL_ROOT/scripts/ohc-run.py sign-elf $HOME/usr/local/lib/libmongoose.so.7.21
```

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 共享库运行 ELF 签名问题 | OHOS 安全机制 | 推荐使用静态库替代 |
| 2 | mg_http_listen() 共享库模式端口绑定失败 | ELF 签名影响动态库加载 | 使用静态库模式正常 |
| 3 | HTTP 服务器测试 | 需验证核心功能 | 静态库模式全部通过 |

## 依赖版本
- 无必须依赖
- 可选：OpenSSL（SSL/TLS支持）

## 验证结果
### 链接测试
- 链接 libmongoose.a ✅ 静态二进制运行正确
- 链接 libmongoose.so ⚠️ 共享二进制链接成功但运行失败（ELF签名）

### 功能测试（静态库模式）
- MG_VERSION → "7.21" ✅
- mg_match() ✅ 模式匹配正确
- mg_http_reply() ✅ 符号链接时解析
- mg_str 长度计算 ✅ 返回正确长度(11)
- mg_mgr_init() ✅ Manager初始化正确
- mg_http_listen() ✅ HTTP服务器启动（端口19999）
- Server poll (3s) ✅ 服务器运行3秒成功

### 功能测试（共享库模式）
- mg_http_listen() ❌ 端口绑定失败（ELF签名问题）

## 交付物
| 文件 | 说明 |
|------|------|
| mongoose-7.21-ohos-aarch64.tar.gz | 主包 |
| mongoose-7.21-ohos-aarch64-debug.tar.gz | debug 包 |

## 注意事项
- 推荐使用静态库（libmongoose.a）部署，功能完整且稳定
- 共享库 ELF 签名问题为平台限制，非编译问题
- mongoose.h 头文件大小 138KB，包含完整 API 定义