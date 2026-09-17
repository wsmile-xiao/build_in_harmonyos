# hsts-test / hsts-db-test 28 项逐项实跑证据（补丁后，-Dtests=true 构建）
## 环境
- 测试二进制目录: /storage/Users/currentUser/.conan2/p/b/libso2bca687fa0e6d/b/builddir/tests
- LD_LIBRARY_PATH: /storage/Users/currentUser/.conan2/p/glibd610586c02b9c/p/lib:/storage/Users/currentUser/.conan2/p/libps28d4305479a99/p/lib:/storage/Users/currentUser/.conan2/p/libng6ed8e1c19a24f/p/lib:/storage/Users/currentUser/usr/local/lib:/storage/Users/currentUser/.conan2/p/b/libso2bca687fa0e6d/b/builddir/tests
- tls_backend: GDummyTlsBackend (supports_tls=0, 无 glib-networking → https_uri 为 NULL)
- 运行方式: <ldpath> ./hsts-test -p /hsts/<name>; exit=0 通过, 1 断言失败, 134 SIGABRT(断言崩溃), 133 为补丁前的 SIGTRAP

## hsts-test (25 项)
- /hsts/case-insensitive-header: exit=134
- /hsts/basic: exit=134
- /hsts/expire: exit=134
- /hsts/delete: exit=1
- /hsts/replace: exit=134
- /hsts/update: exit=134
- /hsts/set_and_delete: exit=134
- /hsts/no_hsts_header: exit=134
- /hsts/persistency: exit=134
- /hsts/subdomains: exit=134
- /hsts/superdomain: exit=134
- /hsts/multiple-headers: exit=134
- /hsts/insecure-sts: exit=0
- /hsts/missing-values: exit=1
- /hsts/invalid-values: exit=1
- /hsts/extra-values: exit=134
- /hsts/duplicated-directives: exit=1
- /hsts/case-insensitive-directives: exit=134
- /hsts/optional-quotations: exit=134
- /hsts/ip-address: exit=1
- /hsts/utf8-address: exit=134
- /hsts/session-policy: exit=1
- /hsts/idna-addresses: exit=0
- /hsts/get-domains: exit=0
- /hsts/get-policies: exit=0

## hsts-db-test (3 项)
- /hsts-db/basic: exit=134
- /hsts-db/subdomains: exit=134
- /hsts-db/large-max-age: exit=134
