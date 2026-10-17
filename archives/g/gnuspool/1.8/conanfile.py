import os
import shutil
import stat

from conan import ConanFile
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches

required_conan_version = ">=2.0"


class GnuspoolConan(ConanFile):
    name = "gnuspool"
    version = "1.8"
    description = ("GNUspool - a comprehensive spooling system for UNIX, "
                   "with transparently shared jobs and printers across the network")
    license = "GPL-2.0-or-later"
    homepage = "https://www.gnu.org/software/gnuspool/"
    url = "https://ftp.gnu.org/gnu/gnuspool/gnuspool-1.8.tar.gz"
    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # full-screen tools (spq/pmenu) link curses; ncurses/6.6 is the
        # published registry package (same pin as dominion 2.8.2)
        self.requires("ncurses/6.6")

    def layout(self):
        from conan.tools.layout import basic_layout
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        VirtualBuildEnv(self).generate()

    def _compilers(self):
        # R33: compilers from the toolchain conf, never from bare PATH
        exe = self.conf.get("tools.build:compiler_executables", default={}) or {}
        cc = exe.get("c") or exe.get("cpp") or "clang"
        cxx = exe.get("cpp") or exe.get("c") or "clang++"
        return cc, cxx

    @staticmethod
    def _drop_umask_077(configure_path):
        # E011/E114: HMDFS rejects the umask 077 temp-dir dance in configure
        with open(configure_path, "r", errors="ignore") as f:
            lines = f.readlines()
        out = [l for l in lines if "umask 077" not in l and "umask(077)" not in l]
        if len(out) != len(lines):
            with open(configure_path, "w") as f:
                f.writelines(out)

    @staticmethod
    def _patch_shm_probe(configure_path):
        # OHOS has no working SysV shm/msgq: replace the fatal AC_TRY_RUN
        # error branches with conservative fallbacks (mmap+flock enabled)
        with open(configure_path, "r", errors="ignore") as f:
            lines = f.readlines()
        hit = 0
        for i, l in enumerate(lines):
            if "No joy - maybe no shm?" in l:
                lines[i] = "  ac_shmsize=1048576\n"
                hit += 1
            elif "Trouble with message queues" in l:
                lines[i] = "  ac_msgqsize=40\n"
                hit += 1
        if hit:
            with open(configure_path, "w") as f:
                f.writelines(lines)
        return hit

    # 上游 Makefile.in 直接调用裸 `libtool`（2008 年的宿主假设：PATH 里有 libtool），
    # 而 OHOS CI worker 的 PATH 没有 → make 在 build/lib 第一步即 Error 127。且上游
    # 链接行引用 libtool 专有产物（$(OBJECTS:.o=.lo)、.libs/libgnuspool_int.a），而
    # make 内建 .c.o 规则只产出 .o，本身不自洽。configure 前统一改写：共享库用
    # $(CC) -fPIC -shared 直接构建（-Wl,-soname/-Wl,-rpath 补回 libtool 原本提供的
    # soname 与 rpath），install 目标去掉 libtool --mode=install 前缀。
    # 构建系统级修复归配方（与 configure 的 umask/shm 处理同类）——refresh-patch
    # 的源码补丁集不覆盖 Makefile.in。
    _LIBTOOL_FILES = (
        "src/lib/Makefile.in", "src/apilib/Makefile.in", "src/Makefile.in",
        "src/loccgi/Makefile.in", "src/lpdint/Makefile.in", "src/remcgi/Makefile.in",
        "src/gtk/Makefile.in", "src/motif/Makefile.in",
        "src/ins/Makefile.in", "src/termserv/Makefile.in",
    )
    _LIBTOOL_REQUIRED = {
        "src/lib/Makefile.in": (
            "libtool --mode=compile @CC@", "libgnuspool_int.la",
            "libgnuspool_curs.la", "$(OBJECTS:.o=.lo)", "$(CURSOBJS:.o=.lo)",
            "$(CCFLAGS) -I$(HDRS) -I$(BASE)",
            "\tlibtool --mode=link @CC@ $(CCFLAGS) -o $(LIB) $(LIBOBJECTS)"
            " -rpath $(RPATH) -version-info 0:0:0",
            "\tlibtool --mode=link @CC@ $(CCFLAGS) -o $(LIBCURS) $(LIBCURSOBJS)"
            " $(LIB) $(LIBCURSES) -rpath $(RPATH) -version-info 0:0:0",
        ),
        "src/apilib/Makefile.in": (
            "libtool --mode=compile @CC@", "libgnuspool.la", "$(OBJECTS:.o=.lo)",
            "$(CCFLAGS) -I$(HDRS)",
            "\tlibtool --mode=link @CC@ $(CCFLAGS) -o $(APILIB) $(LIBOBJECTS)"
            " -rpath $(RPATH) -version-info 0:0:0",
        ),
        "src/Makefile.in": ("lib/libgnuspool_int.la", "lib/libgnuspool_curs.la",
                            "SHLIBCC\t\t=\tlibtool --mode=link $(CC) $(CCFLAGS)"),
        "src/ins/Makefile.in": ("LIB\t\t=\t$(MYLIBDIR)/.libs/libgnuspool_int.a",),
        "src/termserv/Makefile.in": ("LIB\t\t=\t$(MYLIBDIR)/.libs/libgnuspool_int.a",),
        "src/gtk/Makefile.in": ("libgnuspool_int.la",
                                "LIB\t\t=\t$(MYLIBDIR)/.libs/libgnuspool_int.a",
                                "SHLIBCC\t\t=\tlibtool --mode=link $(CC) $(CCFLAGS)"),
        "src/motif/Makefile.in": ("libgnuspool_int.la",
                                  "SHLIBCC\t\t=\tlibtool --mode=link $(CC) $(CCFLAGS)"),
        "src/loccgi/Makefile.in": ("libgnuspool_int.la",
                                   "SHLIBCC\t\t=\tlibtool --mode=link $(CC) $(CCFLAGS)"),
        "src/lpdint/Makefile.in": ("libgnuspool_int.la",
                                   "SHLIBCC\t\t=\tlibtool --mode=link $(CC) $(CCFLAGS)"),
        "src/remcgi/Makefile.in": ("libgnuspool.la",
                                   "LIB\t\t=\t$(MYLIBDIR)/.libs/libgnuspool_int.a",
                                   "APISHLIB\t=\t$(APILIBDIR)/libgnuspool.la",
                                   "SHLIBCC\t\t=\tlibtool --mode=link $(CC) $(CCFLAGS)"),
    }
    _LIBTOOL_SUBS = (
        ("libtool --mode=compile @CC@", "@CC@"),
        ("libgnuspool_int.la", "libgnuspool_int.so"),
        ("libgnuspool_curs.la", "libgnuspool_curs.so"),
        ("libgnuspool.la", "libgnuspool.so"),
        ("$(OBJECTS:.o=.lo)", "$(OBJECTS)"),
        ("$(CURSOBJS:.o=.lo)", "$(CURSOBJS)"),
        ("libtool --mode=install ", ""),
        ("$(CCFLAGS) -I$(HDRS) -I$(BASE)", "$(CCFLAGS) -fPIC -I$(HDRS) -I$(BASE)"),
        ("$(CCFLAGS) -I$(HDRS)", "$(CCFLAGS) -fPIC -I$(HDRS)"),
        ("\tlibtool --mode=link @CC@ $(CCFLAGS) -o $(LIB) $(LIBOBJECTS)"
         " -rpath $(RPATH) -version-info 0:0:0",
         "\t$(CC) $(CFLAGS) -shared -Wl,-soname,$(LIB) -Wl,-rpath,$(RPATH)"
         " -o $(LIB) $(LIBOBJECTS)"),
        ("\tlibtool --mode=link @CC@ $(CCFLAGS) -o $(LIBCURS) $(LIBCURSOBJS)"
         " $(LIB) $(LIBCURSES) -rpath $(RPATH) -version-info 0:0:0",
         "\t$(CC) $(CFLAGS) -shared -Wl,-soname,$(LIBCURS) -Wl,-rpath,$(RPATH)"
         " -o $(LIBCURS) $(LIBCURSOBJS) ./$(LIB) $(LIBCURSES)"),
        ("\tlibtool --mode=link @CC@ $(CCFLAGS) -o $(APILIB) $(LIBOBJECTS)"
         " -rpath $(RPATH) -version-info 0:0:0",
         "\t$(CC) $(CFLAGS) -shared -Wl,-soname,$(APILIB) -Wl,-rpath,$(RPATH)"
         " -o $(APILIB) $(LIBOBJECTS)"),
        ("SHLIBCC\t\t=\tlibtool --mode=link $(CC) $(CCFLAGS)",
         "SHLIBCC\t\t=\t$(CC) $(CCFLAGS) -Wl,-rpath,@libdir@"),
        ("LIB\t\t=\t$(MYLIBDIR)/.libs/libgnuspool_int.a",
         "LIB\t\t=\t$(MYLIBDIR)/libgnuspool_int.so -Wl,-rpath,@libdir@"),
        ("APISHLIB\t=\t$(APILIBDIR)/libgnuspool.la",
         "APISHLIB\t=\t$(APILIBDIR)/libgnuspool.so -Wl,-rpath,@libdir@"),
    )

    @classmethod
    def _rewrite_makefiles(cls, work):
        changed = 0
        for rel in cls._LIBTOOL_FILES:
            path = os.path.join(work, rel)
            if not os.path.isfile(path):
                raise Exception("expected upstream file missing: " + rel)
            with open(path, encoding="utf-8", errors="ignore") as f:
                text = f.read()
            for marker in cls._LIBTOOL_REQUIRED[rel]:
                if marker not in text:
                    raise Exception("upstream Makefile.in changed, marker not "
                                    "found in %s: %r" % (rel, marker))
            for old, new in cls._LIBTOOL_SUBS:
                text = text.replace(old, new)
            if "libtool" in text:
                raise Exception("residual libtool reference in " + rel)
            with open(path, "w", encoding="utf-8", newline="\n") as f:
                f.write(text)
            changed += 1
        return changed

    def build(self):
        apply_conandata_patches(self)
        # HMDFS permission flakiness kills config.status in deep conan cache
        # folders; run the in-source build from a shallow scratch copy.
        work = os.path.join(os.path.expanduser("~"), "tmp", "uc2",
                            "gnuspool-build-{}".format(self.version))
        if os.path.exists(work):
            shutil.rmtree(work)
        shutil.copytree(self.source_folder, work,
                        ignore=shutil.ignore_patterns(".git"))
        configure = os.path.join(work, "configure")
        # E011/E114: HMDFS rejects the umask 077 temp-dir dance in configure
        # (config.status then cannot write conf*/subs1.awk)
        with open(configure, "r", errors="ignore") as f:
            script = f.read()
        if "(umask 077 && " in script:
            script = script.replace("(umask 077 && ", "(")
            with open(configure, "w") as f:
                f.write(script)
        patched = self._patch_shm_probe(configure)
        # shipped lexer sources reference yywrap but link without libfl on
        # OHOS ($(LEXLIB) empty): append the standard no-op definition
        for root, _dirs, files in os.walk(work):
            for name in files:
                if not name.endswith(".c"):
                    continue
                p = os.path.join(root, name)
                with open(p, "r", errors="ignore") as f:
                    content = f.read()
                if "yywrap" not in content:
                    continue
                if "yywrap(void) { return 1; }" in content:
                    continue
                with open(p, "a") as f:
                    f.write("\nint yywrap(void) { return 1; }\n")
        self.output.info("shm probe fallback patched lines: %d" % patched)
        self.output.info("Makefile.in rewritten (host libtool removed): %d files"
                         % self._rewrite_makefiles(work))
        cc, cxx = self._compilers()
        # expose the conan ncurses package to configure's -lcurses probe:
        # the package ships libncurses.a only, so alias it as libcurses.a
        # in a scratch libdir next to the patched configure
        nc = self.dependencies["ncurses"]
        nc_inc = str(nc.cpp_info.includedirs[0])
        if not os.path.isabs(nc_inc):
            nc_inc = os.path.join(str(nc.package_folder or ""), nc_inc)
        nc_libdir = str(nc.cpp_info.libdirs[0])
        if not os.path.isabs(nc_libdir):
            nc_libdir = os.path.join(str(nc.package_folder or ""), nc_libdir)
        alias_lib = os.path.join(work, "scratch-lib", "libcurses.a")
        os.makedirs(os.path.dirname(alias_lib), exist_ok=True)
        src_lib = None
        for cand in ("libncurses.a", "libncursesw.a"):
            p = os.path.join(nc_libdir, cand)
            if os.path.isfile(p):
                src_lib = p
                break
        if not src_lib:
            raise Exception("no static ncurses library in " + nc_libdir)
        shutil.copy2(src_lib, alias_lib)
        # gnuspool 的 Makefile 把 include 目录拼进 CCFLAGS（不认 CPPFLAGS），
        # 且 musl 下 l64a/a64l 需要 _GNU_SOURCE 才可见
        # -DHAVE_TERMIO_H：musl 无 <termio.h>，但源码用 HAVE_TERMIO_H 选择
        # termios 代码路径（否则落到 sgttyb/TIOCGETP 的 BSD 老 API，musl 没有）；
        # termio.h 的包含已被 patches/0004 重定向到 termios.h
        # src/lib 等子目录 Makefile 的链接规则只用 CCFLAGS（无 LDFLAGS），
        # 故 -L 路径也必须进 CCFLAGS
        ccflags = ('-O -g -Wall -fno-stack-protector -D_GNU_SOURCE -DHAVE_TERMIO_H '
                   '-DSIGCLD=SIGCHLD -fcommon '
                   '-I{inc} -L{scratchlib} -L{lib}').format(
            inc=nc_inc, scratchlib=os.path.dirname(alias_lib), lib=nc_libdir)
        configure_cmd = ('cd "{work}" && CC="{cc}" CXX="{cxx}" '
                         'CCFLAGS="{ccflags}" '
                         'CPPFLAGS="-I{inc}" LDFLAGS="-L{scratchlib} -L{lib}" '
                         'LIBS="-lcurses" '
                         'sh configure '
                         '--build=aarch64-unknown-linux-gnu '
                         '--enable-using-mmap --enable-using-flock '
                         '--without-network '
                         '--prefix="{prefix}"').format(
            work=work, cc=cc, cxx=cxx, inc=nc_inc, ccflags=ccflags,
            scratchlib=os.path.dirname(alias_lib), lib=nc_libdir,
            prefix=self.package_folder)
        self.run(configure_cmd)
        self.run(('cd "{work}" && make -j1 CCFLAGS="{ccflags}" '
                  'LDFLAGS="-L{scratchlib} -L{lib}"').format(
            work=work, inc=nc_inc, ccflags=ccflags,
            scratchlib=os.path.dirname(alias_lib), lib=nc_libdir))
        # stage produced executables for package()
        staged = os.path.join(self.build_folder, "staged-bin")
        staged_lib = os.path.join(self.build_folder, "staged-lib")
        for d in (staged, staged_lib):
            if os.path.exists(d):
                shutil.rmtree(d)
            os.makedirs(d)
        count = 0
        for root, _dirs, files in os.walk(os.path.join(work, "build")):
            for name in files:
                p = os.path.join(root, name)
                try:
                    mode = os.stat(p).st_mode
                except OSError:
                    continue
                if not stat.S_ISREG(mode) or not (mode & stat.S_IXUSR):
                    continue
                with open(p, "rb") as fh:
                    if fh.read(4) != b"\x7fELF":
                        continue
                # 共享库归入 lib/：可执行文件的 RUNPATH 指向 <prefix>/lib
                dest = staged_lib if ".so" in name else staged
                shutil.copy2(p, os.path.join(dest, name))
                count += 1
        self.output.info("staged %d binaries from build/" % count)

    def package(self):
        from conan.tools.files import copy
        copy(self, "*", src=os.path.join(self.build_folder, "staged-bin"),
             dst=os.path.join(self.package_folder, "bin"))
        copy(self, "*", src=os.path.join(self.build_folder, "staged-lib"),
             dst=os.path.join(self.package_folder, "lib"))
        # 工具运行期需要 help/message 数据（否则报 "Cannot find help message file"）
        copy(self, "*.help", src=os.path.join(self.source_folder, "src", "helpmsg"),
             dst=os.path.join(self.package_folder, "share", "gnuspool", "help"))

    def package_info(self):
        self.cpp_info.includedirs = []
        # 共享库在 lib/，libdirs 需声明，conanrun 才会把该目录加入 LD_LIBRARY_PATH
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.bindirs = ["bin"]
