# gambit v4.9.5 适配笔记

## 编译环境
- 构建系统: autotools（标准 configure 脚本）
- 编译日期: 2026-05-27
- 编译器: clang 15.0.4
- 状态: built（编译成功，待打包发布）

## 编译步骤

1. **下载源码**：使用 ghfast.top 国内镜像从 GitHub 下载 gambit-v4.9.5.tar.gz
2. **初始化**：`ohc-run.py init-build gambit v4.9.5`
3. **创建编译器软链接**：`ln -s clang cc && ln -s clang++ gcc`
4. **配置**：`./configure --prefix=$DEFAULT_PREFIX`
   - 成功识别平台：aarch64-unknown-linux-ohos
5. **编译核心**：`make core`（约 520 秒）
6. **编译模块**：`make modules`（约 1080 秒）
7. **安装**：`make install DESTDIR=$TEST_PREFIX`
8. **本地安装**：`make install`（安装到 ~/usr/local）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess/config.sub 不存在 | gambit 源码未包含平台检测脚本 | 手动创建支持 ohos 的 config.guess/config.sub |
| 2 | C 编译器 cc/gcc 缺失 | 系统只有 clang，无 cc 软链接 | 创建 cc->clang, gcc->clang 软链接 |
| 3 | config.status HMDFS 权限问题 | umask 077 创建的临时目录对进程不可写（E081） | 修改 config.status 中的 mktemp 调用，去掉 umask 077 |
| 4 | config.h 软链接缺失 | gambit 构建系统需要 config.h 在根目录 | 创建 config.h -> include/config.h 软链接 |
| 5 | contrib/try/xactlog 缺少 makefile | 子目录未包含在构建中 | 修改 SUBDIRS 移除 try/xactlog |
| 6 | prebuilt/githooks 缺少 makefile | 非必要构建目录 | 修改根 Makefile 移除 githooks |

## 源码修改

**补丁文件**：
- `0001-config.guess.patch`：添加 HarmonyOS 平台检测支持
- `0002-config.status.patch`：修复 HMDFS umask 077 临时文件权限问题
- `0003-config.sub.patch`：添加 linux-ohos 内核识别

## 依赖版本

- 无外部库依赖（gambit 是自包含的 Scheme 系统）
- 编译工具：make 4.4.1, autoconf 2.72

## 验证结果

```bash
$ gsc --version
Gambit v4.9.5

$ gsi --version
Gambit v4.9.5
```

编译产物：
- `/storage/Users/currentUser/usr/local/bin/gsc` (22.6MB) - Scheme 编译器
- `/storage/Users/currentUser/usr/local/bin/gsi` (10.1MB) - Scheme 解释器

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| patches/0001-config.guess.patch | 50KB | 平台检测支持 |
| patches/0002-config.status.patch | 67KB | umask 权限修复 |
| patches/0003-config.sub.patch | 34KB | 内核识别支持 |

**待打包**：预编译包尚未生成（需运行 package 命令）

## 注意事项

1. **HMDFS umask 问题**（E081）：鸿蒙 HMDFS 不支持 umask 077 创建的临时目录写入，需修改 autotools 的 config.status
2. **编译时间较长**：gambit 编译约 1600 秒（核心 + 模块）
3. **自包含系统**：gambit 不依赖外部库，适合在受限环境编译
4. **版本验证**：使用 `gsc -e "(display (system-version))"` 可获取详细版本信息

---

**编译结束**: 2026-05-27 11:28
**最终状态**: built
**编译耗时**: ~1600 秒
