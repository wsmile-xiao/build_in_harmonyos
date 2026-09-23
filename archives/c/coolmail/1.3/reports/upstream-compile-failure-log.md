# 未打补丁的上游源码编译失败原始日志（一手证据）

> 留档对象：`upstream-compile-failure.log`（工具生成，未打补丁上游源码的编译失败原始日志）
> **权威副本即本文件正文**：下方 fenced 代码块与生成当时的原始 `.log` 逐字节相同。
> 正文 sha256 `d21452210b92f79ca950ff6168618b85f52453bfafa550dd21ce5d5cdb61d32b`；正文 3238 字节 / 39 行。
> 生成命令：`clang -O2 -I<依赖 include 目录> -c coolmail.c -o /dev/null   # 解压原始 tarball 后`
> 原始 `.log` 由 `.gitignore` 的 `reports/` 规则忽略且**每轮重跑会被覆盖**（W3 尤其明显，其中含时间戳与每轮重建的缓存分片目录名），因此正文才是稳定基线，引用请用可搜索标记而不是行号。
> 仓库规则 `.gitcode/review-memory.md` 第 19 条把 `*.log` 列为 PR 禁入文件，故以 `.md` 留档。

```text
# 上游原始源码的编译失败原始日志（未应用任何补丁）
# 生成命令（工作目录 = 解压后的 coolmail-1.3/）：
#   python3 -c "import tarfile; tarfile.open('coolmail-1.3.tar.gz').extractall('.')"
#   /data/service/hnp/bin/clang -O2 -I/storage/Users/currentUser/.conan2/p/libicb7ea26df82991/p/include -I/storage/Users/currentUser/.conan2/p/libsmb2a1d8b212ef1/p/include -I/storage/Users/currentUser/.conan2/p/libx17963afb6a17e9/p/include -I/storage/Users/currentUser/.conan2/p/libx1c96c2c60af230/p/include -I/storage/Users/currentUser/.conan2/p/libxa6898c29f5713b/p/include -I/storage/Users/currentUser/.conan2/p/libxc29481f84b64ed/p/include -I/storage/Users/currentUser/.conan2/p/libxc498d44a255fe8/p/include -I/storage/Users/currentUser/.conan2/p/libxdc31a2415c1ec8/p/include -I/storage/Users/currentUser/.conan2/p/libxt9f52773f49d71/p/include -I/storage/Users/currentUser/.conan2/p/xorgp20459ba402fe7/p/include  -c coolmail.c -o /dev/null
# 退出码: 1
#
coolmail.c:107:4: warning: call to undeclared library function 'strcat' with type 'char *(char *, const char *)'; ISO C99 and later do not support implicit function declarations [-Wimplicit-function-declaration]
   strcat(mailfile_str, cuserid(username));
   ^
coolmail.c:107:4: note: include the header <string.h> or explicitly provide a declaration for 'strcat'
coolmail.c:107:25: warning: call to undeclared function 'cuserid'; ISO C99 and later do not support implicit function declarations [-Wimplicit-function-declaration]
   strcat(mailfile_str, cuserid(username));
                        ^
coolmail.c:107:25: error: incompatible integer to pointer conversion passing 'int' to parameter of type 'const char *' [-Wint-conversion]
   strcat(mailfile_str, cuserid(username));
                        ^~~~~~~~~~~~~~~~~
coolmail.c:352:12: warning: call to undeclared library function 'strcmp' with type 'int (const char *, const char *)'; ISO C99 and later do not support implicit function declarations [-Wimplicit-function-declaration]
      if (!strcmp(argv[i], "-f"))
           ^
coolmail.c:352:12: note: include the header <string.h> or explicitly provide a declaration for 'strcmp'
coolmail.c:355:10: warning: call to undeclared library function 'strncpy' with type 'char *(char *, const char *, unsigned long)'; ISO C99 and later do not support implicit function declarations [-Wimplicit-function-declaration]
         strncpy(mailfile_str, argv[i], 1023);
         ^
coolmail.c:355:10: note: include the header <string.h> or explicitly provide a declaration for 'strncpy'
coolmail.c:469:4: warning: call to undeclared function 'disp_sync'; ISO C99 and later do not support implicit function declarations [-Wimplicit-function-declaration]
   disp_sync();
   ^
coolmail.c:471:14: warning: using the result of an assignment as a condition without parentheses [-Wparentheses]
   if (child = fork())
       ~~~~~~^~~~~~~~
coolmail.c:471:14: note: place parentheses around the assignment to silence this warning
   if (child = fork())
             ^
       (             )
coolmail.c:471:14: note: use '==' to turn this assignment into an equality comparison
   if (child = fork())
             ^
             ==
6 warnings and 1 error generated.
```
