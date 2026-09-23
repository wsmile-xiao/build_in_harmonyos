# burp 3.3.0 适配笔记

## 编译环境
- 构建系统: cmake（上游 autotools；tarball 仅 Makefile.am、无预生成 configure，OHOS 构建环境缺 automake/libtool，故随归档附 CMakeLists.txt overlay）
- 目标: HarmonyOS PC aarch64（conan profile ohos-aarch64，clang --target=aarch64-linux-ohos）
- 语言: C11（纯 C 项目）
- 许可证: AGPL-3.0
- 编译日期: 2026-09-02

## 编译步骤
1. `conan create archives/b/burp/3.3.0 --name=burp --version=3.3.0 -pr ohos-aarch64 -s build_type=Release`
2. source(): 下载 tarball（sha256 见 conandata.yml），strip_root
3. build(): CMakeToolchain（ohos-aarch64 自动映射 HarmonyOS/sysroot）+ 5 个依赖包路径以 `-D<X>_ROOT_DIR` 传入 overlay（overlay 内 IMPORTED 目标指向 `<ROOT>/lib`、`<ROOT>/include`，与 conan 包目录布局一致）；configure + build
4. package(): 安装 `bin/burp` + `licenses/LICENSE`
5. test_package: 执行打包产物 `bin/burp -V`，断言输出含 `burp-3.3.0` 且退出码 0

## 遇到的问题与解决方案
1. tarball 无预生成 configure、构建环境无 automake/libtool → 从 Makefile.am 机械生成 CMakeLists.txt（解析 main_SOURCES/runner_SOURCES，处理 $(VAR) 展开与反斜杠续行），随归档提交，上游源码零修改
2. config.h 由 CMake 按 OHOS sysroot 逐宏生成：HAVE_LINUX_OS / HAVE_IPV6 / HAVE_ENDIAN_H / HAVE_DIRENT_H / HAVE_FSEEKO / HAVE_TYPEOF / HAVE_LOCKF / HAVE_LUTIMES / HAVE_SYS_XATTR_H / HAVE_XATTR / HAVE_CRYPT / HAVE_BLAKE2 / HAVE_SYS_PRCTL_H / HAVE_PRCTL / HAVE_SETREUID + PACKAGE_* 元数据；每个宏经 sysroot 头文件与 libc.so dyn-syms readelf 验证。缺 HAVE_CRYPT/HAVE_LOCKF 会多挂 2 个测试（test_check_passwd、test_lock_simple_failure）
3. asfd 结构在 -DUTEST 下有额外 mock 字段 → 建共享 libburp 是 ODR 隐患，故镜像上游做法：main_SOURCES 按 target 分别全量编译（burp 111 个源文件、runner 177 个源文件）；prog.c 的 main() 包在 #ifndef UTEST 内，runner 侧自动编译掉、与 utest/main.c 无冲突
4. uthash 头文件不在 tarball 内（src/client/find_logic.c、src/server/bedup.c 直接 #include <uthash.h>）→ 依赖制品库 uthash/2.3.0
5. OHOS /tmp 为只读 erofs，check 0.15.2 的 open_tmp_file() 先查 getenv("TEMP")（先于 P_tmpdir）→ 运行 runner 前 `export TEMP=<可写目录>`
6. 硬链接 EPERM / 大小写不敏感 FS / inode 预置 xattr → 见「验证结果」7 个环境性失败逐条说明

## 依赖版本
| 依赖 | 版本 | 用途 |
| --- | --- | --- |
| openssl | 3.5.6 | 传输加密（libssl/libcrypto，全局目标已含两个组件） |
| zlib | 1.3.2 | 压缩（-z gzip 路径） |
| librsync | 2.3.4 | 块级增量同步核心 + BLAKE2 签名 |
| check | 0.15.2 | 上游 utest 测试框架（runner 专用） |
| uthash | 2.3.0 | 头文件哈希库（find_logic/bedup） |

## 验证结果
- 编译状态: 通过（burp 约 5.5MB、runner 约 6.0MB，均为 ARM64 ELF，NEEDED 仅 libc.so）
- 版本自检: `burp -V` → `burp-3.3.0`（退出码 0）
- 上游测试实跑（host aarch64 直接执行 runner，TEMP 指向可写目录）: `Checks: 233, Failures: 7, Errors: 0` → 226/233 = 96.99%，两次独立运行结果确定一致
- 7 个失败全部为 OHOS 环境性（逐一取证，非适配缺陷）:
  1. `test_find` / 2. `test_atomic_data_jiggle` / 3. `test_bedup_non_burp_simple_link` / 4. `test_bedup_non_burp_link_above_max_links` —— 主机文件系统拒绝硬链接，探针实测 `ln` → Operation not permitted（link(2) EPERM）
  5. `test_xattrs` —— 每个 inode 预置 security.selinux / user.hmdfs.perm / security.isolate 三个 xattr，`has_xattr()==0` 断言必假（探针实测 listxattr 返回 3 项）
  6. `test_authorise_server` —— 仅 setup_lower_failed 子例失败：主机 FS 大小写不敏感，TESTCLIENT 匹配到 testclient 配置文件（探针实测 exists 为真）；上游测试注释自认「大小写不敏感文件系统上此测试会失败」
  7. `test_restore_some_things` —— CMD_HARD_LINK 错误路径 alloc 计数不匹配，slist 含 cmd='L' 项，由硬链接 EPERM 级联
- 消费测试: test_package 运行打包的 `bin/burp -V` 通过

## 交付物
- archives/b/burp/commands.json
- archives/b/burp/3.3.0/conanfile.py
- archives/b/burp/3.3.0/conandata.yml
- archives/b/burp/3.3.0/CMakeLists.txt（Makefile.am 生成的 OHOS overlay，372 行）
- archives/b/burp/3.3.0/manifest.yaml
- archives/b/burp/3.3.0/notes.md
- archives/b/burp/3.3.0/test_package/conanfile.py
- archives/b/burp/3.3.0/test_package/test_burp.py
- archives/b/burp/3.3.0/test_package/MANIFEST.yml
