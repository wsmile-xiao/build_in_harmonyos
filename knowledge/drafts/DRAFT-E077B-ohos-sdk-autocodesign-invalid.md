# E077B：OHOS SDK 链接器自动生成的 .codesign 无效——readelf 见签名 ≠ 可执行

## 错误特征

```
# readelf 显示已有签名（误导性证据）：
llvm-readelf -SW <binary> | grep -c codesign
# → 1

# 但直接执行仍被拒：
bash -c "<binary> --version"
# → sh: <binary>: Operation not permitted（或 exit 126）

# 若只 chmod 反复重试无效；若用 binary-sign-tool 直接补签报 "section already exists"
```

## 根因

OHOS SDK 的 clang/lld 链接器在生成 ELF 时会**自动插入一个 .codesign 占位段**（PROGBITS），但该自动签名对内核**不可用**——ELF 加载校验不认。表现：readelf 能看到 1 个 .codesign，极易被误判为"已签名、问题在别处"，导致排查方向跑偏（反复查权限、查 SELinux、查挂载选项均无效）。

本质：**SDK 自动签名 ≠ 有效签名**。必须在 package() 阶段显式走 E077 四步流程重新签名。

## 解法（E077 四步在 package() 中的应用）

在 conanfile 的 `package()` 末尾对每个可执行 ELF 调用签名函数：

```python
def _sign_ohos_elf(self, bin_path):
    # 1. 移除 SDK 自动生成的无效签名（必须先做，否则补签报 section already exists）
    self.run(f"llvm-objcopy --remove-section .codesign {bin_path}")
    # 2. selfSign 重签
    self.run(f"binary-sign-tool sign -inFile {bin_path} -outFile {bin_path}.signed -selfSign 1")
    # 3. 校验签名计数（应恰好 1）
    # 4. 原子替换 + 恢复权限（签名后权限归零）
    os.replace(f"{bin_path}.signed", bin_path)
    os.chmod(bin_path, 0o755)
```

参考实现：`archives/p/pan/0.165/conanfile.py`（pan 0.165，PR !8699）。

## 与 E077 的关系（增量）

E077 覆盖"**工具修改 ELF 后**签名失效 → 四步重签"；本条覆盖"**SDK 链接器自动插入的签名本身无效**"场景——症状相同（Operation not permitted）但起点不同（没动过 ELF 也会挂）。关键增量是 **forbid 规则**：readelf 见 .codesign 不能认定签名有效，必须实测执行验证；SDK 自动签名的存在恰恰是误判源。

## 禁止事项

- ❌ 见 readelf 有 .codesign 即认定签名有效（SDK 自动签名不是有效签名）
- ❌ 跳过 remove-section 直接补签（报 section already exists）
- 后果：test_package 二进制执行报 Error 126，误判权限问题反复 chmod 无效

## 实证

- pan 0.165（PR !8699）：SDK 自动签名存在（readelf 1 个 .codesign）但执行报 Operation not permitted；package() 四步重签后 `pan --version` 正常输出 "Pan 0.165"
- 佐证：abx/0.1 配方同款处理

## 红线

- 所有 OHOS SDK clang 原生编译的可执行 ELF（application 类包）必须在 package() 显式重签
- 判定签名有效性的唯一标准是真实执行，不是 readelf 段计数
