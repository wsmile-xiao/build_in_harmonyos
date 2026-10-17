# bti 034 原生探索构建证据

在设备上按上游构建文档从最小参数开始的原生探索记录：`./configure
--prefix=<任务私有 prefix>` → `make -j1` → `make install DESTDIR=<task>`，
以及二进制的运行期行为。`configure`/`make` 依赖由 Conan 依赖包提供并经
`PkgConfigDeps` 生成的 `.pc` 注入 `PKG_CONFIG_PATH`。

第 1 次 `configure` 失败（HMDFS：`config.status` 用 `umask 077` 建出不可写的
0700 临时目录）不在本文件里——它是补丁 `0003-configure.patch` 的来源，原始
错误行是 `./config.status[734]: can't create ./confjq6uRh/subs1.awk: Permission
denied`；本文件记录的是修补之后的干净通过过程。

## 逐字证据

- 原始文件：`/storage/Users/currentUser/tmp/bti-034/evidence/native-build-transcript.txt`
- 原始字节数：17316
- 原始行数：252（`wc -l`，即换行符个数）
- sha256（原始文件逐字节）：`7295997e119736c84bd2be4d7aa36c6cc8cb0cf2642a5b12d167173ad19e1cd6`
- 抽取命令（块内含末尾换行，不额外剥除）：

````text
sed -n '/^```text$/,/^```$/p' notes-native-build.md | sed '1d;$d' > native-build-transcript.txt
````

