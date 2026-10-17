# crypto 3.4.7 (OpenSSL) 适配笔记

## 编译环境
- 构建系统: custom-perl（`perl ./Configure`，非 autotools ./configure）
- 编译日期: 2026-09-21
- 编译器: clang 15.0.4 (aarch64, HarmonyOS PC 真机)
- 状态: published

## 编译步骤

```bash
# Adapt 阶段（探索编译，$BUILD_SRC_DIR）
perl ./Configure --prefix=$DEFAULT_PREFIX --openssldir=$DEFAULT_PREFIX/ssl \
  --with-rand-seed=getrandom no-asm no-shared -fPIC linux-aarch64
make -j2
make install DESTDIR=$TEST_PREFIX
make test HARNESS_JOBS=16   # 327 文件 / 3392 测试全部通过 (Result: PASS)

# Conan 配方验证（最终提交配方 -j2 build_sw）
conan create archives/c/crypto/3.4.7 -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing --user=ohpcd --channel=stable
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游测试 make test 被 300s 工具窗口截断 | openssl 全量测试耗时长 | 记录截断证据后以 HARNESS_JOBS=16 重跑完整门禁，干净退出码 0 |
| 2 | conan create 下载 tarball 时 github.com 超时 | 大陆网络访问 github 不稳定 | 命中 E017：conandata.yml 提交官方 URL，CI build_and_test.sh 自动加镜像 fallback；本地验证临时注入 ghfast.top |
| 3 | conan create 单次超过 300s 工具窗口 | openssl 全量编译耗时长 | 内部时限截断处理：记录受影响门禁与原时限，临时提高并行度 -j20 完成验证，随后恢复提交态 -j2 并审计 |
| 4 | test_package 编译失败：OPENSSL_version 未声明 | OpenSSL 公开 API 名为 `OpenSSL_version`（大小写 penSSL） | 修正 test.c 调用，重跑 conan create 通过 1/1 |

## 源码修改

无源码补丁（patches 为空）。适配全部通过 Configure 选项完成：
- E006: `no-asm`（aarch64 汇编 RSA-PSS bug 规避，历史教训 E006）
- E235: `--with-rand-seed=getrandom`（OHOS 熵源，排除 __fd_chk 降级路径）
- R26: `no-shared`（系统同名库 libssl/libcrypto 强制静态，避免污染系统 /lib）

## 依赖版本

- 无 Conan 依赖（requirements 为空；openssl 可选 zlib 未启用，系统仅有运行时 libz.so.1 无头文件）
- 工具链: clang 15.0.4 / make 4.4.1 / perl 5.42.0 / conan 2.30.0 (OHOS 适配版)

## 验证结果

```bash
# upstream_tests: 327 文件 / 3392 测试, Result: PASS, exit 0
# test_package:   1/1 test_crypto Passed (OpenSSL_version / SSL_CTX_new / EVP_Digest / RAND_bytes)
# HarmonyOS 专项: openssl version -a (linux-aarch64, 无 ASM); openssl rand -hex 16 成功; s_server smoke ok
# conan-verify:   G0-G4 + L2/L4/L5 全部 PASS (Verdict: PASS)
# finish:         published, .ci-result.json 写入, submit 就绪 4/4 ✅
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| conanfile.py | 82 行 | custom-perl 配方，no-asm + getrandom + no-shared |
| conandata.yml | — | 官方 GitHub release URL + SHA-256 已核验 |
| test_package/ | — | 实质消费者测试（R34）：版本/SSL_CTX/EVP/RAND_bytes |
| reports/test-report.md | — | 上游测试 + test_package + HarmonyOS 专项记录 |
| packaging/crypto-3.4.7-ohos-aarch64.tar.gz | ~15.6MB | libssl.a/libcrypto.a/include（归档审计用，gitignore 忽略不提交） |

## 注意事项

- 知识路径：路径 A（等价命中 E006/E235/E017），未创建草稿，`path_a_no_knowledge` 记录于 API 拼写候选
- 时限调整审计：conan 门禁本地临时 -j20 完成验证，提交态恢复 -j2；conandata 本地验证临时 ghfast.top 镜像，提交态恢复官方 URL
---

**编译结束**: 2026-09-21
**最终状态**: published
