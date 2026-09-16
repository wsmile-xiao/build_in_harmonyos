# conan-verify-supplement-raw.log — 逐字留档（原文件不随 PR 入库）

- 原始文件: `archives/d/daemontools-encore/1.11/reports/conan-verify-supplement-raw.log`（本机工作区，未入库）
- 字节数: 2129
- 行数: 30
- sha256: `b11b407c9eb6cc50b806eec622f5ca65d9582d21235bde531be923534283a75e`
- 说明: L4 安全属性表与 L5 两轮清缓存可复现性对照
- 生成命令: `readelf -h/-lW/-dW 遍历 bin/ + 两轮包目录 find|sort|xargs sha256sum|sha256sum`
- 逐字性: fenced 内容与原文件逐字节一致（含行尾空格与末尾空行）；头部字节数/行数/sha256 均对原文件计算

以下为原文件逐字内容（```text 代码块）：

```text
### L4 supplement — readelf of every packaged bin/ entry (package: /storage/Users/currentUser/.conan2/p/b/daemo37628b650ddb4/p)
PROGRAM        TYPE   PIE   RELRO   BIND_NOW  STACK_NX  NEEDED
envdir         DYN    yes   yes     yes       yes       libc.so 
envini         DYN    yes   yes     yes       yes       libc.so 
envuidgid      DYN    yes   yes     yes       yes       libc.so 
fghack         DYN    yes   yes     yes       yes       libc.so 
multilog       DYN    yes   yes     yes       yes       libc.so 
pgrphack       DYN    yes   yes     yes       yes       libc.so 
readproctitle  DYN    yes   yes     yes       yes       libc.so 
setlock        DYN    yes   yes     yes       yes       libc.so 
setuidgid      DYN    yes   yes     yes       yes       libc.so 
setuser        DYN    yes   yes     yes       yes       libc.so 
softlimit      DYN    yes   yes     yes       yes       libc.so 
supervise      DYN    yes   yes     yes       yes       libc.so 
svc            DYN    yes   yes     yes       yes       libc.so 
svok           DYN    yes   yes     yes       yes       libc.so 
svscan         DYN    yes   yes     yes       yes       libc.so 
svscanboot     (/bin/sh script)
svstat         DYN    yes   yes     yes       yes       libc.so 
svup           DYN    yes   yes     yes       yes       libc.so 
tai64n         DYN    yes   yes     yes       yes       libc.so 
tai64nlocal    DYN    yes   yes     yes       yes       libc.so 

### L5 supplement — two clean-cache build rounds, payload hashes
round 1 package: /storage/Users/currentUser/.conan2/p/b/daemo5cdac5efc9ae4/p (conan-verify trusted round)
round 2 package: /storage/Users/currentUser/.conan2/p/b/daemo37628b650ddb4/p
per-file sha256 (bin/ share/man/ licenses/, 40 files): diff => no differences (identical)
round 1 aggregate: d43189014913589b79b96c352c6cb3e43223426b864ad10b68e3d5f1057326ad  -
round 2 aggregate: d43189014913589b79b96c352c6cb3e43223426b864ad10b68e3d5f1057326ad  -
excluded from the aggregate: conaninfo.txt / conanmanifest.txt (conanmanifest.txt first line is a pack timestamp: round1 1789094704 vs round2 1789095954)
```
