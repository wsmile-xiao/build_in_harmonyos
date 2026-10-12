=== libgit2-tools 1.9.6 上游测试本地实测摘要 ===
日期: 2026-09-18 10:00:22
构建: conan create OHOS aarch64 (clang 15, bundled PCRE2 regex backend)

[libgit2_tests offline 入口 (-xonline)]
  执行: 3010  通过: 2931  SKIP: 79  失败: 0
[libgit2_tests invasive 入口]
  执行: 41  通过: 39  SKIP: 2  失败: 0
[util_tests]
  执行: 447  通过: 446  失败: 1 (dirent::diriter_at_directory_root: '/' Permission denied — 设备沙箱根目录读权限限制，平台环境限制非代码缺陷)
[headertest]
  通过 (exit 0)

合计执行: 3499  通过: 3417  SKIP: 81  失败: 1
豁免: online 系 9 个 ctest 入口 (online/online_customcert/gitdaemon/gitdaemon_namespace/gitdaemon_sha256/ssh/proxy/auth_clone/auth_clone_and_push) 需外网 git daemon/SSH/proxy 服务，离线环境不可达
