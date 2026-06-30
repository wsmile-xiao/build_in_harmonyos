# libvpx 编译环境配置说明

## 环境依赖

### 1. LD_LIBRARY_PATH 设置

**关键问题**：OHOS SDK 的 lld 链接器依赖 libxml2.so.16，必须将 SDK 的 llvm/lib 路径添加到 LD_LIBRARY_PATH。

```bash
export LD_LIBRARY_PATH="/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib:${LD_LIBRARY_PATH:-}"
```

**失败表现**：
- configure 报错：`Toolchain is unable to link executables`
- config.log 显示：`Error loading shared library libxml2.so.16`

### 2. diff 工具

libvpx 的 configure 脚本需要 diff 工具。确保 GNU diff 已安装：
```bash
# 检查 diff 是否可用
which diff
# 应输出: /storage/Users/currentUser/usr/local/bin/diff 或系统路径
```

### 3. build 目录缺失问题

**现象**：GitHub tarball 解压后可能缺少 build/make/ 目录。

**解决方案**：
```bash
if [ ! -d "$BUILD_SRC_DIR/build/make" ]; then
    cp -r "$BUILD_SRC_ORIG_DIR/build" "$BUILD_SRC_DIR/"
fi
```

## 使用方法

在编译前 source 环境文件：
```bash
source archives/l/libvpx/hints/environment.sh
```

## 配置参数

libvpx 使用自定义 configure 脚本（非标准 autotools）：

```bash
./configure --prefix=$DEFAULT_PREFIX --target=arm64-linux-gcc
```

**关键参数**：
- `--target=arm64-linux-gcc`：指定目标平台（必需）
- `--prefix=$DEFAULT_PREFIX`：安装路径

## 验证环境

运行以下命令验证环境配置正确：
```bash
# 验证链接器
LD_LIBRARY_PATH=/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib \
    /data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin/lld --version

# 验证 diff
diff --version | head -1
```