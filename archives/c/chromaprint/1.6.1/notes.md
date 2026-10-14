# Chromaprint 1.6.1 原生适配

已领取任务 contrib-15049，分支 feat/chromaprint-1.6.1。源码为官方发布资产，配方显式选择已发布 fftw3f/3.3.10，避免根据目标机环境自动切换 FFT 后端。

范围是 Chromaprint 库：BUILD_TOOLS=OFF，与上游默认一致；不声称提供 Picard 所需的 fpcalc CLI，也不把 FFmpeg reader 的条件测试算入此配置。

鸿蒙未知 CMake 平台下补全 C/C++ ELF SONAME 标志，构建阶段局部 loader 环境包含 src、lib 和 Conan 外部依赖。CMAKE_SKIP_RPATH 避免安装时对已签名 ELF 改写 RPATH；不写系统目录、不修改依赖缓存。

有效原生 Conan create 已通过：99/99 上游测试，1/1 消费者，26 个断言，非空 75 项音频指纹及压缩/解压/hash 往返；鸿蒙 uname 与 TMPDIR 文件持久化读回通过。

当前未完成框架 conan-verify/finish、完整知识查重及提交合同，未提交 Issue/PR、未触发 Review/CI。测试 MANIFEST 中初始 pending-native-discovery 需在归档阶段根据原始日志补齐正式清单并重新绑定。
