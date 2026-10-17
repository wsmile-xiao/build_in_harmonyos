# libexecinfo 20180201 适配笔记

## 编译环境
- 构建系统: makefile（上游纯 Makefile，无 configure）
- 编译日期: 2026-09-17
- 编译器: clang 15.0.4 (aarch64-unknown-linux-ohos) / clang++
- 状态: published
- Conan: 2.29.1（OHOS 适配版）
- Profile: ci/conan/profiles/ohos-aarch64（os=OHOS, arch=armv8, compiler=clang-15）

## 编译步骤

```bash
# 配方目录
archives/l/libexecinfo/20180201/
# conan create（ohc-run.py conan-verify 内部执行，E017 自动注入 ghfast.top 镜像下载）
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
    --build=missing --user=ohpcd --channel=stable
# 配方内 build(): 在 source_folder 直接 make -j1（上游 Makefile 不支持 out-of-source）
# package(): 手动拷贝 execinfo.h/stacktraverse.h → include/,
#            libexecinfo.a/libexecinfo.so.1 → lib/, 并用 os.symlink 建相对链接
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | conan create G2: `module 'conan.tools.files.symlinks.symlinks' has no attribute 'symlink'` | conan 2.29 的 symlinks 模块无创建符号链接 API（只有 get/absolute_to_relative/remove 系列） | package() 改用标准库 `os.symlink` 建相对链接（先 unlink 已存在项） |
| 2 | 上游 Makefile install 用 `ln -s /usr/lib/libexecinfo.so.1 ...`（绝对路径） | 以 /usr 为安装根编写 install 目标，Conan DESTDIR 打包会得到指向宿主 /usr/lib 的死链接 | 不依赖上游 make install；package() 手动 copy + os.symlink 相对链接 `libexecinfo.so -> libexecinfo.so.1` |
| 3 | W3 本地 CI: `NotADirectoryError: .../predl_cache/c1cff791_libexecinfo/archive/refs/tags/v20180201.tar.gz` | conandata.yml 注释写了裸仓库 URL `# Source: https://github.com/resslinux/libexecinfo (official upstream)`，被 build_and_test.sh pre-download 正则捕获当作源码 URL，下载了 30KB 仓库主页 HTML（非 tarball），随后前缀替换污染官方 tarball URL | 注释中不写裸仓库 URL；删除 `.build-cache/predl_cache/` 误下载 HTML；恢复官方单 URL。修复后 W3 100% 通过 |
| 4 | W3 JC 命中其他库 cloog 基线文件（.build-closed/.staging-verified，提交前已存在于 main） | 全库 full 模式 junk_check 以 git ls-files 扫描，命中既有基线 | 按基线隔离规则：记录 SHA-256 → 临时移出索引 → 复跑 W3 通过 → 原样恢复（pre==post SHA 一致），未修改/未提交基线（见 reports/baseline-isolation-audit.md） |
| 5 | test_package 首次运行退出码 1 | 自写 test.c 递归求和返回值非 0 | 修正递归逻辑（只递归不求和），复跑退出码 0 |

## 源码修改

无补丁（patches/ 为空）。上游 Makefile 可直接用 OHOS 工具链编译；
打包侧符号链接处理在 conanfile.py package() 内完成（相对链接替代上游绝对路径 ln -s）。

## 依赖版本

无第三方依赖（仅 libc/musl 运行时）。

## 验证结果

```bash
# conan-verify G0-G4 + L2/L4/L5 全绿，可标记 published
ohc-run.py conan-verify libexecinfo 20180201 --profile ohos-aarch64
# W3 本地 CI（build_and_test.sh，含 pre-download + conan create + test_package）
ohc-run.py finish libexecinfo 20180201 published  →  W3 100% (1/1)
# 消费者用例（test_package/test.c）：backtrace() 捕获 6 帧，退出码 0
# 鸿蒙专项测试（test_package/ohos_special_test.cpp）：7 帧 + 符号映射，退出码 0
# 上游测试：tarball 无任何测试入口（0/0，见 reports/upstream-test-ledger.md 清点证据）
```

## 注意事项

- 上游 tag 为 `v20180201`（版本号 20180201 对应 release tag）。
- conandata.yml 注释中不得出现裸仓库 URL（会被 pre-download 正则误捕获，见问题 3）。
- 知识草稿：DRAFT-libexecinfo-20180201-conandata-comment-url-predl-pollution、
  DRAFT-libexecinfo-20180201-makefile-absolute-symlink-conan-packaging（均 Path B）。

---

**编译结束**: 2026-09-17 20:25
**最终状态**: published
---

**编译结束**: 2026-09-18 00:24
**最终状态**: published
