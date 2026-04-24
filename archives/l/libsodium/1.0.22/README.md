# libsodium 1.0.22 — OpenHarmony 编译记录

## 基本信息

| 项目 | 值 |
|------|-----|
| 软件 | libsodium |
| 版本 | 1.0.22 |
| 构建系统 | autotools |
| 目标平台 | ohos-aarch64 |
| 状态 | ⚠️ partial（静态库可用） |
| 编译日期 | 2026-04-24 |
| 源码地址 | https://github.com/jedisct1/libsodium/releases/download/1.0.22-RELEASE/libsodium-1.0.22.tar.gz |

## 编译指导

### 环境准备
```bash
# 设置编译环境
export OHOS_SDK_ROOT=/path/to/ohos-sdk
export CC=aarch64-linux-ohos-gcc
export AR=aarch64-linux-ohos-ar
export RANLIB=aarch64-linux-ohos-ranlib
```

### 构建步骤
```bash
# 1. 解压源码
tar xzf libsodium-1.0.22.tar.gz
cd libsodium-1.0.22

# 2. 应用补丁
patch -p1 < ../patches/0001-build-aux-config.guess.patch
patch -p1 < ../patches/0002-build-aux-config.sub.patch

# 3. 配置（建议使用 VPATH 构建）
mkdir build && cd build
../configure --prefix=/usr/local --host=aarch64-linux-ohos

# 4. 编译
make -j$(nproc)

# 5. 安装
make DESTDIR=/path/to/staging install
```

### 注意事项
- ⚠️ **HMDFS 限制**：在 HMDFS 文件系统上 configure 可能失败，建议在 `$TMPDIR` 中使用 VPATH 构建
- ⚠️ **动态库问题**：测试阶段动态库加载失败，建议使用静态库链接

## 补丁清单

| 序号 | 文件名 | 用途 |
|------|--------|------|
| 0001 | 0001-build-aux-config.guess.patch | 添加 HarmonyOS/__OHOS__ 系统识别，生成正确的目标三元组 |
| 0002 | 0002-build-aux-config.sub.patch | 添加 ohos-linux 三元组支持 |

### 补丁详情

**0001-build-aux-config.guess.patch**
- 在 `#if defined(__ANDROID__)` 后添加 `#elif defined(__OHOS__)` 检测
- 添加 `*:HarmonyOS:*:*` case 分支处理 HarmonyOS 系统
- 输出格式：`{machine}-unknown-linux-ohos`

**0002-build-aux-config.sub.patch**
- 添加 `ohos-linux` 三元组解析支持
- 使 autotools 能正确识别 `*-unknown-linux-ohos` 目标

## 已知限制

### 1. 动态库测试失败
- **现象**：101 个测试用例全部失败，报错 `Error loading shared library libsodium.so.26`
- **根因**：HarmonyOS 对动态库加载有特殊限制，即使设置 `LD_LIBRARY_PATH` 也无法加载
- **影响**：动态库存在兼容性问题
- **解决**：使用静态库链接方式

### 2. HMDFS 临时文件权限
- **现象**：configure 时 `config.status` 报错 `can't create ./confXXXXXX/subs1.awk: Permission denied`
- **根因**：HMDFS 文件系统限制临时子目录创建
- **解决**：使用 VPATH 构建（在 `$TMPDIR` 中构建）

## 功能验证

### 静态库验证
```bash
# 编译测试程序（静态链接）
cat > test_sodium.c << 'EOF'
#include <sodium.h>
#include <stdio.h>
int main() {
    if (sodium_init() < 0) {
        printf("sodium_init failed\n");
        return 1;
    }
    printf("libsodium version: %s\n", sodium_version_string());
    printf("test passed\n");
    return 0;
}
EOF

aarch64-linux-ohos-gcc -o test_sodium test_sodium.c \
    -I/path/to/pkg-libsodium-1.0.22/include \
    -L/path/to/pkg-libsodium-1.0.22/lib \
    -lsodium -static

./test_sodium
# 预期输出：
# libsodium version: 1.0.22
# test passed
```

### 加密功能测试
```bash
# 测试随机数生成
# 测试哈希函数
# 测试签名验证
```

## 交付物清单

| 文件 | 大小 | 说明 |
|------|------|------|
| libsodium-1.0.22-ohos-aarch64.tar.gz | 1.5MB | 预编译包（Release） |
| libsodium-1.0.22-ohos-aarch64-debug.tar.gz | - | 预编译包（Debug，含调试符号） |
| install-libsodium-1.0.22.sh | - | 安装脚本 |

## 参考资料
- [libsodium 官方文档](https://libsodium.gitbook.io/doc/)
- [archive-spec.md](../../../references/archive-spec.md) - 归档规范
- [PROGRESS.md](./PROGRESS.md) - 完整编译进展记录