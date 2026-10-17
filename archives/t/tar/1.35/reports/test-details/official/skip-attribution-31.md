# tar 1.35 上游测试 31 skip 逐项归因（R02）

task: tar-1.35-r02-pc3-13-20260913T113300Z | 数据源: R02 全量重跑 + 工具实测 + .at 源码核对

| # | 入口 | 类别 | 跳过原因（归因） | 依赖/工具实测 | registry 复核 |
|---|---|---|---|---|---|
| 11 | opcomp06 | 格式/版本条件 | opcomp06: --pax-option 与旧版本 pax 兼容性用例——需 GNU tar 构建带特定 pax 选项；当前环境 AT_SKIP_IF 触发（pax_vers 检查） | — | 本期复核：无关 registry（非依赖型 skip） |
| 20 | lzip | 依赖工具缺失 | compress lzip: 依赖工具 lzip 缺失（command -v lzip 实测 MISSING），testsuite AT_GZIP_PREREQ 跳过 | lzip=MISSING | 本期复核：无关 registry（非依赖型 skip） |
| 21 | lzop | 依赖工具缺失 | compress lzop: 依赖工具 lzop 缺失（实测 MISSING），AT_GZIP_PREREQ 跳过 | lzop=MISSING | 本期复核：无关 registry（非依赖型 skip） |
| 22 | zstd | 依赖工具缺失 | compress zstd: 依赖工具 zstd 缺失（实测 MISSING），AT_GZIP_PREREQ 跳过 | zstd=MISSING | 本期复核：无关 registry（非依赖型 skip） |
| 46 | numeric | 平台/文件系统限制 | numeric: --numeric-owner 需 root/特权修改 owner 入口（getuid 检查 / 需 chown），非特权环境跳过 | — | 本期复核：无关 registry（非依赖型 skip） |
| 90 | extrac07 | 平台/文件系统限制 | extrac07: 只读目录 symlink 提取需 chmod 生效（HMDFS chmod 语义，E046 平台限制），AT_SKIP_IF 触发 | — | 本期复核：无关 registry（非依赖型 skip） |
| 92 | extrac09 | 平台/文件系统限制 | extrac09: . 与 .. 不可读目录需特权降级运行，非 root 跳过 | — | 本期复核：无关 registry（非依赖型 skip） |
| 94 | extrac11 | 平台/文件系统限制 | extrac11: scarce file descriptors 需 ulimit 限制可用 FD（资源受限场景），当前环境无限制策略下 AT_SKIP_IF | — | 本期复核：无关 registry（非依赖型 skip） |
| 98 | extrac15 | 平台/文件系统限制 | extrac15: parent mkdir failure 需目录权限冲突构造（HMDFS 权限位不生效），跳过 | — | 本期复核：无关 registry（非依赖型 skip） |
| 104 | extrac21 | 平台/文件系统限制 | extrac21: delay-directory-restore 需非 root 迟延恢复语义验证，环境不支持跳过 | — | 本期复核：无关 registry（非依赖型 skip） |
| 105 | extrac22 | 平台/文件系统限制 | extrac22: delay-directory-restore reversed ordering 同上 | — | 本期复核：无关 registry（非依赖型 skip） |
| 121 | listed03 | 平台/文件系统限制 | listed03: parent unreadable 需特权不可读目录构造（HMDFS 权限位），跳过 | — | 本期复核：无关 registry（非依赖型 skip） |
| 123 | listed05 | 平台/文件系统限制 | listed05: --listed-incremental 与 remounted 目录需 /proc/mounts 多挂载场景，容器环境不满足 | — | 本期复核：无关 registry（非依赖型 skip） |
| 144 | ignfail | 平台/文件系统限制 | ignfail: 需 unreadable 源文件 + readdir 错误模拟（权限位不生效），跳过 | — | 本期复核：无关 registry（非依赖型 skip） |
| 145 | link01 | 平台/文件系统限制 | link01: link count gt 2 需 >2 硬链接计数（HMDFS 硬链接受限/计数语义），跳过 | — | 本期复核：无关 registry（非依赖型 skip） |
| 163 | multiv07 | 格式/版本条件 | multiv07: volumes split at extended header—— AT_SKIP_IF(pax) 版本条件弹窗场景 | — | 本期复核：无关 registry（非依赖型 skip） |
| 174 | sparse06 | 平台/文件系统限制 | sparse06: 需 seek 方法空洞文件（checkseekhole 结果），HMDFS 空洞语义差异跳过 | — | 本期复核：无关 registry（非依赖型 skip） |
| 190 | volsize | 大文件/资源限制 | volsize: volume header size 需 tape 卷容量交互（多卷设备），无多卷设备跳过 | — | 本期复核：无关 registry（非依赖型 skip） |
| 198 | remfiles01 | 格式/版本条件 | remfiles01: remove-files with compression 需 gzip 压缩工具链组合，依赖 lzop/zstd 同类环境跳过 | zstd=MISSING | 本期复核：无关 registry（非依赖型 skip） |
| 228 | acls01 | 依赖工具缺失 | acls01: ACL 基础功能需 setfacl/getfacl（实测 MISSING），AT_SKIP_IF | getfacl=MISSING | 本期复核：无关 registry（非依赖型 skip） |
| 229 | acls02 | 依赖工具缺失 | acls02: ACL -C 需 setfacl（MISSING），跳过 | setfacl=MISSING | 本期复核：无关 registry（非依赖型 skip） |
| 230 | acls03 | 依赖工具缺失 | acls03: default ACLs 需 setfacl（MISSING），跳过 | setfacl=MISSING | 本期复核：无关 registry（非依赖型 skip） |
| 231 | selnx01 | 依赖工具缺失 | selnx01: SELinux store/restore 需 selinux 工具链（chcon/setsebool MISSING），跳过 | chcon=MISSING | 本期复核：无关 registry（非依赖型 skip） |
| 232 | selacl01 | 依赖工具缺失 | selacl01: ACL/SELinux 混合需两套工具（均 MISSING），跳过 | — | 本期复核：无关 registry（非依赖型 skip） |
| 238 | onetop05 | 平台/文件系统限制 | onetop05: --one-top-level 权限恢复需 chmod 语义生效（HMDFS 不生效 E046），跳过 | — | 本期复核：无关 registry（非依赖型 skip） |
| 239 | gtarfail | 对照工具缺失 | gtarfail: star 兼容失败注入用例——需 star/xstar 对照实现（平台无），跳过 | — | 本期复核：无关 registry（非依赖型 skip） |
| 240 | gtarfail2 | 对照工具缺失 | gtarfail2: 同上（star 对照） | — | 本期复核：无关 registry（非依赖型 skip） |
| 241 | multi-fail | 对照工具缺失 | multi-fail: star multivolume 失败注入——需 star 对照，跳过 | — | 本期复核：无关 registry（非依赖型 skip） |
| 242 | ustar-big-2g | 大文件/资源限制 | ustar-big-2g: 需 >2GB 大文件（sparse 2G 制），当前 filesystem 限制跳过 | — | 本期复核：无关 registry（非依赖型 skip） |
| 243 | ustar-big-8g | 大文件/资源限制 | ustar-big-8g: 需 >8GB 大文件，限制同上 | — | 本期复核：无关 registry（非依赖型 skip） |
| 244 | pax-big-10g | 大文件/资源限制 | pax-big-10g: 需 >10GB 大文件，限制同上 | — | 本期复核：无关 registry（非依赖型 skip） |
## 依赖 registry/制品复核记录

### 首次复核（2026-09-13T20:04:25+08:00）
- 命令：`command -v lzip; command -v lzop; command -v zstd; command -v setfacl; command -v getfacl; command -v setcap; command -v getcap`
- cwd：`/storage/Users/currentUser/junshi_liu`
- 退出码：1（lzip/lzop/zstd/setfacl/getfacl/setcap/getcap 全部 MISSING）；setfattr/getfattr FOUND(/usr/bin)
- 结论：工具型 skip 依赖的系统工具在本环境不存在，skip 归因成立（工具缺失，非 registry 制品依赖）
- registry 复核：`conan list "tar/1.35*" -r=ohpcd` → Found 0（tar 尚未发布属预期）；`conan download tar/1.35 -r=ohpcd --only-recipe` → 服务端 system acceleration policy 未开放（不可达，环境策略）；tar conanfile requires 为空（无外部 conan 依赖），全部 31 skip 无一属于"依赖 registry 制品未发布"类型
- 恢复条件：安装对应工具（lzip/lzop/zstd/setfacl/getfacl 等）或使用支持工具链的文件系统后重跑；registry 需分析端开放策略

### 回报前复核（将在最终回报前执行）
- 计划命令：与首次相同 + `conan download` 重试，记录精确版本/时间/退出码
