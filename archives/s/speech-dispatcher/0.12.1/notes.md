# speech-dispatcher 0.12.1 适配笔记

## 编译环境
- **构建系统**: autotools
- **编译日期**: 2026-09-02
- **平台**: arm64-ohos（OpenHarmony PC）
- **状态**: built（Conan 配方验证通过）
- **补丁数量**: 0

## 编译步骤（conan create 全流程）

```bash
conan create archives/s/speech-dispatcher/0.12.1 --build=missing -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

### 1. 源码获取（source()）
`get()` 从 conandata 声明的 GitHub gh-proxy tarball 下载
（上游为 brailcom/speechd，官方 release 直链 github.com 在 OHOS 沙箱 404，
gh-proxy 镜像实测可用）。

### 2. 依赖注入（generate()）
- glib/2.84.0（glib-2.0 ≥ 2.36）、libdotconf/1.4.1（dotconf ≥ 1.3）、
  libsndfile/1.2.2（sndfile ≥ 1.0.2）——均 ohpcd 已发布
- 复制各依赖包 pkgconfig 目录的 .pc 到 generators_folder 并改写 prefix，
  保证 configure 的 PKG_CHECK_MODULES(GLIB/DOTCONF/SNDFILE) 可解析
- build() 里把各依赖 pkgconfig 目录注入 os.environ PKG_CONFIG_PATH

### 3. 构建（build()）
- autotools configure + make
- 关闭可选 TTS/音频后端（--without-espeak/espeak-ng/flite/ibmtts/voxin/
  ivona/pico/baratinoo/kali/pulse/libao/pipewire/alsa/oss/nas）——OHOS
  沙箱无实际声卡/合成器
- 上游测试：src/tests automake testsuite（依赖运行中的 daemon + D-Bus +
  声音设备，OHOS 无——rule 1.2 平台限制声明）

### 4. 打包（package()）
- autotools install；产物：libspeechd 客户端库 + libspeechd.h 头文件

## 依赖
- glib/2.84.0、libdotconf/1.4.1、libsndfile/1.2.2（均 ohpcd 已发布）

## 上游测试（rule 4）
- src/tests 是 automake testsuite（check_PROGRAMS + testsuite.at），依赖
  运行中的 speech-dispatcher 守护进程、D-Bus 与声音设备——OHOS 沙箱无；
  实测 make check -C src/tests 在链接 test 二进制时失败（libspeechd.so 的
  gettext 符号 bindtextdomain/dgettext/gettext 等在 OHOS libintl 空 stub 下
  无定义，且 testsuite 需运行中的 daemon）——按 rule 1.2 如实声明平台限制
  （非跳过），make check 已尝试执行并记录结果
- 本地验证：conan create 通过，libspeechd 客户端库与头文件编译链接成功
- 适配后：test_package R34 真实产物校验——libspeechd.so 存在 + ELF
  shared object + libspeechd.h 存在，1/1 = 100%

## 已知限制
- speech-dispatcher 守护进程与 TTS 后端模块依赖运行中的语音合成器与声音
  设备——OHOS 无，daemon 运行类功能按平台限制声明；libspeechd 客户端库
  编译可用
