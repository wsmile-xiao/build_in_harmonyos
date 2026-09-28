# DRAFT-installation-birthday-debian-native-pinning

## Debian native 源包作 conan 钉死源：pool tarball + .dsc 互证、镜像备源、载荷边界

### 背景

依赖类任务常见上游形态为 Debian 源包（无 github 发行、无 release tarball）。installation-birthday 20 即此例：上游 = Chris Lamb 维护的 Debian native 包（salsa.debian.org/lamby/installation-birthday），版本号即 Debian sid 版本，salsa 上的 tag 与 Debian changelog 同号。

### 要点

1. **钉死源 = Debian pool 源包 tarball**：native 包（`.dsc` 头 `Format: 3.0 (native)`）无 `.orig.tar` 区分，pool 里的 `<pkg>_<ver>.tar.xz` 就是完整源码；
2. **sha256 钉死依据 = `.dsc` 的 `Checksums-Sha256` 字段**：本地下载 tar.xz 实测互证（installation-birthday_20.tar.xz → `e1ed3ef6…a5621`），一次下载同时核对版本与完整性；
3. **salsa gitlab 的 `/-/archive/<ref>/*.tar.gz` 不可钉死**：服务端即时打包的 gzip 流，每次请求字节可能不同，sha256 校验会失败；`git ls-remote --tags` 仅作 tag 存在性旁证（tag 20 = master HEAD dc916f94 实证）；
4. **备源取官方镜像同文件**：无 gitcode 镜像时，备源用清华 TUNA Debian 镜像同路径文件（同字节同 sha256，且真机侧下载更稳），比"另一份不同字节的备份"可靠得多——一份 sha256 覆盖全部 URL；
5. **载荷边界 = 运行时产物**：debian/ 打包目录（cron.daily 集成、help2man 生成的 manpage 规则、autopkgtest 用例）属发行集成，不进入 conan 包载荷；上游测试若仅存在于 debian/tests（autopkgtest，不随发行物走），适配探针复刻其语义（如 `--verbosity=2` 冒烟）并显式声明。

### 通用性

任何以 Debian/Ubuntu 源包为上游的适配任务（版本号取 sid 版本、源 URL 与 sha256 一次到位、debian/ 目录剥离）可整体套用；RPM/其他发行包的 pool 结构类似，方法可类比迁移。

参考实现：`archives/i/installation-birthday/20/conandata.yml`（主源+TUNA 备源+sha256）、`notes.md`（上游与来源节）。
