# bind 9.20.22 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-05-19
- 编译器: clang/clang++
- 状态: built (预编译包已生成)

## TMPDIR设置（关键）
```bash
export TMPDIR=/data/storage/el2/base/cache
```

## 依赖编译

### liburcu 0.14.1
- ✅ 已编译并安装到 ~/usr/local/lib
- 预编译包: 2.5MB

### libuv 1.52.1
- ✅ 重新编译，修改visibility为default
- 修复内部符号问题（uv__platform_loop_init等）
- 预编译包已生成

### OpenSSL 1.1.1w
- ✅ 预编译包已安装

## 编译配置

```bash
./configure --prefix=$HOME/usr/local --without-libnghttp2
make -e -j2
make install DESTDIR=~/tmp/test-install-bind-9.20.22
make install  # 本地安装
```

## 平台适配问题

### 1. TMPDIR问题
- 原TMPDIR指向不存在路径
- 解决：设置TMPDIR=/data/storage/el2/base/cache

### 2. config.guess/config.sub
- 添加HarmonyOS识别
- 识别为：aarch64-unknown-linux-ohos

### 3. interfacemgr.c条件编译
- HarmonyOS不支持RTM_NEWADDR/RTM_DELADDR
- 使用USE_ROUTE_SOCKET条件编译

### 4. libuv visibility问题
- libuv默认visibility=hidden隐藏内部符号
- 修改为visibility=default暴露符号

### 5. 禁用HTTP/2功能
- libnghttp2依赖缺失
- 使用--without-libnghttp2参数

## 验证结果

```bash
$ named -v
BIND 9.20.22 (Stable Release) <id:e609907>

$ dig -v
DiG 9.20.22

$ host -V
host 9.20.22
```

## ELF签名验证

所有核心二进制已签名：
- ✅ named: .codesign section present
- ✅ dig: .codesign section present
- ✅ nslookup: .codesign section present
- ✅ host: .codesign section present
- ✅ rndc: .codesign section present
- ✅ delv: .codesign section present

## 预编译包信息

- 文件: bind-9.20.22-harmonyos.tar.gz
- 大小: 1.8M
- 内容: 
  - sbin/named (DNS服务器)
  - bin/dig, nslookup, host, rndc, delv等工具
  - lib/库文件
  - include/头文件

## 注意事项

- named位于~/usr/local/sbin（不是bin）
- 硬链接(named-compilezone)已改为符号链接
- HTTP/2功能已禁用，不影响核心DNS功能
- 动态链接musl libc，需确保系统有musl运行时

---

**编译结束**: 2026-05-19 18:58
**最终状态**: built