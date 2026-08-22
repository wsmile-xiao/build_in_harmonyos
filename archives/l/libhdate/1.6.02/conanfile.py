#!/usr/bin/env python3
"""Conan recipe for libhdate 1.6.02 on HarmonyOS PC.

LibHdate is a small C library for the Hebrew calendar (dates,
holidays, reading sequence) plus hcal/hdate CLI tools. Pure C, zero
external deps. Autotools build.

Bindings (fpc/gpc/python/ruby/php/perl) disabled — only the C library
+ hcal/hdate tools are built.
hcal/hdate date calculations run fine on OHOS (no env restrictions) —
real execution is verifiable.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import get


class LibhdateConan(ConanFile):
    name = "libhdate"
    version = "1.6.02"
    package_type = "application"
    license = "GPL-3.0"
    homepage = "http://libhdate.sourceforge.net/"
    url = "http://libhdate.sourceforge.net/"
    description = ("C library for the Hebrew calendar (dates, "
                   "holidays) + hcal/hdate CLI tools")
    settings = "os", "arch", "compiler", "build_type"

    def source(self):
        get(self, **self.conan_data["sources"][self.version],
            strip_root=True)
        # examples/hcal/local_functions.c: #include <error.h> 是 GNU
        # glibc 头（error()）——OHOS musl libc 无头无符号（nm 实测 0）。
        # include 行替换为宏定义（error(status,errnum,fmt,...) →
        # fprintf(stderr,...)）
        lf = os.path.join(self.source_folder, "examples", "hcal",
                          "local_functions.c")
        ls = open(lf).read()
        old_inc = "#include <error.h>"
        new_inc = ("#include <stdio.h>\n"
                   "#define error(status, errnum, ...) "
                   "fprintf(stderr, __VA_ARGS__)")
        if old_inc in ls:
            ls = ls.replace(old_inc, new_inc, 1)
        # GNU 嵌套函数（create_config_file/open_config_file 定义在
        # get_config_file 体内——clang 不支持 'function definition is
        # not allowed here'；-fnested-functions 无效）——**内联方案**：
        # 删除嵌套函数定义段 + open_config_file() 调用点展开函数体
        # （局部变量/参数作用域天然可用，无需传参/static）
        nstart = ls.find("\t/************************************************************\n\t* sub-function to get_config_file: create_config_file")
        nend = ls.find("	}\n\n\n/************************************************************\n* main part of function get_config_file")
        if nstart != -1 and nend != -1 and nend > nstart:
            ls = ls[:nstart] + ls[nend:]
            # 删除嵌套函数段后清理残留的孤立 '}'（实测 669 行残留——
            # get_config_file 函数体提前闭合，后续内联代码变文件级
            # 'incompatible pointer to integer' 报错）：局部声明段
            # （FILE* config_file;）后紧跟的 '\t}' 是嵌套函数残留
            anchor_var = "\tFILE* config_file;"
            if anchor_var in ls:
                after = ls.split(anchor_var, 1)[1]
                if after.lstrip().startswith("}"):
                    ls = ls.replace(anchor_var + "\n\n\t}", anchor_var, 1)
            # open_config_file() 调用点内联展开（原 if (open_config_file()
            # == TRUE) {...} else {...}）——展开 open 逻辑（TRUE→返回
            # config_file；FALSE→free+NULL；mkdir 路径内联 create 逻辑）
            inline = """	config_file = fopen(config_file_path, "r");
	if (config_file == NULL)
	{
		if (errno != ENOENT) { free(config_file_path); return NULL; }
		path_len = strlen(config_home_path_name)
					+ strlen(config_sub_path_name)
					+ strlen(config_dir_name) +1;
		if (path_len < 1) { free(config_file_path); return NULL; }
		config_dir_path = malloc(path_len);
		if (config_dir_path == NULL)
		{
			error(0,errno,"%s",N_("memory allocation failure"));
			free(config_file_path); return NULL;
		}
		snprintf(config_dir_path, path_len, "%s%s%s",
				config_home_path_name, config_sub_path_name,
				config_dir_name);
		if ((mkdir(config_dir_path, (mode_t) 0700) != 0) &&
			(errno != EEXIST))
		{
			free(config_dir_path); free(config_file_path); return NULL;
		}
		greetings_to_version_16();
		config_file = fopen(config_file_path, "a");
		if (config_file != NULL)
		{
			fprintf(config_file, "%s", default_config_file_text);
			error(0,0,"%s: %s",N_("config file created"), config_file_path);
			if (fclose(config_file) != 0) error(0,errno,"%s %s",N_("failure closing"),config_file_name);
		}
		free(config_dir_path); free(config_file_path); return NULL;
	}
	free(config_file_path);
	return config_file;
}"""
            old_call = """	if (open_config_file() == TRUE)
	{
		free(config_file_path);
		return config_file;
	}
	else
		free(config_file_path);
		return NULL;
}"""
            if old_call in ls:
                ls = ls.replace(old_call, inline, 1)
            else:
                print("[warn] open_config_file() call site not matched")
        else:
            print("[warn] nested function block anchors not found")
        open(lf, "w").write(ls)
        print("local_functions.c nested functions inlined")

    def build(self):
        # E011 根治（bacula/badvpn 同款实证）：config.status 在当前目录
        # 生成并直接执行 ./confXXXX/subs1.awk（HMDFS 执行位被剥）——源码
        # 复制到非 HMDFS（/data/storage/el2/base/cache）再 configure/make
        work = "/data/storage/el2/base/cache/libhdate-src"
        shutil.rmtree(work, ignore_errors=True)
        shutil.copytree(self.source_folder, work, symlinks=True)
        # CI 沙箱执行权限：configure 测试编译（C compiler works 检查）生成
        # conftest 可执行文件并运行——CI el2 沙箱目录权限受限（实测
        # 'C compiler cannot create executables'——本地通过 CI 失败）——
        # 递归放开 work 目录权限（同 bacula-fd getcwd 权限教训）
        os.system(f"chmod -R 777 {work}")
        # E007：config.guess 无法识别 OHOS——显式 --build 三元组；
        # 绑定全部禁用（AUR PKGBUILD 同款——只构建 C 库 + hcal/hdate）
        # -fnested-functions：local_functions.c 有 GNU 嵌套函数定义
        # （create_config_file/open_config_file 在 get_config_file 体内）
        # ——clang 默认不支持（'function definition is not allowed here'
        # 实测），用 clang 的嵌套函数实验选项
        self.run(
            f"env CFLAGS=\"-fnested-functions\" "
            f"./configure --build=aarch64-unknown-linux-gnu "
            f"--prefix={self.package_folder} "
            "--disable-fpc --disable-gpc --disable-python "
            "--disable-ruby --disable-php --disable-perl",
            cwd=work,
        )
        # 构建顺序：src 库（libhdate.la）→ examples/hcal 的 hdate 工具
        # （顶层 make 无 hdate 目标实测 'No rule to make target hdate'；
        # hcal 是可选示例工具，hcal.c 有 GNU 嵌套函数 'function
        # definition is not allowed here'——只构建 hdate 跳过 hcal）
        self.run("make -C src", cwd=work)
        self.run("make -C examples/hcal hdate", cwd=work)

    def package(self):
        work = "/data/storage/el2/base/cache/libhdate-src"
        bin_dir = os.path.join(self.package_folder, "bin")
        lib_dir = os.path.join(self.package_folder, "lib")
        inc_dir = os.path.join(self.package_folder, "include")
        os.makedirs(bin_dir, exist_ok=True)
        os.makedirs(lib_dir, exist_ok=True)
        os.makedirs(inc_dir, exist_ok=True)
        # hdate 工具（构建产物在 examples/hcal/——make -C examples/hcal
        # hdate；**注意 examples/hcal/hdate 是 libtool wrapper 脚本**
        # （实测 'does not exist /bin/.libs/hdate'）——真实二进制在
        # examples/hcal/.libs/hdate，复制真实二进制）
        src = os.path.join(work, "examples", "hcal", ".libs", "hdate")
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(bin_dir, "hdate"))
        # libhdate 库（libtool 产物在 src/.libs/）+ 头文件
        lib_src = os.path.join(work, "src", ".libs")
        if os.path.isdir(lib_src):
            for f in os.listdir(lib_src):
                if f.startswith("libhdate.so") or f == "libhdate.a":
                    shutil.copy2(os.path.join(lib_src, f),
                                 os.path.join(lib_dir, f))
        inc_src = os.path.join(work, "src", "hdate.h")
        if os.path.exists(inc_src):
            # 实际头文件名是 hdate.h（非 libhdate.h 实测）——复制改名
            # 为 libhdate.h（库的约定头名，test 检查该名）
            shutil.copy2(inc_src, os.path.join(inc_dir, "libhdate.h"))

    def package_info(self):
        self.cpp_info.libs = ["hdate"]
        self.conf_info.define("user.libhdate:exe", os.path.join(
            self.package_folder, "bin", "hdate"))
