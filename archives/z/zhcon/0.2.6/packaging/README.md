# zhcon 0.2.6 packaging

zhcon 0.2.6 构建产物打包（本地验证用，Conan 体系以 `conan create` 替代手动 tar.gz 发布）：

- `zhcon-0.2.6.tar.gz` — 本地打包验证产物（被 gitignore 忽略，不入库）
- 正式发布路径：`conan create . -pr:h=ci/conan/profiles/ohos-aarch64` → `conan upload zhcon/0.2.6@ohpcd/stable`