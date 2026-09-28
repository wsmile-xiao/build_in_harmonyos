# vor 0.5.8 —— 故障态一手读数（逐字摘录，随 PR 附）

- 摘录棒：**主理-75** · 摘录机：**B 机（HarmonyOS PC aarch64）** · 摘录时刻：2026-09-27
- 本件的存在理由：notes.md §4.2 的「第一条真实错误」原先挂在 reports/conan-create.log 名下，
  而那件是**成功轮**日志、不含任何故障态读数。本件把故障态的**盘上实物**逐字搬进 PR，
  使读者不必依赖设备侧目录即可复核。
- 纪律声明：下面所有引用块都是**逐字摘录、未改一字**（由 awk 的 NR 区间从来源件切出，
  每块上方标注来源代号与行区间）。来源件仍在 B 机原路径，可按 §0 的 sha256 复验。

## 0. 来源件（设备侧绝对路径 + 摘录当时实算哈希：字节 | 行数 | sha256）

| 代号 | 绝对路径 | 字节 | 行数 | sha256 |
|---|---|---|---|---|
| S1 | /storage/Users/currentUser/tmp/ch/home-vor/p/b/vor421b198eeb77c/b/build-release/config.log | 66616 | 820 | 8c828449f40b657206b956af830e929afd7708395c57341d74acda50c8f7bdc3
| S2 | /storage/Users/currentUser/tmp/ch/home-vor/p/b/vor421b198eeb77c/b/build-release/Makefile | 6555 | 174 | a898802e2874ee54868066dfc46df622cdb31bcec0650e4b45092aabcfce5397
| S3 | /storage/Users/currentUser/tmp/ch/home-vor/p/voredd60360bd865/s/Makefile.in | 5142 | 174 | fae0dfd6aca7a598d48cd0b80dedcb78e34bd6e4723385809af2f93df27050fc
| S4 | /storage/Users/currentUser/tmp/ch/home-vor/p/b/vor9bd94de5632d0/b/build-release/config.log | 70564 | 820 | e0433947f4d593ac4074ee9328235ba61717960db24303cdaff924bdcf8e640a
| S5 | /storage/Users/currentUser/tmp/ch/home-vor/p/b/vor9bd94de5632d0/b/build-release/Makefile | 8528 | 174 | ebe51fe29523657ab4e4c27ed9072711d47ba8e6c65fa7aeff713998e3cffeeb
| S6 | /storage/Users/currentUser/tmp/uc2/z75q-vor/probe-real-pcset.log | 2999 | 25 | 30498e10c05a9bff4b65e8b734b7cb46dafbaa9a24df0d9f49be1964099721e4
| S7 | /storage/Users/currentUser/tmp/uc2/z75q-vor/selfcheck-pc-alias.log | 394 | 14 | d9c0a27e6335b5da3894478be3f6d19bacaad8c84505931302fdd3848200a3ec

S1/S2 = 故障态那一轮 conan 包内 build 目录的 config.log 与 config.status 生成的 Makefile
（build-release 目录 mtime 2026-09-27 03:46）。S4/S5 = 修复后最后一轮（同目录 mtime 2026-09-27 04:04）
的同名两件，用作对照。S3 = 上游 tarball 的 Makefile.in（tarball sha256
9003089708327e1a3169b412e16725ccb669dd21465d49abec5aa4e6e4cce09a，见 conandata.yml）。
S6/S7 = 本机制的 pkg-config --debug 实拍（由兄弟棒 z75q 落盘，本窗复算哈希一致后引用）。

## 1. 「假绿」现场：pkg-config --exists 全 rc=0、configure 三句 result: yes（S1 第 106–124 行）

~~~
configure:3380: result: yes
configure:3390: checking for SDL
configure:3397: $PKG_CONFIG --exists --print-errors "sdl >= 1.2"
configure:3400: $? = 0
configure:3414: $PKG_CONFIG --exists --print-errors "sdl >= 1.2"
configure:3417: $? = 0
configure:3475: result: yes
configure:3481: checking for SDL_IMAGE
configure:3488: $PKG_CONFIG --exists --print-errors "SDL_image >= 1.2"
configure:3491: $? = 0
configure:3505: $PKG_CONFIG --exists --print-errors "SDL_image >= 1.2"
configure:3508: $? = 0
configure:3546: result: yes
configure:3552: checking for SDL_MIXER
configure:3559: $PKG_CONFIG --exists --print-errors "SDL_mixer >= 1.2"
configure:3562: $? = 0
configure:3576: $PKG_CONFIG --exists --print-errors "SDL_mixer >= 1.2"
configure:3579: $? = 0
configure:3617: result: yes
~~~

⇒ 三格 PKG_CHECK_MODULES 全报成功（$? = 0 → result: yes），故障藏到这里还看不出来。

## 2. 同一轮里唯一落了盘的 ld.lld 原文 —— 但它**不是**本机制的证据（S1 第 125–135 行）

