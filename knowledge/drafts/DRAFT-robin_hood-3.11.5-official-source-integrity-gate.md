# DRAFT — robin_hood 3.11.5 官方来源完整性门禁

> 草稿（Path B 候选）。本文件与同名 `.kv` 条目成对，仅描述官方来源完整性不变式；
> 不主张任何共享框架修复、完整 finish 成功、远端 CI 成功或任何远端交付。

## 主题（topic）

HarmonyOS PC 三方库 Conan 配方中，源码归档必须始终指向官方 HTTPS 归档，
并对其身份（URL 链、格式、SHA-256）做可审计核验；任何镜像/代理/缓存/file:// 改写
或非归档内容（HTML）响应均视为来源完整性首错。

## 错误特征（error signature）

- `conandata.yml` 中 `sources.url` 在执行期间被改写为 `ghfast.top`、`gh-proxy.com`、
  `file://`、`.build-cache/predl_cache` 等非官方值
- 下载对象为 HTML/错误页而非 `application/x-gzip` 归档
- 下载对象 SHA-256 与配方声明不一致
- 官方 URL 重定向后最终有效 URL 不可追溯，或 HTTPS 身份被降级

## 根因（root cause）

Conan `get()` 对 GitHub 归档仅尝试一次，网络不稳定时失败；为提速/兜底，
部分共享预下载/镜像机制会在执行期间改写来源配置或缓存到本地路径，
导致"配方声明的官方来源"与"实际使用的对象"不一致，且改写痕迹残留在原始日志。

## 受影响行为（affected behavior）

- 官方来源完整性审计无法通过（URL 链/格式/SHA-256 记录不完整或含禁用标记）
- 当前库 Conan/上游/鸿蒙验证的门禁日志可能夹带镜像改写痕迹
- 交付评审时来源证据与原子性审计快照不一致

## 方案（solution）

1. 来源配置全程保持官方 HTTPS 单值 URL：`https://github.com/martinus/robin-hood-hashing/archive/refs/tags/3.11.5.tar.gz`
2. 审计时以 `curl -sSL -D -` 记录完整重定向链与最终有效 URL，确认 HTTPS 身份与
   `Content-Type`，下载后校验 `file` 格式与 `sha256sum`
3. 禁止在来源配置与验证日志中出现 `ghfast`、`gh-proxy`、`file://`、缓存路径
4. 验证完成后删除任务创建的审计下载文件，并证明其不在当前库交付集合

## 适用边界（scope）

适用于 HarmonyOS PC 平台上需要固定官方源码归档的三方库 Conan 配方
（尤其 GitHub 托管的 C/C++ 库）。本条目以 robin_hood 3.11.5 为实例。

## 验证证据（validation evidence）

- 官方归档审计：请求 URL 302 → `codeload.github.com/.../3.11.5`（HTTP 200），
  `Content-Type: application/x-gzip`，177134 字节，SHA-256
  `3693e44dda569e9a8b87ce8263f7477b23af448a3c3600c8ab9004fe79c20ad0` 与配方一致
- `conandata.yml` 执行前/中/后内容与 SHA-256（`dd3b3109...`）保持不变，零禁用标记
- 当前库验证：conan-verify G0-G4 PASS（含消费 test_package、ctest 1/1）、
  上游 doctest 129/129 通过、鸿蒙行为测试通过、W3/W2 通过

## 恢复/维护条件（recovery condition）

- 若来源配置或日志出现任一禁用标记或 SHA/格式不匹配：立即以官方 URL + 期望 SHA-256
  重做审计；共享预下载/镜像机制需恢复原样后重新验证
- 后续版本升级时，以新 tag 的官方归档 URL 与 SHA-256 更新 `conandata.yml` 并重跑本审计
