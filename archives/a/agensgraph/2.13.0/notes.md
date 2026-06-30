# agensgraph 2.13.0 编译笔记

## 编译环境

- **日期**: 2026-06-03
- **编译器**: clang 15.0.4
- **构建系统**: autotools
- **平台**: aarch64-unknown-linux-ohos

## 源码信息

- **URL**: https://github.com/bitnine-oss/agensgraph/archive/refs/tags/v2.13.0.tar.gz
- **基础**: PostgreSQL 13.8

## 编译步骤

### 1. 初始化

```bash
python3 scripts/ohc-run.py init-build agensgraph 2.13.0 --url=https://github.com/bitnine-oss/agensgraph/archive/refs/tags/v2.13.0.tar.gz
```

### 2. 替换 config.guess/config.sub (E072)

```bash
cp /storage/Users/currentUser/usr/local/share/autoconf/build-aux/config.guess config/
cp /storage/Users/currentUser/usr/local/share/autoconf/build-aux/config.sub config/
chmod +x config/config.guess config/config.sub
```

### 3. 安装依赖 readline

```bash
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- readline 8.2
```

### 4. 修改 configure umask (E011)

```bash
sed -i 's/umask 077/umask 022/g' configure
```

### 5. Configure

```bash
export TMPDIR=/storage/Users/currentUser/tmp
export LD_LIBRARY_PATH=/storage/Users/currentUser/usr/local/lib:$LD_LIBRARY_PATH
./configure --prefix=/storage/Users/currentUser/usr/local --with-includes=/storage/Users/currentUser/usr/local/include --with-libraries=/storage/Users/currentUser/usr/local/lib
```

### 6. Make (单线程)

```bash
make -j1  # HMDFS 不支持 mkfifo
```

### 7. Install

```bash
make install DESTDIR=/storage/Users/currentUser/tmp/test-install-agensgraph-2.13.0
```

### 8. 打包 (zip 格式)

```bash
cd /storage/Users/currentUser/tmp/test-install-agensgraph-2.13.0/storage/Users/currentUser/usr/local
zip -r agensgraph-2.13.0-ohos-aarch64.zip .
```

## 问题与方案

### 问题 1: config.guess 不识别 OHOS (E072)

- **现象**: `config.guess: unable to guess system type`
- **根因**: 旧版 config.guess 不支持 OHOS 平台
- **方案**: 替换为最新版 config.guess/config.sub
- **知识**: E072

### 问题 2: 缺少 readline (依赖缺失)

- **现象**: `configure: error: readline library not found`
- **根因**: readline 未安装
- **方案**: 安装预编译包 readline 8.2

### 问题 3: LD_LIBRARY_PATH 未设置

- **现象**: `Error loading shared library libreadline.so.8`
- **根因**: 运行时库路径未设置
- **方案**: 设置 `LD_LIBRARY_PATH=/storage/Users/currentUser/usr/local/lib`

### 问题 4: config.status 权限错误 (E011)

- **现象**: `config.status: can't create ./confXXX/subs1.awk: Permission denied`
- **根因**: HMDFS 的 umask 077 权限问题
- **方案**: 修改 configure 中 `umask 077` 为 `umask 022`
- **知识**: E011

### 问题 5: make mkfifo 失败

- **现象**: `make: jobserver mkfifo: Operation not permitted`
- **根因**: HMDFS 不支持 mkfifo
- **方案**: 使用单线程编译 `make -j1`

### 问题 6: ustar 路径长度限制

- **现象**: `tar: ustar header field is too small for file ...`
- **根因**: HMDFS 的 ustar 格式不支持长路径
- **方案**: 使用 zip 格式打包预编译包

## 验证结果

- **编译**: ✅ 成功
- **安装**: ✅ 成功
- **打包**: ✅ 成功 (zip格式)
- **功能**: ⚠️ 基础功能验证通过，完整功能测试受限

## 交付物

- **补丁**: 3 个 (0001, 0002, 0003)
- **预编译包**: agensgraph-2.13.0-ohos-aarch64.zip (13MB)
- **状态**: built

## 注意事项

- 预编译包使用 zip 格式（而非 tar.gz）
- 编译需单线程（make -j1）
- 需设置 LD_LIBRARY_PATH