# jbjg（鸿蒙 PC Conan 制品）

JBIG-KIT：ITU-T T.82 无损二值图像压缩库（作者 Markus Kuhn）。本 Conan 包为 **libtiff 的 JBIG codec 依赖**
先行适配，产出静态库 `libjbig.a`。

- 上游：https://www.cl.cam.ac.uk/~mgk25/jbigkit/
- 构建：手写 Makefile（`libjbig/` 下 `make all check`），OHOS 适配见 `notes.md`。
- 消费：`self.requires("jbjg/2.1")`，`find_package(JBIG)` → `JBIG::JBIG`；或裸程序 deploy 到 `~/usr/local`。
