# DRAFT-13502: 双源受限源码构建期注入配方模式(amrnb/amrwb 类)

## 模式

部分编解码封装项目(amrnb/amrwb)只发布 autotools 骨架，真实厂商源码是**独立的许可受限
压缩包**(3GPP zip 无任何发行版镜像)，需在 make 前放在 configure 旁边。Makefile 自带
prepare 规则(unzip → patch → sed 接口变换)并把生成的 .c/.h 写进 `$(top_srcdir)`。

## 配方要点(libamrnb 11.0.0.0 实证)

1. `conandata.yml` 两个 sources 条目(wrapper tarball、vendor zip),各自 url 列表+sha256;
2. `source()`:`get(entry0, strip_root=True)` 解包 wrapper;`download(entry1.url, "26104-b00.zip",
   sha256=...)` 让 zip 原样落在源码目录(不自动解压);
3. `build()`:整树 `copy(self, "*", source_folder, build_folder)` 后 **in-tree 构建**——
   prepare 规则在一次性副本里生成厂商源码，conan source 缓存保持干净;
4. `build()` 断言 zip 精确大小(26104-b00.zip = 427897 字节),把 WAF 页污染变成可读报错;
5. `make -j1`(prepare 链是上游注释明言的串行点);
6. **构建期宿主工具**:bash/unzip/patch/sed/tr(configure AC_PATH_PROG 强制探测 unzip+patch,
   缺失直接 AC_MSG_ERROR);真机跑包前先 `command -v unzip patch`(实测一台真机缺 unzip)。

## 禁止

- 把厂商受限源码(解包后或重打包)提交进仓库——3GPP 许可限制 + PF2 制品闸。
