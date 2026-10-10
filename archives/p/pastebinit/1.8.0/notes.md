# pastebinit 1.8.0 适配笔记

## 源码

- 上游：https://launchpad.net/pastebinit
- 源码包：https://deb.debian.org/debian/pool/main/p/pastebinit/pastebinit_1.8.0.orig.tar.gz
- SHA256: fc8ed4323ddfb130c17380af8f4970ac9c1648563fb1ab4efd307e87eb2c41e7

## 构建过程

- 纯 Python3 脚本工具，无 C/C++ 编译步骤
- 构建步骤：`make build-mo` 编译 .po 翻译文件为 .mo (msgfmt)
- 安装步骤：手动使用 shutil 打包（上游 Makefile 使用 `install` 命令，OHOS 无 coreutils install）

## 依赖

- distro/1.9.0：运行时可选依赖，pastebinit 脚本通过 `import distro; distro.id()` 检测 OS 并设置默认 pastebin
  - 源码第 48-59 行：`try: import distro; release = distro.id() ... except ImportError: distro = None`
  - 按任务要求声明为 Conan 强制依赖

## 上游测试

- 测试入口：`test.sh`（shell 集成测试）
- 测试内容：遍历 13 个 pastebin 服务，发送文本并通过 HTTP 客户端验证
- OHOS 适配补丁（patches/fix-ohos-python3-curl.patch）：
  - `python` -> `python3`（OHOS 仅有 python3，无 python）
  - `wget -O - -q` -> `curl -s`（toybox wget 不支持 -q 选项）
  - `echo "$str\n$str"` -> `printf '%s\n'`（POSIX 兼容换行）
- 实测结果（真机，2026-09-10）：
  - PASS: 7/13 (53.8%)
  - PASS 服务：dpaste.com, p.defau.lt, paste.centos.org, paste.debian.net, paste.opendev.org, paste.opensuse.org, pastebin.com
  - FAIL 服务（服务端原因，非环境限制）：
    1. bpa.st - HTTP 400 Bad Request（服务端拒绝请求）
    2. dpaste.org - HTTP 403 Forbidden（服务端拒绝访问）
    3. paste.ubuntu.com - 连接超时（服务端不可达）
    4. paste.ubuntu.org.cn - 响应非 gzip 格式（服务端 API 变更）
    5. paste2.org - DNS 解析失败（域名不可达）
    6. sprunge.us - HTTP 404 Not Found（服务端 API 变更）
- 测试在 conanfile.py build() 中通过 `self.run('sh test.sh', cwd=self.source_folder)` 执行
- 非网络冒烟测试通过：`pastebinit -h`、`pastebinit -v`、`pastebinit -l`

## OHOS 平台适配

- 补丁：patches/fix-ohos-python3-curl.patch（test.sh 兼容性修复：python->python3, wget->curl, echo->printf）
- conanfile.py 在 build() 中使用 `self.run('msgfmt ...')` 编译翻译
- conanfile.py 在 build() 中运行 `sh test.sh` 执行上游集成测试
- conanfile.py 在 package() 中使用 shutil 手动打包（绕过 `install` 命令缺失）
- package_info() 设置 bindirs=["bin"]，并注入 PATH

最终状态: built
---

**编译结束**: 2026-09-09 16:19
**最终状态**: built
