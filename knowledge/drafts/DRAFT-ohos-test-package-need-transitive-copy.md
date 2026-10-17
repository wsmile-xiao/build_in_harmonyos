# DRAFT-ohos-test-package-need-transitive-copy：test_package 消费者运行时——NEEDED 传递依赖须全部实体拷贝至 $ORIGIN 并签名； 本地 bin/ 残留手工拷贝库会掩盖缺陷，CI 干净检出才暴露（本地过/CI 败）

> Status: **Draft**（待审核 promote）| severity: `2` | category: `runtime|test_package|conan|ohos|hmdfs|signing|portability` | Updated: ?
> 对应: `knowledge/drafts/DRAFT-ohos-test-package-need-transitive-copy.kv`

---

## 触发面

- trigger_tool: `test_package|conan create|meson`
- phase: `runtime|test_package`

**匹配关键词**：test_package, $ORIGIN, NEEDED 传递依赖, libgpg-error, 实体拷贝, binary-sign-tool, E077 重签名, 本地过 CI 败, 残留 .so, 干净检出, RUNPATH 不含传递依赖 libdir, Error relocating, symbol not found

## 错误签名（error_signature）

```text
Error relocating .*\.so.*: \w+: symbol not found| Error in test\(\) method.*self\.run\(test_binary\)| gpg_strerror: symbol not found
```

## 根因（root_cause）

OHOS 加载器约束（E050/E073/E077）：(a) HMDFS 上经符号链接加载 Conan 缓存内的 .so 失败——必须把运行时依赖库以真实文件拷贝到可执行文件旁（$ORIGIN）； (b) 新拷贝/修改的 ELF 必须 binary-sign-tool 重签名（.codesign）才能执行。 libsecret/0.20.5 的 test_package 实现该逻辑时，NEEDED 遍历只解析了可执行文件 自身的 RUNPATH（meson.build 里 libsecret/glib/libgcrypt 三个 libdir）， 但没有把传递依赖（libgcrypt.so.20 的 NEEDED libgpg-error.so.0）的 libdir 纳入 搜索集：依赖库（libgcrypt.so.20）自身无 RUNPATH，遍历到它时找不到 libgpg-error.so.0 → 未拷贝 → 运行时加载器从 Conan 缓存路径加载 libgcrypt.so.20 并重定位失败（gpg_strerror: symbol not found）→ test() 的 self.run(test_binary) 崩溃。关键陷阱：本地 test_package/bin/ 残留了之前手工拷贝的 7 个 .so （libgpg-error/libgcrypt/glib 系，gitignore 不提交），$ORIGIN 命中这些真实文件， 本地 conan-verify/W3 全部通过；CI 是干净检出，bin/ 只有 test_libsecret 本体， 缺陷立即暴露——「本地通过、PR CI 失败」的典型形态（同 babeltrace 草稿第 6 条）。

## 影响范围（affected_scope）

OHOS 上任何消费者 test_package 需要运行时加载共享库链的场景 （glib/gcrypt/gpg-error 等带传递依赖的库）；尤其依赖链 >1 层且依赖库自身无 RUNPATH 时。

## 推荐方案（rec_approach: `test-package-ohos-runtime-full-need-copy（递归收集全部依赖包 libdir + NEEDED 全链实体拷贝 + 逐文件 E077 重签名 + $ORIGIN 置顶）`）

1) 递归遍历依赖图（conan 依赖列表的 package_folder/lib 全部加入搜索集）， 从 test 二进制开始按 NEEDED 逐层展开，每个 .so 以真实文件拷贝到 bindir， 拷贝后立即 binary-sign-tool 重签名（先删旧 .codesign）并 chmod 755； 2) 可执行文件 RUNPATH 必须以 $ORIGIN 开头（meson build_rpath/install_rpath）， 确保实体拷贝优先于 Conan 缓存路径；测试时勿注入 conanrun env （其 LD_LIBRARY_PATH 优先级高于 RUNPATH 会覆盖 $ORIGIN）； 3) 验证前必须清理 test_package/bin 残留（或干净 Conan home 复跑）， 杜绝「本地残留掩盖、CI 暴露」的假通过；CI 日志判定以评论标题 "## CI 校验通过/失败" 为准（状态行可能误报）。

## 验证方式（verification_cmd）

```text
在干净 Conan home（无 test_package/bin 残留）下执行 conan create . -pr:h=.../ohos-aarch64 -pr:b=.../ohos-aarch64 --build=missing 应完整通过并输出 schema/value API OK（exit 0）； CI #49547 复跑应 PASS。
```

---

*本文件由 `knowledge/drafts/DRAFT-ohos-test-package-need-transitive-copy.kv` 字段派生生成（补齐 kv↔md 配套）；内容与 kv 一致，待主编审核 promote 后转入 `knowledge/doc/`。*
