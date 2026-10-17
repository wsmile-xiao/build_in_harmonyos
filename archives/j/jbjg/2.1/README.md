# jbjg（鸿蒙 PC Conan 制品）

JBIG-KIT：ITU-T T.82 无损二值图像压缩库（作者 Markus Kuhn）。本 Conan 包按平台任务名发布为 `jbjg/2.1`，产出静态库 `libjbig.a`。

- 上游：https://www.cl.cam.ac.uk/~mgk25/jbigkit/
- 构建：手写 Makefile（`libjbig/` 下 `make check`，包含上游 tstcodec/tstcodec85），OHOS 适配见 `notes.md`。
- 消费：`self.requires("jbjg/2.1")`，`find_package(JBIG)` → `JBIG::JBIG`。
