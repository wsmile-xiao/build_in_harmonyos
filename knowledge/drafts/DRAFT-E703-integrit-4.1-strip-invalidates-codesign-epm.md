# OHOS 上 `strip` 让 clang 自带的 `.codesign` 签名失效：装出来的可执行文件 `Operation not permitted`

- **草稿 ID**: DRAFT-E703-INTEGRIT-4.1-STRIP-INVALIDATES-CODESIGN-EPERM
- **严重度**: 3
- **类别**: ohos, codesign, strip, autotools, packaging, loader
- **来源**: integrit 4.1 适配（HarmonyOS PC aarch64，任务卡 7495）

## 错误特征

配方本地构建与 `make test` 全绿，唯独**安装后的**可执行文件一运行就被加载器拒绝：

```text
$ ./bin/integrit -V
bash: ./bin/integrit: Operation not permitted
```

**辨别性指纹**（三条同时成立即可命中本条）：

1. **同一份程序，make 产物能跑、install 产物不能跑**：
   ```text
   -rwxrwx--- 67968 ./integrit                 → integrit version 4.1   (rc=0)
   -rwxrwx--- 51032 <prefix>/bin/integrit      → Operation not permitted
   ```
2. **`cp` 一份未 strip 的原始产物 → 照样能跑**（排除权限位、目录、文件系统差异）。
3. **`readelf -S` 里 `.codesign` section 两边都还在**：
   ```text
   未 strip:  [37] .codesign   PROGBITS   ... 0000f000
   strip 后:  [24] .codesign   PROGBITS   ... 0000b000
   ```
   ⇒ **不是 section 被删，是签名内容与新布局失配**。看到"section 还在"就以为签名没问题，
   是本条最容易踩的误判方向。

## 根因分析

hnp 的 clang 会给每个 ELF 链接一个 `.codesign` 签名 section，加载器执行前校验它。
上游 autotools 的 install 规则普遍是：

```make
$(INSTALL) $(STRIP) -m 755 $(PROG) $(SBINDIR)/$(PROG)
```

`configure` 检测到系统有 `strip` 后令 `STRIP = -s`。`strip` 把符号表等段去掉，
**文件布局随之改变**，原先写入的 `.codesign` 不再匹配实际内容 ⇒ 校验失败 ⇒ `EPERM`。
integrit 实测三组对照（67968 → 51032 字节，差 16936 字节的符号表）完全吻合。

这与 `device-facts` 已记载的「禁止对 `.so` 执行 `binary-sign-tool sign -selfSign` 重签」
是同一件事的两面：**签名只能在布局定稿后算一次**，strip 是在签名之后又改了布局。

## 推荐方案

**方法**: 禁掉 install 阶段的 strip（零源码改动）—— **仅适用支持 `$(DESTDIR)` 的包**

> ⚠️ **适用范围（先读）**：本法依赖 `make install` 经 `DESTDIR=<package_folder>` 落包。
> **integrit 上游三份 `Makefile.in` 的 `$(DESTDIR)` 计数全为 0**，`make install` 会直写根目录
> （`install: //info: Permission denied`），因此**本包 `package()` 不走 install，改为直接 `copy`
> 收 make 原产物**（完整机制与三重根因见 `archives/i/integrit/4.1/notes.md` 问题表#4）。
> copy 取的同样是**未经 `$(STRIP)`** 的原始产物，`.codesign` 签名同样有效，本条 EPERM 风险一并规避。
> 下方 `STRIP=` 写法保留给**支持 `$(DESTDIR)` 且必须经 install 链路**的包参考。

`Makefile` 里 `$(STRIP)` 是普通 make 变量，**命令行变量优先级最高**：

```python
# conanfile.py
def package(self):
    autotools = Autotools(self)
    # Conan 会自动补 DESTDIR=，最终执行 `make DESTDIR=<pkg> STRIP= install`
    autotools.install(args=["STRIP="])
```

实测（W0 手工预演、`--prefix` 绝对路径形态）：产物回到 67968B（未 strip），`bin/integrit -V`
→ `integrit version 4.1` rc=0，`man/` `info/` 仍完整安装。**本包最终交付路径是 `package()` copy**
（同一份未 strip 产物），上述 install 形态仅作支持 `$(DESTDIR)` 包的参考。

> 注意：`configure STRIP=` **传不进去**（autoconf 的 `AC_PROG_STRIP` 仍会把它定成 `-s`），
> `tc.autotools_vars["STRIP"]` 也不如 make 命令行可靠 —— **在 install 调用上传 `STRIP=` 才是正解**。

**方法二（退路）**: 布局定稿后重新自签

```sh
LD_LIBRARY_PATH= binary-sign-tool sign -selfSign <binary>
```

两个必须注意的点：
- `package()` 里调 hnp 宿主工具时，`conanbuild` 注入的 `LD_LIBRARY_PATH` 指向**目标 sysroot**，
  宿主工具会报 `Error loading shared library libc++.so` ⇒ 调用前用 `LD_LIBRARY_PATH=` 清空。
- **禁止对 `.so` 重签**（本机 musl 加载器 SIGSEGV，`readelf -S` 可核）；只对可执行文件用。

## 影响面

**任何上游 install 规则含 `$(STRIP)`、且产物要作为可执行文件被 `test_package` / CI 运行的包**。
autotools 项目几乎默认如此，因此这是 application 类包的系统性风险：
构建与上游测试全绿、**只有消费已安装产物的那一步才爆**，极像 test_package 写错了。

## 判读口径

- `make test` 通过 **不等于** 安装产物可运行 —— 测的是构建目录里的未 strip 文件。
- 诊断顺序：`ls -la` 比字节 → `cp` 原始产物试跑 → `readelf -S | grep codesign`。
  三步即可定性，不要从权限位或文件系统方向排查（HMDFS 权限问题的形态与此不同：
  那类是 `chmod` 不生效，这里文件本身能读能执行，只是被加载器拒绝）。

## 关联

- **similar_to**: device-facts 附录（`.codesign` 与 `binary-sign-tool` 禁止对 `.so` 重签）、
  coinor-symphony notes「OHOS 一切 ELF 运行前须 binary-sign-tool 自签（加载器 EPERM）」
- **本条新增价值**: ①定位到 **`$(STRIP)` install 路径**是 EPERM 的直接诱因而非"忘了签"；
  ②给出**零源码改动**的 `make STRIP= install` 修法并实测；
  ③给出"**section 还在但签名失效**"这一反直觉判读，避免误诊方向。

## 复现命令（设备可直接执行）

```sh
cd "$TASK_DIR/w0/src/integrit-4.1"

# 1) 未 strip 的 make 产物 —— 可跑
./integrit -V                       # → integrit version 4.1

# 2) 用上游规则 strip 后安装 —— EPERM
rm -rf "$TASK_DIR/w0/sbindir-prefix"
make install                         # $(INSTALL) $(STRIP) …
"$TASK_DIR/w0/sbindir-prefix/bin/integrit" -V   # → Operation not permitted

# 3) 禁 strip 后安装 —— 可跑
rm -rf "$TASK_DIR/w0/nostrip-prefix"
make STRIP= install
"$TASK_DIR/w0/nostrip-prefix/bin/integrit" -V   # → integrit version 4.1

# 4) 签名 section 对照（证明不是被删）
readelf -S ./integrit | grep codesign
readelf -S "$TASK_DIR/w0/sbindir-prefix/bin/integrit" | grep codesign
```

证据留档：`$TASK_DIR/w0/ns-install.log`、`$TASK_DIR/w0/sb-install.log`。
