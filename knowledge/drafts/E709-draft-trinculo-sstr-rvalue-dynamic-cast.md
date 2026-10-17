# trinculo 0.96 SSTR 宏 rvalue dynamic_cast 的 clang15 代差（草稿 E709）

- **来源**：trinculo 0.96 OHOS 移植（任务卡 11293），W0 编译探针 + 逐档 `-std` 探针
- **日期**：2026-09-24
- **证据**：`archives/t/trinculo/0.96/notes.md` 问题表 #1；`$TASK_DIR/w0/W0-evidence.md` 关③

## 症状

```
src/trinculo.cpp:412:44: error: dynamic_cast from rvalue to reference type 'std::ostringstream &'
```

源头是字符串化宏（`trinculo.cpp:44-46`，2016）：

```cpp
#define SSTR( x ) dynamic_cast< std::ostringstream & >( \
        ( std::ostringstream() << std::dec << x ) ).str()
```

## 根因

`std::ostringstream()` 是临时对象；其插入链在 C++11 语义下按右值处理，
`dynamic_cast<T&>` 绑定右值 ill-formed。旧 g++（上游 2016 构建环境）实现
宽松故能编。**逐档探针**：`-std=gnu++98/03/11/14/17` 五档全部报同一错
（rc 全 1）⇒ 不是标准版本代差，降档是伪修——与止损先例 #2（bcp 动态异常
规格降档有效）的关键判别点：**是否全变体同错**。

单 TU 项目里宏只有一个调用点（`SSTR(j+1)`，trinculo.cpp:412），修复不必
波及调用面。

## 对策

宏体改 lambda 内具名局部流，临时对象有名字后 `dynamic_cast` 整个消失：

```cpp
#define SSTR( x ) ([&]{ std::ostringstream _ss; _ss << std::dec << (x); return _ss.str(); }())
```

语义逐字等价（`std::dec` 初始化、同一插入序列、返回 `.str()`），调用面零改动。

## 验证

```bash
# 修前（五档 -std 同错）
clang++ -DLINUX -Isrc -fsyntax-only src/trinculo.cpp 2>&1 | grep -c "dynamic_cast from rvalue"   # → 1
# 修后
clang++ -DLINUX -O3 -pipe -DNDEBUG -std=gnu++17 -Isrc -o bin/trinculo src/trinculo.cpp \
  -L<lapack>/lib -llapack -lblas -lFortranRuntime -lFortranDecimal -lm -lpthread   # → rc=0，arm64 ELF
# 上游测试 9/9 PASSED（golden MD5 字节全等）
```

## 禁行

- 降 `-std` 到 gnu++98/03/11/14：逐档探针实证全变体同错，属伪修。
- 在调用点改写（宏体单点修 delta 最小；调用面扩散增加 W4 复审面）。

> 提交后回填 source_commit；晋升需人工/AI 评审改名 `E709.kv` 移入 `knowledge/graph/` 并登记 index.tsv。
