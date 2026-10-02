// gift test_package 运行时探针（真机验证版，HarmonyOS aarch64/musl）
//
// 验证内容：
//  1. 探针可执行文件直接 NEEDED 链接包内全部 9 个共享库（libMRML、
//     libGIFTQuPerl、libGIFTAcPerl、libGIFTQuInvertedFile、
//     libGIFTQuHierarchy、libGIFTAcInvertedFile、libGIFTAcHierarchy、
//     libGIFTAcDistanceMatrix、libGIFTAcURL2FTS）。各库 DF_BIND_NOW，
//     exec 时加载器对同加载组全量重定位 —— 任一库加载/重定位失败即
//     进程启动失败，测试不通过。
//  2. 调用 libMRML 公开 API createErrorMessage("gift test_package
//     probe")，断言返回非空 XML 元素并完整析构（真实 API 往返，非仅
//     符号闭包检查）。
//
// Perl 桩符号说明（仅参与符号解析，永不调用）：
//   libGIFTQuPerl/libGIFTAcPerl 按上游设计引用宿主 perl 解释器符号
//   （perl_alloc/perl_parse/Perl_*/PL_*/boot_DynaLoader 等，gift 客户
//   端二进制以 -Wl,-E 嵌入 perl 解释器时提供）。本探针提供同名空桩，
//   lld 会自动把"被所链共享库 UND 引用的本可执行文件符号"导出到
//   .dynsym，从而满足 BIND_NOW 全量重定位。
//   另提供 CAFPerl::CAFPerl() 构造桩：libMRML 与 libGIFTAcPerl 存在
//   构造函数级互相引用（MRML→CAFPerl ctor、AcPerl→MRML 类型），该桩
//   打破加载顺序环；dlopen libGIFTAcPerl 时其真实定义并存不冲突。
#include <cassert>
#include <cstdio>

#include <CXMLElement.h>

// ── perl 解释器桩（libGIFTQuPerl/libGIFTAcPerl UND，永不调用）──
void *PL_markstack_max, *PL_markstack_ptr, *PL_stack_base, *PL_stack_max,
    *PL_stack_sp, *PL_tmps_floor, *PL_tmps_ix;
extern "C" {
void Perl_call_pv(void) {}
void Perl_free_tmps(void) {}
void Perl_markstack_grow(void) {}
void Perl_newSViv(void) {}
void Perl_newSVpv(void) {}
void Perl_newSVsv_flags(void) {}
void Perl_newXS(void) {}
void Perl_pop_scope(void) {}
void Perl_push_scope(void) {}
void Perl_savetmps(void) {}
void Perl_stack_grow(void) {}
void Perl_sv_2iv_flags(void) {}
void Perl_sv_2mortal(void) {}
void Perl_sv_2pv_flags(void) {}
void Perl_sv_free2(void) {}
void boot_DynaLoader(void) {}
void perl_alloc(void) {}
void perl_construct(void) {}
void perl_parse(void) {}
}

// ── CAFPerl 构造桩（打破 MRML↔AcPerl 加载环，永不调用）──
class CAFPerl {
public:
    CAFPerl();
};
CAFPerl::CAFPerl() {}

// libMRML 公开 API：根据错误文本构造 MRML XML 错误应答元素
CXMLElement *createErrorMessage(const char *message);

int main() {
    // 9 库已在进程启动时以 NEEDED 同加载组方式全部加载并完成
    // BIND_NOW 全量重定位（任一失败则本进程无法启动）。
    CXMLElement *elem = createErrorMessage("gift test_package probe");
    if (elem == nullptr) {
        fprintf(stderr, "FAIL: createErrorMessage returned null\n");
        return 1;
    }
    printf("createErrorMessage(\"gift test_package probe\") -> %p OK\n",
           static_cast<void *>(elem));
    delete elem;
    printf("PASS: 9 libs exec-loaded + libMRML API round-trip OK\n");
    return 0;
}
