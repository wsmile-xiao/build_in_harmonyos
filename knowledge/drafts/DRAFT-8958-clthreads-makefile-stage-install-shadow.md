# DRAFT-8958：clthreads 2.4.2 适配 OHOS 真机 Makefile 共享库打包链两重障碍与配方侧打包范式

> Contributor: gcw_6YxinkyD | Status: Draft | Updated: 2026-09-08
> Source: PR !8958 【知识库扩展】feat(clthreads): 2.4.2 编译完成（真机 3 轮迭代）

## 背景

clthreads 2.4.2 是纯 Makefile C++ 共享库（zita 系，LGPL→GPL-2.0-or-later），
零外部依赖，上游 `make install` 规则使用裸 `install` 命令 + `ln -sf` 符号链接链。
在 HarmonyOS PC 真机（10.62.134.118）上做 Conan 适配，build/check 阶段全绿后，
package 阶段连续暴露两个**设备环境级**障碍；均与代码正确性无关，但会让一切
"调 make install 打包"的 Makefile 库配方在同一台 worker 上必然失败。

## 坑 1：`install` 命令被不可执行文件遮蔽（package 阶段）

### 现象

```text
clthreads/2.4.2: RUN: make -C source install PREFIX=/ INCDIR=/include LIBDIR=/lib DESTDIR="..."
install -d /storage/.../p///include
make: install: Permission denied
make: *** [Makefile:56: install] Error 127
```

### 根因（真机探测实证）

真机 `$HOME`（/storage/Users/currentUser，HMDFS）下存在
`usr/local/bin/install`，权限 `rwxrwx---`、属主 20001006:file_manager——
当前用户**不可执行**。conan 构建环境（profile buildenv 将
`/storage/Users/currentUser/usr/local/bin` 前置到 PATH）里它遮蔽了 `/bin/install`：

```text
$ ls -la /usr/bin/install /bin/install          # → Permission denied（stat 受限）
  /storage/.../usr/local/bin/install             # rwxrwx--- 1 20001006 file_manager 805
$ command -v install                              # → /bin/install（交互 shell 可用）
$ install -d ~/tmp/probe/d1 && echo OK           # 交互 shell 里 OK
```

即：**同一台设备上交互 shell 可用 `install`，conan build env 里不可用**。
Error 127 + "Permission denied" 是 execvp 对不可执行文件的表现。

## 坑 2：home 文件系统拒绝 symlink（package 阶段）

### 现象

```text
ln: cannot create symbolic link from 'foo' to '/storage/Users/currentUser/tmp/...':
Permission denied
```

### 根因

真机 $HOME 挂载为 HMDFS（分布式文件系统），`ln -s`/`ln -sf` 返回 EACCES。
conan 包目录（CONAN_HOME 下 p/b/.../p）同样位于 /storage，上游 Makefile 的
`ln -sf libclthreads.so.2.4.2 .../libclthreads.so` 符号链接链无法创建。
（botan3 的 configure.py symlink 头文件链是同一限制的另一表现，彼处用
`--link-method=copy` 解决。）

## 修复范式：配方侧打包 + 真实文件副本 soname 链

不再调用 `make install`，`package()` 直接用 Conan `copy()` + `shutil.copyfile`
落产物，soname 链用三份真实文件副本（md5 一致）代替符号链接——对链接期
（-lclthreads 找 libclthreads.so）与运行期（loader 找 DT_SONAME
libclthreads.so.2）行为完全等价：

```python
def package(self):
    src = os.path.join(self.build_folder, "source")
    copy(self, "clthreads.h", src, os.path.join(self.package_folder, "include"))
    lib = os.path.join(self.package_folder, "lib")
    min_name = "libclthreads.so.{}".format(self.version)
    copy(self, min_name, src, lib)
    base = os.path.join(lib, min_name)
    maj_name = "libclthreads.so.{}".format(str(self.version).split(".")[0])
    for name in (maj_name, "libclthreads.so"):
        shutil.copyfile(base, os.path.join(lib, name))
```

适配后在真机与 Linux CI 上行为一致，不依赖 `install`/`ln` 二进制与文件系统能力。

## 坑 3（同链附带）：上游 Makefile 的 `-march=native`

2.4.2 上游新增 `CXXFLAGS += -march=native`（2018 年上游加入）。交叉编译器
（clang for aarch64-ohos 跑在 x86_64 host 上）会探测 host CPU 生成错误
target 参数，必须 patch 移除；同时也不可复现。zita 系（clxclient、zita-*）
新版本 Makefile 普遍带此行，适配时统一去掉。

## 坑 4（流程教训）：为上游新 Makefile 重制补丁时丢语义 hunk

2.4.0 已合入补丁含"make 变量 `CLTHREADS_NO_PTHREAD_CANCEL=1` → CPPFLAGS -D 宏"
的 `ifeq` 块；2.4.2 上游重写 Makefile 后人工重制补丁时该块被遗漏，且本机
（Windows，无交叉编译器）静态校验（git apply 干净、conan export 通过、
graph info 通过）**全部拦不住**，直到真机编译才在 `#else` 分支炸出
`use of undeclared identifier 'pthread_cancel'`（OHOS musl 的 pthread.h
不声明该函数）。教训：为上游构建系统变更重制补丁时，必须逐 hunk 对照
旧补丁的语义清单，尤其宏接线类 hunk（无上下文报错、只在目标平台触发）。

## 验证

真机（10.62.134.118）隔离 CONAN_HOME + 离线 download cache + jobs=1：

```sh
conan create archives/c/clthreads/2.4.2 -pr:h ohos-aarch64 -pr:b ohos-aarch64 --build=missing
# exit 0；make check（源码树 API 测试）通过；
# test_package 2/2：test_clthreads + test_clthreads_threads（H_thread 真实线程
# 请求/回复消费者用例）；
# 产物 lib/libclthreads.so{,.2,.2.4.2}（各 43456 字节，md5 一致）+ include/clthreads.h
```

## 关系

- 类似 E011（HMDFS 权限类）与 botan3 DRAFT-8945 坑 1（hmdfs 拒绝 symlink 的
  configure 级表现）；本条新增 package 阶段的 `install` 遮蔽表现与共享库
  soname 链的 copy 替代范式。
- E085（pthread_cancel 缺失）驱动了 CLTHREADS_NO_PTHREAD_CANCEL 宏接线，
  坑 4 是其工程流程反面教材。
- 适用面：一切"package 阶段调 make install / 依赖 install、ln -sf"的
  Makefile 库适配（zita 系、众多传统 Unix 库）在该 worker/CI 环境直接适用。
