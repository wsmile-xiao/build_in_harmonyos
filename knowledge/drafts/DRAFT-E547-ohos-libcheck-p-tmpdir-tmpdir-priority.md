# E547（草稿）: libcheck P_tmpdir 优先于 TMPDIR,/tmp 只读时测试无法启动

## 基本信息
- **严重度**: 3
- **类别**: platform, hmdfs, test-framework
- **作者**: Awstme
- **来源 PR**: (本 PR)
- **来源 commit**: (待提交后回填)

## 错误特征
```
Unable to create temporary file for communication; may not have permissions to do so|
                         check_msg\.c:317
```

## 根因分析
OHOS 设备 /tmp 为只读 root 目录（实测 drwxr-xr-x root root），musl 的 P_tmpdir 宏
固定展开为 "/tmp"；libcheck 0.15.x 的 open_tmp_file（src/check_msg.c）的临时目录
探测顺序是 TEMP → P_tmpdir → TMPDIR → "."，P_tmpdir 排在 TMPDIR 之前，与"环境变量
覆盖内建默认"的常规预期相反。因此即使 export TMPDIR 指向可写任务目录，
mkstemp("/tmp/check_XXXXXX") 仍以只读文件系统失败，check 框架父子进程通信文件
无法创建，所有用例 exit status 2。

## 推荐方案
**方法**: promote-tmpdir-before-p_tmpdir

**说明**: libcheck 作为仅测试使用的私有依赖从源码自建时，在 src/check_msg.c 的
open_tmp_file 中把 getenv("TMPDIR") 探测移到 P_tmpdir 之前（TEMP 保持最高优先），
重建 libcheck.a 后重链测试二进制；运行环境同时显式 export TMPDIR=<任务可写目录>
（配合上游测试沙箱 HOME 口径）。

**验证/命令**:
```
TMPDIR=<可写目录> make check 2>&1 | grep -c "check_msg.c:317"   # 仍>0 即命中本模式
```

## 关键词
libcheck, check_msg.c, mkstemp, P_tmpdir, TMPDIR, TEMP, /tmp read-only,
check 测试, exit status 2, 测试框架迁移

---
*与 E011 的区分：E011 是 umask 077 目录权限位（HMDFS UID 映射）问题，发生在
configure/config.status 阶段；本条发生在测试运行阶段，且调整 TMPDIR 无效是关键指纹。
二者可叠加出现，需按阶段与证据区分。*
