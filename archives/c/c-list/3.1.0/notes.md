# c-list 3.1.0 适配笔记

## 编译环境
- 构建系统: meson（上游 meson.build，c_std=c99，meson_version>=0.60.0）
- 编译日期: 2026-09-06
- 编译器: clang/clang++ 15.0.4（OHOS 适配版 conan 2.29.1 + ci/conan/profiles/ohos-aarch64，tool_requires meson/1.11.0）
- 状态: built
- worktree: ~/qzy/c-list 分支 feat/c-list-3.1.0（基线 upstream/main dfe3d3ac77）

## 任务与 W0/W0b
- 任务号 #6162（开源鸿蒙PC专项积分赛），认领人 wanderlust_0823，status assigned，无同名同版本重复任务，upstream/main 归档树无 c-list 目录。
- 上游确认：github.com/c-util/c-list（C-Util 项目，Circular Intrusive Double Linked List Collection，ISO-C11，header-only），tag v3.1.0 存在，tarball SHA256 7d5b12166859bd729404cba8da575ae47952cbb97d650c5bbe50559c03631e4b。
- W0: 运行时/编译依赖为零；构建工具 meson/1.11.0 已在制品仓发布（conan download 探测通过，account-utils/1.4.0 同款先例）。
- W0b: 无同软件历史归档。语言预检通过（task=cpp, detected=c，c↔cpp 兼容族），无绑定误报。

## 编译步骤
1. `ohc-run.py init-build c-list 3.1.0 --url=https://github.com/c-util/c-list/archive/refs/tags/v3.1.0.tar.gz`
2. `lang-preflight` 通过
3. 上游套件真机独立复现：meson setup + meson test 于原始源码树（~/tmp/uc2/c-list/clist-upstream-build），3/3 套件通过
4. 配方：header-only Meson 配方（tool_requires meson/1.11.0），build() 内 meson configure/build/test
5. `conan create`：rc=0，build() 内上游套件 3/3 OK，test_package 消费者测试 PASSED
6. conan-verify / finish：见 reports/ 与 .ci-result.json

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | cmake_layout import 路径 | conan 2.x 中 cmake_layout 位于 conan.tools.cmake 而非 conan.tools.layout | 修正 import；ConanCenter 示例多用 conan.tools.cmake 导出 |
| 2 | 上游无 LICENSE 文件 | tarball 仅 AUTHORS/NEWS.md/README.md | 许可证按 meson.build `license: 'Apache'` 与 README "Apache-2.0 OR LGPL-2.1-or-later" 声明为双许可；包内无 license 文件可拷贝 |
| 3 | meson install 在 HMDFS 有符号链接坑（account-utils 先例） | 上游 install 仅 install_headers + pkgconfig | package() 直接 copy src/c-list.h 到 include/，不执行 meson install |

## 源码修改
- 无补丁（patches: {}），未修改上游任何文件。

## 依赖版本
- 运行时/编译依赖：无。
- 构建工具：meson/1.11.0（制品仓 tool_requires）。

## 验证结果
- 上游测试（R51 三步法）：
  - 静态清点：src/meson.build 注册 3 个 meson test 套件；测试函数 test_api/test_api_gnu（API 套件 2）+ test_iterators/swap/splice/split/flush/macros/gnu（Basic 套件 7）+ test_entry/test_entry_gnu（Embedded 套件 2）= **11 个测试用例**（*_gnu 为 glibc/通用双实现条件编译，各编译执行其一；合计约 170 个 assert）
  - 实际执行（双口径）：
    a) 真机独立复现（原始源码树 meson test）：3/3 套件 OK，11/11 用例，0 失败 0 跳过（~/tmp/uc2/c-list/clist_meson_test.log）
    b) 配方 build() 内随 conan create 执行（即 CI 将执行的路径）：meson test -v 3/3 OK（~/tmp/uc2/c-list/first_create.log）
- test_package 消费者测试：test_c_list（C，find_package(c-list) + c-list::c-list target），覆盖 C_LIST_INIT 空表、link_tail 尾插顺序、c_list_for_each 计数、unlink 中间/头节点、清空回空表，**12 项断言全部通过**。

## 注意事项
- 上游 *_gnu 测试函数在 glibc 平台编译 GNU 扩展变体、在 OHOS（musl）编译通用变体，属同用例的条件编译实现，不计为跳过。
- 头文件安装路径为 include/c-list.h（上游 pkgconfig filebase libclist-3）；消费者经 CMakeDeps find_package(c-list) 或直接 include 使用。
---

**编译结束**: 2026-09-06 02:12
**最终状态**: built
