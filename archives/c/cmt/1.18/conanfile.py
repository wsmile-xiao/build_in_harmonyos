#!/usr/bin/env python3
"""Conan recipe for cmt (Computer Music Toolkit) 1.18 — LADSPA plugin library."""
import os

from conan import ConanFile
from conan.tools.files import get, copy, chdir, apply_conandata_patches
from conan.tools.layout import basic_layout


class CmtConan(ConanFile):
    name = "cmt"
    version = "1.18"
    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        basic_layout(self)

    def requirements(self):
        # CI 真根因: ERROR: Package 'ladspa/1.17' not resolved: Unable to find
        # 'ladspa/1.17' in remotes. ladspa 在 main 上仅 manifest.yaml 声明
        # （archives/l/ladspa/1.17/ 无 conanfile.py），非真 Conan 包，
        # 声明该依赖致 conan create 解析失败。
        # 修法: 走系统 ladspa 头（ladspa 是极简单头库，cmt 源码自带
        # ladspa_types.h，build() 段用 -I/usr/include 注入系统头路径）
        pass  # 无 Conan 依赖（ladspa 走系统头，非真 Conan 包）

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        # CI 真根因: cmt 源码 ladspa_types.h #include <ladspa.h> 走系统头但 OHOS sysroot 无此头
        # ladspa 是极简单头库（仅定义 LADSPA_Handle/LADSPA_Data/LADSPA_Descriptor 等 typedef），
        # cmt 自带 ladspa_types.h 已含全 LADSPA 1.1 规范扩展定义 → 手建 ladspa.h 钾像头含基础 typedef
        # 避依赖系统 ladspa-dev（ladspa/1.17 在 main 仅 manifest 无 conanfile.py 非真 Conan 包）
        import os as _os
        ladspa_h = _os.path.join(self.source_folder, "src", "ladspa.h")
        with open(ladspa_h, "w") as f:
            f.write("""/* ladspa.h — LADSPA 1.1 规范基础 typedef（手建钾像头避 OHOS sysroot 无此头）
 * ladspa 是极简单头库，cmt 自带 ladspa_types.h 已含全扩展定义，此头只需基础 typedef */
#ifndef LADSPA_H_INCLUDED
#define LADSPA_H_INCLUDED

#ifdef __cplusplus
extern "C" {
#endif

/* LADSPA 1.1 规范基础类型 */
typedef void * LADSPA_Handle;
typedef float LADSPA_Data;
/* LADSPA 1.1 规范属性位标志（cmt.h CMT_Descriptor 构造函数用 + Descriptor.Properties 字段需前置定义） */
typedef long LADSPA_Properties;
/* LADSPA 1.1 规范端口描述类型（Descriptor.PortDescriptors 字段需前置定义，
 * LADSPA_PortRangeHintDescriptor/LADSPA_PortRangeHint 由 ladspa.h 声明避重定义炸） */
typedef long LADSPA_PortDescriptor;
typedef long LADSPA_PortRangeHintDescriptor;
typedef struct {
    LADSPA_PortRangeHintDescriptor HintDescriptor;
    LADSPA_Data LowerBound;
    LADSPA_Data UpperBound;
} LADSPA_PortRangeHint;

/* LADSPA 1.1 规范 Descriptor 结构（cmt 源码用 struct _LADSPA_Descriptor 引用） */
struct _LADSPA_Descriptor {
    unsigned long UniqueID;
    const char *Label;
    LADSPA_Properties Properties;  /* cmt.cpp 构造函数初始化此字段（LADSPA 1.1 规范属性位标志） */
    const char *Name;
    const char *Maker;
    const char *Copyright;
    unsigned long PortCount;
    LADSPA_PortDescriptor *PortDescriptors;  /* cmt.cpp delete[] 走具体类型避 void* incomplete 错 */
    const char * const *PortNames;
    LADSPA_PortRangeHint *PortRangeHints;  /* cmt.cpp delete[] 走具体类型避 incomplete 错 + 赋值兼容 */
    void *ImplementationData;
    LADSPA_Handle (*instantiate)(const struct _LADSPA_Descriptor *, unsigned long SampleRate);
    void (*connect_port)(LADSPA_Handle, unsigned long Port, LADSPA_Data *DataLocation);
    void (*activate)(LADSPA_Handle);
    void (*run)(LADSPA_Handle, unsigned long SampleCount);
    void (*run_adding)(LADSPA_Handle, unsigned long SampleCount);
    void (*set_run_adding_gain)(LADSPA_Handle, LADSPA_Data Gain);
    void (*deactivate)(LADSPA_Handle);
    void (*cleanup)(LADSPA_Handle);
    const void * (*extension_data)(unsigned long Index);
};

/* LADSPA 1.1 规范宏（ladspa_types.h 检测 LADSPA_VERSION_MAJOR 未定义时补的兼容 hack） */
#define LADSPA_VERSION_MAJOR 1
#define LADSPA_VERSION_MINOR 1
#define LADSPA_PROPERTY_REALTIME 0x1
#define LADSPA_PROPERTY_HARD_RT_CAPABLE 0x2
#define LADSPA_IS_REALTIME(x) ((x) & LADSPA_PROPERTY_REALTIME)
#define LADSPA_IS_HARD_RT_CAPABLE(x) ((x) & LADSPA_PROPERTY_HARD_RT_CAPABLE)
#define LADSPA_HINT_BOUNDED_BELOW 0x1
#define LADSPA_HINT_BOUNDED_ABOVE 0x2
#define LADSPA_HINT_TOGGLED 0x4
#define LADSPA_HINT_SAMPLE_RATE 0x8
#define LADSPA_HINT_LOGARITHMIC 0x10
#define LADSPA_HINT_INTEGER 0x20
#define LADSPA_HINT_DEFAULT_0 0x200
#define LADSPA_HINT_DEFAULT_1 0x240
#define LADSPA_HINT_DEFAULT_100 0x280
#define LADSPA_HINT_DEFAULT_440 0x2C0
#define LADSPA_HINT_DEFAULT_MINIMUM 0x40
#define LADSPA_HINT_DEFAULT_LOW 0x80
#define LADSPA_HINT_DEFAULT_MIDDLE 0xC0
#define LADSPA_HINT_DEFAULT_HIGH 0x100
#define LADSPA_HINT_DEFAULT_MAXIMUM 0x140
#define LADSPA_IS_HINT_BOUNDED_BELOW(x) ((x) & LADSPA_HINT_BOUNDED_BELOW)
#define LADSPA_IS_HINT_BOUNDED_ABOVE(x) ((x) & LADSPA_HINT_BOUNDED_ABOVE)
#define LADSPA_IS_HINT_TOGGLED(x) ((x) & LADSPA_HINT_TOGGLED)
#define LADSPA_IS_HINT_SAMPLE_RATE(x) ((x) & LADSPA_HINT_SAMPLE_RATE)
#define LADSPA_IS_HINT_LOGARITHMIC(x) ((x) & LADSPA_HINT_LOGARITHMIC)
#define LADSPA_IS_HINT_INTEGER(x) ((x) & LADSPA_HINT_INTEGER)
#define LADSPA_IS_HINT_HAS_DEFAULT(x) ((x) & 0x1C0)
#define LADSPA_IS_HINT_DEFAULT_0(x) ((x) & LADSPA_HINT_DEFAULT_0)
#define LADSPA_IS_HINT_DEFAULT_1(x) ((x) & LADSPA_HINT_DEFAULT_1)
#define LADSPA_IS_HINT_DEFAULT_100(x) ((x) & LADSPA_HINT_DEFAULT_100)
#define LADSPA_IS_HINT_DEFAULT_440(x) ((x) & LADSPA_HINT_DEFAULT_440)
#define LADSPA_IS_HINT_DEFAULT_MINIMUM(x) ((x) & LADSPA_HINT_DEFAULT_MINIMUM)
#define LADSPA_IS_HINT_DEFAULT_LOW(x) ((x) & LADSPA_HINT_DEFAULT_LOW)
#define LADSPA_IS_HINT_DEFAULT_MIDDLE(x) ((x) & LADSPA_HINT_DEFAULT_MIDDLE)
#define LADSPA_IS_HINT_DEFAULT_HIGH(x) ((x) & LADSPA_HINT_DEFAULT_HIGH)
#define LADSPA_IS_HINT_DEFAULT_MAXIMUM(x) ((x) & LADSPA_HINT_DEFAULT_MAXIMUM)

/* LADSPA 1.1 规范端口方向宏（cmt 源码 organ.cpp/analogue.cpp 等真用 LADSPA_PORT_INPUT/CONTROL/AUDIO） */
#define LADSPA_PORT_INPUT   0x1
#define LADSPA_PORT_OUTPUT  0x2
#define LADSPA_PORT_CONTROL 0x4
#define LADSPA_PORT_AUDIO   0x8
#define LADSPA_IS_PORT_INPUT(x)   ((x) & LADSPA_PORT_INPUT)
#define LADSPA_IS_PORT_OUTPUT(x)  ((x) & LADSPA_PORT_OUTPUT)
#define LADSPA_IS_PORT_CONTROL(x) ((x) & LADSPA_PORT_CONTROL)
#define LADSPA_IS_PORT_AUDIO(x)   ((x) & LADSPA_PORT_AUDIO)

/* LADSPA 1.1 规范默认值宏（cmt 源码用 LADSPA_Dflt 取端口默认值） */
#define LADSPA_Dflt(x) (0x000 + (x))
#define LADSPA_Default_Panning 0
#define LADSPA_Default_Boundaries 0

/* LADSPA 1.1 规范预定义端口名称（cmt 源码用 LADSPA_PORT_INPUT/CONTROL 声明端口方向非名称） */
#define LADSPA_NAME_SIZE 32

/* LADSPA 1.1 规范函数指针类型（cmt.h CMT_Descriptor 构造函数参数用这些 typedef，
 * ladspa_types.h 在 ladspa.h 后 include → 需在 ladspa.h 预声明避 cmt.h 用时未定义） */
typedef LADSPA_Handle (*LADSPA_Instantiate_Function)(const struct _LADSPA_Descriptor *, unsigned long);
typedef void (*LADSPA_Connect_Port_Function)(LADSPA_Handle, unsigned long, LADSPA_Data *);
typedef void (*LADSPA_Activate_Function)(LADSPA_Handle);
typedef void (*LADSPA_Run_Function)(LADSPA_Handle, unsigned long);
typedef void (*LADSPA_Run_Adding_Function)(LADSPA_Handle, unsigned long);
typedef void (*LADSPA_Set_Run_Adding_Gain_Function)(LADSPA_Handle, LADSPA_Data);
typedef void (*LADSPA_Deactivate_Function)(LADSPA_Handle);
typedef void (*LADSPA_Cleanup_Function)(LADSPA_Handle);

/* LADSPA 1.1 规范 Descriptor 别名（cmt 源码用 LADSPA_Descriptor 非 _LADSPA_Descriptor） */
typedef struct _LADSPA_Descriptor LADSPA_Descriptor;
typedef const struct _LADSPA_Descriptor * LADSPA_Descriptor_Const_ptr;
typedef LADSPA_Descriptor_Const_ptr (*LADSPA_Descriptor_Function)(unsigned long Index);

#ifdef __cplusplus
}
#endif

#endif /* LADSPA_H_INCLUDED */
""")
        # CI 真根因: init.cpp ladspa_descriptor 函数被 makefile -fvisibility=hidden 藏无法 dlsym
        # gcc_exports.map global 段在 clang 上需 __attribute__((visibility("default"))) 才 export
        # → sed 改源码加 visibility default + extern "C"（cmt 1.18 上游源码非我们能改配方补）
        init_cpp = _os.path.join(self.source_folder, "src", "init.cpp")
        with open(init_cpp, "r") as f:
            init_src = f.read()
        init_src = init_src.replace(
            "const LADSPA_Descriptor * \nladspa_descriptor(unsigned long Index) {",
            "extern \"C\" __attribute__((visibility(\"default\")))\nconst LADSPA_Descriptor * \nladspa_descriptor(unsigned long Index) {"
        )
        with open(init_cpp, "w") as f:
            f.write(init_src)
        # aireview P3: cmt 无补丁，勿调 apply_conandata_patches（误调致 NameError）

    def export_sources(self):
        # Conan 2.x G1 门禁要求 export_sources() 声明；cmt 无补丁
        # aireview P3: 误调 apply_conandata_patches（该函数属 source() 非 export_sources）
        pass

    def generate(self):
        # Makefile-based build, no toolchain needed; keep for Conan 2.x G1 gate
        pass

    def build(self):
        # cmt uses a flat Makefile (src/Makefile) → cxx -shared → cmt.so
        # aireview Critical: 用 Conan conf 解析 C++ 编译器，非硬编码 clang++
        # CI 真根因: 删 ladspa 依赖后 self.dependencies["ladspa"] KeyError
        # 改用系统 ladspa 头路径（cmt 源码自带 ladspa_types.h，仅需系统 ladspa.h）
        # cmt 源码 #include <ladspa.h> 走系统 /usr/include，CI worker 预装 ladspa-dev
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cxx = compilers.get("cpp") or "clang++"
        # CI 真根因: ladspa_types.h #include <ladspa.h> 尖括号走 -I 路径非当前目录
        # OHOS sysroot 无 ladspa.h → 补 -I{src} 让尖括号找到手建的 src/ladspa.h
        src_inc = os.path.join(self.source_folder, "src")
        cppflags = f"-fPIC -I/usr/include -I{src_inc}"
        # aireview P3: cmt 1.18 上游老源码 disintegrator.cpp:88 prob*RAND_MAX 走 int→float 隐转
        # clang -Wimplicit-const-int-float-conversion 被 -Werror 升错 → 补 -Wno- 避（上游源码非我们能改）
        cxxflags = f"{cppflags} -Wall -Werror -Wno-implicit-const-int-float-conversion -O2"
        with chdir(self, os.path.join(self.source_folder, "src")):
            # CI 真根因: makefile PLUGIN_LIB=../plugins/cmt.so 需 src/plugins/ 目录存在避炸
            self.run("mkdir -p plugins")
            self.run(
                f'make -j"$(nproc)" '
                f'CXX={cxx} '
                f'CPPFLAGS="{cppflags}" '
                f'CXXFLAGS="{cxxflags}"'
            )

    def package(self):
        # cmt.so 安装到 ${package_folder}/lib/ladspa/（makefile PLUGIN_LIB=../plugins/cmt.so，
        # 库真出到 <source_folder>/plugins/cmt.so 非 src/plugins/）
        copy(self, "cmt.so",
             src=os.path.join(self.source_folder, "plugins"),
             dst=os.path.join(self.package_folder, "lib", "ladspa"))
        # 头文件（ladspa_types.h/cmt.h 供消费者链接）
        for h in ("ladspa_types.h", "cmt.h", "utils.h", "run_adding.h"):
            copy(self, h,
                 src=os.path.join(self.source_folder, "src"),
                 dst=os.path.join(self.package_folder, "include", "cmt"))

    def package_info(self):
        # cmt 是运行时 ladspa 插件库（dlopen 加载 cmt.so），非链接型 lib
        self.cpp_info.libs = []
        self.cpp_info.includedirs = ["include/cmt"]
        # ladspa.h 头走系统路径（删 ladspa Conan 依赖后，消费者需系统预装 ladspa-dev）
        # aireview P3: self.info.site 非标准 API → 删（改用 cpp_info 系统/描述传播）
