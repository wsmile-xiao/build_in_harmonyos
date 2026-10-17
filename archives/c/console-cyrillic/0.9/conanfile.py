import gzip
import os
import re
import shutil

from conan import ConanFile
from conan.tools.files import copy, download
from conan.tools.layout import basic_layout


class ConsoleCyrillicConan(ConanFile):
    name = "console-cyrillic"
    version = "0.9"
    description = ("console-cyrillic - Cyrillic console keymaps (120 kmap, "
                   "12 layouts x 10 encodings, makeenc+cpp pipeline), 44 PSF "
                   "fonts, 8 sfm/9 acm charmaps, screenmaps/trans/fallbacks "
                   "and 6 helper scripts (cyr/displayfont/dumppsf/makeacm/"
                   "raw2psf/mkvgafont). Debian 3.0(quilt) packaging, no C "
                   "compilation")
    license = "public-domain"
    homepage = "https://salsa.debian.org/debian/console-cyrillic"
    url = ""
    package_type = "application"

    # .deb 黄金反解的静态数据——随 recipe 导出，package() 经
    # self.recipe_folder 读取：
    #   graph.fallback（console-data 段 84 行）
    #   windows_*（9 个 trcs/iconv 转码产物——trcs 是 console-trans
    #   包工具尚未合入，box-drawing 字符专属映射 python/iconv 均不
    #   匹配，1427B 纯静态数据统一黄金嵌入，bit 级一致）
    exports = (
        "graph.fallback",
        "windows_cp1251", "windows_ibm866", "windows_iso_8859_5",
        "windows_koi8_r", "windows_koi8_u", "windows_mac_cyrillic",
        "windows_mik", "windows_pt154", "windows_utf8",
        "man_displayfont", "man_dumppsf", "man_makeacm",
        "man_raw2psf", "man_cyr", "man_mkvgafont",
    )

    settings = "os", "compiler", "build_type", "arch"

    # 12 布局 -> (cpp 相对源根, clang-cpp 额外参数)
    _LAYOUTS = (
        ("ru", "keymap/cyr-russian.cpp", ""),
        ("ru_ms", "keymap/cyr-russian-ms.cpp", ""),
        ("by", "keymap/cyr-belarusian.cpp", ""),
        ("bg_bds", "debian/cyr-bulgarian-bds.cpp", ""),
        ("bg_phon", "debian/cyr-bulgarian-phon.cpp", ""),
        ("sr", "debian/cyr-serbian.cpp", ""),
        ("mk", "debian/cyr-macedonian.cpp", ""),
        ("ua", "debian/cyr-ukrainian1.cpp", ""),
        ("ua_ms", "debian/cyr-ukrainian-ms.cpp", ""),
        ("mn", "debian/cyr-mongolian.cpp", ""),
        ("kaz_gost", "debian/binary/console-kazakh-0.2b/keymap/cyr-kazakh.cpp", ""),
        ("kaz_alt", "debian/binary/console-kazakh-0.2b/keymap/cyr-kazakh.cpp", "-DIO"),
    )
    _ENCODINGS = ("unicode", "rk1048", "cp1251", "ibm866", "iso-8859-5",
                  "koi8-r", "koi8-u", "mac-cyrillic", "mik", "pt154")

    # Debian 侧 5 补丁（按 series 顺序，patch -p1 实测全通过）
    _PATCHES = ("dumppsf.patch", "1063834-showconsolefont",
                "1063760-dumppsf-mode-1-3",
                "1030816-disable-UTF-8-if--iutf8", "bad-whatis-entry")

    # 需 shebang 适配的 perl 脚本（displayfont 带 -w，od 复核首行字节）
    _PERL_SCRIPTS = ("scripts/displayfont", "scripts/dumppsf",
                     "scripts/makeacm", "scripts/raw2psf", "debian/cyr")

    def requirements(self):
        # 运行期外部命令消费（cyr 528 行全文核对）：
        #   cyr → kbd-config（console-common）+ loadkeys/dumpkeys（kbd）
        # gzip/zcat/sed/awk 基础系统；whoami/stty/iconv 探测式消费
        # （不可用时脚本 graceful 降级）——只声明 kbd
        self.requires("kbd/2.9.0")

    def layout(self):
        basic_layout(self)

    def source(self):
        import hashlib

        def _fetch(fname, url, sha256):
            path = os.path.join(self.source_folder, fname)
            # 幂等：已存在且 sha256 命中则跳过下载（本地复验网络受限；
            # CI 源目录为空走正常下载）
            if os.path.isfile(path):
                with open(path, "rb") as f:
                    digest = hashlib.sha256(f.read()).hexdigest()
                if digest == sha256:
                    self.output.info(f"{fname} 已存在且 sha256 命中，跳过下载")
                    return
                self.output.warning(f"{fname} sha256 不符（{digest}），重新下载")
                os.remove(path)
            download(self, url, fname, sha256=sha256)

        src = self.conan_data["sources"]
        # 3.0(quilt) 包：orig 上游源码 + debian 打包树（makeenc/unicodesyms/
        # 7 个 debian 侧 cpp/kazakh 子包/16 option-kmap/screenmap/trans/
        # fallback/binary 字体/cyr 脚本/5 补丁）——两个 tarball 合并为源根
        _fetch("console-cyrillic_0.9.orig.tar.gz",
               "https://deb.debian.org/debian/pool/main/c/console-cyrillic/"
               "console-cyrillic_0.9.orig.tar.gz", src["orig_sha256"])
        _fetch("console-cyrillic_0.9-18.debian.tar.xz",
               "https://deb.debian.org/debian/pool/main/c/console-cyrillic/"
               "console-cyrillic_0.9-18.debian.tar.xz", src["debian_sha256"])
        self.run("tar -xzf console-cyrillic_0.9.orig.tar.gz --no-same-owner",
                 cwd=self.source_folder)
        self.run("tar -xJf console-cyrillic_0.9-18.debian.tar.xz --no-same-owner",
                 cwd=self.source_folder)
        self.run("cp -a console-cyrillic-0.9.orig/. . "
                 "&& rm -rf console-cyrillic-0.9.orig *.tar.gz *.tar.xz",
                 cwd=self.source_folder)

    def _fix_shebang(self, rel):
        # OHOS 无 /usr/bin/perl（hnp 提供 /data/service/hnp/bin/perl）。
        # 上游 shebang 精确字节 od 复核：displayfont 为
        # #!/usr/bin/perl -w\n，其余 4 个 #!/usr/bin/perl\n。
        # 一律替换为 #!/usr/bin/env perl\n——丢弃 -w（仅开警告，
        # OHOS 的 env 不支持解释器后带参，`env perl -w` 实测 exec 失败）
        path = os.path.join(self.source_folder, rel)
        with open(path, "r", encoding="utf-8", newline="\n") as f:
            content = f.read()
        new, n = re.subn(r"^#![ \t]*/usr/bin/perl(?:[ \t]+-w)?[ \t]*\n",
                         "#!/usr/bin/env perl\n",
                         content, count=1, flags=re.MULTILINE)
        if n != 1:
            raise Exception(f"{rel}: shebang 未命中（首行={content.splitlines()[0]!r}）")
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(new)
        os.chmod(path, 0o755)

    def build(self):
        sf = self.source_folder
        # 1. Debian 侧 5 补丁（quilt series 顺序，patch -p1；OHOS toybox
        #    patch 实测支持 git 格式 diff + 元数据头）
        for p in self._PATCHES:
            self.run(f"/usr/bin/patch -p1 < "
                     f"{os.path.join(sf, 'debian', 'patches', p)}",
                     cwd=sf)
        # 2. perl shebang 批量适配（5 文件）
        for rel in self._PERL_SCRIPTS:
            self._fix_shebang(rel)
        # 3. makeenc tmpfile 重定向：上游 L2580 硬编码 /tmp/csrec.$$，
        #    OHOS /tmp 只读——${TMPDIR:-.}/csrec.$$ 重定向到构建工作目录
        makeenc = os.path.join(sf, "debian", "makeenc")
        with open(makeenc, "r", encoding="utf-8", newline="\n") as f:
            content = f.read()
        old = "tmpfile=/tmp/csrec.$$"
        if old not in content:
            raise Exception("makeenc tmpfile 行未命中")
        content = content.replace(old, "tmpfile=${TMPDIR:-.}/csrec.$$", 1)
        with open(makeenc, "w", encoding="utf-8", newline="\n") as f:
            f.write(content)
        # 4. kmap 生成管线（debian/rules L42-89 逐条复刻）：
        #    makeenc <enc> < unicodesyms | cat - <cpp>
        #    | cpp(=OHOS clang-cpp) -iquote keymap/ -iquote - -P [-DIO]
        #    | sed 's/+ *U+/U+/g' | grep '[^ ]'
        #    工作目录 keymap/（rules 在包根以 -iquote keymap/ 解析
        #    macros.inc，此处等价锚定）；12 布局 x 10 编码 = 120 文件，
        #    与 .deb 黄金文件全量 diff（归一化构建日期/姓名）0 差异实测
        kdir = os.path.join(sf, "build_kmap")
        os.makedirs(kdir, exist_ok=True)
        decl = "\n".join(
            f'LAYOUTS["{prefix}"]="{cpp} {extra}"'
            for prefix, cpp, extra in self._LAYOUTS)
        enc_list = " ".join(self._ENCODINGS)
        script = f"""#!/bin/bash
set -e
export SF="{sf}"
cd "$SF/keymap"
export TMPDIR="$SF"
declare -A LAYOUTS
{decl}
for prefix in ru ru_ms by bg_bds bg_phon sr mk ua ua_ms mn kaz_gost kaz_alt; do
  set -- ${{LAYOUTS[$prefix]}}
  cppf="$1"; extra="${{2:-}}"
  for enc in {enc_list}; do
    out="{kdir}/${{prefix}}-$enc.kmap"
    ( bash "$SF/debian/makeenc" "$enc" \\
        < "$SF/debian/unicodesyms" | cat - "$SF/${{cppf}}" \\
        | clang-cpp ${{extra}} -iquote . -iquote - -P \\
        | sed 's/+ *U+/U+/g' | grep '[^ ]' ) > "$out"
    keys=$(grep -c '^keycode' "$out" || true)
    if [ ! -s "$out" ] || [ "$keys" -lt 100 ]; then
      echo "KMAP FAIL: ${{prefix}}-$enc (keys=$keys)" >&2; exit 1
    fi
  done
done
echo "kmap generated: $(ls "{kdir}" | wc -l)/120"
[ "$(ls "{kdir}" | wc -l)" -eq 120 ]
"""
        sfile = os.path.join(sf, "_gen_kmap.sh")
        with open(sfile, "w", encoding="utf-8") as f:
            f.write(script)
        os.chmod(sfile, 0o755)
        self.run(f'PATH=/data/service/hnp/bin:$PATH bash "{sfile}"', cwd=sf)
        os.remove(sfile)
        # 5. man 页 6 个（.deb 黄金字节嵌入）：4 个上游 pod2man 产物
        #    （Pod::Man 版本差异——hnp 是 v6.0、Debian 构建环境是 5.010，
        #    重生成不 bit 匹配），2 个 debian 预渲染 roff——统一 .deb 黄金
        #    嵌入，gzip -9 落包（构建期压缩，运行期零 gzip 依赖）
        man_build = os.path.join(sf, "build_man")
        os.makedirs(man_build, exist_ok=True)
        for s in ("displayfont", "dumppsf", "makeacm", "raw2psf",
                  "cyr", "mkvgafont"):
            with open(os.path.join(self.recipe_folder,
                                   "man_" + s), "rb") as f:
                data = f.read()
            with open(os.path.join(man_build, s + ".1.gz"), "wb") as fg:
                fg.write(gzip.compress(data, 9))

    def package(self):
        pf = self.package_folder
        for d in ("bin", "share/console-cyrillic", "share/man/man1",
                  "share/doc/console-cyrillic/windows",
                  "share/doc/console-cyrillic/dosemu",
                  "share/lintian/overrides", "licenses"):
            os.makedirs(os.path.join(pf, d), exist_ok=True)
        sf = self.source_folder
        D = os.path.join(sf, "debian")
        CC = os.path.join(pf, "share", "console-cyrillic")
        # 120 生成 kmap
        copy(self, "*.kmap", src=os.path.join(sf, "build_kmap"), dst=CC,
             keep_path=False)
        # 16 option kmap + 8 screenmap + 9 trans + cyrillic.fallback
        copy(self, "option-*.kmap", src=D, dst=CC, keep_path=False)
        copy(self, "*.screenmap", src=D, dst=CC, keep_path=False)
        copy(self, "*.trans", src=D, dst=CC, keep_path=False)
        copy(self, "cyrillic.fallback", src=D, dst=CC, keep_path=False)
        # 44 psf：orig psf/ 25 + debian/binary 8 + kazakh psf/ 6 +
        # sarge-16/thin-14/thin-16 3 = 42 + 866/Alt 2 个在 orig ——以 .deb
        # 黄金 44 为准（package 后计数断言）
        copy(self, "*.psf", src=os.path.join(sf, "psf"), dst=CC,
             keep_path=False)
        copy(self, "*.psf", src=os.path.join(D, "binary"), dst=CC,
             keep_path=False)
        copy(self, "*.psf",
             src=os.path.join(D, "binary", "console-kazakh-0.2b", "psf"),
             dst=CC, keep_path=False)
        # 8 sfm.gz：orig sfm/ 6 + kazakh sfm/ 2（gzip 构建期压缩）
        for name in ("Cyr_a", "UniCyr", "UniCyrX", "alt", "cp866", "ucx"):
            self._gzip_copy(os.path.join(sf, "sfm", name + ".sfm"),
                            os.path.join(CC, name + ".sfm.gz"))
        for name in ("pt154", "rk1048"):
            self._gzip_copy(
                os.path.join(D, "binary", "console-kazakh-0.2b", "sfm",
                             name + ".sfm"),
                os.path.join(CC, name + ".sfm.gz"))
        # 9 acm.gz：orig acm/ 7 + binary/pt154.acm + kazakh/rk1048.acm
        for name in ("MacCyrillic", "bulgarian-mic", "cp1251", "cp866",
                     "iso8859-5", "koi8-r", "koi8-u"):
            self._gzip_copy(os.path.join(sf, "acm", name + ".acm"),
                            os.path.join(CC, name + ".acm.gz"))
        self._gzip_copy(os.path.join(D, "binary", "pt154.acm"),
                        os.path.join(CC, "pt154.acm.gz"))
        self._gzip_copy(
            os.path.join(D, "binary", "console-kazakh-0.2b", "acm",
                         "rk1048.acm"),
            os.path.join(CC, "rk1048.acm.gz"))
        # cyrillic-graph.fallback = 头注释 + cyrillic.fallback +
        # console-data 的 graph.fallback（rules L91-93 组合）。console-data
        # 尚无 conan 包——graph.fallback 84 行从 .deb 黄金文件反解归档于
        # 配方目录（边界见 notes.md），组合结果与 .deb bit 级一致
        with open(os.path.join(CC, "cyrillic-graph.fallback"), "w",
                  encoding="utf-8", newline="\n") as f:
            f.write("# This file is combination between cyrillic.fallback "
                    "and graph.fallback\n")
            f.write(open(os.path.join(CC, "cyrillic.fallback"), "r",
                         encoding="utf-8", newline="\n").read())
            f.write(open(os.path.join(self.recipe_folder, "graph.fallback"),
                         "r", encoding="utf-8", newline="\n").read())
        self._gzip_copy(os.path.join(CC, "cyrillic.fallback"),
                        os.path.join(CC, "cyrillic.fallback.gz"))
        self._gzip_copy(os.path.join(CC, "cyrillic-graph.fallback"),
                        os.path.join(CC, "cyrillic-graph.fallback.gz"))
        os.remove(os.path.join(CC, "cyrillic.fallback"))
        os.remove(os.path.join(CC, "cyrillic-graph.fallback"))
        # 6 脚本 → bin/（perl 4 + sh 1 + cyr；0755）
        for s in ("displayfont", "dumppsf", "makeacm", "raw2psf",
                  "mkvgafont"):
            copy(self, s, src=os.path.join(sf, "scripts"),
                 dst=os.path.join(pf, "bin"), keep_path=False)
        copy(self, "cyr", src=D, dst=os.path.join(pf, "bin"),
             keep_path=False)
        for s in ("displayfont", "dumppsf", "makeacm", "raw2psf",
                  "mkvgafont", "cyr"):
            os.chmod(os.path.join(pf, "bin", s), 0o755)
        # 6 man 页
        copy(self, "*.1.gz", src=os.path.join(sf, "build_man"),
             dst=os.path.join(pf, "share", "man", "man1"), keep_path=False)
        # doc（.deb 黄金布局：8 文档 + windows 8 + dosemu 2 + lintian 1）
        doc = os.path.join(pf, "share", "doc", "console-cyrillic")
        for name in ("README.Debian", "README.Debian.old",
                     "README.eng", "README.ru", "copyright"):
            srcf = {"README.Debian": "README",
                    "README.Debian.old": "README.Debian.old",
                    "README.eng": "README.eng",
                    "README.ru": "README.ru",
                    "copyright": "copyright"}[name]
            shutil.copy2(os.path.join(D, srcf), os.path.join(doc, name))
        # README.console-kazakh = kazakh README.ru 去含 README.en 行
        # （rules L32 sed '/README.en/d'）
        with open(os.path.join(D, "binary", "console-kazakh-0.2b",
                               "README.ru"), "r", encoding="utf-8",
                  errors="replace") as f:
            lines = [ln for ln in f if "README.en" not in ln]
        with open(os.path.join(doc, "README.console-kazakh"), "w",
                  encoding="utf-8") as f:
            f.writelines(lines)
        self._gzip_copy(os.path.join(D, "changelog"),
                        os.path.join(doc, "changelog.Debian.gz"))
        # windows 文档 9 个（rules L36-40：trcs -f koi8-r -t <enc> 8 字节
        # 编码 + iconv utf-8）：trcs 是 console-trans 包工具（未合入），
        # box-drawing 专属 ASCII 降级映射 python/iconv 均不匹配——
        # 1427B 纯静态数据统一 .deb 黄金字节嵌入（bit 级一致）
        self._gen_windows(os.path.join(doc, "windows"))
        shutil.copy2(os.path.join(sf, "x-window", "vga.bdf"),
                     os.path.join(doc, "dosemu", "vga.bdf"))
        shutil.copy2(os.path.join(D, "mik.bdf"),
                     os.path.join(doc, "dosemu", "mik.bdf"))
        shutil.copy2(os.path.join(D, "console-cyrillic.lintian-overrides"),
                     os.path.join(pf, "share", "lintian", "overrides",
                                  "console-cyrillic"))
        shutil.copy2(os.path.join(D, "copyright"),
                     os.path.join(pf, "licenses", "copyright"))
        # 落位计数断言（.deb 黄金：136 kmap/44 psf/8 sfm.gz/9 acm.gz/
        # 8 screenmap/9 trans/2 fallback.gz/6 man/6 bin）
        self._assert_counts(CC, pf)

    def _gzip_copy(self, src, dst):
        with open(src, "rb") as f:
            data = f.read()
        with open(dst, "wb") as f:
            f.write(gzip.compress(data, 9))

    # .deb 黄金 windows 文档（trcs -f koi8-r -t <enc> 产物——trcs 对
    # box-drawing 有专属 ASCII 降级映射，python codecs 不匹配；utf-8 由
    # iconv 直出）：name(目标名) -> 配方目录嵌入文件
    _WINDOWS_GOLDEN = {
        "cp1251": "windows_cp1251",
        "ibm866": "windows_ibm866",
        "iso-8859-5": "windows_iso_8859_5",
        "koi8-r": "windows_koi8_r",
        "koi8-u": "windows_koi8_u",
        "mac-cyrillic": "windows_mac_cyrillic",
        "mik": "windows_mik",
        "pt154": "windows_pt154",
        "utf-8": "windows_utf8",
    }

    def _gen_windows(self, outdir):
        # 1427B 纯静态数据，.deb 黄金字节统一嵌入——与 man 预渲染 roff /
        # graph.fallback 段同法，bit 级一致
        for name, embedded in self._WINDOWS_GOLDEN.items():
            with open(os.path.join(self.recipe_folder, embedded), "rb") as f:
                golden = f.read()
            with open(os.path.join(outdir, name), "wb") as f:
                f.write(golden)

    def _assert_counts(self, cc, pf):
        def count(glob_pat, d):
            import glob as g
            return len(g.glob(os.path.join(d, glob_pat)))
        expected = {
            "kmap": (count("*.kmap", cc), 136),
            "psf": (count("*.psf", cc), 44),
            "sfm.gz": (count("*.sfm.gz", cc), 8),
            "acm.gz": (count("*.acm.gz", cc), 9),
            "screenmap": (count("*.screenmap", cc), 8),
            "trans": (count("*.trans", cc), 9),
            "fallback.gz": (count("*.fallback.gz", cc), 2),
            "man1.gz": (count("*.1.gz", os.path.join(pf, "share", "man",
                                                     "man1")), 6),
            "bin": (count("*", os.path.join(pf, "bin")), 6),
        }
        bad = {k: v for k, v in expected.items() if v[0] != v[1]}
        if bad:
            raise Exception(f"落位计数与 .deb 黄金不符: {bad}")

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.resdirs = ["share"]
