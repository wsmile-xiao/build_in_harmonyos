import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, load, save
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


# harmonyos-pwd.c: getpwnam/getpwuid/getgrnam/getgrgid stubs for HarmonyOS
# Created in build() via save() — not a patch (refresh-patch can't handle new file format)
_HARMONYOS_PWD_C = r"""
#include <pwd.h>
#include <grp.h>
#include <string.h>
#include <unistd.h>

static struct passwd g_pw;
static struct group  g_gr;
static int g_inited = 0;

static void init_pw(void)
{
    if (g_inited) return;
    g_pw.pw_name   = "currentUser";
    g_pw.pw_passwd = "*";
    g_pw.pw_uid    = getuid();
    g_pw.pw_gid    = getgid();
    g_pw.pw_gecos  = "HarmonyOS User";
    g_pw.pw_dir    = "/storage/Users/currentUser";
    g_pw.pw_shell  = "/usr/bin/zsh";

    g_gr.gr_name   = "currentUser";
    g_gr.gr_passwd = "*";
    g_gr.gr_gid    = getgid();
    g_gr.gr_mem    = NULL;

    g_inited = 1;
}

struct passwd *
__wrap_getpwnam(const char *name)
{
    (void)name;
    init_pw();
    return &g_pw;
}

struct passwd *
__wrap_getpwuid(uid_t uid)
{
    (void)uid;
    init_pw();
    return &g_pw;
}

struct group *
__wrap_getgrnam(const char *name)
{
    (void)name;
    init_pw();
    return &g_gr;
}

struct group *
__wrap_getgrgid(gid_t gid)
{
    (void)gid;
    init_pw();
    return &g_gr;
}
"""


class OpensshConan(ConanFile):
    name = "openssh"
    version = "10.0p1"
    description = "OpenBSD Secure Shell suite (ssh, sshd, scp, sftp, ssh-keygen)"
    license = "SSH-OpenSSH"
    homepage = "https://www.openssh.com/"
    url = ""

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("openssl/3.5.6")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _fix_shebangs(self):
        src = self.source_folder
        for fname in ["configure", "install-sh", "mkinstalldirs"]:
            fpath = os.path.join(src, fname)
            if not os.path.isfile(fpath):
                continue
            content = load(self, fpath)
            content = content.replace("#!/bin/sh", "#! /system/bin/sh")
            content = content.replace("#! /bin/sh", "#! /system/bin/sh")
            content = content.replace("#!/bin/bash", "#! /data/service/hnp/bin/bash")
            content = content.replace("#! /bin/bash", "#! /data/service/hnp/bin/bash")
            save(self, fpath, content)

    def _fix_umask(self):
        src = self.source_folder
        fpath = os.path.join(src, "configure")
        if os.path.isfile(fpath):
            content = load(self, fpath)
            content = content.replace("umask 077", "umask 022")
            save(self, fpath, content)

    def _create_and_compile_harmonyos_pwd(self):
        """Create harmonyos-pwd.c stub and compile to harmonyos-pwd.o."""
        src = self.source_folder
        pwd_c = os.path.join(src, "harmonyos-pwd.c")
        pwd_o = os.path.join(src, "harmonyos-pwd.o")
        save(self, pwd_c, _HARMONYOS_PWD_C)
        self.run(f'$CC -c "{pwd_c}" -o "{pwd_o}"', env="conanbuild")

    def _inject_pwd_obj_to_makefile(self):
        """Append harmonyos-pwd.o to LDFLAGS via GNU Make += operator."""
        pwd_o_abs = os.path.join(self.source_folder, "harmonyos-pwd.o")
        candidates = [
            os.path.join(self.source_folder, "Makefile"),
            os.path.join(self.build_folder, "Makefile") if hasattr(self, "build_folder") else None,
            os.path.join(os.getcwd(), "Makefile"),
        ]
        for makefile in candidates:
            if makefile is None or not os.path.isfile(makefile):
                continue
            content = load(self, makefile)
            append_line = f"\n# Injected by conanfile.py for HarmonyOS pwd stub\nLDFLAGS += {pwd_o_abs}\n"
            save(self, makefile, content + append_line)
            self.output.info(f"Appended LDFLAGS += harmonyos-pwd.o to {makefile}")
            return
        self.output.warning("Could not inject harmonyos-pwd.o into any Makefile")

    def generate(self):
        tc = AutotoolsToolchain(self)
        if self.settings.os in ("Linux", "OHOS"):
            openssl_dir = self.dependencies["openssl"].package_folder
            prefix = "/usr/local"
            tc.configure_args.extend([
                f"--prefix={prefix}",
                f"--libexecdir={prefix}/lib",
                f"--sysconfdir={prefix}/etc",
                f"--with-ssl-dir={openssl_dir}",
                "--without-pam",
                "--without-shadow",
                "--without-sandbox",
                "--without-privsep-user",
                "--without-privsep-path",
                "--disable-privsep",
                "--disable-lastlog",
                "--disable-utmp",
                "--disable-utmpx",
                "--disable-wtmp",
                "--disable-wtmpx",
                "--disable-libutil",
                "--without-md5-passwords",
            ])
        if self.settings.os == "OHOS":
            tc.extra_cflags.extend([
                "-DENABLE_OPENSSH_HOME=1",
                "-DSKIP_STRICT_PERMISSIONS=1",
                "-DOHOS_NET_IF_FIX=1",
            ])
            tc.extra_ldflags.extend([
                "-Wl,--wrap=getpwnam",
                "-Wl,--wrap=getpwuid",
                "-Wl,--wrap=getgrnam",
                "-Wl,--wrap=getgrgid",
            ])
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        if self.settings.os == "OHOS":
            self._fix_shebangs()
            self._fix_umask()
        self._create_and_compile_harmonyos_pwd()
        autotools = Autotools(self)
        autotools.configure()
        self._inject_pwd_obj_to_makefile()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install(args=[f"DESTDIR={self.package_folder}"])

    def package_info(self):
        prefix_rel = "usr/local"
        self.cpp_info.bindirs = [
            os.path.join(prefix_rel, "bin"),
            os.path.join(prefix_rel, "sbin"),
            os.path.join(prefix_rel, "libexec"),
        ]
        self.cpp_info.libs = []