~~~
configure:3623: checking for IMG_LoadPNG_RW in -lSDL_image
configure:3648: /data/service/hnp/bin/clang -o conftest -O3 -DNDEBUG -I/storage/Users/currentUser/tmp/ch/home-vor/p/sdl_i6806c92396375/p/include -I/storage/Users/currentUser/tmp/ch/home-vor/p/sdl_m75bc569fbe221/p/include -I/storage/Users/currentUser/tmp/ch/home-vor/p/libtif1285c27f6987/p/include -I/storage/Users/currentUser/tmp/ch/home-vor/p/libpn5853a41e8625a/p/include -I/storage/Users/currentUser/tmp/ch/home-vor/p/sdl12eb04425fea651/p/include/SDL -I/storage/Users/currentUser/tmp/ch/home-vor/p/libwe0ec18ba5a65fb/p/include -I/storage/Users/currentUser/tmp/ch/home-vor/p/zstda785316832b9b/p/include -I/storage/Users/currentUser/tmp/ch/home-vor/p/libjp48ea65bd29cfb/p/include -I/storage/Users/currentUser/tmp/ch/home-vor/p/zlibef5df15a693be/p/include -L/storage/Users/currentUser/tmp/ch/home-vor/p/sdl_i6806c92396375/p/lib -L/storage/Users/currentUser/tmp/ch/home-vor/p/sdl_m75bc569fbe221/p/lib -L/storage/Users/currentUser/tmp/ch/home-vor/p/libtif1285c27f6987/p/lib -L/storage/Users/currentUser/tmp/ch/home-vor/p/libpn5853a41e8625a/p/lib -L/storage/Users/currentUser/tmp/ch/home-vor/p/sdl12eb04425fea651/p/lib -L/storage/Users/currentUser/tmp/ch/home-vor/p/libwe0ec18ba5a65fb/p/lib -L/storage/Users/currentUser/tmp/ch/home-vor/p/zstda785316832b9b/p/lib -L/storage/Users/currentUser/tmp/ch/home-vor/p/libjp48ea65bd29cfb/p/lib -L/storage/Users/currentUser/tmp/ch/home-vor/p/zlibef5df15a693be/p/lib conftest.c -lSDL_image  -lSDL_image -lSDL_mixer -ltiff -lpng -lSDL-1.2 -lwebp -lsharpyuv -lzstd -ljpeg -lturbojpeg -lz >&5
configure:3648: $? = 0
configure:3657: result: yes
configure:3669: checking for Mix_InitOgg in -lSDL_mixer
configure:3694: /data/service/hnp/bin/clang -o conftest -O3 -DNDEBUG -I/storage/Users/currentUser/tmp/ch/home-vor/p/sdl_i6806c92396375/p/include -I/storage/Users/currentUser/tmp/ch/home-vor/p/sdl_m75bc569fbe221/p/include -I/storage/Users/currentUser/tmp/ch/home-vor/p/libtif1285c27f6987/p/include -I/storage/Users/currentUser/tmp/ch/home-vor/p/libpn5853a41e8625a/p/include -I/storage/Users/currentUser/tmp/ch/home-vor/p/sdl12eb04425fea651/p/include/SDL -I/storage/Users/currentUser/tmp/ch/home-vor/p/libwe0ec18ba5a65fb/p/include -I/storage/Users/currentUser/tmp/ch/home-vor/p/zstda785316832b9b/p/include -I/storage/Users/currentUser/tmp/ch/home-vor/p/libjp48ea65bd29cfb/p/include -I/storage/Users/currentUser/tmp/ch/home-vor/p/zlibef5df15a693be/p/include -L/storage/Users/currentUser/tmp/ch/home-vor/p/sdl_i6806c92396375/p/lib -L/storage/Users/currentUser/tmp/ch/home-vor/p/sdl_m75bc569fbe221/p/lib -L/storage/Users/currentUser/tmp/ch/home-vor/p/libtif1285c27f6987/p/lib -L/storage/Users/currentUser/tmp/ch/home-vor/p/libpn5853a41e8625a/p/lib -L/storage/Users/currentUser/tmp/ch/home-vor/p/sdl12eb04425fea651/p/lib -L/storage/Users/currentUser/tmp/ch/home-vor/p/libwe0ec18ba5a65fb/p/lib -L/storage/Users/currentUser/tmp/ch/home-vor/p/zstda785316832b9b/p/lib -L/storage/Users/currentUser/tmp/ch/home-vor/p/libjp48ea65bd29cfb/p/lib -L/storage/Users/currentUser/tmp/ch/home-vor/p/zlibef5df15a693be/p/lib conftest.c -lSDL_mixer  -lSDL_image -lSDL_image -lSDL_mixer -ltiff -lpng -lSDL-1.2 -lwebp -lsharpyuv -lzstd -ljpeg -lturbojpeg -lz >&5
ld.lld: error: undefined symbol: Mix_InitOgg
>>> referenced by conftest.c
>>>               /storage/Users/currentUser/tmp/conftest-2a88a5.o:(main)
clang-15: error: linker command failed with exit code 1 (use -v to see invocation)
configure:3694: $? = 1
~~~

