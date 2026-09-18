# libdroplet 2.0 适配笔记

## 编译环境
- 构建系统: autotools（configure.ac + Makefile.am，上游 tag v2.0 未自带 configure，需 autoreconf 生成）
- 编译日期: 2026-09-17
- 编译器: clang 15.0.4（OHOS aarch64）
- 状态: 已完成

## 上游信息
- 真实上游: https://github.com/scality/Droplet（仓库名 Droplet，非 libdroplet）
- tag: v2.0（commit 22e7e46214），仓库已归档（archived: True）但源码可用
- 注意: configure.ac 内 AC_INIT 版本号为 1.1.0（上游 tag v2.0 内部未更新），版本号以 tag/任务指定 2.0 为准
- Alpine aports community/libdroplet 2.0-r13 有完整适配参考（补丁已在探索阶段参考应用）

## 依赖（均已在 ohpcd 制品仓发布，W0 已验证）
- json-c/0.18（configure.ac 需要 PKG_CHECK_MODULES(JSON, json-c)，上游写 dead json 需修正）
- libxml2/2.15.3（PKG_CHECK_MODULES(LIBXML, libxml-2.0)）
- openssl/3.5.8.1（PKG_CHECK_MODULES(OPENSSL, openssl)）
- 工具链: automake/1.18 + libtool/2.5.4（tool_requires，autoreconf 生成 configure）

## 编译要点
1. configure.ac: `PKG_CHECK_MODULES(JSON, json)` → `json-c`（Alpine 同款修正）
2. json-c 头文件 `<json/json.h>` → `<json-c/json.h>`（2 处：libdroplet/cdmi/replyparser.c、libdroplet/include/dropletp.h）
3. openssl HMAC_CTX 旧 API → 新 API（libdroplet/src/utils.c dpl_hmac_sha1，openssl 3.x 移除 HMAC_CTX_init）
4. 缺失系统头文件（gcc14/clang15 隐式声明报错）：
   - examples/srwskey.c: +ctype.h（isdigit）、+droplet/utils.h（dpl_rand_u64/u62）
   - libdroplet/src/conn.c: +sys/uio.h（writev）
5. 依赖注入须用 conan build_folder 私有 prefix（R49），libxml2/openssl/json-c 均从制品仓注入
6. 上游无测试用例（tests/ 目录仅有空 Makefile.am 和 README），需自研 test_package 断言覆盖核心 API

## 构建命令参考（探索阶段）
- autoreconf -fi 生成 configure（需 automake/aclocal/libtoolize，conan tool_requires 注入）
- configure 阶段注意 config.guess 对 HarmonyOS 的识别（参考 abiword-plugin-clarisworks 传 --build/--host triplet）
---

**编译结束**: 2026-09-17 03:41
**最终状态**: built

## 最终验证结果
- conan-verify 8 道门禁（G0-G4 + L2/L4/L5）全部 PASS
- W3 本地 CI 模拟（setup.sh + build_and_test.sh）PASS：L0（含 JC/KC）全过，
  test_package 4 组自研断言全部通过
- 上游无测试用例（tests/ 仅空 Makefile.am + README），自研 test_package 覆盖
  核心公开 API（dpl_init/dpl_status_str/dpl_method/dpl_canned_acl/dpl_size_str）

## 知识沉淀
- E580-draft-3325：conandata.yml 注释含 https URL 被 build_and_test.sh pre-download
  正则误提取为下载源（NotADirectoryError）→ 注释禁写带 scheme URL
- E333 复用：pre-download 正则连字符截断（FileNotFoundError）
- E114 复用：HMDFS config.status umask 077 临时目录不可写
- E468 复用：PkgConfigDeps 需注入 PKG_CONFIG_PATH
