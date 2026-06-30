# wireless-regdb 2026.05.30 适配笔记

## 编译环境
- 构建系统: makefile (无 configure)
- 编译日期: 2026-06-13
- 状态: published

## 编译步骤
- `make -j1` → PASS
- `make install DESTDIR=$TEST_PREFIX` → PASS

## 遇到的问题与解决方案
- wireless-regdb 是纯数据包 (regulatory database)，无 ELF 二进制文件
- 补丁: 0001-gen-pubcert.sh.patch (shebang: `#!/bin/bash` → `#!/usr/bin/env bash`)

## 验证结果
- regulatory.bin, regulatory.db, regulatory.db.p7s 生成成功
- Quality Report: PASS (G1/G2/G3/G4)