第 131 行「ld.lld: error: undefined symbol: Mix_InitOgg」确实是盘上实物的链接器原文，
它落在「configure:3694: $? = 1」之前 ⇒ 出自 AC_CHECK_LIB([SDL_mixer],[Mix_InitOgg]) 的 conftest 链接。
⚠ 归属必须说死：第 130 行的链接行里 -lSDL_mixer 明明在位（出现两次），拿不到 Mix_InitOgg
是因为该 sdl_mixer 构建时关掉了 ogg/mod 解码 —— 对应 notes.md §3 的**依赖能力缺口**，
**不是**本条 §4.2 的别名自引用。同段第 126–128 行的 IMG_LoadPNG_RW 探针 result: yes（第 127 行 $? = 0），
也与别名故障无关。本窗把这一段放进来，是为了让读者知道"这一轮 config.log 里的 ld.lld 只此一处、
且属于另一件事"，免得把它错当本机制的凭据。本机制的盘上凭据是 §1 + §3 + §4/§5 + §6 + §7。

## 3. 缓存值读数：SDL 本体有值、image/mixer 四格全空（S1 第 691–692 行 与 第 705–710 行）

~~~
ac_cv_lib_SDL_image_IMG_LoadPNG_RW=yes
ac_cv_lib_SDL_mixer_Mix_InitOgg=no
~~~

~~~
pkg_cv_SDL_CFLAGS=-I/storage/Users/currentUser/tmp/ch/home-vor/p/sdl12eb04425fea651/p/include/SDL
pkg_cv_SDL_IMAGE_CFLAGS=''
pkg_cv_SDL_IMAGE_LIBS=''
pkg_cv_SDL_LIBS='-L/storage/Users/currentUser/tmp/ch/home-vor/p/sdl12eb04425fea651/p/lib -lSDL-1.2'
pkg_cv_SDL_MIXER_CFLAGS=''
pkg_cv_SDL_MIXER_LIBS=''
~~~

⇒ 这就是 notes.md §4.2 说的「configure 打印 yes、pkg_cv_* 却为空」：pkg_cv_SDL_IMAGE_CFLAGS、
pkg_cv_SDL_IMAGE_LIBS、pkg_cv_SDL_MIXER_CFLAGS、pkg_cv_SDL_MIXER_LIBS 四格为**空串**，
而 pkg_cv_SDL_CFLAGS / pkg_cv_SDL_LIBS 有值（选择性症状：sdl 与 sdl12-compat 拼写不成对 ⇒ 幸存）。

## 4. 故障态的链接输入：SDL_LIBS 里 image/mixer 两格被替换成空（S2 第 30–47 行）

~~~
CC = /data/service/hnp/bin/clang
CPPFLAGS = -DNDEBUG -I/storage/Users/currentUser/tmp/ch/home-vor/p/sdl_i6806c92396375/p/include -I/storage/Users/currentUser/tmp/ch/home-vor/p/sdl_m75bc569fbe221/p/include -I/storage/Users/currentUser/tmp/ch/home-vor/p/libtif1285c27f6987/p/include -I/storage/Users/currentUser/tmp/ch/home-vor/p/libpn5853a41e8625a/p/include -I/storage/Users/currentUser/tmp/ch/home-vor/p/sdl12eb04425fea651/p/include/SDL -I/storage/Users/currentUser/tmp/ch/home-vor/p/libwe0ec18ba5a65fb/p/include -I/storage/Users/currentUser/tmp/ch/home-vor/p/zstda785316832b9b/p/include -I/storage/Users/currentUser/tmp/ch/home-vor/p/libjp48ea65bd29cfb/p/include -I/storage/Users/currentUser/tmp/ch/home-vor/p/zlibef5df15a693be/p/include
CFLAGS = $(CPPFLAGS) -O3
LDFLAGS = -L/storage/Users/currentUser/tmp/ch/home-vor/p/sdl_i6806c92396375/p/lib -L/storage/Users/currentUser/tmp/ch/home-vor/p/sdl_m75bc569fbe221/p/lib -L/storage/Users/currentUser/tmp/ch/home-vor/p/libtif1285c27f6987/p/lib -L/storage/Users/currentUser/tmp/ch/home-vor/p/libpn5853a41e8625a/p/lib -L/storage/Users/currentUser/tmp/ch/home-vor/p/sdl12eb04425fea651/p/lib -L/storage/Users/currentUser/tmp/ch/home-vor/p/libwe0ec18ba5a65fb/p/lib -L/storage/Users/currentUser/tmp/ch/home-vor/p/zstda785316832b9b/p/lib -L/storage/Users/currentUser/tmp/ch/home-vor/p/libjp48ea65bd29cfb/p/lib -L/storage/Users/currentUser/tmp/ch/home-vor/p/zlibef5df15a693be/p/lib
LIBS = -lSDL_image -lSDL_image -lSDL_mixer -ltiff -lpng -lSDL-1.2 -lwebp -lsharpyuv -lzstd -ljpeg -lturbojpeg -lz
INSTALL = /storage/Users/currentUser/usr/local/bin/ginstall -c


exe_name = vor



paths := -DDATA_PREFIX=\"$(pkgdatadir)\"
SDL_CFLAGS := -I/storage/Users/currentUser/tmp/ch/home-vor/p/sdl12eb04425fea651/p/include/SDL  
SDL_LIBS := -L/storage/Users/currentUser/tmp/ch/home-vor/p/sdl12eb04425fea651/p/lib -lSDL-1.2  

