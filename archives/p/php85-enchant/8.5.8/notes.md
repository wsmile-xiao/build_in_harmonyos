# php85-enchant 8.5.8 适配笔记

任务 #367，分支 `feat/php85-enchant-8.5.8`。

## 源码及语言

使用 PHP 官方 `php-8.5.8.tar.gz`，SHA256 为 `6ebc55e52af4396385e689f7af0f28944fbbf966843433b573e9dc1dc03df539`。构建范围为 `ext/enchant`，其生产实现为 `enchant.c`。语言预检 task=cpp / detected=c，按 R47 兼容族通过。未裁剪生产功能、未修改任何上游 PHPT。

## 依赖发布核验

在共享 Conan 空闲时分别执行 `conan download --only-recipe` 和 `conan download`，php/8.5.8、enchant/2.8.2、glib/2.84.0.1 均退出 0，验证 OHOS armv8 二进制存在。最终完整依赖图以 conan create 实测日志为准。

## 适配

1. 将官方扩展目录复制到当前 Conan build_folder，使用依赖包的 phpize 生成扩展构建系统。
2. 已发布 PHP 的 phpize/php-config 为 prefix=/；在 build_folder/php-tools 中生成私有副本，将 prefix 指向实际依赖包。phpize 中原有 `s#/#$prefix#` 会替换 phpize.m4 的所有斜线，改为原样复制模板。这些更改仅作用于私有工具副本。
3. OHOS 下 generate() 写入私有 ohos-tempdir.m4 源宏；私有 phpize 将其放在 configure.ac 模板前，覆写 AS_TMPDIR 的 umask，再由 Autoconf 正常生成 configure。生成文件不直接改写，生产 C 源码与 PHPT 保持原样。移除 --build，由依赖自带 config.guess 检测 aarch64-unknown-linux-ohos。编译器与参数由 Conan AutotoolsToolchain 提供。
4. Enchant 的头文件/链接 flags 和依赖库运行路径均从 Conan cpp_info 获取，不依赖共享安装前缀。
5. 只打包模块和许可证；没有 CLI，不需要 commands.json。

## 上游测试申报（R51）

官方 `ext/enchant/tests` 有 33 个 PHPT，配方校验数量并以 PHP 原版 run-tests.php 全部调度。上游词典/提供者 SKIPIF 保留，跳过不可计为通过。已发布 Enchant 关闭可选后端，因此自然语言字典相关测试可能跳过；实际数字由日志与最终测试报告填写。

test_package 提供 12 个消费者断言，使用真实 Enchant 个人词表，无需模拟后端：加载/版本/broker/发现、空标签错误、个人词表、未知词、会话词添加/移除及词表路径。

## 知识与路线

仓库 engine 查询命中 E273：已发布依赖的前缀元数据应在构建目录私有副本中重定位。临时目录权限已有 E011 等知识覆盖。本任务没有足够证据提出新的类级知识问题，暂定路径 A。

## 验证进度

conan-verify 退出 0；上游 33 PHPT 调度，9 PASS / 0 FAIL / 24 SKIP；消费者 12/12。跳过不计为通过。本地 CI 与独立审计继续执行，最终结果以 reports/test-report.md 为准。

官方源码连接重置后使用本任务私有 Conan core.sources:download_cache，内容为二次 SHA256 核验的官方发布包；没有修改共享配置或源 URL。

**编译结束**：2026-10-01。当前状态 built（尚未发布）。
---

**编译结束**: 2026-10-01 14:25
**最终状态**: built

最终权限方案为 AS_TMPDIR 源宏覆写：generate() 生成私有 m4，私有 phpize 在 configure.ac 源模板中加载，再由 Autoconf 正常生成 configure。中间 shell/BASH_ENV 方案失败已记录并移除；最终 Conan 验证及官方 finish W3 通过。使用既有 E011/HMDFS 权限经验，无新知识条目。
