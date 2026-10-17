# smhasher

SMHasher is a test suite designed to test the distribution, collision, and performance
properties of non-cryptographic hash functions. It is also the home of the MurmurHash
family (MurmurHash1/2/3) plus City, Spooky, lookup3, SuperFastHash and others.

## 基本信息

- **名称**: smhasher
- **主页**: https://github.com/aappleby/smhasher
- **许可证**: MIT（MurmurHash 系列本身为 Public Domain）
- **分类**: library

## 鸿蒙适配要点

- 上游自带 `src/CMakeLists.txt`（构建 SMHasherSupport 库 + SMHasher 测试主程序），配方直接使用
- 补丁仅两处可移植调整：CMake 最低版本 2.4→3.15；`main.cpp` 新增 `--selftest-only` 速检开关
- 不安装 SMHasher 测试主程序，只交付 SMHasherSupport 库与全部头文件（纯库包）
- 无外部依赖，纯 C/C++

## API

交付 `SMHasherSupport` 库，头文件见 `include/`（`Hashes.h` 汇总全部哈希包装函数，
`MurmurHash1/2/3.h`、`City.h`、`Spooky.h`、`PMurHash.h` 等）。测试主程序用法：

```bash
SMHasher --selftest-only   # 22 个哈希函数固定验证值自检（门禁内运行）
```
