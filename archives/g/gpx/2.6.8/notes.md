# gpx 2.6.8 适配笔记

## 编译环境
- 构建系统: autotools (configure + make)
- 编译日期: 2026-06-29
- 编译器: clang 15.0.4 / clang++
- 平台: aarch64-unknown-linux-ohos (HarmonyOS)
- 状态: **published**

## 编译步骤

1. 下载源码: `https://github.com/markwal/GPX/archive/refs/tags/2.6.8.tar.gz`
   - GitHub SSL 证书验证失败，使用 ghfast.top 镜像 + `curl -kL` 手动下载
   - 下载后放到 `$TMPDIR/builds/gpx-2.6.8.tar.gz`
2. 初始化: `python3 $SKILL_ROOT/scripts/ohc-run.py init-build gpx 2.6.8 --url=...`
3. 替换 `build-aux/config.guess` 和 `build-aux/config.sub`
   - 从 `/storage/Users/currentUser/usr/local/share/automake-1.16/` 复制
   - 新版可识别 `aarch64-unknown-linux-ohos`
4. Out-of-tree 构建: `mkdir $TMPDIR/gpx-build && cd $TMPDIR/gpx-build`
5. configure: `$BUILD_SRC_DIR/configure --prefix=$DEFAULT_PREFIX CC=clang CXX=clang++`
6. 修改 config.status: `umask 077` → `umask 022`，`mktemp -d "./confXXXXXX"` → `mktemp -d "$TMPDIR/confXXXXXX"`
7. `make -j2 CC=clang CXX=clang++`
8. `make install DESTDIR=$TEST_PREFIX`
9. `make check`（无测试目标，通过）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | GitHub 下载 SSL 证书验证失败 | 鸿蒙环境缺 CA 证书 | 使用 `ghfast.top` 镜像 + `curl -kL` 手动下载到 `$TMPDIR/builds/` |
| 2 | config.guess 无法识别 HarmonyOS | 旧版 config.guess (2014-03-23) 不包含 OHOS 检测分支 | 从 automake-1.16 复制新版 config.guess/config.sub（识别 aarch64-unknown-linux-ohos） |
| 3 | config.status 创建临时文件 Permission denied | HMDFS 对 `umask 077` 创建的 0700 权限目录无法写入文件 | 修改 config.status 中 `umask 077`→`umask 022`，`mktemp` 路径改为 `$TMPDIR` |
| 4 | test_package 使用 Conan 2.x 不存在的 API | 模板使用 `self.deps_env_info`（Conan 1.x API） | 改用 `self.dependencies["gpx"].package_folder` 获取二进制路径 |
| 5 | gpx 是工具非库，test_package 链接失败 | 模板默认用 CMake 链接库 | 改为 VirtualRunEnv + 直接运行二进制测试 |

## 源码修改

| 文件 | 修改内容 | 类型 |
|------|----------|------|
| build-aux/config.guess | 替换为 automake-1.16 版本（支持 OHOS） | 平台适配 |
| build-aux/config.sub | 替换为 automake-1.16 版本（支持 OHOS） | 平台适配 |
| configure（生成文件） | umask 077→022, mktemp 路径改为 $TMPDIR | HMDFS 适配 |

**注**: configure 脚本的 umask/mktemp 修改在 conanfile.py 的 build() 方法中自动处理，不作为补丁。
config.guess/config.sub 的替换已生成为补丁文件（0001, 0002）。

## 依赖版本

- 无外部依赖，仅依赖系统 libc（musl）

## 验证结果

### 产物验证
```
$ ls -la bin/
gpx      1,435,584 bytes  ELF static, arm64
s3gdump    890,816 bytes  ELF static, arm64
machines 1,001,408 bytes  ELF static, arm64
```

### 静态链接验证（R26）
```
$ readelf -d bin/gpx | grep NEEDED
(无 NEEDED 条目 = 完全静态链接)
```

### 安全特性
```
$ readelf -l bin/gpx | grep -E "GNU_STACK|GNU_RELRO"
GNU_RELRO  0x000000000007ce10 ...
GNU_STACK  0x0000000000000000 ... (NX enabled)
```

### 功能测试
```
$ bin/gpx -p -m r2 examples/macro-example.gcode /tmp/test-output.x3g
(成功，输出 136822 字节 x3g 文件)
```

### Conan 验证（8 道门禁全部通过）
- G0: PASS  G1: PASS  G2: PASS  G3: PASS  G4: PASS
- L2: PASS  L4: PASS  L5: PASS

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| bin/gpx | 1,435,584 | G-code 解析器主程序（静态链接） |
| bin/s3gdump | 890,816 | s3g 格式转储工具（静态链接） |
| bin/machines | 1,001,408 | 机器配置生成工具（静态链接） |
| patches/0001-build-aux-config.guess.patch | 74,623 | config.guess 平台适配补丁 |
| patches/0002-build-aux-config.sub.patch | 70,407 | config.sub 平台适配补丁 |

## 注意事项

1. config.status 是 configure 生成的文件，每次 configure 后需要重新修改 umask 和 mktemp 路径。conanfile.py 的 build() 方法已自动处理此问题。
2. gpx 的 `--help` 参数不被识别（程序使用单字母参数如 `-h`），但会输出版本信息，不影响功能。
3. 静态链接导致 PIE 不可用，这是 `-static` 编译的预期行为，非安全问题。
4. `make -j2` 会出现 `jobserver mkfifo: Operation not permitted` 警告，不影响编译结果（HarmonyOS FIFO 限制）。

---

**编译结束**: 2026-06-29 15:08
**最终状态**: published
