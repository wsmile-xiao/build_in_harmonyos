# aws-lc 5.5.0 适配笔记

## 项目简介
AWS-LC（AWS LibCrypto）—— AWS 密码团队维护的通用密码库（BoringSSL 分支），
提供 libcrypto/libssl 作为 OpenSSL 的 drop-in 替代。Apache-2.0/ISC/MIT 等混合
许可。C（libcrypto）+ C++（libssl）实现，CMake 构建。

本配方基于 **5.4.0（main 仓库已适配合入，archives/a/aws-lc/5.4.0）升级**：
仅版本号 + 源码 sha256 变化，适配逻辑与 5.4.0 完全一致。

## 构建系统与依赖
- CMake 3.0+（本机 4.1.2 ✅）；Perl（hnp v5.42.0 ✅）；ninja（hnp ✅）
- **Go 1.20+（本机无）**——CMakeLists 支持 `DISABLE_GO=ON` 时用
  `generated-src/` 预生成代码构建（鸿蒙适配关键）
- 无第三方 conan 依赖（requirements 空，纯自包含）
- C/C++ 编译器：clang 15（OHOS 工具链 ✅）

## OHOS 适配要点（同 5.4.0 先例）
1. **R26**：`BUILD_SHARED_LIBS=OFF`——system-name 库（libcrypto/libssl）必须
   静态，避免污染 /lib（R26 强制）；
2. **DISABLE_GO=ON**：鸿蒙无 Go 工具链 → 用上游 generated-src 预生成代码；
3. **BUILD_TESTING=OFF / BUILD_TOOL=OFF**：纯库构建（鸿蒙 C++ 测试链接问题
   规避，同 5.4.0）；
4. **OPENSSL_NO_ASM=ON**：鸿蒙 CMake 报 `CMAKE_SYSTEM_PROCESSOR=unknown`
   （uname -p 返回 unknown）→ aws-lc 回退 "generic" 架构却不定义
   OPENSSL_NO_ASM → 汇编符号引用链接时未解析。显式 ON 启用纯 C fallback；
5. **package_info**：`libs=["crypto","ssl"]` + `system_libs=["pthread","dl","rt"]`。

## 验证
- 模拟 CI 干净 PATH conan create（--build=missing, ohos-aarch64 profile）；
- test_package：test.c 调 `SHA256("abc")` known-answer 校验（ba7816bf...），
  链接 aws-lc::aws-lc。

## 参考
- main 仓库 5.4.0 配方（conanfile.py/conandata.yml/test_package 模板）
- 制品仓已发布 aws-lc/5.4.0（本 5.5.0 为升级版本）
