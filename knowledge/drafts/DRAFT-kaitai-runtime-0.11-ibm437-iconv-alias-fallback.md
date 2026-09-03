# DRAFT: HarmonyOS/musl iconv 缺 IBM437 别名时的编码名回退

- 关联 KV: `knowledge/drafts/DRAFT-kaitai-runtime-0.11-ibm437-iconv-alias-fallback.kv`
- 库: kaitai-runtime 0.11
- 执行器: pc2-5
- 日期: 2026-09-03

## 问题

kaitai-runtime 0.11 的 `kstream::bytes_to_str()` 直接以调用方传入的编码名字符串调用
`iconv_open(KS_STR_DEFAULT_ENCODING, src_enc)`。上游测试以 `"IBM437"` 为编码名：
`bytes_to_str_ibm437`（3 字节转换断言）与 `bytes_to_str_big_dest`（10MB 大缓冲、
期望 3 倍 UTF-8 输出）。在 HarmonyOS PC（musl 系 libc iconv）上，
`iconv_open("UTF-8", "IBM437")` 返回 `EINVAL`，`bytes_to_str` 抛出
`unknown_encoding("IBM437")`，两个测试失败，其余 51 项通过（53 项共 1 disabled）。

## 根因

glibc 系 iconv 对同一 IBM code page 437 同时登记 `IBM437` 与 `CP437` 两个别名；
HarmonyOS 的 musl 系 iconv 只登记 `CP437` / `CP-437` 别名，`IBM437` / `IBM-437`
未登记。这是平台 iconv 别名表差异，不是上游代码缺陷（glibc 平台无此问题）。
本机实测：`iconv_open("UTF-8","CP437")` 成功，`"IBM437"`/`"IBM-437"`/`"437"` 均 EINVAL。
GNU libiconv 静态包（ohpcd libiconv/1.17，系统 iconv 别名转发构建）同样不支持
`IBM437`，因此依赖外部 libiconv 无法解决。

## 方案

源码最小补丁（`kaitai/kaitaistream.cpp` 的 `bytes_to_str` EINVAL 分支）：

```cpp
iconv_t cd = iconv_open(KS_STR_DEFAULT_ENCODING, src_enc);
if (cd == (iconv_t)-1) {
    if (errno == EINVAL) {
        std::string enc(src_enc);
        std::string alias;
        if (enc == "IBM437" || enc == "IBM-437") {
            alias = "CP437";   // HarmonyOS/musl iconv 的平台别名
        }
        if (!alias.empty()) {
            cd = iconv_open(KS_STR_DEFAULT_ENCODING, alias.c_str());
        }
        if (cd == (iconv_t)-1) {
            throw unknown_encoding(src_enc);
        }
    } else {
        throw bytes_to_str_error("error opening iconv");
    }
}
```

- 只影响转换函数内部；glibc 平台上首次调用即成功，行为不变。
- 不引入新依赖、不改 URL、不改 sha256。
- 补丁文件: `archives/k/kaitai-runtime/0.11/patches/0001-ibm437-iconv-alias-fallback.patch`
  （diff a/kaitai/kaitaistream.cpp b/kaitai/kaitaistream.cpp，patch -p1 可应用）

## 验证

- 修复前: `unittest --gtest_filter='*ibm437*:*big_dest*'` → 2 FAILED
  （`unknown encoding: \`IBM437\``）
- 修复后: 2/2 PASSED；全套 `./build-dir/tests/unittest` 53/53 PASSED（1 disabled）
- Conan 干净构建: `conan-verify kaitai-runtime 0.11` → G2 conan create PASS
  （补丁在 conan create 内应用），G0-G4 + L2/L4/L5 全通过
- W3 本地 CI: `.ci-result.json` exit_code=0

## 适用边界

- 适用: musl 系 iconv（HarmonyOS/OpenHarmony、其他 musl 发行版）上以
  `IBM437`/`IBM-437` 调用 iconv 的 C/C++ 库；同代码页别名差异亦可推广到
  其他缺失别名（按平台实测补充映射表）。
- 不适用: glibc 平台（别名齐全，无触发）；非 iconv 转换路径；
  `//IGNORE`/`//TRANSLIT` 后缀问题（见 E039，不同错误面）。

## 反例与限制

- 反例: 用静态 GNU libiconv 依赖代替源码回退——ohpcd libiconv/1.17 实测为
  系统 iconv 别名转发构建，`IBM437` 仍 EINVAL，不解决问题。
- 限制: 别名映射表需随平台实测维护；若上游未来改用 libiconv 或新增编码名，
  需重新评估补丁范围。

## 查重差异

- 快照扫描 `knowledge/graph/E*.kv`（540 条）+ `knowledge/drafts/*.{kv,md}` +
  根目录 `DRAFT-*` 配对：
  - E039（musl iconv 不支持 //IGNORE 后缀）: 同为 musl iconv 兼容问题但
    error_signature、根因、方案均不同（后缀扩展 vs 别名缺失），不构成等价命中。
  - E246/E270/E044/E220/E437: 分别对应 seccomp、CLOCK_SGI_CYCLE、PYTHONHOME、
    权限、Qt 命名问题，与本候选无关。
  - 无任何条目以 `IBM437`/`CP437`/iconv 别名缺失为 error_signature。
- 结论: 无等价命中；候选具有跨库复用价值（任何依赖 iconv 编码转换的库
  在 HarmonyOS 上都会遇到）→ 路径 B（new_draft）。

## 依赖项说明

zlib/1.3.2（配方依赖，KS_ZLIB 通路）与 gtest 1.17.0（仅上游测试构建用，非配方
依赖）为本次适配所用依赖；本知识条目不改变它们的 PR-only 依赖分类，
`issue_action: none` 不变。
