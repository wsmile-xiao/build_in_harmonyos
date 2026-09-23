# packaging 说明 — boost1.84-locale 1.84.0

打包产物（.tar.gz / .sig）由 CI release 流水线在 PR 合并后生成并上传制品仓，
源码仓不入库（.gitignore `archives/**/packaging/*.tar.gz`）。

本地验证产物：
- `libboost_locale.a`（21 源文件手动编译：核心 15 + std 后端 5 + gregorian 1）
- 完整 boost/ 头文件树（locale 及其依赖头文件族）

消费方式：
```bash
conan install --requires=boost1.84-locale/1.84.0 -pr=<ohos-aarch64 profile>
```