ldflags := $(SDL_LIBS) $(LDFLAGS) -lm
cflags := -I. $(SDL_CFLAGS) $(paths) $(CFLAGS)
~~~

第 44 行 SDL_LIBS 只有 -L<sdl12-compat>/lib -lSDL-1.2，行尾留下「两格空替换」的双空格痕迹；
第 33 行 LDFLAGS 只有九枚 -L、**一枚 -l 都没有**。

## 5. 为什么「少一格」就等于「链接行少一组 -l」（S3 第 42–47 行 与 第 113–114 行）

~~~
paths := -DDATA_PREFIX=\"$(pkgdatadir)\"
SDL_CFLAGS := @SDL_CFLAGS@ @SDL_MIXER_CFLAGS@ @SDL_IMAGE_CFLAGS@
SDL_LIBS := @SDL_LIBS@ @SDL_MIXER_LIBS@ @SDL_IMAGE_LIBS@

ldflags := $(SDL_LIBS) $(LDFLAGS) -lm
cflags := -I. $(SDL_CFLAGS) $(paths) $(CFLAGS)
~~~

~~~
$(exe_name): $(objects)
	$(CC) $^ $(ldflags) -o $@
~~~

第 114 行的链接命令**只吃 $(ldflags)**，而 ldflags := $(SDL_LIBS) $(LDFLAGS) -lm（第 46 行），
SDL_LIBS 又由第 44 行的 @SDL_LIBS@ @SDL_MIXER_LIBS@ @SDL_IMAGE_LIBS@ 三格 substitution 决定。
⇒ 上游 Makefile **不引用** conan 注入的 LIBS 变量（S2 第 34 行那句 -lSDL_image -lSDL_mixer …
到不了链接行），所以 pkg-config 一被清空，-lSDL_image / -lSDL_mixer 就真的不在链接行里，
只剩一串 -L 加 -lSDL-1.2 —— 与 §4 的读数一一对上。

## 6. 修复态对照（S4 第 705–710 行 与 S5 第 43–44 行）

~~~
pkg_cv_SDL_CFLAGS='-I/storage/Users/currentUser/tmp/ch/home-vor/p/sdl12eb04425fea651/p/include/SDL -I/storage/Users/currentUser/tmp/ch/home-vor/p/sdl12eb04425fea651/p/include'
pkg_cv_SDL_IMAGE_CFLAGS='-I/storage/Users/currentUser/tmp/ch/home-vor/p/sdl_i6806c92396375/p/include -I/storage/Users/currentUser/tmp/ch/home-vor/p/sdl_i6806c92396375/p/include/SDL -I/storage/Users/currentUser/tmp/ch/home-vor/p/sdl_i6806c92396375/p/include -I/storage/Users/currentUser/tmp/ch/home-vor/p/sdl12eb04425fea651/p/include/SDL -I/storage/Users/currentUser/tmp/ch/home-vor/p/libpn5853a41e8625a/p/include -I/storage/Users/currentUser/tmp/ch/home-vor/p/libtif1285c27f6987/p/include -I/storage/Users/currentUser/tmp/ch/home-vor/p/zlibef5df15a693be/p/include -I/storage/Users/currentUser/tmp/ch/home-vor/p/libjp48ea65bd29cfb/p/include -I/storage/Users/currentUser/tmp/ch/home-vor/p/zstda785316832b9b/p/include -I/storage/Users/currentUser/tmp/ch/home-vor/p/libwe0ec18ba5a65fb/p/include'
pkg_cv_SDL_IMAGE_LIBS='-L/storage/Users/currentUser/tmp/ch/home-vor/p/sdl_i6806c92396375/p/lib -L/storage/Users/currentUser/tmp/ch/home-vor/p/sdl12eb04425fea651/p/lib -L/storage/Users/currentUser/tmp/ch/home-vor/p/libpn5853a41e8625a/p/lib -L/storage/Users/currentUser/tmp/ch/home-vor/p/libtif1285c27f6987/p/lib -L/storage/Users/currentUser/tmp/ch/home-vor/p/zlibef5df15a693be/p/lib -L/storage/Users/currentUser/tmp/ch/home-vor/p/libjp48ea65bd29cfb/p/lib -L/storage/Users/currentUser/tmp/ch/home-vor/p/zstda785316832b9b/p/lib -L/storage/Users/currentUser/tmp/ch/home-vor/p/libwe0ec18ba5a65fb/p/lib -lSDL_image -lSDL-1.2 -lpng -ltiff -lz -ljpeg -lturbojpeg -lzstd -lwebp -lsharpyuv'
pkg_cv_SDL_LIBS='-L/storage/Users/currentUser/tmp/ch/home-vor/p/sdl12eb04425fea651/p/lib -lSDL-1.2'
pkg_cv_SDL_MIXER_CFLAGS='-I/storage/Users/currentUser/tmp/ch/home-vor/p/sdl_m75bc569fbe221/p/include -I/storage/Users/currentUser/tmp/ch/home-vor/p/sdl_m75bc569fbe221/p/include/SDL -I/storage/Users/currentUser/tmp/ch/home-vor/p/sdl_m75bc569fbe221/p/include -I/storage/Users/currentUser/tmp/ch/home-vor/p/sdl12eb04425fea651/p/include/SDL'
pkg_cv_SDL_MIXER_LIBS='-L/storage/Users/currentUser/tmp/ch/home-vor/p/sdl_m75bc569fbe221/p/lib -L/storage/Users/currentUser/tmp/ch/home-vor/p/sdl12eb04425fea651/p/lib -lSDL_mixer -lSDL-1.2'
~~~

