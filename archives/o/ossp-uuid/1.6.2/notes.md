# ossp-uuid 1.6.2 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-07-03
- 编译器: clang 15.0.4 / clang++
- 状态: published

## 编译步骤

1. **init-build**: `python3 $SKILL_ROOT/scripts/ohc-run.py init-build ossp-uuid 1.6.2 --url=https://www.mirrorservice.org/sites/ftp.ossp.org/pkg/lib/uuid/uuid-1.6.2.tar.gz` — 下载源码、解压、创建工作目录、生成 .build-context
2. **工具检查**: `python3 $SKILL_ROOT/scripts/ohc-run.py resolve-deps --check-tools` — 所有构建工具就绪 (make, autoconf, automake, libtool, pkg-config 等)
3. **configure**: `./configure --prefix=$DEFAULT_PREFIX` — 更新 config.guess/config.sub 后 configure 成功，检测平台为 aarch64-unknown-linux-ohos
4. **make**: `make -j2` — 编译 libuuid (共享库+静态库) 和 uuid CLI 工具
5. **make install DESTDIR**: `make install DESTDIR=$TEST_PREFIX` — 安装到 staging 隔离目录验证
6. **make check**: `make check` — 所有测试通过 (UUID v1/v3/v4/v5 生成与解码)
7. **conan-init**: `python3 $SKILL_ROOT/scripts/ohc-run.py conan-init ossp-uuid 1.6.2` — 生成 conanfile.py + conandata.yml + test_package/
8. **conan-verify**: `python3 $SKILL_ROOT/scripts/ohc-run.py conan-verify ossp-uuid 1.6.2` — 8道门禁全部通过
9. **finish**: `python3 $SKILL_ROOT/scripts/ohc-run.py finish ossp-uuid 1.6.2 published` — 归档收尾，状态=published，退出码=0

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 下载URL未自动找到 | ossp-uuid 是老项目，原始 ftp.ossp.org 已下线 | 手动搜索镜像，使用 mirrorservice.org 镜像下载 uuid-1.6.2.tar.gz (397048 bytes) |
| 2 | configure 报 "cannot guess build type" (E007) | 源码自带 config.guess 为 2008-01-08 版本，不包含 HarmonyOS/OHOS 检测分支 | 从 automake 1.16 复制更新的 config.guess/config.sub，可正确检测 aarch64-unknown-linux-ohos |
| 3 | config.status 报 "Permission denied" 创建 subs1.awk 失败 (E125) | mktemp -d 在 HMDFS/tmpfs 上创建的目录带有 MAC 安全标签 (hmmac=use_task)，即使 chmod 后仍无法写入 | 将 configure 和 config.status 中的 `mktemp -d "./confXXXXXX"` 替换为 `mkdir "$tmp"` (mkdir 不受 MAC 限制) |
| 4 | Conan 配方 package_info().libs 错误 | 模板生成库名为 "ossp-uuid"，但实际库名为 "uuid" (libuuid.so/libuuid.a) | 修正为 `self.cpp_info.libs = ["uuid"]` |
| 5 | 系统同名库 libuuid 需静态编译 (R26) | libuuid 是 util-linux 的系统同名库，构建 .so 会污染 /lib、/lib64 | 在 generate() 添加 `--disable-shared --enable-static` |
| 6 | Conan conan create 失败：config.guess 未更新 | conan create 下载原始源码，不含 config.guess/mktemp 修复 | 在 conanfile.py build() 方法中添加 config.guess/config.sub 替换和 mktemp 修复步骤 |
| 7 | make install 失败：uuid.pc 路径找不到 | Conan basic_layout 使用源外构建 (build-release 子目录)，config.status 在构建目录生成 uuid.pc，但 Makefile 在源目录查找 | 在 package() 方法中添加从构建目录复制生成文件到源目录的逻辑 |
| 8 | test_package 测试失败：UUID 长度断言错误 | uuid_export(UUID_FMT_STR) 返回 37 字节 (36字符 + null终止符)，测试断言期望 36 | 修正 test.c 长度检查为 `len < 37` |

