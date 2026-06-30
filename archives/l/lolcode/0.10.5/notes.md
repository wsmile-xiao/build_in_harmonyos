# lolcode 0.10.5 适配笔记

## 编译环境
- 构建系统: makefile（原始源码仅含 `gcc *.c -o lolcode` 的简易 Makefile，通过注入 configure 脚本使其兼容 autotools 工作流）
- 编译日期: 2026-06-26
- 编译器: clang (路径: /data/service/hnp/bin/clang)
- 状态: published（conan-verify 全部通过）

## 编译步骤

### 手动探索阶段
1. 下载源码 tarball（GitHub master 分支，通过 HTTP API 获取）
2. 解压到 .orig 和 .work 目录
3. 重写 Makefile：支持 CC/CFLAGS/LDFLAGS/PREFIX/DESTDIR/TMPDIR 变量
4. 创建 configure 脚本：接受 --prefix=DIR 参数，生成 config.mk
5. 执行 `./configure --prefix=$DEFAULT_PREFIX && make -j1 && make install DESTDIR=$TEST_PREFIX`
6. 执行 `make check`（输出 "HAI WORLD!" 和 "Tests complete."）

### Conan 打包阶段
1. `conan-init`：生成 conanfile.py 和 conandata.yml
2. 修正 conanfile.py：
   - license 改为 GPL-3.0-or-later
   - homepage 填入 GitHub 地址
   - source() 中注入 configure 脚本和 Makefile
   - build() 使用 self.run() 直接调用 make（cwd=source_folder）
   - R26：LDFLAGS='-static' 静态链接
   - package_info() 设置 bindirs=["bin"] 和 libs=["lolcode"]
3. 修正 conandata.yml：填入真实 SHA256
4. 预填充 conan 下载缓存（解决 GitHub HTTPS 超时）
5. `conan-verify`：8 道门禁全部通过
6. `finish`：归档关闭，生成补丁和 SUMMARY.md

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | GitHub HTTPS 下载超时 | 中国大陆网络环境下 github.com:443 连接超时 (E017) | 将 tarball 预放入 conan 下载缓存 `~/.conan2/downloads/s/{sha256}`，conan create 从本地缓存获取 |
| 2 | 原始源码无 configure 脚本 | lolcode 项目仅含简易 Makefile，非标准 autotools 项目 | 在 conanfile.py 的 source() 方法中用 save() 注入 configure 脚本和标准 Makefile |
| 3 | Autotools 类在 build-release 子目录运行 make 失败 | Conan Autotools 工具链创建 build-release 子目录，但 Makefile 在源码根目录 | 改用 self.run() 直接调用，通过 cwd=self.source_folder 指定工作目录 |
| 4 | test_package 找不到 lolcode 二进制 | VirtualRunEnv 未正确设置 PATH | 使用 self.dependencies["lolcode"].cpp_info.bindirs[0] 获取路径，并在 package_info() 设置 bindirs=["bin"] |
| 5 | /tmp 只读文件系统 | 鸿蒙系统 /tmp 为只读 | Makefile 中使用 TMPDIR 变量（可覆盖） |
| 6 | make -j20 jobserver mkfifo 失败 | 系统不支持 mkfifo | 使用 make -j1 单线程编译 |
| 7 | conan conf.get() API 不兼容 | Conan 2.12 的 conf.get() 不支持 `:c` 子键 | 使用 check_type=dict 读取整个字典再取 'c' 键 |

## 源码修改

### 补丁: 0001-Makefile.patch
- 文件: Makefile
- 修改内容: 将原始 `gcc *.c -o lolcode` 替换为标准 Makefile
  - 支持 CC/CFLAGS/LDFLAGS 环境变量覆盖
  - 添加 install/check/clean 目标
  - 支持 PREFIX/DESTDIR/TMPDIR 变量
  - check 目标使用 TMPDIR 而非硬编码 /tmp

### 注入文件（在 conanfile.py source() 方法中动态创建）
- `configure`: 简单 shell 脚本，接受 --prefix=DIR，生成 config.mk
- `Makefile`: 标准 Makefile（同补丁内容）

## 依赖版本

- 无外部依赖
- 编译器: clang 15 (路径: /data/service/hnp/bin/clang)
- Conan: 2.12.0
- 构建配置: os=Linux, arch=armv8, compiler=clang, build_type=Release

## 验证结果

```bash
$ readelf -d lolcode
There is no dynamic section in this file.  # 静态链接 ✅

$ ./lolcode -f test.lol  # VISIBLE "HAI WORLD!"
HAI WORLD!  # 退出码 0 ✅

$ conan create ... --build=missing --user=ohpcd --channel=stable
# G1-G4, L2/L4/L5 全部 PASS ✅
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| bin/lolcode | 935872 bytes (914 KB) | 静态链接 ELF arm64 二进制 |
| patches/0001-Makefile.patch | 713 bytes | Makefile 标准化补丁 |
| conanfile.py | ~3.5 KB | Conan 配方 |
| conandata.yml | ~200 bytes | 源码元数据 |

## 注意事项

- lolcode 是已废弃项目，作者推荐使用 lci 替代，但 master 分支源码仍可正常编译
- conandata.yml 中的 URL 为原始 HTTPS 发布地址，实际下载通过 conan 下载缓存完成
- 二进制不支持 --help/--version 参数（上游限制），仅支持 `-f file.lol` 用法
- 补丁中 Makefile 的 TMPDIR 默认为 /tmp，在鸿蒙系统上需通过环境变量覆盖
---

**编译结束**: 2026-06-29 16:57
**最终状态**: published