~~~
SDL_CFLAGS := -I/storage/Users/currentUser/tmp/ch/home-vor/p/sdl12eb04425fea651/p/include/SDL -I/storage/Users/currentUser/tmp/ch/home-vor/p/sdl12eb04425fea651/p/include -I/storage/Users/currentUser/tmp/ch/home-vor/p/sdl_m75bc569fbe221/p/include -I/storage/Users/currentUser/tmp/ch/home-vor/p/sdl_m75bc569fbe221/p/include/SDL -I/storage/Users/currentUser/tmp/ch/home-vor/p/sdl_m75bc569fbe221/p/include -I/storage/Users/currentUser/tmp/ch/home-vor/p/sdl12eb04425fea651/p/include/SDL -I/storage/Users/currentUser/tmp/ch/home-vor/p/sdl_i6806c92396375/p/include -I/storage/Users/currentUser/tmp/ch/home-vor/p/sdl_i6806c92396375/p/include/SDL -I/storage/Users/currentUser/tmp/ch/home-vor/p/sdl_i6806c92396375/p/include -I/storage/Users/currentUser/tmp/ch/home-vor/p/sdl12eb04425fea651/p/include/SDL -I/storage/Users/currentUser/tmp/ch/home-vor/p/libpn5853a41e8625a/p/include -I/storage/Users/currentUser/tmp/ch/home-vor/p/libtif1285c27f6987/p/include -I/storage/Users/currentUser/tmp/ch/home-vor/p/zlibef5df15a693be/p/include -I/storage/Users/currentUser/tmp/ch/home-vor/p/libjp48ea65bd29cfb/p/include -I/storage/Users/currentUser/tmp/ch/home-vor/p/zstda785316832b9b/p/include -I/storage/Users/currentUser/tmp/ch/home-vor/p/libwe0ec18ba5a65fb/p/include
SDL_LIBS := -L/storage/Users/currentUser/tmp/ch/home-vor/p/sdl12eb04425fea651/p/lib -lSDL-1.2 -L/storage/Users/currentUser/tmp/ch/home-vor/p/sdl_m75bc569fbe221/p/lib -L/storage/Users/currentUser/tmp/ch/home-vor/p/sdl12eb04425fea651/p/lib -lSDL_mixer -lSDL-1.2 -L/storage/Users/currentUser/tmp/ch/home-vor/p/sdl_i6806c92396375/p/lib -L/storage/Users/currentUser/tmp/ch/home-vor/p/sdl12eb04425fea651/p/lib -L/storage/Users/currentUser/tmp/ch/home-vor/p/libpn5853a41e8625a/p/lib -L/storage/Users/currentUser/tmp/ch/home-vor/p/libtif1285c27f6987/p/lib -L/storage/Users/currentUser/tmp/ch/home-vor/p/zlibef5df15a693be/p/lib -L/storage/Users/currentUser/tmp/ch/home-vor/p/libjp48ea65bd29cfb/p/lib -L/storage/Users/currentUser/tmp/ch/home-vor/p/zstda785316832b9b/p/lib -L/storage/Users/currentUser/tmp/ch/home-vor/p/libwe0ec18ba5a65fb/p/lib -lSDL_image -lSDL-1.2 -lpng -ltiff -lz -ljpeg -lturbojpeg -lzstd -lwebp -lsharpyuv
~~~

⇒ 同一份配方、同一台机、同一 conan 生成集：把别名改成「读回原 .pc 全文后改写副本」，
四格立刻有值，链接输入里出现 -lSDL_image 与 -lSDL_mixer（S5 第 44 行可见）。

## 7. 机制读数：pkg-config --debug 的同名自引用（S6 全文 25 行）

