# packaging 说明 — boost1.84-random 1.84.0

打包产物（.tar.gz / .sig）由 CI release 流水线在 PR 合并后生成并上传制品仓，
源码仓不入库（.gitignore `archives/**/packaging/*.tar.gz`）。

本地验证产物：
- `libboost_random.a`（random_device.cpp 手动编译，POSIX /dev/urandom 后端）
- 完整 boost/ 头文件树（mt19937/分布器等全部 header-only）

消费方式：
```bash
conan install --requires=boost1.84-random/1.84.0 -pr=<ohos-aarch64 profile>
```
