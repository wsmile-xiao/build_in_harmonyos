// test_package 开发面探针 —— 真实调用本包 LLVM + 6 个 clang 组件库的导出符号（R34 反空壳：
// 不是只打印字符串，每一段都链接并执行对应静态库里的真实实现）。
//
//   clangBasic        → clang::getClangFullVersion()
//   clangFrontend     → clang::CompilerInstance 构造/析构
//   clangASTMatchers  → clang::ast_matchers::MatchFinder 构造/析构
//   clangSupport      → clang::RISCV::LMULType 构造 + str()
//   clangEdit         → clang::edit::EditedSource 构造
//   clangLex          → clang::Lexer::getLocForEndOfToken()
//   libLLVM.so        → llvm::sys::getDefaultTargetTriple()
#include "clang/ASTMatchers/ASTMatchFinder.h"
#include "clang/Basic/Diagnostic.h"
#include "clang/Basic/DiagnosticOptions.h"
#include "clang/Basic/FileManager.h"
#include "clang/Basic/LangOptions.h"
#include "clang/Basic/SourceManager.h"
#include "clang/Basic/Version.h"
#include "clang/Edit/EditedSource.h"
#include "clang/Frontend/CompilerInstance.h"
#include "clang/Lex/Lexer.h"
#include "clang/Support/RISCVVIntrinsicUtils.h"
#include "llvm/TargetParser/Host.h"
#include "llvm/Support/raw_ostream.h"

#include <cstdio>
#include <string>

int main() {
  int checks = 0;

  // clangBasic
  std::string version = clang::getClangFullVersion();
  if (version.empty()) {
    std::fprintf(stderr, "probe: clangBasic getClangFullVersion() empty\n");
    return 1;
  }
  ++checks;

  // clangFrontend
  clang::CompilerInstance compiler;
  ++checks;

  // clangASTMatchers
  clang::ast_matchers::MatchFinder finder;
  ++checks;

  // clangSupport
  clang::RISCV::LMULType lmul(0);
  std::string lmul_str = lmul.str();
  if (lmul_str.empty()) {
    std::fprintf(stderr, "probe: clangSupport LMULType::str() empty\n");
    return 1;
  }
  ++checks;

  // clangEdit + clangLex
  clang::FileSystemOptions fso;
  clang::FileManager files(fso);
  llvm::IntrusiveRefCntPtr<clang::DiagnosticIDs> diag_ids(new clang::DiagnosticIDs());
  llvm::IntrusiveRefCntPtr<clang::DiagnosticOptions> diag_opts =
      llvm::makeIntrusiveRefCnt<clang::DiagnosticOptions>();
  clang::DiagnosticsEngine diags(diag_ids, diag_opts, new clang::IgnoringDiagConsumer());
  clang::SourceManager sources(diags, files);
  clang::LangOptions lang_opts;
  clang::edit::EditedSource edited(sources, lang_opts);
  ++checks;
  clang::SourceLocation eot =
      clang::Lexer::getLocForEndOfToken(clang::SourceLocation(), 0, sources, lang_opts);
  (void)eot;
  ++checks;

  // libLLVM.so
  std::string triple = llvm::sys::getDefaultTargetTriple();
  if (triple.empty()) {
    std::fprintf(stderr, "probe: LLVM getDefaultTargetTriple() empty\n");
    return 1;
  }
  ++checks;

  std::printf("llvm-project devface probe OK: clang %s, %d component checks, host triple %s\n",
              version.c_str(), checks, triple.c_str());
  return 0;
}