~~~
===== [A] BUGGY: 只 Requires 前转的别名桩盖住真身 =====
A_UNIQUE_INODES=1
A_lowercase_body_says: 1
A_exists_rc=0
A_dbg_rc=0
14:Searching for 'sdl_image' requirement 'sdl_image'
15:Package sdl_image already in requires chain, skipping
16:Package sdl_image already in requires chain, skipping
19:Package sdl_image already in requires chain, skipping
A_CFLAGS=[]
A_LIBS=[]
A_upper_LIBS=[]
===== [B] FIXED: 读回真身内容改写副本（配方 _write_pkgconfig_aliases 同形） =====
B_UNIQUE_INODES=1
6:Name: SDL_image
9:Libs: -L"${libdir}" -lSDL_image
10:Cflags: -I"${includedir}" -I"/storage/Users/currentUser/tmp/ch/home-vor/p/sdl_i6806c92396375/p/include/SDL" -I"/storage/Users/currentUser/tmp/ch/home-vor/p/sdl_i6806c92396375/p/include"
11:Requires: sdl12-compat libpng libjpeg libtiff-4 libwebp
B_exists_rc=0
B_dbg_rc=0
B_selfref_lines=9
B_upper_CFLAGS=[-I/storage/Users/currentUser/tmp/ch/home-vor/p/sdl_i6806c92396375/p/include -I/storage/Users/currentUser/tmp/ch/home-vor/p/sdl_i6806c92396375/p/include/SDL -I/storage/Users/currentUser/tmp/ch/home-vor/p/sdl_i6806c92396375/p/include -I/storage/Users/currentUser/tmp/ch/home-vor/p/sdl12eb04425fea651/p/include/SDL -I/storage/Users/currentUser/tmp/ch/home-vor/p/libpn5853a41e8625a/p/include -I/storage/Users/currentUser/tmp/ch/home-vor/p/libtif1285c27f6987/p/include -I/storage/Users/currentUser/tmp/ch/home-vor/p/zlibef5df15a693be/p/include -I/storage/Users/currentUser/tmp/ch/home-vor/p/libjp48ea65bd29cfb/p/include -I/storage/Users/currentUser/tmp/ch/home-vor/p/zstda785316832b9b/p/include -I/storage/Users/currentUser/tmp/ch/home-vor/p/libwe0ec18ba5a65fb/p/include]
B_upper_LIBS=[-L/storage/Users/currentUser/tmp/ch/home-vor/p/sdl_i6806c92396375/p/lib -L/storage/Users/currentUser/tmp/ch/home-vor/p/sdl12eb04425fea651/p/lib -L/storage/Users/currentUser/tmp/ch/home-vor/p/libpn5853a41e8625a/p/lib -L/storage/Users/currentUser/tmp/ch/home-vor/p/libtif1285c27f6987/p/lib -L/storage/Users/currentUser/tmp/ch/home-vor/p/zlibef5df15a693be/p/lib -L/storage/Users/currentUser/tmp/ch/home-vor/p/libjp48ea65bd29cfb/p/lib -L/storage/Users/currentUser/tmp/ch/home-vor/p/zstda785316832b9b/p/lib -L/storage/Users/currentUser/tmp/ch/home-vor/p/libwe0ec18ba5a65fb/p/lib -lSDL_image -lSDL-1.2 -lpng -ltiff -lz -ljpeg -lturbojpeg -lzstd -lwebp -lsharpyuv]
B_lower_LIBS=[-L/storage/Users/currentUser/tmp/ch/home-vor/p/sdl_i6806c92396375/p/lib -L/storage/Users/currentUser/tmp/ch/home-vor/p/sdl12eb04425fea651/p/lib -L/storage/Users/currentUser/tmp/ch/home-vor/p/libpn5853a41e8625a/p/lib -L/storage/Users/currentUser/tmp/ch/home-vor/p/libtif1285c27f6987/p/lib -L/storage/Users/currentUser/tmp/ch/home-vor/p/zlibef5df15a693be/p/lib -L/storage/Users/currentUser/tmp/ch/home-vor/p/libjp48ea65bd29cfb/p/lib -L/storage/Users/currentUser/tmp/ch/home-vor/p/zstda785316832b9b/p/lib -L/storage/Users/currentUser/tmp/ch/home-vor/p/libwe0ec18ba5a65fb/p/lib -lSDL_image -lSDL-1.2 -lpng -ltiff -lz -ljpeg -lturbojpeg -lzstd -lwebp -lsharpyuv]
===== END =====
~~~

第 6–7 行是判别式（Searching for 'sdl_image' requirement 'sdl_image' 同名对 + already in requires
chain, skipping），第 10–12 行是结果（A_CFLAGS / A_LIBS / A_upper_LIBS 全空），
第 4 行 A_exists_rc=0 是假绿。另附自造最小复现（S7 全文 14 行）：

~~~
A_unique_inodes=1
A_exists_rc=0
Searching for 'foo' requirement 'foo'
Package foo already in requires chain, skipping
Package foo already in requires chain, skipping
A_libs=[]
B_unique_inodes=1
B_body=[Name: Foo;Description: real package;Version: 1.0;Libs: -lfoo_real;Cflags: -I/opt/inc;]
B_exists_rc=0
B_libs=[-lfoo_real]
B_cflags=[-I/opt/inc]
B_lower_libs=[-lfoo_real]
B_selfref_lines=0
RC=0
~~~

两处读数差异必须写明、不得抹平：S7 用单文件桩探针，目录项只剩 foo.pc 一枚；S6 用 conan 真实
生成集时是另一组目录状态。inode 数与目录项计数**受 HMDFS 目录状态影响**（本窗另址复测出现过
A_unique_inodes=2 / A_dir_entries="foo.pc Foo.pc" 与修复态三值全空两种读数）⇒ 稳定判据只有
「A_libs 为空 + --debug 里的同名对」这一条，其余读数只作现场记录（草稿的「三个探针坑」第三条）。

## 8. 未随 PR 附的读数（如实披露，不冒充可核）

