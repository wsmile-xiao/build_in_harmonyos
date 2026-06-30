# E101: ELF 签名要求错误

## 问题表现

执行二进制文件时出现错误：
```
ENXIO: create_process
ELF: signature required
binary-sign-tool: failed
cannot execute: ELF
```

## 根因分析

HarmonyOS/OpenHarmony安全机制要求ELF二进制文件必须签名才能执行，未签名的二进制返回ENXIO错误。

## 解决方案

使用字节码编译器替代优化编译器，或将二进制文件签名：

```bash
ln -sf ocamlc.byte ocamlc.opt
ln -sf ocamlc.byte ocamlopt.opt
export PATH=...
```

## 影响范围

所有生成ELF二进制的项目，OCaml优化编译器，任何编译产物的执行。

## 验证方法

```bash
file ocamlc.opt | grep -q "script"
echo "Bytecode compiler linked"
```

## 分类

- 类别: security, elf, signature, harmonyos, execution
- 严重性: 3（阻塞二进制执行）
- 贡献者: 0D0A