# mmdb

## 简介
CCP4 的大分子坐标库（mmdb2）：读写 PDB / mmCIF / MMDB 坐标文件，提供 Model-Chain-Residue-Atom 层级容器、元素与残基查找表、晶体学与数学工具。C 与 C++ 混编，零外部依赖。

## 基本信息
- 官网: https://www.ccp4.ac.uk
- 许可证: LGPL-3.0-or-later
- 构建系统: autotools（上游 LT_INIT 声明 disable-shared，仅产出静态库）

## 已编译版本
- 2.0.22 (2026-09-25)

## 使用方式
```bash
conan install --requires=mmdb/2.0.22 -pr ohos-native
```

详见 `2.0.22/notes.md`。
