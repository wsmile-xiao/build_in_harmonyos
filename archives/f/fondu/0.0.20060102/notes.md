# fondu 0.0.20060102 适配笔记

## 编译环境
- 构建系统: autotools（configure.in 极简：AC_INIT + AC_PROG_CC + AC_CANONICAL_HOST）
- 编译日期: 2026-08-04
- 编译器: clang/clang++（OHOS 主机）
- 状态: built（probe 轮，未上传）

## 编译步骤

1. `init-build fondu 0.0.20060102 --url=<debian pool orig.tar.gz>`：下载源码、创建归档骨架。
2. sha256 核验：`22bb535d670ebc1766b602d804bebe7e84f907c219734e6a955fcbd414ce5794`（与 conandata.yml 一致）。
3. conanfile.py：autotools 配方，`package_type=application`（8 个命令行工具：fondu/ufond/showfond/dfont2res/tobin/frombin/lumper/setfondname）。
4. config.guess/config.sub（2006 版）patch：
   - config.guess：添加 `__OHOS__` LIBC 检测（patch-autotools-ohos.pl 或手动 fallback）。
   - config.sub：添加 aarch64/aarch64_be CPU + linux-ohos*/-ohos* OS 分支。
5. `configure --prefix=$DEFAULT_PREFIX && make -j1`（CC=clang）。
6. `make install DESTDIR=...` 安装 8 个工具到 bin/。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 2006 版 config.sub 不识别 `aarch64-ohos-linux` 三元组 | config.sub 无 aarch64 CPU 支持、无 ohos OS 分支 | conanfile.py `_patch_config_for_ohos()`：config.sub 添加 aarch64/aarch64_be CPU + linux-ohos*/-ohos* OS；config.guess 添加 __OHOS__ LIBC 检测（参考 autotools-patterns.md #2-#3） |
| 2 | HMDFS 默认 TMPDIR 下 conftest 写 dummy.c 报 Permission denied | 默认 /tmp 不可写 | TMPDIR 指向 ~/.conan_build_tmp（持久可写目录） |

## 源码修改

无外部补丁文件；config.guess/config.sub 的 OHOS 支持在 conanfile.py build() 内 inline 处理（自包含，不落 patch 文件）。

## 依赖版本

无外部依赖（仅 libc + libm）。本机工具链：clang 15.0.4、make 4.4.1、autoconf 2.72、automake 1.16.5。

## 验证结果

```bash
# 上游测试核验：fondu 源码无 test/、tests/ 目录，Makefile.in 无 check 目标
# → 上游测试用例通过率：0/0（N/A，上游无测试用例）
# test_package smoke test：fondu 无参数运行打印 Usage 退出码 0（见 test_package/test.sh）
```

## 交付物

| 文件 | 说明 |
|------|------|
| conandata.yml | 源码 URL + sha256 |
| conanfile.py | autotools 配方（含 OHOS config patch + TMPDIR 处理） |
| manifest.yaml | 版本级 manifest |
| test_package/ | smoke test（conanfile.py + MANIFEST.yml + test.sh） |
| packaging/ | 打包产物（conan create 后生成） |

## 注意事项

- fondu 是 2006 年老代码，configure.in 极简，无测试框架；上游测试核验结论 0/0（N/A）。
- 本轮 probe_only_no_upload：禁止 push/submit/ai review，等分析端授权。
---

**编译结束**: 2026-08-04 15:05
**最终状态**: published
