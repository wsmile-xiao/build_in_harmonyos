# DRAFT-appstream-1.2.0-ohos-meson-usr-include-hardcode — meson 硬编码 /usr/include 在 OHOS 配置期失败

> **Contributor**: pc2-19 | **Status**: DRAFT | **Updated**: 2026-09-20
> **Severity**: medium (2) | **Category**: build-system / meson / platform / portability
> **Audience**: 所有在 OHOS（无 /usr/include）上构建 meson 项目且上游硬编码系统头目录的配方

## 触发（trigger）

- appstream 1.2.0（archives/a/appstream/1.2.0）OHOS 适配：上游对 Snowball libstemmer
  用 `cc.find_library('stemmer')` + `include_directories(['/usr/include'])` 探测，
  `/usr/include` 在 OHOS 构建机不存在。

## 症状（symptom）

```
../meson.build:232:23: ERROR: Include dir /usr/include does not exist.
```

meson 对绝对路径 include_directories 在配置期做存在性校验，目录不存在直接 ERROR
（非警告、不可降级）。

## 机制（root cause）

OHOS 构建环境无 `/usr/include`（工具链以 sysroot 方式布局）。上游 meson.build 对
"裸库名 + 系统头目录" 探测的依赖（Snowball stemmer 等）硬编码 `/usr/include`
作为后备 include 目录；meson 配置期校验失败即中断。

## 修复（rec）

最小补丁移除硬编码 include_directories（补丁内不留平台宏，遵循 iron-rules R8）；
头文件由 Conan 依赖经 MesonToolchain `extra_cflags -I<dep>/include` 提供，
`cc.has_header('stemmer.h')` 经 c_args 探测成功。

```patch
--- a/meson.build
+++ b/meson.build
@@ -229,10 +229,12 @@ stemmer_inc_dirs = include_directories()
 if get_option('stemming')
     stemmer_lib = cc.find_library('stemmer', required: true)
-    stemmer_inc_dirs = include_directories(['/usr/include'])
     if not cc.has_header('libstemmer.h')
         ...
+    else
+        # OHOS 构建机无 /usr/include；libstemmer.h 由 Conan 依赖经 extra_cflags -I 提供
+        stemmer_inc_dirs = include_directories()
     endif
 endif
```

配方侧：
```python
stemmer_pkg = self.dependencies["libstemmer"].package_folder
tc.extra_cflags.append(f"-I{os.path.join(stemmer_pkg, 'include')}")
tc.extra_ldflags.append(f"-L{os.path.join(stemmer_pkg, 'lib')}")
```

## 验证（verification）

conan create 配置期通过；主库与测试全部编译链接；harmonyos-test 10/10 PASS。

## 适用边界 / 反例

- 仅影响按裸库名 + 系统头目录探测的库（cc.find_library + cc.has_header）；
- 反例：若上游用 pkg-config dependency() 探测，则走 PKG_CONFIG_PATH 机制，不适用本补丁；
- 反例：全功能 /usr/include 的发行版容器不受影响。

## 关系

- `similar_to`: E075（env 头路径陷阱）、E238（嵌入式 clang 头发现）
- `caused_by`: OHOS 构建机无 /usr/include
- 查重：E498（conan cpp_info.includedirs 默认目录）错误面不同无关；草稿无同面条目。

## 证据

- 补丁：`archives/a/appstream/1.2.0/patches/0001-stemmer-include-dir.patch`
- 构建日志：`archives/a/appstream/1.2.0/reports/conan-create.log`
- 台账：`archives/a/appstream/1.2.0/reports/knowledge-candidate-ledger.md` 候选 1