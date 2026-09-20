# 知识候选台账 — sioyek 2.0.0

| # | 知识点 | 去向 |
|---|---|---|
| 1 | qtbase 包 qt.conf/mkspecs *.pri 构建期硬编码路径失效，消费侧 build() 重写指向实际 package 目录（qtsvg 先例复用） | manifest knowledge_gained / notes.md |
| 2 | qt5-qtbase/5.15.2.2 未启用 sharedmemory 特性（QT_NO_SHAREDMEMORY 对全部 TU 生效），QSharedMemory 类不存在 | manifest knowledge_gained / notes.md / R31 草稿 |
| 3 | 上游 sioyek 2.0.0 按 Qt6 头布局写 `#include <qkeyevent.h>`，Qt5.15 须用 qevent.h | manifest knowledge_gained |
| 4 | OHOS GLES 头无桌面 GL 1.x 枚举 GL_CLAMP，GL_CLAMP_TO_EDGE 语义等价替代 | manifest knowledge_gained |
| 5 | mupdf 1.25 删除 pdf_parse_link_uri，fitz 层 fz_resolve_link_dest(ctx, doc, uri) 为等价 API | manifest knowledge_gained |
| 6 | FUSE 文件系统 patch/git apply 失效；补丁可应用性校验须 python hunk 模拟；conandata 补丁采用 git 风格 a/ b/ 前缀以兼容 patch -p1 | notes.md |

知识整理：check-knowledge-gap 复核通过后由 finish 写入 .knowledge-done。
