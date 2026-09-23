# zchunk

zchunk 是一种分块压缩文件格式及其参考实现（libzck 库与 zck/unzck/zck_delta_size/zck_gen_zdict/zck_read_header/zckdl 工具），专为压缩文件的高效增量下载/差分设计（delt-RPM、MirrorManager 等场景使用）。上游：https://github.com/zchunk/zchunk（MIT）。

- 构建系统：meson（本归档经 vendored meson 1.11.2 适配 conan 流程）
- 适配版本：1.5.2（见 1.5.2/ 子目录与软件级 commands.json 工具声明）
