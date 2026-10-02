# gift 0.1.9 — aarch64-linux-ohos 适配

GNU Gift 0.1.9（GNU 图像检索系统）适配 HarmonyOS PC（aarch64-linux-ohos, clang 15/libc++/C++17）。

## 内容物

- `conanfile.py` — Conan 2 配方（autotools in-source 构建，依赖 expat/2.8.4、libuuid/2.42.2）
- `conandata.yml` — 官方 GNU FTP 源（SHA-256 已核验）+ 3 个 portability 补丁
- `gift-regen-config-files.sh` — 确定性 Makefile 生成脚本（替代 config.status 重生成阶段）
- `patches/` — 0001 构建脚本（config.guess 识别 ohos、mktemp→mkdir、sed 上限、perl 5.42）；0002 C++ 兼容（30 文件）；0003 sed 分隔符 ASCII 化（消除 Latin-1 0xA7 非法字节）
- `test_package/` — 链接期探针：9 库 NEEDED 同加载组 BIND_NOW 重定位 + libMRML `createErrorMessage` API 实调往返

## 本地构建与验证

```bash
conan create <本目录绝对路径> \
  -pr:h=<repo>/ci/conan/profiles/ohos-aarch64 \
  -pr:b=<repo>/ci/conan/profiles/ohos-aarch64 \
  --build=missing
```

test_package 真机输出：

```
createErrorMessage("gift test_package probe") -> 0x... OK
PASS: 9 libs exec-loaded + libMRML API round-trip OK
```

## 适配要点

- 2002 年 autotools 2.13/libtool 1.4 在 HMDFS（0700 setgid tmpdir、禁 exec tarball 内容、禁 make -j）与 toybox（sed 管道写后读损坏、缓冲上限）下的大量兼容修复，见 patches/ 与 notes.md
- libGIFTQuPerl/libGIFTAcPerl 引用宿主 perl 解释器符号（上游设计：gift 客户端以 -Wl,-E 嵌入 perl）；探针以同名空桩满足 BIND_NOW 重定位，另以 CAFPerl 构造桩打破 MRML↔AcPerl 构造环
- 9 个共享库全部 DF_BIND_NOW；libGIFTQuBayesian 为 header-only 不产库
- 串行 make 全量构建约 11 分钟（默认 3600s 超时预算内）
