# DRAFT-6053-libmrss-0.19.4-automake-news-missing — GitHub tag 归档缺 NEWS 实体文件，automake 非 foreign 包报 required file './NEWS' not found

- 触发事件：libmrss 0.19.4 适配，autoreconf -fi 自举即败
- 路径：Path B（知识库扩展）
- 编号：DRAFT-6053

## 现象

tarball 解包后 autoreconf -fi（或 automake --add-missing）立即失败：

```
configure.ac:6: installing './compile'
configure.ac:6: installing './config.guess'
...
Makefile.am: error: required file './NEWS' not found
autoreconf: error: automake failed with exit status: 1
```

## 根因

automake 对未声明 `AUTOMAKE_OPTIONS = foreign` 的包（GNU 严格模式）
强制要求 NEWS、README、AUTHORS、ChangeLog 四个文件存在于包顶层。
libmrss 上游 git 仓库本身就没有 NEWS 文件（README/AUTHORS/ChangeLog
有），GitHub 自动生成的 tag 归档（codeload tar.gz）忠实于仓库内容，
于是 tarball 顶层缺 NEWS。上游发布流程从未跑过 autoreconf（发版用的
是仓库维护者本地环境），CI 也没有 autoreconf 步骤，所以上游从未暴露
此问题；对需要 autoreconf 自举的下游（OHOS conan 适配即属此类）则
必现。

## 可复用处置

1. 症状速查：
   ```bash
   tar tzf <tarball> | grep -c '/NEWS'    # 0 且 Makefile.am 无 foreign 即中招
   grep -c "AUTOMAKE_OPTIONS.*foreign" Makefile.am   # 0 = GNU 严格模式
   ```
2. 规避（自举前，不改源码逻辑）：
   ```bash
   touch NEWS   # 空文件即可，automake 只要求存在
   autoreconf -fi
   ```
3. conanfile.py 内等价写法：`conan.tools.files.touch(self, os.path.join(self.source_folder, "NEWS"))`，
   放在 autoreconf 之前；0 源码补丁，conandata.yml 不需要 patch 条目。

## 判定要点

- 与 DRAFT-6051（远端 automake 包丢点文件）区分：6051 是 conan 缓存
  包损坏（No such file or directory 指向 .aclocal-real）；本条错误
  明确指向源码树 './NEWS'，且 fresh 解包必现、与缓存无关。
- 与 missing AC_CONFIG_FILES 等模板错误区分：本条是文件系统实体缺失
  报错（required file '...' not found 路径带 ./），不是模板展开错。
- NEWS 空文件不影响 make check 计数与任何测试逻辑；dist 目标不在
  conan 构建路径上。

## 实证

- libmrss-0.19.4 适配：tar tzf 统计 NEWS 0 个；fresh 解包 +
  autoreconf -fi 复现 exit 1；touch NEWS 后 autoreconf 成功、
  configure 生成 17000+ 行、make / make check 全通过
- 查重：graph 全库 `required file.*NEWS|touch NEWS|NEWS not found`
  0 命中；当前分支 knowledge/drafts/ 18 个草稿 0 命中；libnxml
  分支 DRAFT-6049~6052 无关（perl/点文件/L0o/死域名）
