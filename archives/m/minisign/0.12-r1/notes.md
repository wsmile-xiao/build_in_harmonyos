# minisign 0.12-r1 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-17（重构版：改用 conan 依赖 libsodium）
- 编译器: clang/clang++（OHOS aarch64，HNP 工具链）
- 状态: built（本地 conan create 验证通过；published 待合入后 release 流水线 upload）

## 编译步骤
1. 上游源码：GitHub archive 0.12 tag，sha256: 796dce1376f9bcb1a19ece729c075c47054364355fe0c0c1ebe5104d508c7db0
2. 依赖：libsodium/1.0.22（ohpcd 制品仓 conan 依赖，静态库；R36 已发布实测 conan install --build=never 可解析）
3. 补丁 0001：PkgConfig 放宽为可选（OHOS 交叉环境无系统 libsodium .pc）
4. conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64

## 历史演进（W0b）
- 2026-06-04 PR #4444：首版适配（manifest/notes stub 遗留于 main），用 cmd-pkgs
  预编译 libsodium 安装到 ~/usr/local
- 2026-08-13 minisign/0.12 合入 main 并发布制品仓（同 cmd-pkgs 方案）
- 2026-08-30 PR #7163：0.12-r1 全量配方（仍为 cmd-pkgs 方案），CI 绿
- 2026-09-03 重写 rebase 时误将 pstree/libxext/垃圾清理等无关变更带入 PR 分支
  （W2 原子性违规，JC6 会拦）→ 本次重做：仅保留 minisign 变更
- 2026-09-17 本次：libsodium/1.0.22 已在制品仓（静态二进制实测可解析），
  按 R36 改为声明 conan requires，去掉 cmd-pkgs 下载安装逻辑；
  conandata.yml 改为官方单 URL（R39/PF7：CI 自动做镜像 fallback）；
  test_package 按 E428 改绝对路径调用

## 验证结果
- conan create: SUCCESS (5/5 test_package assertions passed)
- test_package: version output, key generation, signing, verification, tamper detection

## 注意事项
- minisign 是命令行工具（application 包），package_info 只需 bindirs
- minisign 无 --version，用 -v 输出版本
- 上游 CMakeLists 的 find_path/find_library 缓存变量 SODIUM_INCLUDE_DIR/SODIUM_LIBRARY
  已由 toolchain 预设时不再搜索，pkg_check_modules 结果为空也无影响
- E077：install 后 strip 会破坏 .codesign 签名，package() 中重签
