# E642-draft: OHOS 上 strip 后的二进制 exec 报 Operation not permitted（rc=126）

—— hnp clang 产物 `.codesign` 签名被 strip 失效，内核拒绝执行；配方须跳过 strip，不是权限问题。

## 问题

cramfsswap 1.4.5 移植（Makefile 直编）时：`conan create` 编译链接全部成功，
build() 内 smoke 执行刚构建的产物即失败：

```
cramfsswap/1.4.5@ohpcd/stable: RUN: "/storage/.../.conan2/p/b/<hash>/b/cramfsswap" --version
/system/bin/sh: /storage/.../.conan2/p/b/<hash>/b/cramfsswap: Operation not permitted
ConanException: Error 126 while executing
```

三个烟幕叠加，极易误诊：

1. `Operation not permitted`（EPERM）像权限位问题——`chmod 777` 无效；
2. 文件属主显示共享属主 `20001006:file_manager`，而进程 euid 是另一个号
   （HMFS 属主映射，device-facts §一.10）——像属主问题；
3. `readelf -S` 里 strip 后的产物**仍有 `.codesign` 段**——「有签名」的表象
   会让人排除签名方向。

## 根因

HNP 工具链的 clang（`/data/service/hnp/bin/clang`，LLVM 15，target
aarch64-unknown-linux-ohos）链接产物自带链接器代码签名（`.codesign` 段）。
`strip` 重排 ELF（剥离符号/调试段、`.codesign` 位置与覆盖范围改变）后，
签名与文件内容不再一致，OHOS 内核 exec 校验失败直接拒绝 → EPERM rc=126。

对照实测（同一源文件、同一目录、同属主同权限位）：

| 产物 | 处置 | exec 结果 |
|---|---|---|
| `clang -Wall -O2 -o s s.c` | 未 strip | 正常执行（rc=0） |
| `cp s s_stripped && strip s_stripped` | strip | `Operation not permitted`（rc=126） |

与构建系统无关：Makefile `strip` 目标、`cmake install --strip`、
`meson install --strip`、手动 `llvm-strip` 全部命中。

## 方案

配方侧跳过 strip、保留有效签名：

1. **上游 Makefile 有独立编译目标**（本例 `all: cramfsswap strip`）：
   conan `build()` 用 `make <目标名>` 直指编译目标，不调用 `all`/`strip`：

   ```python
   self.run(f'make -C "{src}" cramfsswap CC="{cc}" LD="{cc}" ...',
            env="conanbuild")
   ```

   不改上游源码，零补丁。
2. 无独立目标：构建后不执行 strip（不调 strip 目标、不传
   `INSTALL_STRIP`/`-s`）。
3. cmake/meson：去掉 install 的 strip 选项。

判据边界：conan-verify L4（NX/PIE/RELRO/BIND_NOW）按 ELF header/program
header 判定，**不依赖 strip**；CI 也不校验是否 strip。产物体积增量可接受。

反例（不可走的路）：
- 改权限/属主「修复」EPERM——方向错误（同权限未 strip 产物可执行）；
- strip 后用 `binary-sign-tool sign -selfSign` 重签——既有登记实测本机
  musl 加载器 SIGSEGV，当前无可用的 strip 后重签工具链。

## 验证

- cramfsswap 1.4.5：配方改 `make cramfsswap` 后 conan-verify 八门禁
  PASS（G4/L2/L4/L5 人工补测补足 application 包跳过分支），test_package
  消费者断言 11/11 PASS，finish 内嵌 W3 本地 CI 通过。
- 通用复现（任意鸿蒙设备、任意可写目录）：

  ```sh
  cd "$HOME/tmp" && printf 'int main(){return 0;}\n' > s.c \
    && clang -o s s.c && cp s s_stripped && strip s_stripped \
    && ./s; echo "nostrip_rc=$?"; ./s_stripped; echo "stripped_rc=$?"
  # 期望: nostrip_rc=0; stripped_rc=126 → 命中本模式
  ```

## 适用边界

- 命中：OHOS 设备（HNP clang）上构建后经任何 strip 的可执行/共享库，
  exec/dlopen 前即失败，报 EPERM/Operation not permitted。
- 不命中：①加载阶段 `Error loading shared library`（缺库/soname 别名问题，
  见 E505/E492）；②真权限位问题（`ls -l` 可见权限缺失且未 strip 副本同样
  失败）；③非 HNP 工具链（不带 .codesign 的交叉工具链）产物。