- notes.md §4.2 症状段里那句
  「ld.lld: error: undefined symbol: IMG_Load / Mix_OpenAudio / Mix_LoadMUS / Mix_LoadWAV_RW /
  Mix_PlayChannelTimed …」是**当时最终 vor 链接失败输出的一次性转述**，从未落盘：本窗对
  archives/v/vor/0.5.8/reports/ 四件与两个证据目录全量 grep -cE "undefined symbol" 依次得
  conan-create.log=0、conan-verify-report.md=0、test-report.md=0、w3-local-ci.log=0、
  ~/tmp/uc2/z75v-vor/ 全件=0；对 5 个 vor 包内 build 目录的 config.log 逐件 grep 得
  唯一 1 处命中 = §2 的 Mix_InitOgg（另一码事）。唯一的 IMG_Load 命中是
  w3-local-ci.log:243 与 S1 第 125 行的「checking for IMG_LoadPNG_RW in -lSDL_image」，
  那是 configure 的检查回显，**不是链接失败行**。
- 因此该句在 PR 内的可核支撑改为本件 §1（假绿的 $? = 0 / result: yes）＋ §3–§5
  （空 pkg_cv_* → 空 substitution → 链接行少两组 -l）＋ §6（修复态对照）＋ §7（同名自引用），
  **不再声称**「链接期原文见某日志件」。

## 9. 复现探针（任意 HMDFS 机可跑；命令体与草稿 verification_cmd 同一行）

命令原文（探针脚本文件本体，1 行）：

~~~
sh -c 'd=$HOME/tmp/uc2/z75x-vor-fix/kc-pc-alias; rm -rf $d; mkdir -p $d; printf "Name: foo\nDescription: real package\nVersion: 1.0\nLibs: -lfoo_real\nCflags: -I/opt/inc\n" > $d/foo.pc; printf "Name: Foo\nDescription: forwarding stub\nVersion: 1.0\nRequires: foo\n" > $d/Foo.pc; echo "A_unique_inodes=$(stat -c %i $d/foo.pc $d/Foo.pc | sort -u | wc -l)"; echo "A_dir_entries=$(ls -1 $d | tr "\n" " ")"; PKG_CONFIG_PATH=$d pkg-config --exists Foo; echo "A_exists_rc=$?"; PKG_CONFIG_PATH=$d pkg-config --debug --libs foo 2>&1 | grep -E "Searching for .foo. requirement .foo.|already in requires chain" | head -3; echo "A_libs=[$(PKG_CONFIG_PATH=$d pkg-config --libs foo 2>/dev/null)]"; printf "Name: foo\nDescription: real package\nVersion: 1.0\nLibs: -lfoo_real\nCflags: -I/opt/inc\n" > $d/foo.pc; cp $d/foo.pc $d/orig.pc; sed "s/^Name: foo/Name: Foo/" $d/orig.pc > $d/Foo.pc; rm -f $d/orig.pc; echo "B_unique_inodes=$(stat -c %i $d/foo.pc $d/Foo.pc | sort -u | wc -l)"; echo "B_libs=[$(PKG_CONFIG_PATH=$d pkg-config --libs Foo 2>/dev/null)]"; echo "B_cflags=[$(PKG_CONFIG_PATH=$d pkg-config --cflags Foo 2>/dev/null)]"; echo "B_lower_libs=[$(PKG_CONFIG_PATH=$d pkg-config --libs foo 2>/dev/null)]"'
~~~

本窗实测输出（连跑两次，两次输出逐字节相同，共 11 行）：

~~~
A_unique_inodes=1
A_dir_entries=foo.pc 
A_exists_rc=0
Searching for 'foo' requirement 'foo'
Package foo already in requires chain, skipping
Package foo already in requires chain, skipping
A_libs=[]
B_unique_inodes=1
B_libs=[-lfoo_real]
B_cflags=[-I/opt/inc]
B_lower_libs=[-lfoo_real]
~~~

实测输出件字节数与哈希：284 | 11 | 7906fba85918cab139cbee9011dcc475a1a3d394f14233f0396266a72b1b54f4

- 探针工作目录是**摘录棒**（上一窗）私有目录 $HOME/tmp/uc2/z75x-vor-fix/kc-pc-alias，
  **故意不与他窗的 kc-pc-alias 互踩**；除该路径外命令体与草稿 verification_cmd 一字不差。
  ⚠ 草稿 .kv 现已把探针目录指向**整改棒**的私有目录（见本件 §10）⇒ 本块的 z75x 与 .kv 的
  z75r 只差这一处目录名，读 §9 时按本条理解。
- 上面「命令原文」块 = 草稿 verification_cmd 的那一行本体（外层 export PATH 由调用方提供，
  不在块内）。它与草稿文件的差别只有探针工作目录名一处，见上条。

## 10. 整改棒（写入区 ~/tmp/uc2/z75r-vor-fix2/）把草稿 .kv 的那一行**原样**复跑一遍

取串方式：本仓解析器 `scripts/ohc/models.py:72` 的 `parse_kv_file()` 读
`knowledge/drafts/DRAFT-vor-0.5.8-hmdfs-case-insensitive-pc-alias-self-reference.kv`，得 **41 个键**；
`verification_cmd` 取出的值 = **1199 字节 / 1 行**（无续行；尾部是 `--libs foo 2>/dev/null)]"'`，
**不是悬空 `-`**）。该行（`.kv:116`）整行 sha256 =
`0695b206b320bf6e5abd8b0b4390bd112e4f5b7a138f87925409710a32f9bbc7`。