## 源码修改

共生成 4 个补丁文件：

| 补丁文件 | 修改内容 |
|---------|---------|
| 0001-config.guess.patch | 替换 config.guess 为 automake 1.16 版本，添加 HarmonyOS/OHOS 平台检测 (E007) |
| 0002-config.status.patch | config.status 中 mktemp -d 替换为 mkdir，修复 HMDFS MAC 限制 (E125) |
| 0003-config.sub.patch | 替换 config.sub 为 automake 1.16 版本，支持 OHOS 平台识别 (E007) |
| 0004-configure.patch | configure 中 mktemp -d 替换为 mkdir，修复 HMDFS MAC 限制 (E125) |

conanfile.py 额外修改（非补丁，内嵌于配方）：
- build() 方法：从系统 automake 复制 config.guess/config.sub；replace_in_file 修复 configure 中 mktemp 模式
- generate() 方法：添加 --disable-shared --enable-static (R26)
- package() 方法：源外构建兼容，复制生成文件
- package_info()：libs = ["uuid"]

## 依赖版本

无外部依赖。ossp-uuid 1.6.2 是自包含的 UUID 库，不依赖任何外部库。

构建工具版本：
- clang 15.0.4
- make 4.4.1
- autoconf 2.72
- automake 1.16
- libtool (已安装)
- pkg-config 0.29.2

## 验证结果

### make check
```
==== UUID version 1 (time and node based): 4 single iterations — PASS
==== UUID version 1 (time and node based): 4 subsequent iterations — PASS
==== UUID version 3 (name based, MD5): 2 times repeated (deterministic) — PASS
==== UUID version 5 (name based, SHA-1): 2 times repeated (deterministic) — PASS
==== UUID version 4 (random data based): 4 single iterations — PASS
Exit code: 0
```

### conan-verify (8道门禁)
```
G0 预构建风险评估: PASS
G1 配方完整性: PASS
G2 conan create (干净构建): PASS
G3 系统同名库隔离 (R26): PASS
G4 产物完整性: PASS
L2 smoke test: PASS
L4 安全扫描 (checksec): PASS
L5 产物基线对比: PASS
Verdict: PASS
```

## 交付物

| 文件 | 说明 |
|------|------|
| libuuid.a | 静态库 (R26 系统同名库强制静态) |
| uuid | CLI 工具 (uuid 生成/解析命令行) |
| uuid.h | 公共头文件 |
| uuid.pc | pkg-config 配置文件 |
| uuid-config | 配置脚本 (编译链接参数查询) |
| man/man1/uuid.1 | uuid 命令手册 |
| man/man1/uuid-config.1 | uuid-config 手册 |
| man/man3/uuid.3 | UUID API 手册 |

## 注意事项

- **R26 系统同名库静态链接**: libuuid 是 util-linux 的系统同名库，conanfile.py 中通过 `--disable-shared --enable-static` 强制静态构建，避免 .so 污染系统 /lib、/lib64 路径
- **E007 config.guess 平台检测**: 源码自带 config.guess (2008年版) 不识别 HarmonyOS，必须替换为 automake 1.16+ 版本。conanfile.py build() 方法中已内嵌自动替换逻辑
- **E125 mktemp MAC 限制**: HMDFS/tmpfs 上 `mktemp -d` 创建的目录因 `hmmac=use_task` 安全策略无法写入文件，即使 chmod 也无效。必须用 `mkdir` 替代。conanfile.py build() 方法中已内嵌 replace_in_file 修复
- **源外构建兼容**: Conan basic_layout 可能使用 build-release 子目录进行源外构建，需在 package() 中将 config.status 生成的文件 (uuid.pc, uuid-config, uuid.h, config.h, Makefile) 从构建目录复制到源目录
- **/tmp 只读**: 鸿蒙平台 /tmp 为只读文件系统 (E002)，必须使用 $TMPDIR (~/tmp) 作为临时目录
---

**编译结束**: 2026-07-03 16:28
**最终状态**: published
