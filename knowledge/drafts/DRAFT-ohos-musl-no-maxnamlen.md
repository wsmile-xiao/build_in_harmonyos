# DRAFT-ohos-musl-no-maxnamlen：OHOS musl libc 无 glibc 的 MAXNAMLEN（仅 NAME_MAX）——C 源码用 MAXNAMLEN 编译报 undeclared——patch 用 POSIX NAME_MAX

> Contributor: boa-0.94.14rc21 适配 | Status: Draft | Updated: 2026-08-24
> Source: archives/b/boa/0.94.14rc21（本地 conan create 实测）

## 现象

boa 的 index_dir.c 编译时 clang 报错：

```
src/index_dir.c:209:24: error: use of undeclared identifier 'MAXNAMLEN'
    char http_filename[MAX_FILE_LENGTH * 3];
                       ^
src/index_dir.c:32:49: note: expanded from macro 'MAX_FILE_LENGTH'
#define MAX_FILE_LENGTH                         MAXNAMLEN
```

原因：`MAXNAMLEN` 是 glibc `<dirent.h>` 提供的文件名长度上限宏（非
POSIX 标准）。OHOS 使用 musl libc，头文件中无 `MAXNAMLEN`——POSIX
标准名称是 `<limits.h>` 的 `NAME_MAX`（musl 有）。

## 主从根因

- **主根因**：glibc→musl 头文件宏差异——`MAXNAMLEN` 是 glibc 扩展，
  musl 仅提供 POSIX 标准 `NAME_MAX`（平台 libc 差异，归轴 1 平台能力
  边界）。
- **附加 note（非主根因，常伴随出现）**：clang C2x 对无原型函数声明
  报 `-Wstrict-prototypes`，若构建带 `-Werror` 直接失败（aegean 同款
  教训——需 `-Wno-error=strict-prototypes` 或 patch CFLAGS）。

## 与现有知识的关系

- 现有 musl/glibc 差异类草稿（如 DRAFT-aflplusplus-ohos-posix-types）
  覆盖 POSIX 类型定义差异，不覆盖 MAXNAMLEN 这个 glibc 私有宏——本
  主题无直接覆盖（MAXNAMLEN 属于 glibc <dirent.h> 扩展宏）。
- 跨库可复用：任何 C 源码使用 glibc 私有宏（MAXNAMLEN 等）在 OHOS
  musl 上编译都会命中——需替换为 POSIX 等价物或条件定义。

## 方案

patch 源码把 glibc 私有宏替换为 POSIX 等价宏（配方 build() 内文本
替换，不改上游测试用例）：

```python
# 配方 build() 内（boa conanfile.py 实测有效）：
idx = os.path.join(self.source_folder, "src", "index_dir.c")
with open(idx, "r", encoding="latin-1") as f:
    s = f.read()
s = s.replace("#define MAX_FILE_LENGTH                         MAXNAMLEN",
              "#define MAX_FILE_LENGTH                         NAME_MAX")
with open(idx, "w", encoding="latin-1") as f:
    f.write(s)
```

`NAME_MAX` 在 `<limits.h>` 定义（index_dir.c 已 include `<limits.h>`
——`/* for PATH_MAX */` 注释行），替换后编译通过。

## 验证

- 本地 conan create（boa/0.94.14rc21）通过：patch 后 index_dir.o 编译
  成功，make -j1 全过，Package created + test_package PASSED。
- patch 前后对照：patch 前 3 处 MAXNAMLEN 未声明错误（index_dir.c
  209/210/211 行）；patch 后全部编译通过。