```text
# 原生探索构建逐字记录（/bin/sh 记录）
### 03 configure（打补丁后，rc=0）
checking for a BSD-compatible install... /storage/Users/currentUser/usr/local/bin/ginstall -c
checking whether build environment is sane... yes
checking for a thread-safe mkdir -p... /storage/Users/currentUser/usr/local/bin/mkdir -p
checking for gawk... gawk
checking whether make sets $(MAKE)... yes
checking whether make supports nested variables... yes
checking whether make supports nested variables... (cached) yes
checking for gcc... /data/service/hnp/bin/clang
checking whether the C compiler works... yes
checking for C compiler default output file name... a.out
checking for suffix of executables... 
checking whether we are cross compiling... no
checking for suffix of object files... o
checking whether we are using the GNU C compiler... yes
checking whether /data/service/hnp/bin/clang accepts -g... yes
checking for /data/service/hnp/bin/clang option to accept ISO C89... none needed
checking whether /data/service/hnp/bin/clang understands -c and -o together... yes
checking for style of include used by make... GNU
checking dependency style of /data/service/hnp/bin/clang... gcc3
checking for xsltproc... /data/service/hnp/bin/xsltproc
checking for pkg-config... /data/service/hnp/bin/pkg-config
checking pkg-config is at least version 0.9.0... yes
checking for LIBOAUTH... yes
checking for LIBPCRE... yes
checking for LIBCURL... yes
checking for XML... yes
checking for JSON... yes
checking for library containing dlopen... none required
checking that generated files are newer than configure... done
configure: creating ./config.status
config.status: creating Makefile
config.status: executing depfiles commands

	bti 034
	=======

	prefix:                 /storage/Users/currentUser/tmp/bti-034/native/prefix
	datarootdir:            ${prefix}/share
	mandir:                 ${datarootdir}/man

	compiler:               /data/service/hnp/bin/clang
	cflags:                 -g -O2
	ldflags:                

	xsltproc:               /data/service/hnp/bin/xsltproc

### 04 make -j1（rc=0）
  CC       bti-bti.o
bti.c:808:10: warning: 'oauth_http_get' is deprecated [-Wdeprecated-declarations]
        reply = oauth_http_get(request_url, post_params);
                ^
/storage/Users/currentUser/.conan2/p/b/liboa4862fd7269437/p/include/oauth.h:572:53: note: 'oauth_http_get' has been explicitly marked deprecated here
char *oauth_http_get (const char *u, const char *q) attribute_deprecated;
                                                    ^
/storage/Users/currentUser/.conan2/p/b/liboa4862fd7269437/p/include/oauth.h:51:49: note: expanded from macro 'attribute_deprecated'
#    define attribute_deprecated __attribute__((deprecated))
                                                ^
bti.c:844:10: warning: 'oauth_http_get' is deprecated [-Wdeprecated-declarations]
        reply = oauth_http_get(request_url, post_params);
                ^
/storage/Users/currentUser/.conan2/p/b/liboa4862fd7269437/p/include/oauth.h:572:53: note: 'oauth_http_get' has been explicitly marked deprecated here
char *oauth_http_get (const char *u, const char *q) attribute_deprecated;
                                                    ^
/storage/Users/currentUser/.conan2/p/b/liboa4862fd7269437/p/include/oauth.h:51:49: note: expanded from macro 'attribute_deprecated'
#    define attribute_deprecated __attribute__((deprecated))
                                                ^
bti.c:909:4: warning: 'curl_formadd' is deprecated: since 7.56.0. Use curl_mime_init() [-Wdeprecated-declarations]
                        curl_formadd(&formpost, &lastptr,
                        ^
/storage/Users/currentUser/.conan2/p/curl3b1c48f2fda9f/p/include/curl/curl.h:2624:26: note: 'curl_formadd' has been explicitly marked deprecated here
CURL_EXTERN CURLFORMcode CURL_DEPRECATED(7.56.0, "Use curl_mime_init()")
                         ^
/storage/Users/currentUser/.conan2/p/curl3b1c48f2fda9f/p/include/curl/curl.h:44:18: note: expanded from macro 'CURL_DEPRECATED'
  __attribute__((deprecated("since " # version ". " message)))
                 ^
bti.c:910:10: warning: 'CURLFORM_COPYNAME' is deprecated: since 7.56.0. Use curl_mime_name() [-Wdeprecated-declarations]
                                     CURLFORM_COPYNAME, "status",
                                     ^
/storage/Users/currentUser/.conan2/p/curl3b1c48f2fda9f/p/include/curl/curl.h:2550:28: note: 'CURLFORM_COPYNAME' has been explicitly marked deprecated here
  CURLFORM_COPYNAME        CURL_DEPRECATED(7.56.0, "Use curl_mime_name()"),
                           ^
/storage/Users/currentUser/.conan2/p/curl3b1c48f2fda9f/p/include/curl/curl.h:44:18: note: expanded from macro 'CURL_DEPRECATED'
  __attribute__((deprecated("since " # version ". " message)))
                 ^
bti.c:911:10: warning: 'CURLFORM_COPYCONTENTS' is deprecated: since 7.56.0. Use curl_mime_data() [-Wdeprecated-declarations]
                                     CURLFORM_COPYCONTENTS, session->tweet,
                                     ^
/storage/Users/currentUser/.conan2/p/curl3b1c48f2fda9f/p/include/curl/curl.h:2553:28: note: 'CURLFORM_COPYCONTENTS' has been explicitly marked deprecated here
  CURLFORM_COPYCONTENTS    CURL_DEPRECATED(7.56.0, "Use curl_mime_data()"),
                           ^
/storage/Users/currentUser/.conan2/p/curl3b1c48f2fda9f/p/include/curl/curl.h:44:18: note: expanded from macro 'CURL_DEPRECATED'
  __attribute__((deprecated("since " # version ". " message)))
                 ^
bti.c:914:4: warning: 'curl_formadd' is deprecated: since 7.56.0. Use curl_mime_init() [-Wdeprecated-declarations]
                        curl_formadd(&formpost, &lastptr,
                        ^
/storage/Users/currentUser/.conan2/p/curl3b1c48f2fda9f/p/include/curl/curl.h:2624:26: note: 'curl_formadd' has been explicitly marked deprecated here
CURL_EXTERN CURLFORMcode CURL_DEPRECATED(7.56.0, "Use curl_mime_init()")
                         ^
/storage/Users/currentUser/.conan2/p/curl3b1c48f2fda9f/p/include/curl/curl.h:44:18: note: expanded from macro 'CURL_DEPRECATED'
  __attribute__((deprecated("since " # version ". " message)))
                 ^
bti.c:915:10: warning: 'CURLFORM_COPYNAME' is deprecated: since 7.56.0. Use curl_mime_name() [-Wdeprecated-declarations]
                                     CURLFORM_COPYNAME, "source",
                                     ^
/storage/Users/currentUser/.conan2/p/curl3b1c48f2fda9f/p/include/curl/curl.h:2550:28: note: 'CURLFORM_COPYNAME' has been explicitly marked deprecated here
  CURLFORM_COPYNAME        CURL_DEPRECATED(7.56.0, "Use curl_mime_name()"),
                           ^
/storage/Users/currentUser/.conan2/p/curl3b1c48f2fda9f/p/include/curl/curl.h:44:18: note: expanded from macro 'CURL_DEPRECATED'
  __attribute__((deprecated("since " # version ". " message)))
                 ^
bti.c:916:10: warning: 'CURLFORM_COPYCONTENTS' is deprecated: since 7.56.0. Use curl_mime_data() [-Wdeprecated-declarations]
                                     CURLFORM_COPYCONTENTS, "bti",
                                     ^
/storage/Users/currentUser/.conan2/p/curl3b1c48f2fda9f/p/include/curl/curl.h:2553:28: note: 'CURLFORM_COPYCONTENTS' has been explicitly marked deprecated here
  CURLFORM_COPYCONTENTS    CURL_DEPRECATED(7.56.0, "Use curl_mime_data()"),
                           ^
/storage/Users/currentUser/.conan2/p/curl3b1c48f2fda9f/p/include/curl/curl.h:44:18: note: expanded from macro 'CURL_DEPRECATED'
  __attribute__((deprecated("since " # version ". " message)))
                 ^
bti.c:920:5: warning: 'curl_formadd' is deprecated: since 7.56.0. Use curl_mime_init() [-Wdeprecated-declarations]
                                curl_formadd(&formpost, &lastptr,
                                ^
/storage/Users/currentUser/.conan2/p/curl3b1c48f2fda9f/p/include/curl/curl.h:2624:26: note: 'curl_formadd' has been explicitly marked deprecated here
CURL_EXTERN CURLFORMcode CURL_DEPRECATED(7.56.0, "Use curl_mime_init()")
                         ^
/storage/Users/currentUser/.conan2/p/curl3b1c48f2fda9f/p/include/curl/curl.h:44:18: note: expanded from macro 'CURL_DEPRECATED'
  __attribute__((deprecated("since " # version ". " message)))
                 ^
bti.c:921:11: warning: 'CURLFORM_COPYNAME' is deprecated: since 7.56.0. Use curl_mime_name() [-Wdeprecated-declarations]
                                             CURLFORM_COPYNAME,
                                             ^
/storage/Users/currentUser/.conan2/p/curl3b1c48f2fda9f/p/include/curl/curl.h:2550:28: note: 'CURLFORM_COPYNAME' has been explicitly marked deprecated here
  CURLFORM_COPYNAME        CURL_DEPRECATED(7.56.0, "Use curl_mime_name()"),
                           ^
/storage/Users/currentUser/.conan2/p/curl3b1c48f2fda9f/p/include/curl/curl.h:44:18: note: expanded from macro 'CURL_DEPRECATED'
  __attribute__((deprecated("since " # version ". " message)))
                 ^
bti.c:923:11: warning: 'CURLFORM_COPYCONTENTS' is deprecated: since 7.56.0. Use curl_mime_data() [-Wdeprecated-declarations]
                                             CURLFORM_COPYCONTENTS,
                                             ^
/storage/Users/currentUser/.conan2/p/curl3b1c48f2fda9f/p/include/curl/curl.h:2553:28: note: 'CURLFORM_COPYCONTENTS' has been explicitly marked deprecated here
  CURLFORM_COPYCONTENTS    CURL_DEPRECATED(7.56.0, "Use curl_mime_data()"),
                           ^
/storage/Users/currentUser/.conan2/p/curl3b1c48f2fda9f/p/include/curl/curl.h:44:18: note: expanded from macro 'CURL_DEPRECATED'
  __attribute__((deprecated("since " # version ". " message)))
                 ^
bti.c:927:27: warning: 'CURLOPT_HTTPPOST' is deprecated: since 7.56.0. Use CURLOPT_MIMEPOST [-Wdeprecated-declarations]
                        curl_easy_setopt(curl, CURLOPT_HTTPPOST, formpost);
                                               ^
/storage/Users/currentUser/.conan2/p/curl3b1c48f2fda9f/p/include/curl/curl.h:1225:3: note: 'CURLOPT_HTTPPOST' has been explicitly marked deprecated here
  CURLOPTDEPRECATED(CURLOPT_HTTPPOST, CURLOPTTYPE_OBJECTPOINT, 24,
  ^
/storage/Users/currentUser/.conan2/p/curl3b1c48f2fda9f/p/include/curl/curl.h:1111:43: note: expanded from macro 'CURLOPTDEPRECATED'
#define CURLOPTDEPRECATED(na,t,nu,v,m) na CURL_DEPRECATED(v,m) = t + nu
                                          ^
/storage/Users/currentUser/.conan2/p/curl3b1c48f2fda9f/p/include/curl/curl.h:44:18: note: expanded from macro 'CURL_DEPRECATED'
  __attribute__((deprecated("since " # version ". " message)))
                 ^
bti.c:1006:7: warning: 'curl_formfree' is deprecated: since 7.56.0. Use curl_mime_free() [-Wdeprecated-declarations]
                                                curl_formfree(formpost);
                                                ^
/storage/Users/currentUser/.conan2/p/curl3b1c48f2fda9f/p/include/curl/curl.h:2660:18: note: 'curl_formfree' has been explicitly marked deprecated here
CURL_EXTERN void CURL_DEPRECATED(7.56.0, "Use curl_mime_free()")
                 ^
/storage/Users/currentUser/.conan2/p/curl3b1c48f2fda9f/p/include/curl/curl.h:44:18: note: expanded from macro 'CURL_DEPRECATED'
  __attribute__((deprecated("since " # version ". " message)))
                 ^
bti.c:1018:7: warning: 'curl_formfree' is deprecated: since 7.56.0. Use curl_mime_free() [-Wdeprecated-declarations]
                                                curl_formfree(formpost);
                                                ^
/storage/Users/currentUser/.conan2/p/curl3b1c48f2fda9f/p/include/curl/curl.h:2660:18: note: 'curl_formfree' has been explicitly marked deprecated here
CURL_EXTERN void CURL_DEPRECATED(7.56.0, "Use curl_mime_free()")
                 ^
/storage/Users/currentUser/.conan2/p/curl3b1c48f2fda9f/p/include/curl/curl.h:44:18: note: expanded from macro 'CURL_DEPRECATED'
  __attribute__((deprecated("since " # version ". " message)))
                 ^
bti.c:1029:7: warning: 'curl_formfree' is deprecated: since 7.56.0. Use curl_mime_free() [-Wdeprecated-declarations]
                                                curl_formfree(formpost);
                                                ^
/storage/Users/currentUser/.conan2/p/curl3b1c48f2fda9f/p/include/curl/curl.h:2660:18: note: 'curl_formfree' has been explicitly marked deprecated here
CURL_EXTERN void CURL_DEPRECATED(7.56.0, "Use curl_mime_free()")
                 ^
/storage/Users/currentUser/.conan2/p/curl3b1c48f2fda9f/p/include/curl/curl.h:44:18: note: expanded from macro 'CURL_DEPRECATED'
  __attribute__((deprecated("since " # version ". " message)))
                 ^
bti.c:1039:7: warning: 'curl_formfree' is deprecated: since 7.56.0. Use curl_mime_free() [-Wdeprecated-declarations]
                                                curl_formfree(formpost);
                                                ^
/storage/Users/currentUser/.conan2/p/curl3b1c48f2fda9f/p/include/curl/curl.h:2660:18: note: 'curl_formfree' has been explicitly marked deprecated here
CURL_EXTERN void CURL_DEPRECATED(7.56.0, "Use curl_mime_free()")
                 ^
/storage/Users/currentUser/.conan2/p/curl3b1c48f2fda9f/p/include/curl/curl.h:44:18: note: expanded from macro 'CURL_DEPRECATED'
  __attribute__((deprecated("since " # version ". " message)))
                 ^
bti.c:1050:4: warning: 'curl_formfree' is deprecated: since 7.56.0. Use curl_mime_free() [-Wdeprecated-declarations]
                        curl_formfree(formpost);
                        ^
/storage/Users/currentUser/.conan2/p/curl3b1c48f2fda9f/p/include/curl/curl.h:2660:18: note: 'curl_formfree' has been explicitly marked deprecated here
CURL_EXTERN void CURL_DEPRECATED(7.56.0, "Use curl_mime_free()")
                 ^
/storage/Users/currentUser/.conan2/p/curl3b1c48f2fda9f/p/include/curl/curl.h:44:18: note: expanded from macro 'CURL_DEPRECATED'
  __attribute__((deprecated("since " # version ". " message)))
                 ^
bti.c:1121:13: warning: 'oauth_http_post' is deprecated [-Wdeprecated-declarations]
                                reply = oauth_http_post(req_url, postarg);
                                        ^
/storage/Users/currentUser/.conan2/p/b/liboa4862fd7269437/p/include/oauth.h:629:54: note: 'oauth_http_post' has been explicitly marked deprecated here
char *oauth_http_post (const char *u, const char *p) attribute_deprecated;
                                                     ^
/storage/Users/currentUser/.conan2/p/b/liboa4862fd7269437/p/include/oauth.h:51:49: note: expanded from macro 'attribute_deprecated'
#    define attribute_deprecated __attribute__((deprecated))
                                                ^
bti.c:1128:13: warning: 'oauth_http_get' is deprecated [-Wdeprecated-declarations]
                                reply = oauth_http_get(req_url, postarg);
                                        ^
/storage/Users/currentUser/.conan2/p/b/liboa4862fd7269437/p/include/oauth.h:572:53: note: 'oauth_http_get' has been explicitly marked deprecated here
char *oauth_http_get (const char *u, const char *q) attribute_deprecated;
                                                    ^
/storage/Users/currentUser/.conan2/p/b/liboa4862fd7269437/p/include/oauth.h:51:49: note: expanded from macro 'attribute_deprecated'
#    define attribute_deprecated __attribute__((deprecated))
                                                ^
19 warnings generated.
  CCLD     bti
### 05 make install DESTDIR=…（rc=0）
make[1]: Entering directory '/storage/Users/currentUser/builds/bti-034.work'
 /storage/Users/currentUser/usr/local/bin/mkdir -p '/storage/Users/currentUser/tmp/bti-034/native/stage/storage/Users/currentUser/tmp/bti-034/native/prefix/bin'
  /storage/Users/currentUser/usr/local/bin/ginstall -c bti '/storage/Users/currentUser/tmp/bti-034/native/stage/storage/Users/currentUser/tmp/bti-034/native/prefix/bin'
 /storage/Users/currentUser/usr/local/bin/mkdir -p '/storage/Users/currentUser/tmp/bti-034/native/stage/storage/Users/currentUser/tmp/bti-034/native/prefix/bin'
 /storage/Users/currentUser/usr/local/bin/ginstall -c bti-shrink-urls '/storage/Users/currentUser/tmp/bti-034/native/stage/storage/Users/currentUser/tmp/bti-034/native/prefix/bin'
 /storage/Users/currentUser/usr/local/bin/mkdir -p '/storage/Users/currentUser/tmp/bti-034/native/stage/storage/Users/currentUser/tmp/bti-034/native/prefix/share/man/man1'
 /storage/Users/currentUser/usr/local/bin/ginstall -c -m 644 bti.1 bti-shrink-urls.1 '/storage/Users/currentUser/tmp/bti-034/native/stage/storage/Users/currentUser/tmp/bti-034/native/prefix/share/man/man1'
make[1]: Leaving directory '/storage/Users/currentUser/builds/bti-034.work'
### 06 运行期行为（LD_LIBRARY_PATH 指向 Conan 依赖的 lib 目录）
$ ./bti --version
bti - version 034
rc=0
$ ./bti --debug --dry-run --account=someuser --password=somepass --host=identi.ca --action=update <<< 'hello bti'
bti: main: account = someuser
bti: main: password = somepass
bti: main: host = 2
bti: main: action = 0
bti - version 034
bti: main: tweet = hello bti
bti: main: config file = 
bti: main: host = 2
bti: main: action = 0
bti: send_request: user_password = someuser:somepass
bti: send_request: data = status="hello bti"
bti: send_request: proxy = (null)
```
