# openslp 2.0.0 适配笔记

## 编译环境
- 构建系统: autotools（官方 release tarball 自带 configure，2012 版 config.sub）
- 编译日期: 2026-09-04
- 编译器: clang（aarch64-linux-ohos 交叉，BiSheng clang + musl sysroot）
- 状态: built

## 源码
- 官方 tarball: sourceforge `2.0.0 Release/openslp-2.0.0.tar.gz`
- sha256: 924337a2a8e5be043ebaea2a78365c7427ac6e9cee24610a0780808b2ba7579b
- 注：openslp-org GitHub monorepo tag openslp-2.0.0 的 `openslp/` 子目录即此 C 包，但无 configure（需 autoreconf），故采用官方 release tarball

## 编译步骤
1. configure（host=aarch64-linux-ohos，交叉）
   - 前置：给 config.sub 补 `linux-ohos`（见 conanfile.py `_patch_config_sub`，三处替换）
   - 环境：`ac_cv_func_fnmatch_works=yes`（configure 的 fnmatch 探针是运行时测试，交叉无法执行）
   - 参数：`--disable-shared --enable-static --disable-dependency-tracking`
2. make -j2

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.sub 报 `system 'ohos' not recognized` | 2012 config.sub 无 OHOS OS 条目 | conanfile.py `_patch_config_sub` 三处替换（kernel-os 表 / valid-os 表 / -linux 归一化特例），与 open-isns 0.101 同型 |
| 2 | configure 尾部 `config.status: linking fnmatch_.h: file not found` | AC_FUNC_FNMATCH 探针需运行时执行，交叉编译返回 cross → 误入 LIBOBJS 替换分支链接不存在的 fnmatch_.h | `ac_cv_func_fnmatch_works=yes`（musl sysroot 自带 fnmatch） |
| 3 | 二次 make 报 `.deps/*.Plo: multiple target patterns` | Windows BiSheng clang.exe 的 -MP 依赖文件里含 `D:ohos-sysroot/...` 盘符头路径，make 误解析 | `--disable-dependency-tracking`（仅本地 Windows 交叉工具链场景；Linux CI 无此问题但该参数无害） |
| 4 | slptool 链接 `libslp.so: no such file` | libtool 生成的 .so 是符号链接，clang.exe 经 \\wsl$ UNC 读 WSL 软链接失败 | 静态构建 `--disable-shared --enable-static` |

## 源码修改
无。OHOS 适配全部在 conanfile.py 的 build() 内完成（config.sub 运行时补丁 + configure 缓存变量），未改动任何上游源码文件。

## 验证结果
- 交叉 configure + make 成功：libslp.a（+ libslpattr）、slpd、slptool 全部产出
- 产物为 aarch64 musl ELF（file 校验）
- make install DESTDIR 暂存正常：bin/slptool sbin/slpd include/slp.h lib/libslp.a
- 特性开关默认：SLPv1 yes / SLPv2 Security no（无需 openssl）/ Predicates yes
- 上游 DA 集成测试（需 root + 网络）未在本机交叉环境执行，见 test_package/MANIFEST.yml

## 注意事项
- SLPv2 Security（openssl）默认关闭，规避 openssl 依赖与老 API 兼容问题；如后续需要可另开包
- slpd 守护进程在真机运行需先 sign-elf（ELF 签名）
