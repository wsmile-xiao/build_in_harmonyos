# DRAFT-c89stringutils-0.0.2-test-dep-stale-sha256-pin：上游测试头文件固定 SHA-256 过期

> Status: DRAFT | Source: c89stringutils 0.0.2 适配（feat/c89stringutils-0.0.2）

## 问题

上游 `c89stringutils_tests/test_c89stringutils/CMakeLists.txt` 用 `file(DOWNLOAD)`
从 `https://raw.githubusercontent.com/SamuelMarks/greatest/cmake-and-msvc/greatest.h`
下载测试框架头文件，并固定 `GREATEST_SHA256="b3f89eca…"`。实际下载内容经官方直连
与镜像两条路径实测均为 `a0d9697c92d2167bd4ae6e79c56b72d60136c4fd42f7254643a129a9335827c4`，
与 pin 不符 → cmake configure 阶段 `message(FATAL_ERROR "SHA256 hash verification failed")`，
主库源码本身完全正确、网络也正常。

## 根因

上游测试依赖（greatest 仓库的 `cmake-and-msvc` 分支）内容随上游演进，而测试
CMakeLists 中硬编码的 SHA-256 pin 没有同步更新，属于**过期货 pin（stale pin）**，
不是内容被篡改、不是 URL 错误、也不是网络超时。

## 触发条件

1. 上游测试用 `file(DOWNLOAD)` 下载测试专用文件并固定 SHA-256；
2. 测试依赖仓库在 pin 写入后发生过内容变更；
3. `BUILD_TESTING=ON` 且配置阶段执行该下载。

## 方案（可复用修复模式）

1. **双路径交叉验证**：官方直连 + 镜像（如 ghfast.top）分别下载同一文件，比对
   SHA-256 一致 → 证明内容未被篡改，哈希即为当前官方值。
2. **更新 pin**：以 `patches/0001-*-CMakeLists.txt.patch` 形式把过期固定哈希更新为
   实检值，不改主源码、不注释掉校验逻辑。
3. **复验**：`cmake configure && cmake --build && ctest --output-on-failure` 全过，
   上游测试真实执行（本库 1/1 用例、4 断言全过）。

## 验证方法

```bash
curl -fsSL <官方URL> | sha256sum   # 路径 A
curl -fsSL <镜像URL> | sha256sum   # 路径 B（两条路径比对一致）
cmake -S <src> -B build -DBUILD_TESTING=ON && cmake --build build && ctest --output-on-failure
```

## 适用边界

- 适用于所有上游测试通过 `file(DOWNLOAD)` 拉取测试专用文件并固定 SHA-256 的
  CMake 项目（greatest/CppUTest/单头文件测试框架类）。
- 补丁只更新测试 CMakeLists 的 pin，不改变测试注册、不关闭测试套件。

## 反例与限制

- **禁止**：`BUILD_TESTING=OFF` 或跳过校验来掩盖下载失败——上游测试未执行，
  报告虚报覆盖。
- **禁止**：单一路径采集合成哈希直接写死——若该路径返回被改动内容，会固化错误值
  （参考 E406 多路径交叉验证）。
- **限制**：若上游持续漂移且无稳定 pin，回退方案是在 recipe `source()` 用 Conan
  `tools.files.download(..., sha256=已核验值)` 拉取并放到上游约定的构建目录
  （保持测试注册不变），此时本条 pin 更新补丁不再适用。

## 与既有知识差异

- E299 是 conan `source()` 下载失败的分层诊断（传输/HTTP/完整性），不含"上游测试
  依赖固定 pin 过期"这一具体形态。
- E406 面向 recipe 创建期 scout 采集 SHA-256 的多路径交叉验证，触发阶段与本条
  （上游测试 CMakeLists 既有 pin 过期）不同。
- 本库另一候选（conandata 源 URL 指向仓库主页致镜像 403）判定为 E299 等价命中
  （`403 Forbidden`/`Could not download from the URL` 命中其 error_signature），
  走路径 A，不建草稿。

## 字段一致性

- .kv/.md 同 stem 成对；error_signature / root_cause / rec_approach / 验证方法 /
  适用边界 / 反例限制六要素齐全；SHA-256 见草稿对审计记录。
