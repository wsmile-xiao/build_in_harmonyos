# E430 — 静态 libmagic 在 OHOS 无 MAGIC 环境变量时报 magic database 加载失败

## 错误特征

```
Exception: Failed to load the file magic database (could not find any valid magic files!)
FAIL omindextest (exit status: 1)
Skipping - unknown MIME type 'video/x-msvideo'（随后异常）
```

## 触发条件
- 构建系统: 任意（链接静态 `libmagic.a` 的包，如 file/omindex 族）
- 阶段: testing / runtime（`magic_open` + `magic_load(cookie, NULL)`）

## 根因分析
libmagic 静态构建时把默认数据库搜索路径（/usr/share/misc/magic.mgc、/etc/magic 等）
编进二进制；OHOS musl 用户态不存在这些目录，而 conan 的 libmagic 发布包把编译好的
`magic.mgc` 放在包内 `share/misc/magic.mgc`，静态库无法自行感知安装位置。
`magic_load(NULL)` 因此找不到任何有效数据库并抛异常。

## 解决方案

### 推荐方案
配方在 `generate()` 的 `Environment(scope="build")` 中导出
`MAGIC=<libmagic package_folder>/share/misc/magic.mgc`，使 `make`/`make check`
与构建期测试通过静态库自带的 `MAGIC` 覆盖机制命中包内数据库。
参考实现：`archives/o/omega/2.0.0/conanfile.py::generate`（omega_deps 环境脚本）。

### 禁止做法
- ❌ 把 magic.mgc 复制进共享系统目录（污染 /usr，CI 互扰，违反 R49/PF6 精神）
- ❌ 跳过 omindextest 等依赖 magic 的上游用例来"绿"（违反 R51 如实申报）

## 验证
```bash
MAGIC=$LIBMAGIC_PKG/share/misc/magic.mgc make check   # 目标用例由 FAIL 转 PASS
```

## 关联条目
- 相关: R51（上游测试三步法）、E429（同为"发布包内容不可全信路径"家族）
- 来源 PR: feat/omega-2.0.0
