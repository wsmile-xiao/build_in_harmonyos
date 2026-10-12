import os
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, chdir, copy, export_conandata_patches, get
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout


class RtpengineConan(ConanFile):
    """NGCP RTP engine（sipwise/rtpengine）— 裸 GNU Make + pkg-config 16 硬依赖包。

    OHOS 适配要点（详见同目录 notes.md）：
    - wrapper .pc ×4：gen-common-flags 探测系统标准名（libcrypto/libpcre2-8/libmariadb/libjwt），
      generate() 将 PkgConfigDeps 产物改名为探测名
    - 关 LTO（make 变量 CFLAGS_DEFAULT=/LDFLAGS_DEFAULT=）：回退 LTO 使链接自动追加 -latomic，
      OHOS 工具链无 libatomic
    - -j1：FIFO 系统级不可用（mkfifo EPERM），make jobserver 不可用
    - without_nftables=yes：OHOS 无 libiptc/内核 netfilter
    - pthread 取消 API weak stub（lib/ohos_pthread_stubs.c，patch 0016）
    """

    name = "rtpengine"
    version = "26.0.1.15"
    description = "NGCP RTP engine: SIP 媒体代理/中继/转码/DTMF/录音（daemon + 控制 CLI）"
    license = "GPL-2.0-only"
    url = "https://github.com/sipwise/rtpengine"
    homepage = "https://github.com/sipwise/rtpengine"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"
    exports_sources = "patches/*"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"rtpengine does not support os={self.settings.os}")

    def requirements(self):
        # 16 硬依赖 — glib 2.84 世代对齐集（registry 原生一致，详见 notes.md）
        self.requires("glib/2.84.0.1")
        self.requires("json-glib/1.10.6.1")
        self.requires("libcurl/8.5.0")
        # override：libjwt2 硬 pin openssl/3.5.6.1，全图（ffmpeg/libcurl 等）按 3.5.6 构建
        self.requires("openssl/3.5.6", override=True)
        self.requires("libevent/2.1.13")
        self.requires("pcre2/10.45")
        self.requires("libwebsockets/4.3.5.1")
        self.requires("zlib/1.3.1.1")
        self.requires("ncurses/6.6")
        self.requires("opus/1.5.2.1")
        # rtpengine oauth.c 用 maddevs/libjwt v2 经典 API（jwt_add_grant 系），
        # 非 libjwt/3.x builder/checker API
        self.requires("libjwt2/2.1.3")
        self.requires("hiredis/1.2.0")
        self.requires("libpcap/1.10.6")
        self.requires("ffmpeg/7.1.5")
        self.requires("spandsp/0.0.6")
        # gen-common-flags 无条件要求 libmariadb 或 mysqlclient（recording 库）
        self.requires("mariadb-connector-c/3.4.8")

    def tool_requirements(self):
        # 构建期 perl：utils/const_str_hash 生成 *.strhash.c（构建步骤）
        self.tool_requires("perl/5.42.2.3")

    def layout(self):
        basic_layout(self, src_folder="src")

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version])

    def _write_pc_wrappers(self):
        """rtpengine gen-common-flags 探测系统标准 pc 名（任一缺失即 exit 1）；
        conan 配方暴露 openssl/pcre2/mariadb-connector-c/libjwt2 名，
        将 PkgConfigDeps 生成的 .pc 复制为探测名（内容相同，仅 Name 字段改写）。
        """
        mapping = {
            "openssl.pc": "libcrypto.pc",
            "pcre2.pc": "libpcre2-8.pc",
            "mariadb-connector-c.pc": "libmariadb.pc",
            "libjwt2.pc": "libjwt.pc",
        }
        for src_name, dst_name in mapping.items():
            src_path = os.path.join(self.generators_folder, src_name)
            if not os.path.isfile(src_path):
                raise ConanException(f"缺少 {src_name}，无法生成 wrapper {dst_name}")
            with open(src_path, encoding="utf-8") as f:
                lines = [ln for ln in f.read().splitlines()
                         if not ln.startswith("Name:")]
            lines.insert(0, f"Name: {dst_name[:-3]}")
            with open(os.path.join(self.generators_folder, dst_name), "w",
                      encoding="utf-8") as f:
                f.write("\n".join(lines) + "\n")

    def generate(self):
        PkgConfigDeps(self).generate()
        self._write_pc_wrappers()
        # R49：TMPDIR 私有目录（OHOS /tmp 只读）；CC 取固定工具链路径（R33）
        tmpdir = os.path.join(self.build_folder, ".tmp")
        os.makedirs(tmpdir, exist_ok=True)
        env = Environment()
        env.define("TMPDIR", tmpdir)
        env.define("TMP", tmpdir)
        env.define("TEMP", tmpdir)
        env.define("CC", "/data/service/hnp/bin/clang")
        env.append_path("PKG_CONFIG_PATH", self.generators_folder)
        env.vars(self, scope="build").save_script("ohc_rtpengine_env")

    def build(self):
        apply_conandata_patches(self)
        # HMDFS：conan 源码缓存目录 noexec（生成脚本/conftest 不可执行）→
        # 在 build_folder 下 worktree 构建（conan 构建目录天然可执行，R49/E052）
        work = os.path.join(self.build_folder, "worktree")
        if os.path.exists(work):
            shutil.rmtree(work)
        shutil.copytree(self.source_folder, work,
                        ignore=shutil.ignore_patterns(".tmp"))
        with chdir(self, work):
            # -j1：FIFO 系统级不可用（mkfifo EPERM），make jobserver 不可用
            # CFLAGS_DEFAULT=/LDFLAGS_DEFAULT=：剥离 dpkg-buildflags 缺失回退的 LTO 值
            #   （LTO 链接自动追加 -latomic，OHOS 工具链无 libatomic）
            # without_nftables=yes：无 libiptc/内核 netfilter（配合 patch 0001 的
            #   netfilter_api.c 条件排除）
            self.run("make -j1 "
                     "CC=/data/service/hnp/bin/clang "
                     "without_nftables=yes "
                     "CFLAGS_DEFAULT= LDFLAGS_DEFAULT=",
                     env="conanbuild")

    def package(self):
        work = os.path.join(self.build_folder, "worktree")
        pkg_bin = os.path.join(self.package_folder, "bin")
        # 三个构建产物（in-tree 构建，位于 worktree 子目录）
        copy(self, "rtpengine", src=os.path.join(work, "daemon"), dst=pkg_bin)
        copy(self, "rtpengine-recording",
             src=os.path.join(work, "recording-daemon"), dst=pkg_bin)
        copy(self, "rtpengine-perftest",
             src=os.path.join(work, "perf-tester"), dst=pkg_bin)
        # 控制脚本（shebang 已 patch 为 #!/usr/bin/env perl）
        copy(self, "rtpengine-ctl", src=os.path.join(work, "utils"), dst=pkg_bin)
        copy(self, "rtpengine-ng-client",
             src=os.path.join(work, "utils"), dst=pkg_bin)
        copy(self, "rtpengine-get-table", src=os.path.join(work, "utils"),
             dst=os.path.join(self.package_folder, "libexec", "rtpengine"))
        copy(self, "rtpengine-ctl.1", src=os.path.join(work, "utils"),
             dst=os.path.join(self.package_folder, "share", "man", "man1"))
        copy(self, "rtpengine-ng-client.1", src=os.path.join(work, "utils"),
             dst=os.path.join(self.package_folder, "share", "man", "man1"))
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin", "libexec/rtpengine"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libs = []
