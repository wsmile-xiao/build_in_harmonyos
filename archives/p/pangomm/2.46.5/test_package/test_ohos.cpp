// test_ohos.cpp — pangomm 2.46.5 鸿蒙特有测试（OHOS 加载器/签名/依赖链运行时探针）
//
// 与 test.cpp（编译期头文件 + 静态链接消费者测试）互补：本探针**不链接**
// libpangomm-1.4，而是像真实 OHOS 应用那样在运行时 dlopen 它，用来验证
// 鸿蒙平台特有的三条性质：
//   1. 包内 .so 已通过 OHOS codesign（未签名 .so 在 OHOS 上 dlopen 返回
//      NULL/EACCES —— E135 实坑）；
//   2. RTLD_NOW 下整条 DT_NEEDED 链（glibmm-2.4 / cairomm-1.0 / sigc-2.0 /
//      pango / pangocairo / libc++_shared）都能被加载器解析；
//   3. 解析出的符号确实来自被测包（dladdr 校验镜像路径），且符号可调用。
//
// 用法: ./test_ohos_probe <package_folder>
// 退出码 0 = 全部断言通过；非 0 = 失败（stderr 打印 FAIL 明细）。
#ifndef _GNU_SOURCE
#define _GNU_SOURCE
#endif
#include <dlfcn.h>

#include <cstdio>
#include <cstring>

namespace {

int g_checks = 0;

bool check(bool condition, const char* what)
{
  ++g_checks;
  if (!condition)
    std::fprintf(stderr, "FAIL: %s\n", what);
  return condition;
}

} // namespace

int main(int argc, char** argv)
{
  const char* pkg = (argc > 1) ? argv[1] : "";
  const char* soname = "libpangomm-1.4.so.1";

  bool ok = true;

  // ── 断言 1: 按 SONAME dlopen（RTLD_NOW 强制解析全部 DT_NEEDED）────────
  dlerror();                            // 清空错误状态
  void* handle = dlopen(soname, RTLD_NOW | RTLD_GLOBAL);
  const char* dl_err = dlerror();
  ok &= check(handle != nullptr,
              "dlopen(\"libpangomm-1.4.so.1\", RTLD_NOW) succeeds "
              "(OHOS codesign valid + full DT_NEEDED chain resolvable)");
  if (!handle)
  {
    std::fprintf(stderr, "  dlerror: %s\n", dl_err ? dl_err : "()");
    std::fprintf(stderr, "  package_folder: %s\n", pkg);
    return 1;
  }

  // ── 断言 2: 导出符号存在（libpangomm-1.4 符号表）────────────────────
  // Pango::init(); Pango::FontDescription::FontDescription(Glib::ustring const&);
  // Pango::FontDescription::get_family() const
  const char* sym_init = "_ZN5Pango4initEv";
  const char* sym_fd_ctor = "_ZN5Pango15FontDescriptionC1ERKN4Glib7ustringE";
  const char* sym_fd_family = "_ZNK5Pango15FontDescription10get_familyEv";

  void* p_init = dlsym(handle, sym_init);
  void* p_ctor = dlsym(handle, sym_fd_ctor);
  void* p_family = dlsym(handle, sym_fd_family);
  ok &= check(p_init != nullptr, "dlsym Pango::init() present");
  ok &= check(p_ctor != nullptr, "dlsym Pango::FontDescription ctor present");
  ok &= check(p_family != nullptr, "dlsym Pango::FontDescription::get_family() present");
  if (!ok)
  {
    const char* dlsym_err = dlerror();   // 只取一次：dlerror() 读取后即清除错误状态
    std::fprintf(stderr, "  dlsym err: %s\n", dlsym_err ? dlsym_err : "()");
    dlclose(handle);
    return 1;
  }

  // ── 断言 3: 符号镜像即被测包（dladdr 路径校验，排除残留系统库）────────
  Dl_info info;
  if (dladdr(p_init, &info) != 0 && info.dli_fname)
  {
    const char* base = std::strrchr(info.dli_fname, '/');
    base = base ? base + 1 : info.dli_fname;
    ok &= check(std::strcmp(base, soname) == 0,
                "dladdr: Pango::init resolved from libpangomm-1.4.so.1 (packaged image)");
    if (pkg && *pkg && std::strlen(pkg) > 0)
    {
      // 镜像路径应位于被测 package_folder 下（真实调用被测包产物）。
      ok &= check(std::strncmp(info.dli_fname, pkg, std::strlen(pkg)) == 0,
                  "dladdr: library image lives inside the tested package_folder");
    }
  }
  else
  {
    ok &= check(false, "dladdr(Pango::init) available on OHOS");
  }

  // ── 断言 4: 真实调用（dlopen 出来的符号可执行，无独立计数）────────────
  typedef void (*init_fn)();
  init_fn pango_init = reinterpret_cast<init_fn>(p_init);
  pango_init();                         // 真实执行：符号/ABI 不符会在此暴露

  // ── 断言 5: 阴性对照（确认 dlsym 确实会报错）─────────────────────────
  // 可失败判据：若 dlsym 对不存在的符号返回非空、或 dlerror() 未置错，
  // 则前面"符号存在"的阳性结果不具说明力，本项 FAIL。
  // 注：dlerror() 读取后即清除错误状态，必须先存局部变量再打印。
  dlerror();                            // 清空错误状态
  void* p_bogus = dlsym(handle, "_ZN5Pango30__opendesk_absent_symbol_probe__Ev");
  const char* bogus_err = dlerror();    // 只取一次
  ok &= check(p_bogus == nullptr && bogus_err != nullptr,
              "dlsym reports an error for an absent symbol");

  dlclose(handle);

  if (!ok)
  {
    std::fprintf(stderr, "pangomm OHOS probe: %d checks, FAILURES present\n", g_checks);
    return 1;
  }
  std::printf("pangomm 2.46.5 OHOS probe: all %d checks passed\n", g_checks);
  return 0;
}
