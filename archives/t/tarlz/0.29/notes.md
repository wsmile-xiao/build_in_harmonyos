# tarlz 0.29 — notes (device verification log appended during build)

## 选库结论（§3.2）
1. 上游：Antonio Diaz，https://www.nongnu.org/lzip/tarlz.html；0.29 经 lzip-bug 邮件列表 release 公告确认，文件在 releases/lzip/tarlz/（注意不是 releases/tarlz/，该路径 404）
2. 语言/构建生态：C++ + autotools（configure 自带，无需自举）；外部库依赖 lzlib（制品仓已发布 lzlib/1.15，直接引用）
3. 源码包为 .tar.lz：conan 2.32 的 unzip_and_get 不支持该后缀，source() 只下载验签，解包（lzip -d + tar -xf）在 build() 经 tool_requires(lzip/1.25) 闭环；lzip CLI 制品仓已发布
4. main/制品双零（2026-09-28 实测）；任务 id=11035，分支 feat/tarlz-0.29
5. 可行性：高；难度 A/B

## 降级边界声明
- 只装 `install-bin`（tarlz 单工具）：`install-doc/install-man` 需 GROFF+ps2pdf（PDF 手册），设备/CI 无此工具链，故文档不随包

## 上游测试执行情况（2026-09-28 设备实测，R51）
- `make check`（testsuite/check.sh，lzip/1.25 入 PATH）：8 命名组全过（--delete/--dereference/--append/dirs-and-links/long-names/--compress/bad-input/--keep-damaged）
- 初始 create/extract roundtrip 内容逐字节一致；6 处 "Mode differs" 均为 mode 位差异（hmdfs 不保留 Unix mode 位，平台文件系统语义，与本配方 umask  workaround 同类），非逻辑失败
- harness 自带平台容忍：link 测试因系统无 ln 被跳过（"ln does not work on your system"）
