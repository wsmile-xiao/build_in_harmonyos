# libfontenc — OpenHarmony 预编译包

## 软件简介
libfontenc 是 X.Org 的字体编码库，用于处理各种字体编码格式的解析和转换。

## 基本信息
- 软件名称: libfontenc
- 最新版本: 1.1.9
- 构建系统: autotools
- 目标平台: ohos-aarch64
- 源码地址: https://xorg.freedesktop.org/archive/individual/lib/libfontenc-1.1.9.tar.xz

## 快速安装

```bash
# 下载预编译包
curl -LO https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/libfontenc/libfontenc-1.1.9-ohos-aarch64.tar.gz

# 解压并安装
tar xzf libfontenc-1.1.9-ohos-aarch64.tar.gz -C ~/usr/local
cd ~/usr/local/libfontenc-1.1.9-ohos-aarch64 && sh install.sh
```

## 可用版本

| 版本 | 状态 | 补丁数 | 编译日期 |
|------|------|--------|----------|
| 1.1.9 | ✅ success | 3 | 2026-05-06 |

## 补丁清单

### 1.1.9 版本补丁
| 补丁文件 | 说明 |
|----------|------|
| 0001-configure-umask.patch | 修复 HMDFS 临时目录权限问题（umask 077 → 022） |
| 0002-config.guess.patch | 添加 HarmonyOS 系统识别（__OHOS__ LIBC + HarmonyOS case 分支） |
| 0003-config.sub.patch | 添加 ohos-linux 三元组支持 |

## 依赖说明

### 运行依赖
- zlib: 压缩库（预编译包已包含 libz.so）

### 编译依赖
- xproto: X.Org 协议头文件（需手动安装）
- zlib: 已有预编译包

## 编译指导

```bash
# 1. 初始化构建
python3 $SKILL_ROOT/scripts/ohc-run.py init-build libfontenc 1.1.9 \
  --url=https://xorg.freedesktop.org/archive/individual/lib/libfontenc-1.1.9.tar.xz

# 2. 安装 xproto 头文件（首次编译需要）
mkdir -p ~/usr/local/include/X11
# 下载 xproto 并复制头文件...

# 3. 进入源码目录编译
cd ~/builds/libfontenc-1.1.9.work
./configure --prefix=~/usr/local
make -j$(nproc)
make install DESTDIR=~/test-install-libfontenc-1.1.9

# 4. 打包
python3 $SKILL_ROOT/scripts/ohc-run.py package libfontenc 1.1.9

# 5. 完成
python3 $SKILL_ROOT/scripts/ohc-run.py finish libfontenc 1.1.9 success
```

## 已知限制

1. **无测试套件**: 该库没有 `make check` 测试，无法进行自动化功能验证
2. **xproto 依赖**: 需手动安装 X.Org 协议头文件（无预编译包）
3. **编译警告**: encparse.c 有 format string 非字面量警告（不影响功能）

## 功能验证

```bash
# 检查库是否安装成功
pkg-config --cflags fontenc
# 输出: -I~/usr/local/include

pkg-config --libs fontenc
# 输出: -L~/usr/local/lib -lfontenc

# 检查库文件
ls ~/usr/local/lib/libfontenc*
# libfontenc.a  libfontenc.la  libfontenc.so  libfontenc.so.1  libfontenc.so.1.0.0
```

## 知识沉淀

- **E007 变体**: HMDFS 文件系统上 `umask 077` 创建的临时目录具有特殊权限限制，脚本无法写入文件。解决方案是将 configure 中的 umask 改为 022。
- **xproto 手动安装**: 对于无预编译包的 X.Org 基础库，可手动安装头文件并创建 pkg-config 文件来满足依赖检查。