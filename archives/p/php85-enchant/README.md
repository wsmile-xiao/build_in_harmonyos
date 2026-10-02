# php85-enchant

PHP 8.5.8 官方 `ext/enchant` 扩展，提供 Enchant broker、字典发现、个人词表和拼写检查 API。软件来自 PHP 官方发布包，本归档仅打包 `enchant.so`，不重复打包 PHP 或 Enchant。

依赖：`php/8.5.8`、`enchant/2.8.2`（传递依赖由 Conan 解析）。扩展需要使用相同 PHP/Zend 模块 ABI 的 PHP 解释器加载。

安装后使用依赖 PHP 的 `bin/php`，通过 `-n -d extension=<package>/lib/php/extensions/enchant.so` 显式加载模块。配方提供运行环境变量 `PHP85_ENCHANT_EXTENSION`，消费者仍需传入 `-d extension`。

消费者测试使用个人词表验证真实拼写检查、未知词拒绝、会话词添加和移除。自然语言字典及后端由 Enchant 提供；当前已发布的 Enchant 2.8.2 包关闭了可选后端，因此不能把此依赖包视为自带英语等语言字典。上游测试保留原始 `SKIPIF`，相关测试的实际跳过数在测试报告中列出。

配方在构建目录生成 PHP 工具私有副本，修复已发布 PHP 包固定为 `/` 的前缀元数据，不修改依赖缓存。OHOS 构建通过私有 AS_TMPDIR 源宏设置临时目录权限；configure 由 Autoconf 正常生成，全部生产 C 源码保持上游原样。

上游：https://www.php.net/manual/en/book.enchant.php

最终权限方案为 AS_TMPDIR 源宏覆写：generate() 生成私有 m4，私有 phpize 在 configure.ac 源模板中加载，再由 Autoconf 正常生成 configure。中间 shell/BASH_ENV 方案失败已记录并移除；最终 Conan 验证及官方 finish W3 通过。使用既有 E011/HMDFS 权限经验，无新知识条目。
