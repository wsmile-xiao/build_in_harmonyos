# DRAFT-installation-birthday-conan-src-env-injection

## conan 2 在 build() 前向 source folder 注入聚合环境文件：文件计数类漂移守卫真机误报

### 现象

真机（HarmonyOS PC，Conan 2.29.1）`conan-verify installation-birthday 20` G2 首验 FAIL：

```
ERROR: installation-birthday/20@ohpcd/stable: Invalid configuration:
installation-birthday 20 total file count 23 != 17
```

配方 `build()` 的防漂移守卫按「上游 tarball 全树 17 文件」计数（kicad-demos 纯数据包范式），真机却数出 23。真机 ls 实证：source folder 多出 6 个文件——`conanbuild.sh`、`conanrun.sh`、`conanbuildenv-release-armv8.sh`、`conanrunenv-release-armv8.sh`、`deactivate_conanbuild.sh`、`deactivate_conanrun.sh`，全部是 conan 2 在 build() 前生成的**聚合环境文件**（conan 日志可见 `Generated aggregated env files`）。17 + 6 = 23。

### 根因

- conan 2 执行 build() 前向 source folder 根注入环境脚本（虚拟环境聚合产物），非上游内容；
- 纯数据包防漂移守卫按「全树总数 == 上游计数」写死，未把 conan 注入物排除；
- 本机预演常用**手工模拟源目录**（不经过 conan 构建），无注入物 → 本机不炸、真机必炸的经典环境差；
- 知识图谱命中 E540（runner-path-prepend）为误报——真实根因是计数口径，教训同前例：**G2 FAIL 先看 conan-create.log 首行真实 ERROR**。

### 推荐方案

守卫排除 conan 注入物（fabric-completion 先例同款口径）：

- 排除 `*.sh`（注入的环境文件全部是 .sh；上游 tarball 无 .sh 时零副作用）；
- 排除簿记文件 `conaninfo.txt` / `conanmanifest.txt`；
- 防漂移的主体仍是「载荷文件逐项在位」存在性检查 + 载荷内容锚点（探针层）。

```python
total = sum(1 for _, _, files in os.walk(self.source_folder)
            for f in files
            if not f.endswith(".sh")
            and f not in ("conaninfo.txt", "conanmanifest.txt"))
```

### 边界

- 若上游 tarball 本身含 .sh（部分源码包），改用「载荷文件逐项在位」存在性守卫，放弃全树总数；
- 与 [[DRAFT-fabric-completion-conan-pkg-bookkeeping]] 区分：彼为**包根**（package folder）簿记文件影响消费者探针计数，此为**源目录**（source folder）环境文件影响配方 build() 守卫计数，位置与文件均不同。

参考实现：`archives/i/installation-birthday/20/conanfile.py`（build() 注释含真机 G2 首验实录）。
