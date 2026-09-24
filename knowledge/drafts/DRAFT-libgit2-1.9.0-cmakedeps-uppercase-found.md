# DRAFT-libgit2-1.9.0: CMakeDeps PREFER_CONFIG × 大写 FOUND 变量失配

> 草稿（B 类知识库贡献候选）。关联任务：#libgit2-1.9.0-r01-pc4-30。
> 同根因族：DRAFT-13532（getdns，target 名失配）、E473（target 缺失注入）；
> 本条是新分支——FOUND 变量名大小写失配。

## 错误现场

libgit2 1.9.0 CMake 配置（conan 2 CMakeDeps + ohos-aarch64 profile）：

```
-- Conan: Target declared 'openssl::openssl'
CMake Error at cmake/SelectHTTPSBackend.cmake:57 (message):
  Asked for OpenSSL TLS backend, but it wasn't found
-- Configuring incomplete, errors occurred!
```

## 根因

1. CMakeToolchain 生成的 conan_toolchain.cmake 强制
   `CMAKE_FIND_PACKAGE_PREFER_CONFIG=ON`
2. `find_package(OpenSSL)` 命中 CMakeDeps 的 `openssl-config.cmake`（配置模式），
   该文件只置小写 `openssl_FOUND` 并声明 `openssl::openssl` target
3. libgit2 `SelectHTTPSBackend.cmake:57` 检查的是**大写** `OPENSSL_FOUND`
   （CMake 内置 FindOpenSSL 模块的变量），配置模式下为空 → 误判 OpenSSL 不存在

与 DRAFT-13532 对比：getdns 是上游 Find 模块定义的 target 名（Check::Check）与
CMakeDeps 不一致（Check::check）；本条是上游直接用内置模块的 FOUND 变量名，
conan config 不提供同名大写变量。

## 方案（变量注入，最轻量）

```python
def generate(self):
    tc = CMakeToolchain(self)
    tc.variables["CMAKE_FIND_PACKAGE_PREFER_CONFIG"] = "OFF"   # 回退模块模式
    osl = self.dependencies["openssl"].package_folder
    if osl:
        tc.variables["OPENSSL_ROOT_DIR"] = osl                  # 指向 conan 包
        tc.variables["OPENSSL_INCLUDE_DIR"] = os.path.join(osl, "include")
    tc.generate()
```

模块模式 FindOpenSSL 会设置大写 `OPENSSL_FOUND`/`OPENSSL_INCLUDE_DIR`/
`OPENSSL_LIBRARIES`，libgit2 检测通过。

## 验证

- configure 输出：`-- Found OpenSSL: .../libcrypto.a (found version "1.1.1w")` +
  `* HTTPS, using OpenSSL` + `* SHA256, using OpenSSL`
- conan-verify G2 conan create PASS（test_package 真实 API 运行通过）

## 适用边界 / 反例

- 适用：上游用 `find_package(OpenSSL)` 且检查大写 FOUND 变量的库（libgit2 系、
  其他 HTTPS 后端自检测库），Conan 2 + OHOS 交叉编译
- 反例：上游自带完整 Find 模块且 target 名成套失配（走 DRAFT-13532 的
  CMAKE_PROJECT_INCLUDE 方案）；缺个别 target（走 E473 build-module 注入）

## 查重差异（相对 DRAFT-13532 / E473）

- DRAFT-13532：target 名失配 → CMAKE_PROJECT_INCLUDE 注入禁用 PREFER_CONFIG（全局改查找模式）
- E473：个别 IMPORTED target 缺失 → cmake_build_modules 注入补 target
- 本条：FOUND 变量名大小写失配 → tc.variables 关闭 PREFER_CONFIG + 路径注入，
  改动面最小，不需要额外 .cmake 文件
