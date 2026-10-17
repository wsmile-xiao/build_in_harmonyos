# Draft: `DRAFT-XMILL-08-UPSTREAM-CLI-DEFECTS-INVISIBLE-TO-BUILD`
> Stem: `xmill-0.8-upstream-cli-defects-invisible-to-build` — pairs with the same-stem `.kv`

# 编译/链接/打包全绿，但 CLI 本身不可用

## 基本信息

- **ID**: DRAFT-XMILL-08-UPSTREAM-CLI-DEFECTS-INVISIBLE-TO-BUILD
- **严重度**: 2（默认流程全绿，只有把 CLI 当被测对象才发现）
- **类别**: upstream-defect | cli | runtime | smoke-test | portability
- **触发工具**: conan | cmake | clang | runtime
- **阶段**: compilation（零诊断）→ runtime（不可用 / SIGSEGV）
- **来源**: xmill 0.8 适配（2026-10-01）

## 问题（两类，同一后果）

适配过程中 CMake 构建、`conan create`、`conan-verify` G1–G4 全部通过，产出两个形态正确的
aarch64/OHOS ELF。但 CLI 实际不可用：

### (a) 入口被打桩

镜像仓库把 `main()` 换成了忽略 `argc/argv`、写死文件的调试驱动：

```c
int main(int argc,char **argv)
{
   try { globallabeldict.Init(); FSMInit(); ... }
   catch(XMillException *) { return -1; }

   HandleSingleFile("sprot1_2.xml",0);      // <- 忽略 argv，永远是同一个文件
   //HandleSingleFile("f:\\sprot1_1.xmi",1);
   return 0;
}
```

关键旁证：同文件仍保留 `void PrintUsage(char);` 与 `int HandleAllOptions(char**,int);`
的声明（原入口就是建立在这两个函数上的），说明入口是被替换而非上游原本如此。
编译 100% 通过，但任何命令行用法都不生效。

### (b) 诊断路径跨模式误用状态 → SIGSEGV

```c
// LabelDict.hpp:499（修复前）
void PrintLabel(TLabelID labelid) {
   ...
   len=LookupCompressLabel(labelid,&ptr);       // 压缩字典（有效）
   len=LookupLabel(labelid,&ptr,&isattrib);     // 解压字典 labeldictlist
}
// LookupLabel(): UncompressLabelDict *labeldict=labeldictlist;   <- 压缩器里恒为 NULL
```

`labeldictlist` 只在 `LabelDict::Load()`（解压路径）里构建。该函数被
`PathDictNode::PrintInfo` / `VRegExpr` / `FSMEdge::PrintLabelList` / `PathTree` 多处
打印路径共用，而打印只在 `-v`（或 `-h`）下触发 → 默认流程永不执行，只有
`xmill -v` 才会以 139 退出。

## 共同点与检出方式

| 特征 | 说明 |
|------|------|
| 编译期零诊断 | 既非类型错误也非未定义符号 |
| 默认路径不触发 | 不打 `-v` 就永远看不到 |
| 只有 CLI 冒烟能发现 | 必须真实调用 + 用 `echo $?` 判定 |

```bash
./xmill ; echo $?                  # 无参：应打印 usage 且非 0
./xmill in.xml && ls -l in.xmi     # 入口是否真正接受 argv
./xmill -v in.xml ; echo $?        # 诊断路径是否崩（139 = SIGSEGV）
./xmill -h ; echo $?               # 文档化开关是否真的实现
```

## 修法

1. 入口被打桩：按同文件里既有的 `PrintUsage()` / `HandleAllOptions()` 接口还原命令行入口，
   并在 notes/PR 里写明"这是对上游入口的修复（还原），不是新增功能"。
2. 打印跨模式误用：让打印函数按当前模式选择数据源（压缩模式用压缩字典 `LookupCompressLabel`），
   而不是无条件走另一套状态。
3. **不要顺手自造缺失功能**：`xmill -h` 是"用法文本有、解析器无 `'h'` 分支"的上游瑕疵
   （以 255 退出），登记为已知瑕疵即可，不属移植适配范围。

## 判定口径

编译成功、链接成功、`conan create` + `test_package` 通过，**都不构成"CLI 可用"的证据**；
唯一证据是逐条开关的真实调用与退出码。

## 关联

- `notes.md` §2（上游测试入口）、§3.4（verbose 崩溃根因）、§4（20/20 CLI 矩阵）
- 同类：`zpaq-7.15-nojit-aarch64-sigill`（同为"能编过但不可用"）、
  `zpaq-7.15-no-version-flag-smoke-gate`（同为 CLI 冒烟门禁主题）
