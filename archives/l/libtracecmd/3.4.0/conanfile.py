import os
import shlex
import shutil

from conan import ConanFile
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, patch
from conan.tools.layout import basic_layout

# libtracecmd 必须链接 libtraceevent / libtracefs（trace-cmd 3.4 的 Makefile 下限
# 是 >= 1.9 / >= 1.8，meson.build 写的是 >= 1.9.0 / >= 1.8.0）。制品仓里两者均未
# 发布（GET /api/registry?keyword=libtrace 命中 0 条），按 L0i/R36 不能出现在
# requires 里，所以作为构建期输入下载并静态链入，公共头随包交付。
_BUNDLED = ("libtraceevent", "libtracefs")


class LibtracecmdConan(ConanFile):
    name = "libtracecmd"
    version = "3.4.0"
    description = ("Library to read, write and analyse Linux ftrace trace-cmd (.dat) trace "
                   "files, as published by the trace-cmd project")
    license = "LGPL-2.1-only"
    homepage = "https://git.kernel.org/pub/scm/utils/trace-cmd/trace-cmd.git"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    # ------------------------------------------------------------------ layout

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        basic_layout(self, src_folder="src")

    def export_sources(self):
        export_conandata_patches(self)
        # bundled_patches 不在 conandata 的 patches 键下（apply_conandata_patches 会把
        # 它们往主源码树上打），所以自己导出、自己在 build() 里按目标树应用。
        for name, patches in self.conan_data.get("bundled_patches", {}).items():
            for entry in patches:
                copy(self, os.path.basename(entry["patch_file"]),
                     src=os.path.join(self.recipe_folder, "patches"),
                     dst=os.path.join(self.export_sources_folder, "patches"))

    def requirements(self):
        # 可选压缩后端：trace-compress-zlib.c，制品仓已发布。
        self.requires("zlib/1.3.1.1")

    def build_requirements(self):
        # 上游 CUnit 套件（utest/）只在构建期用，不进消费者依赖图。
        self.test_requires("cunit/2.1-3")

    # ----------------------------------------------------------------- sources

    @property
    def _root(self):
        return self.source_folder

    def _bundled_root(self, name):
        return os.path.join(self.source_folder, "bundled", name)

    def _stage_lib(self):
        return os.path.join(self.build_folder, "bundled-stage", "lib")

    def _stage_inc(self):
        return os.path.join(self.build_folder, "bundled-stage", "include")

    def _extract(self, spec, destination, marker):
        if os.path.isfile(os.path.join(destination, marker)):
            return
        urls = spec["url"]
        if isinstance(urls, str):
            urls = [urls]

        last_error = None
        for url in urls:
            filename = os.path.basename(url)
            try:
                get(self, filename=filename, destination=destination, url=url,
                    sha256=spec["sha256"], strip_root=True)
                return
            except Exception as exc:
                last_error = exc
                # A failed download may leave a partial archive behind.  Remove
                # it so the next mirror is actually attempted.
                archive = os.path.join(destination, filename)
                if os.path.isfile(archive):
                    os.remove(archive)
                self.output.warning("Source download failed from %s: %s" % (url, exc))

        if last_error is not None:
            raise last_error
        raise RuntimeError("No source URL configured for %s" % destination)

    def _ensure_sources(self):
        # conan create 在 source 目录已有缓存时会跳过 source()，所以构建前按关键
        # 文件复查一遍，缺哪个补哪个。
        self._extract(self.conan_data["sources"], self._root, "Makefile")
        for name in _BUNDLED:
            self._extract(self.conan_data["bundled_sources"][name],
                          self._bundled_root(name), "Makefile")

    def source(self):
        self._ensure_sources()

    # ------------------------------------------------------------------- tools

    @property
    def _cc(self):
        exes = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        if exes.get("c"):
            return str(exes["c"])
        return {"clang": "clang", "apple-clang": "clang", "gcc": "gcc"}.get(
            str(self.settings.compiler), "cc")

    def _bin_tool(self, env_var, names, fallback):
        value = os.environ.get(env_var)
        if value:
            return value
        cc_dir = os.path.dirname(os.path.abspath(self._cc))
        for name in names:
            candidate = os.path.join(cc_dir, name)
            if os.path.isfile(candidate):
                return candidate
        for name in names:
            found = shutil.which(name)
            if found:
                return found
        return fallback

    @property
    def _ar(self):
        return self._bin_tool("AR", ("llvm-ar", "ar"), "ar")

    @property
    def _ranlib(self):
        return self._bin_tool("RANLIB", ("llvm-ranlib", "ranlib"), "ranlib")

    @property
    def _jobs(self):
        return max(1, min(os.cpu_count() or 1, 8))

    def _dep_dirs(self, dep_name):
        dep = self.dependencies[dep_name]
        root = str(dep.package_folder)
        includes = [d if os.path.isabs(d) else os.path.join(root, d)
                    for d in dep.cpp_info.includedirs]
        libs = [d if os.path.isabs(d) else os.path.join(root, d)
                for d in dep.cpp_info.libdirs]
        return includes, libs

    def _cunit_flags(self):
        incs, libs = self._dep_dirs("cunit")
        return ["-I%s" % d for d in incs], ["-L%s" % d for d in libs]

    # -------------------------------------------------------------------- make

    # 上游 kbuild 风格 Makefile 里 nm/objcopy 是写死的命令名（libtraceevent
    # scripts/utils.mk 的 redefine_local 用 nm 生成 --redefine-sym 列表，src/Makefile
    # 第 23 行用 objcopy 落地静态库），而 OHOS 工具链只给 llvm-* 前缀的名字。
    # 与其改上游 Makefile，不如在构建目录里放一层转发脚本，worker 上有原生同名工具
    # 时不会被遮蔽。
    _shim_tools = {
        "nm": ("llvm-nm",),
        "objcopy": ("llvm-objcopy",),
        "ar": ("llvm-ar",),
        "ranlib": ("llvm-ranlib",),
        "strip": ("llvm-strip",),
        "readelf": ("llvm-readelf",),
    }

    def _tool_shims(self):
        shim_dir = os.path.join(self.build_folder, "tool-shims")
        cc_dir = os.path.dirname(os.path.abspath(self._cc))
        for name, providers in self._shim_tools.items():
            if shutil.which(name):
                continue
            real = None
            for provider in providers:
                candidate = os.path.join(cc_dir, provider)
                if os.path.isfile(candidate):
                    real = candidate
                    break
                found = shutil.which(provider)
                if found:
                    real = found
                    break
            if not real:
                continue
            link = os.path.join(shim_dir, name)
            if os.path.isfile(link):
                continue
            os.makedirs(shim_dir, exist_ok=True)
            script = "#!/bin/sh" + chr(10)
            script += "exec " + shlex.quote(real) + ' \"$@\"' + chr(10)
            with open(link, "w", encoding="utf-8", newline=chr(10)) as handle:
                handle.write(script)
            os.chmod(link, 0o755)
        return shim_dir

    def _make(self, directory, targets, cflags=(), ldflags=(), variables=()):
        # CC/AR/RANLIB/CFLAGS/LDFLAGS 走环境而不是 make 命令行：这几个 Makefile 都是
        # kbuild 风格，顶层 `override CFLAGS += $(INCLUDES)` 之后再 descend，而 make
        # 命令行的同名变量会以 MAKEFLAGS 覆盖到子 make，子 make 就把 -I 全丢了
        # （libtracefs src/Makefile 编 tracefs-utils.c 时报 'tracefs.h' file not found）。
        # 环境变量则相反：`CFLAGS ?=` 不覆盖它，`override CFLAGS +=` 能追加，且会
        # 随子 make 继续传递。需要压过 := 探测的变量（TEST_*/*_LDLAGS/NO_*）留在命令行。
        flags = " ".join(("-O2", "-Wall", "-g") + tuple(cflags))
        # EXTRA_CFLAGS 也要给：libtraceevent 的 Makefile 是 `CFLAGS := $(EXTRA_CFLAGS)`
        # 形态（128 行），不认环境里的 CFLAGS，会被它重置成 -g -Wall 而丢掉 -I。
        env_vars = [("CC", self._cc), ("AR", self._ar), ("RANLIB", self._ranlib),
                    ("CFLAGS", flags), ("EXTRA_CFLAGS", flags)]
        if ldflags:
            env_vars.append(("LDFLAGS", " ".join(ldflags)))
        prefix = " ".join("%s=%s" % (key, shlex.quote(value)) for key, value in env_vars)
        cmd = ["make", "-C", directory, "-j%d" % self._jobs]
        cmd += list(variables) + list(targets)
        command = " ".join(shlex.quote(part) for part in cmd)
        self.run("PATH=%s:$PATH %s %s" % (shlex.quote(self._tool_shims()), prefix, command),
                 env="conanbuild")

    def _produced(self, root, name):
        # kbuild 风格 Makefile 的 bdir 会被 descend 改写（libtraceevent 的 utest 落在
        # utest/，lib 落在 lib/），所以按候选路径找产物而不是猜目录。
        for candidate in (os.path.join(root, "utest", name),
                          os.path.join(root, "lib", name),
                          os.path.join(root, name)):
            if os.path.isfile(candidate):
                return candidate
        raise Exception("%s not produced under %s" % (name, root))

    def _runtime_lib_paths(self):
        paths = [self._stage_lib()]
        for dep in ("zlib", "cunit"):
            if dep in self.dependencies:
                paths += self._dep_dirs(dep)[1]
        return paths

    def _rpath_flags(self):
        # 上游套件的可执行文件在 build() 里就要跑，而 libz.so / libcunit 只在
        # conan 包目录里；把搜索路径烘进测试二进制，不依赖 LD_LIBRARY_PATH。
        return ["-Wl,-rpath,%s" % path for path in self._runtime_lib_paths()]

    def generate(self):
        VirtualBuildEnv(self).generate()

    # ------------------------------------------------------------------ patch

    def _patch_bundled(self):
        for name, patches in self.conan_data.get("bundled_patches", {}).items():
            root = self._bundled_root(name)
            for entry in patches:
                patch_file = os.path.join(self.export_sources_folder, entry["patch_file"])
                if not self._patch_needed(root, patch_file, entry):
                    self.output.info("already applied: %s" % entry["patch_file"])
                    continue
                patch(self, patch_file=patch_file, base_path=root, strip=1)

    @staticmethod
    def _patch_needed(root, patch_file, entry):
        """构建目录会在同一次 create 里重复执行 build()，用补丁引入的符号名判重。"""
        target = os.path.join(root, entry["probe_target"])
        if not os.path.isfile(target):
            raise Exception("patch target missing in %s: %s" % (entry["probe_target"], root))
        with open(target, encoding="utf-8", errors="ignore") as handle:
            applied = entry["probe_symbol"] in handle.read()
        if applied:
            return False
        if not os.path.isfile(patch_file):
            raise Exception("patch file not exported: %s" % patch_file)
        return True

    # ------------------------------------------------------------------- build

    def build(self):
        self._ensure_sources()
        apply_conandata_patches(self)
        self._patch_bundled()
        for name in _BUNDLED:
            self._build_bundled(name)
        self._run_libtraceevent_suite()
        self._build_trace_cmd()
        self._run_trace_cmd_suite()

    def _build_bundled(self, name):
        root = self._bundled_root(name)
        cflags = ["-fPIC"]
        variables = []
        if name == "libtracefs":
            # libtracefs 的 Makefile 在 pkg-config 探测失败时直接 $(error)，且需要
            # libtraceevent 的头文件。
            cflags += ["-I%s" % self._stage_inc()]
            # OHOS SDK 的 <linux/vm_sockets.h> 会带进旧版 <linux/socket.h>，与
            # <sys/socket.h> 里的 struct sockaddr_storage 冲突（tracefs-vsock.c 同时
            # 包含两者），vsock 传输在本平台关掉；读写解析路径不受影响。
            variables += ["TEST_LIBTRACEEVENT=y", "VSOCK_DEFINED=0"]
        self._make(root, ["%s.a" % name], cflags=cflags, variables=variables)

        built = os.path.join(root, "lib", "%s.a" % name)
        if not os.path.isfile(built):
            raise Exception("bundled %s archive not produced: %s" % (name, built))
        os.makedirs(self._stage_lib(), exist_ok=True)
        os.makedirs(self._stage_inc(), exist_ok=True)
        shutil.copy(built, os.path.join(self._stage_lib(), os.path.basename(built)))
        spec = self.conan_data["bundled_sources"][name]
        copy(self, "*.h", src=os.path.join(root, spec["header_dir"]), dst=self._stage_inc())
        for header in spec["public_headers"]:
            if not os.path.isfile(os.path.join(self._stage_inc(), header)):
                raise Exception("bundled %s header not staged: %s" % (name, header))

    def _run_libtraceevent_suite(self):
        """libtraceevent 被静态链进本包，它的上游 CUnit 套件即本包所发布代码的测试。"""
        root = self._bundled_root("libtraceevent")
        cflags, ldflags = self._cunit_flags()
        self._make(root, ["test"], cflags=cflags, ldflags=ldflags + self._rpath_flags())
        exe = self._produced(root, "trace-utest")
        self.output.info("upstream libtraceevent CUnit suite: %s" % exe)
        self.run("%s -s" % shlex.quote(exe), env="conanbuild")

    def _trace_cmd_vars(self, whole_archive=False):
        ev_inc = "-I%s" % self._stage_inc()
        stage = "-L%s" % self._stage_lib()
        z_incs, z_libs = self._dep_dirs("zlib")
        cflags = [ev_inc, stage] + ["-I%s" % d for d in z_incs]
        ldflags = [stage]
        if whole_archive:
            ldflags.append("-Wl,--whole-archive")
        ldflags += ["-L%s" % d for d in z_libs] + ["-lpthread"]
        variables = [
            # 上游靠 pkg-config 探测这两个依赖，构建期输入不在系统搜索路径内，因此
            # 直接给判定结果与 flag（命令行变量优先于 makefile 里的 := 赋值）。
            # --whole-archive 只用在编 libtracecmd.so 那一次：把两个静态库整体装进
            # .so，否则消费者只链 -ltracecmd 时，libtracecmd 自己没引用到的
            # tep_*/tracefs_* 符号会缺失。trace-cmd 可执行文件与 utest 的链接行里
            # 同时有 $(LIBTRACECMD_STATIC) 和 -ltracecmd，那里整体归档会变成
            # duplicate symbol，所以那两次不开。收尾 flag 挂在 LIBS 里最后一个静态库
            # （LIBTRACEFS_LDLAGS）后面，多写一次对不开归档的链接是无操作。
            "TEST_LIBTRACEEVENT=y", "TEST_LIBTRACEFS=y",
            "LIBTRACEEVENT_CFLAGS=%s" % ev_inc, "LIBTRACEEVENT_LDLAGS=-ltraceevent",
            "LIBTRACEFS_CFLAGS=%s" % ev_inc,
            "LIBTRACEFS_LDLAGS=-ltracefs -Wl,--no-whole-archive",
            "ZLIB_INSTALLED=1", "ZLIB_LDLAGS=-lz",
            # zstd 只在开发机上可见（harmonybrew /opt/zstd），既不是制品仓也不是系统
            # 库，链进去会让消费者依赖一个构建机路径。
            "NO_LIBZSTD=1", "NO_PYTHON=1", "NO_VSOCK=1",
        ]
        return cflags, ldflags, variables

    def _build_trace_cmd(self):
        cflags, ldflags, variables = self._trace_cmd_vars()
        so_cflags, so_ldflags, so_variables = self._trace_cmd_vars(whole_archive=True)
        unit_cflags, unit_ldflags = self._cunit_flags()
        cflags += unit_cflags
        ldflags += unit_ldflags
        variables += ["CUNIT_INSTALLED=1", "libdir_relative=lib"]
        self._make(self._root, ["libtracecmd.a", "libtracecmd.so"],
                   cflags=so_cflags + unit_cflags, ldflags=so_ldflags + unit_ldflags,
                   variables=so_variables + ["libdir_relative=lib"])
        # 上游 utest 需要 trace-cmd 可执行文件（utest/tracecmd-utest.c 的
        # test_suite_init 要求 ../tracecmd/trace-cmd 存在且可执行）。trace-cmd 本身
        # 是 GPL-2.0，只在构建目录里用来跑测试，不进包。
        self._make(self._root, ["trace-cmd"], cflags=cflags, ldflags=ldflags, variables=variables)
        self._make(self._root, ["test"], cflags=cflags,
                   ldflags=ldflags + ["-lpthread"] + self._rpath_flags(),
                   variables=variables)

    def _tracefs_usable(self):
        for base in ("/sys/kernel/tracing", "/sys/kernel/debug/tracing"):
            for entry in ("tracing_on", "trace"):
                if os.access(os.path.join(base, entry), os.R_OK | os.W_OK):
                    return True
        return False

    def _run_trace_cmd_suite(self):
        exe = self._produced(self._root, "trace-utest")
        if not self._tracefs_usable():
            self.output.warning(
                "SKIP upstream libtracecmd suite: all 8 CU_add_test cases drive the trace-cmd "
                "CLI against tracefs (record/sqlhist/kprobe/uprobe/eprobe/reset); on this host "
                "/sys/kernel/tracing is root-owned 0755 and the build user has no CAP_SYS_ADMIN, "
                "so not even test_suite_init can produce a trace file")
            return
        self.output.info("upstream libtracecmd CUnit suite: %s" % exe)
        self.run("%s -s" % shlex.quote(exe), env="conanbuild")

    # ----------------------------------------------------------------- package

    def _merge_static(self, built_dir, lib_dst):
        """静态形态必须自带被链入的构建期输入，否则只 -ltracecmd 的消费者拿不到
        tep_*/tracefs_* 符号。三个归档并成一个 libtracecmd.a，包里仍然只有一个库名。
        """
        work = os.path.join(self.build_folder, "merged-objs")
        shutil.rmtree(work, ignore_errors=True)
        os.makedirs(work)
        for archive in (os.path.join(built_dir, "libtracecmd.a"),
                        os.path.join(self._stage_lib(), "libtraceevent.a"),
                        os.path.join(self._stage_lib(), "libtracefs.a")):
            if not os.path.isfile(archive):
                raise Exception("archive to merge is missing: %s" % archive)
            self.run("%s x %s" % (shlex.quote(self._ar), shlex.quote(archive)),
                     cwd=work, env="conanbuild")
        objects = sorted(name for name in os.listdir(work) if name.endswith(".o"))
        if not objects:
            raise Exception("no objects extracted from the static archives")
        self.run("%s rcs %s %s" % (shlex.quote(self._ar),
                                   shlex.quote(os.path.join(lib_dst, "libtracecmd.a")),
                                   " ".join(shlex.quote(name) for name in objects)),
                 cwd=work, env="conanbuild")
        self.output.info("merged static library: %d objects" % len(objects))

    @staticmethod
    def _copy_shared(built_dir, lib_dst):
        """libtracecmd.so.1.5.5 是真文件，.so/.so.1.5 是上游 ln -sf 出来的符号链接；
        这个 conan 版本的 copy() 没有 symlinks 参数，逐个搬运以免把同一份内容拷三遍。
        """
        os.makedirs(lib_dst, exist_ok=True)
        for name in sorted(os.listdir(built_dir)):
            if not name.startswith("libtracecmd.so"):
                continue
            src = os.path.join(built_dir, name)
            dst = os.path.join(lib_dst, name)
            if os.path.islink(src):
                os.symlink(os.readlink(src), dst)
            elif os.path.isfile(src):
                shutil.copy(src, dst)

    def package(self):
        lib_dst = os.path.join(self.package_folder, "lib")
        inc_dst = os.path.join(self.package_folder, "include")
        built = os.path.join(self._root, "lib", "trace-cmd")

        self._copy_shared(built, lib_dst)
        self._merge_static(built, lib_dst)
        copy(self, "trace-cmd.h", src=os.path.join(self._root, "include", "trace-cmd"),
             dst=os.path.join(inc_dst, "trace-cmd"))
        # trace-cmd.h 里写的是 #include "event-parse.h" / "tracefs.h"，被静态链入的
        # 两个构建期输入的公共头必须随包交付，否则消费者连头文件都读不进去。
        # 只搬 public_headers 里点名的头（libtracefs 的 include/ 下还有
        # tracefs-local.h，那是上游内部头，不该进交付面）。
        for name in _BUNDLED:
            spec = self.conan_data["bundled_sources"][name]
            for header in spec["public_headers"]:
                copy(self, header, src=os.path.join(self._bundled_root(name),
                                                    spec["header_dir"]), dst=inc_dst)
                if not os.path.isfile(os.path.join(inc_dst, header)):
                    raise Exception("public header missing in package: %s" % header)

        copy(self, "COPYING.LIB", src=self._root, dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "LGPL-2.1", src=os.path.join(self._root, "LICENSES"),
             dst=os.path.join(self.package_folder, "licenses"))
        self._write_pkgconfig(os.path.join(lib_dst, "pkgconfig", "libtracecmd.pc"))

    def _write_pkgconfig(self, path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        text = "\n".join([
            "prefix=${pcfiledir}/../..",
            "libdir=${prefix}/lib",
            "includedir=${prefix}/include",
            "",
            "Name: libtracecmd",
            "Description: Library for reading and writing trace-cmd.dat files",
            "URL: %s" % self.homepage,
            "Version: %s" % self.version,
            # libtraceevent/libtracefs 静态链进了本库（制品仓未发布，见 conandata.yml），
            # 所以这里不能写 Requires——那两个 .pc 在任何一个安装环境里都不存在。
            # tracefs.h / trace-cmd.h 的原型里用了 cpu_set_t，OHOS 与 glibc 都把它
            # 关在 __USE_GNU 后面，头文件消费者必须自己开 _GNU_SOURCE。
            "Cflags: -D_GNU_SOURCE -I${includedir}",
            "Libs: -L${libdir} -ltracecmd",
            "",
        ])
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(text)

    def package_info(self):
        self.cpp_info.set_property("pkg_config_name", "libtracecmd")
        self.cpp_info.libs = ["tracecmd"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.bindirs = []
        self.cpp_info.system_libs = ["pthread"]
        # 同上：tracefs.h/trace-cmd.h 里的 cpu_set_t 只在 _GNU_SOURCE 下可见。
        self.cpp_info.defines = ["_GNU_SOURCE"]
