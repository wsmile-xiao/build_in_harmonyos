# DRAFT-13491-lesspipe-2.27-toybox-file-mime-fallback

## 问题

lesspipe 的文件类型检测依赖 `file -L -s -b --mime`（GNU file/libmagic 的 MIME 输出）。
OHOS 系统自带的 `file` 是 toybox 0.8.12 实现，只支持 `-bhLs`，**没有 `--mime` 选项，
也没有 libmagic MIME 数据库**：

```
$ file -L -s -b --mime hello.txt.gz
file: Unknown option 'mime' (see "file --help")
```

后果：`filetype()` 里的命令替换得到空串，解析出的 ftype 为空，所有依赖 MIME 的
分支（gzip/bzip2/xz/zstd/lzma 压缩、tar/zip/jar/deb/ar/rar/7z 归档）全部退化成
原始二进制透传。上游测试套件实测 20 个用例失败（tar 成员提取、链式归档、deb/rar/ar
提取、bzip2/lzma/xz/lz4 解压、binary data strings 输出、特殊字符归档成员等）。

## 根因

- OHOS toybox file(1) 无 `--mime`、无 libmagic —— 平台能力差异，非上游 bug。
- 任何"file --mime 识别类型"的脚本工具（lesspipe 及同类预处理器）在 OHOS 上都会
  静默失效，因为命令替换失败返回空串而非报错。

## 修复（platform-adaptive fallback）

在工具自身的类型检测函数里加 fallback（不依赖 GNU file 包，零外部依赖）：

1. `file --mime` 输出为空时，改用 `file -L -s -b` 的描述文本，用 bash case 把
   toybox 的描述映射为等效 MIME：
   - `*tar archive*` → `application/x-tar`
   - `*Zip archive*` → `application/zip`
   - `*gzip/bzip2/xz/zstd compressed*` → `application/gzip|x-bzip2|x-xz|zstd`
   - `*ar archive*` → `application/x-archive`
   - `*7-zip archive*` → `application/x-7z-compressed`
   - `*text*` → `text/plain`（charset 置 utf-8，保持 cat 路径而不是走 strings）
   - `*directory*` → `inode/directory`
2. toybox 报 `data` 的格式，直接探 magic 字节：
   - 前 4 字节 `Rar!` → `application/x-rar`
3. Debian 包是含 `debian-binary` 成员的 ar 归档：读前 32 字节匹配
   `*debian-binary*` → `application/vnd.debian.binary-package`
4. GNU 路径零改动（fallback 只在 `--mime` 失败时触发），同一脚本在
   GNU/Linux 和 OHOS 上都可用。

## 验证

- 上游 test.sh（134 个注册用例）：
  - 补丁前：41 passed / 73 ignored / **20 FAILED**
  - 补丁后：61 passed / 73 ignored / **0 failed**（73 个 ignore 均为缺少可选外部
    工具——rpm2cpio/pandoc/vimcolor/GNU cpio 等，套件自动跳过并打印 needs 提示）
- conan create（ohos-aarch64 profile）：build() 阶段真跑上游套件，test_package
  冒烟（gzip 解压/tar 列表/LESSOPEN 协议/安装完整性）全过。

## 适用范围

任何在 OHOS 上依赖 `file --mime` 做类型分发的 shell/python 工具（预处理器、
文件管理器后端、安装脚本）。核心模式：**检测命令失败返回空 → 描述文本→MIME 映射
→ magic 字节兜底**，可直接迁移。