把取出的串原样交给 bash 连跑两次（PATH 含 `/data/service/hnp/bin` 以取到 pkg-config 0.29.2），
两次输出逐字节相同：`VC_RC=0`｜284 字节｜11 行｜sha256
`7906fba85918cab139cbee9011dcc475a1a3d394f14233f0396266a72b1b54f4`（**与 §9 同值**）：

~~~
A_unique_inodes=1
A_dir_entries=foo.pc 
A_exists_rc=0
Searching for 'foo' requirement 'foo'
Package foo already in requires chain, skipping
Package foo already in requires chain, skipping
A_libs=[]
B_unique_inodes=1
B_libs=[-lfoo_real]
B_cflags=[-I/opt/inc]
B_lower_libs=[-lfoo_real]
~~~

⇒ 两条结论落地：①**单行命令真的可执行**（RC=0，不需要调用方再补任何 shell）；②**换一处私有目录读数
不变**（撰写棒一次 + 本棒两次，三处跑出的字节完全相同）。§7 末段记的「另址跑出 inode=2 / 修复态三值
全空」是另一种目录状态（换假 HOME、或目录里已有内容）下的现场，与本条不冲突——本条只把
「`A_libs` 为空 + `--debug` 的同名对」当判据，inode 数与目录项计数一律不作判据。

## 11. 上游 tarball 实物（整改棒 2026-09-27 复算；notes §1/§6 与本条草稿引用的行号都指这些件）

解包目录 = `/storage/Users/currentUser/tmp/ch/home-vor/p/voredd60360bd865/s/`
（tarball sha256 `9003089708327e1a3169b412e16725ccb669dd21465d49abec5aa4e6e4cce09a`，即 conandata.yml
里那枚；§0 的 S3 就是本表的 Makefile.in，此处把同目录另外四件一次补齐）。

| 件 | 字节 | 行数 | sha256 |
|---|---|---|---|
| Makefile.in | 5142 | 174 | fae0dfd6aca7a598d48cd0b80dedcb78e34bd6e4723385809af2f93df27050fc |
| gfx.mk | 730 | 25 | 5273a7c07712825bc81655d181ec5225e8712d4434cdefccc607500e0953b2a4 |
| povimg.sh | 114 | 3 | 8fc9c3f5002ac60fff2e50bad420b2544ac08647faa8231344c6c51bb33be4e0 |
| INSTALL | 2449 | 106 | 3435ae7cfdd37fb60ba72d1dbde53caeeb0ffce0de92c72ff74a06f5dc812e76 |
| configure.ac | 1196 | 42 | cad1144a2048e40f9cbf0857a1d9b02742966d1308ceb73c758103315ab69757 |

复算读数（本窗逐条实跑，脚本与输出留 `~/tmp/uc2/z75r-vor-fix2/`）：

- `grep -cE "povimg" Makefile.in` = **0**；`grep -cE "povimg" gfx.mk` = **7**。
- `grep -n "^data/" gfx.mk` = **4 / 7 / 10 / 13 / 16 / 24** 共六条 `data/*.png` 再生规则，recipe 全是
  `./povimg.sh +W.. +H.. $< > $@ || sh -c "rm $@; false"`（font.png 那条另依赖现编的 `font_guts`）。
- `Makefile.in:77` = `data: $(graphics) build-dir-data-link`；`:59-60` 定义 `rocks` 与 `graphics`；
  `:116` = `include $(srcdir)/gfx.mk` ⇒ **「`Makefile.in` 里 grep 不到 povimg」绝不等于「没有 PNG 规则」**：
  `include` 之后规则齐全，真实后果是重建 PNG 时缺 `povray`/`pnmtopng` 而失败，不是 `No rule to make target`。
- `povimg.sh:3` = `povray -D +A -O- +FP $* 2>/dev/null | pnmcrop | pnmtopng -transparent '#000000' -gamma .45 2>/dev/null`。
- `INSTALL:13-16` 逐字（原文跨 13-14 两行 + 空行 + 16 行，16 行行首是制表符、词间多个空格）：
  `If you are building from git, (or editing the graphics) you will also` / `need:` /
  `	autoconf      version 2.63 or greater` ⇒ notes §1 引的是**跨行连读**，已在原处标注为节选口径。
- `configure.ac:15-19` = 三枚 `PKG_CHECK_MODULES`（`SDL` 在 :15、`SDL_IMAGE` 在 :16-17、`SDL_MIXER`
  在 :18-19）⇒ 上游要求的模块名 `sdl`/`SDL_image`/`SDL_mixer` 实物在此。
- `command -v povray` 与 `command -v pnmtopng` 在 B 机均 **NOT FOUND**。
- `data/` 条目 61、其中 `*.png` 59；`data/ship.png` 与 `rocks.pov`/`font.pov`/`gfx.mk`/`povimg.sh` 的
  mtime 全部 = 2020-04-18 09:51 ⇒ make 判不需重建 PNG。构建日志里只出现
  `test -e data || ln -s $(srcdir)/data`（实读 = `reports/w3-local-ci.log:312` 与 `:320`），
  且两份随 PR 日志 `grep -c povimg` 均为 **0** ⇒ "整条构建链没调用 povimg.sh" 是可核读数。
