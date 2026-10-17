# DRAFT: make 4.4.1 整文件替换式 config.guess/config.sub 补丁在 Conan 配方中的覆盖处理

Source package: make/4.4.1(上游 GNU make 4.4.1,autotools,C)

## 现象

仓库中不少 autotools 库的 `patches/` 目录里放的"补丁"实际上是 **config.guess/config.sub 的完整替换文件**(文件名带 `0001-`/`.patch` 后缀,内容是整份 shell 脚本,不是 unified diff)。make/4.4.1 即此形态。

## 根因

- Conan 的 `apply_conandata_patches()` / `git apply` 只接受 unified diff;对整文件替换内容会直接失败或产生无法应用的空 patch。
- 不能为了走 conandata 补丁管线而手工把整文件"逆向"成 diff——维护成本高且易错。

## 处理方式(make/4.4.1 采用)

1. 不创建 `conandata.yml`,源码 URL/SHA256 内联于 `conanfile.py`(同时规避 CI pre-download `BUILD_DIR: parameter not set` 缺陷)。
2. 配方声明 `exports = "patches/*"` 把整文件补丁随配方导出。
3. `build()` 起始处执行 `_apply_config_patches()`:把 `patches/0001-config.guess-harmonyos.patch` 覆盖复制到 `<source>/build-aux/config.guess`(`config.sub` 同理),并补执行位(`chmod +x`)。configure 在补丁之后运行,自然识别 HarmonyOS triplet。

## 边界与注意

- 只适用于"目标路径固定、内容自包含"的整文件替换;若补丁同时改多个文件或需要保留上游更新,应转为真正的 unified diff。
- 覆盖目标路径要基于真实归档结构确认(make 4.4.1 的 config.guess 在 `build-aux/`,部分老包在根目录)。
- 不要把这类覆盖逻辑写进公共脚本或模板(基础设施边界)。

## 验证

- `conan graph info`(Conan 2.29.1,Linux/armv8 profile):配方加载成功,error=null。
- `python -m py_compile`:配方与 test_package 均通过。
- 完整 configure 应用效果待真机/shadow CI 确认(r9 已在设备上手动验证过同样的替换文件可让 configure 识别 aarch64-unknown-linux-ohos)。
