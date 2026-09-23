# crunch-dxtc — OpenHarmony 编译档案

## 软件简介
crunch-dxtc 是 DXTc 纹理压缩与转码工具及 crnlib 库（Dæmon 团队维护分支，含 Unity 改进），可压缩/转码 DXT1/5、CRN、DDS、KTX 等 GPU 纹理格式。

## OHOS 适配要点
- 上游为 DaemonEngine/crunch `unvanquished/0.56.2` 标签，CMake 构建，零外部依赖
- `USE_FAST_MATH=OFF`（与上游 CI 一致，保证校验和可复现）
- 静态库需 `BUILD_STATIC_LIBCRN + INSTALL_STATIC_LIBCRN` 才会 install；头文件配方手动 copy
- 上游自带 `test/test.py` harness（89 条校验和），配方在 build() 中全量运行

## 参考资料
- [DaemonEngine/crunch](https://github.com/DaemonEngine/crunch)
- [Ubuntu crunch-dxtc 源码包](https://launchpad.net/ubuntu/+source/crunch-dxtc)
