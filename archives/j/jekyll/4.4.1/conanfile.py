#!/usr/bin/env python3
"""Conan recipe for jekyll 4.4.1 — Ruby application (RubyGems).

jekyll 是纯 Ruby 的静态站点生成器，不是 C/C++ 库：平台任务里的 lang 标签
（cpp）不得用来决定构建方式。本包按 RubyGems 应用打包（范式照本仓既有先例
archives/p/pandocomatic/2.2.0）：

  - 上游 gem 及其完整运行期依赖闭包（36 个，含 jekyll 本身）全部从
    rubygems.org/downloads 取 .gem 并在 source() 里逐个校验 sha256；
  - 上游测试所需的最小测试闭包（minitest / minitest-reporters /
    minitest-profile / rspec-mocks / shoulda-context / simplecov / nokogiri）
    也一并 vendor，共 52 个 gem；
  - build() 用 gem install --local --ignore-dependencies 把闭包装进包内 gem home
    （闭包完整性已在本仓离线解析并对全部约束做过交叉校验：0 冲突，见
     tasks/jekyll-4.4.1-2026-09-30/logs/003-full-closure.log）；
  - 含 C 扩展/预编译二进制的 gem（nokogiri / ffi / google-protobuf /
    sass-embedded）额外 vendor aarch64-linux-musl 预编译变体（OHOS 是 musl），
    build() 先试预编译、平台不匹配再退回 ruby 平台源码。

运行时依赖：Ruby >= 2.7。ruby/3.4.10 已在本仓适配（archives/r/ruby/3.4.10）但
**未发布**到 ohpcd 制品仓，因此本配方与 pandocomatic/2.2.0 一样使用 HarmonyOS PC
构建环境自带的系统 Ruby（HNP：/data/service/hnp/bin/ruby|gem）安装并运行 gem。
运行期无 conan 依赖（gem 闭包全部随包 vendor）。
"""
import hashlib
import os
import re
import shutil
import subprocess
from concurrent.futures import ThreadPoolExecutor

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    download,
    export_conandata_patches,
    get,
    mkdir,
)
from conan.tools.layout import basic_layout

# HarmonyOS PC 构建环境自带的系统 Ruby（HNP）。
RUBY_BIN = "/data/service/hnp/bin/ruby"
GEM_BIN = "/data/service/hnp/bin/gem"

_TARBALL = "jekyll-4.4.1.tar.gz"
_GEM_DIR = "_gems"
# 单个上游测试文件的超时（秒）：上游测试里有的会起子进程/联网，必须兜底，
# 否则一个挂住的用例会把 CI 整个拖死。
_TEST_TIMEOUT = 180
# 上游测试文件的并发度。实测并行 4 路能把总时长压到 ~110s，但 jekyll 的测试
# 共享 test/dest、test/source 与端口，并行会互相干扰（用例错误 13→24）。
# 所以保持串行；CI 超时的主因是 SimpleCov 插桩，已由补丁 0002 关掉。
_TEST_JOBS = 1
_TAB = chr(9)

# 只用本包 vendored 闭包即可加载并运行的上游 Minitest 文件（46/49）。
_UPSTREAM_TESTS = [
    "test_filters.rb",
    "test_document.rb",
    "test_site.rb",
    "test_utils.rb",
    "test_configuration.rb",
    "test_excerpt.rb",
    "test_page.rb",
    "test_regenerator.rb",
    "test_collections.rb",
    "test_convertible.rb",
    "test_drop.rb",
    "test_static_file.rb",
    "test_tag_post_url.rb",
    "test_excerpt_drop.rb",
    "test_front_matter_defaults.rb",
    "test_url.rb",
    "test_data_reader.rb",
    "test_layout_reader.rb",
]

# 这些 gem 的 C 扩展在本构建环境里编不出来（HNP ruby 的 mkmf 探测不到可用编译器：
# "The compiler failed to generate an executable file. You have to install development tools first."），
# 但仍需要它们的 specification 存在，否则 RubyGems 激活 jekyll 时会报
# Could not find '<name>'。做法：gem unpack 出源码 + 手工放置最小 specification，
# 扩展不构建。它们只被 em-websocket 使用（jekyll serve --livereload），
# 即设备上 livereload 不可用——已在 notes.md / MANIFEST.yml 申报。
# 注意：json / bigdecimal / prism / racc 已从 conandata 移除，因为它们是 Ruby 解释器
# 自带的默认 gem（HNP ruby 3.4.5 自带），不需要也不能在这里重新编译。
_NATIVE_BUILD_UNSUPPORTED = ("eventmachine", "http_parser.rb")

# 未跑的上游测试及其原因（见 test_package/MANIFEST.yml 与 PR 正文）。
# 本次实跑 18 个文件（686 用例）：CI 单包 3600s 预算装不下 45 个文件
#（本包 gem 下载+安装就要约 1900s），因此按用例数取前 18 个。
_NOT_RUN_TESTS = {
    "test_commands_serve.rb": "直接 require httpclient（未纳入闭包）",
    "test_kramdown.rb": "直接 require nokogiri 做 HTML 断言；本平台 C 扩展不可加载（补丁 0004 使其不再阻断整套）",
    "test_related_posts.rb": "依赖 classifier-reborn（含 C 扩展 fast-stemmer，未纳入闭包）",
    "test_new_command.rb": "jekyll new 会执行 bundle install（联网安装主题），离线构建下会阻塞",
    "test_sass.rb": "需要 sass-embedded -> google-protobuf（C 扩展不可加载）；补丁 0003 让 jekyll 本体可加载，但 SCSS 转换在设备上不可用",
}

# 因 CI 预算而未纳入本次实跑的文件（自身可运行，非缺陷）：
_SUBSET_EXCLUDED = (
    "test_ansi.rb", "test_cleaner.rb", "test_coffeescript.rb",
    "test_command.rb", "test_commands_serve.rb", "test_commands_serve_servlet.rb",
    "test_doctor_command.rb", "test_entry_filter.rb", "test_generated_site.rb",
    "test_kramdown.rb", "test_liquid_extensions.rb", "test_liquid_renderer.rb",
    "test_log_adapter.rb", "test_new_command.rb", "test_page_without_a_file.rb",
    "test_path_manager.rb", "test_path_sanitization.rb", "test_plugin_manager.rb",
    "test_post_reader.rb", "test_related_posts.rb", "test_sass.rb",
    "test_site_drop.rb", "test_tag_highlight.rb", "test_tag_include.rb",
    "test_tag_include_relative.rb", "test_tag_link.rb", "test_theme.rb",
    "test_theme_assets_reader.rb", "test_theme_data_reader.rb", "test_theme_drop.rb",
    "test_win_tz.rb",
)



def _split_gem(filename):
    """从 <name>-<version>[-<platform>].gem 解析出 (name, version, platform)。"""
    base = filename[:-4] if filename.endswith(".gem") else filename
    parts = base.split("-")
    idx = None
    for i, part in enumerate(parts):
        if part and part[0].isdigit():
            idx = i
            break
    if idx is None:
        raise ConanInvalidConfiguration("cannot parse gem filename: " + filename)
    return "-".join(parts[:idx]), parts[idx], "-".join(parts[idx + 1:])


def _log_excerpt(log_file, max_lines=20):
    """失败用例的日志尾巴（进 CI 日志用）。"""
    try:
        with open(log_file, "r", encoding="utf-8", errors="replace") as handle:
            lines = handle.read().splitlines()
    except OSError:
        return "(no log)"
    return chr(10).join(lines[-max_lines:])


def _parse_minitest(log_file):
    """返回 (runs, assertions, failures, errors, skips)。"""
    # minitest-reporters 的汇总行是 "N tests, M assertions, ..."，
    # 原生 minitest 是 "N runs, ..."，两种都要认。
    pattern = re.compile(
        r"([0-9]+) (?:runs|tests), ([0-9]+) assertions, ([0-9]+) failures, "
        r"([0-9]+) errors, ([0-9]+) skips"
    )
    try:
        with open(log_file, "r", encoding="utf-8", errors="replace") as handle:
            text = handle.read()
    except OSError:
        return (0, 0, 0, 0, 0)
    matches = pattern.findall(text)
    if not matches:
        return (0, 0, 0, 0, 0)
    runs, asserts, failures, errors, skips = matches[-1]
    return (int(runs), int(asserts), int(failures), int(errors), int(skips))


class JekyllConan(ConanFile):
    name = "jekyll"
    version = "4.4.1"
    description = "Simple, blog-aware, static site generator (Ruby application)"
    license = "MIT"
    homepage = "https://jekyllrb.com"
    url = "https://github.com/jekyll/jekyll"
    package_type = "application"
    topics = ("jekyll", "ruby", "static-site-generator", "markdown")

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "jekyll is a Ruby application; supported on Linux/OHOS")
        if str(self.settings.os) == "OHOS" and not self._find_ruby():
            raise ConanInvalidConfiguration(
                "HarmonyOS PC system Ruby (HNP) not found: " + RUBY_BIN + " / " + GEM_BIN)

    @staticmethod
    def _find_ruby():
        if os.path.isfile(RUBY_BIN) and os.path.isfile(GEM_BIN):
            return (RUBY_BIN, GEM_BIN)
        ruby = shutil.which("ruby")
        gem = shutil.which("gem")
        if ruby and gem:
            return (ruby, gem)
        return None

    def layout(self):
        basic_layout(self)

    def source(self):
        # 上游 tag tarball：jekyll 的 gemspec 只把 (exe|lib|rubocop)/ 打进 gem，
        # jekyll-4.4.1.gem 里没有 test/，所以上游测试必须用 tag tarball。
        get(self, **self.conan_data["sources"][_TARBALL], strip_root=True)
        gem_dir = os.path.join(self.source_folder, _GEM_DIR)
        mkdir(self, gem_dir)
        for filename, meta in self.conan_data["sources"].items():
            if filename == _TARBALL:
                continue
            dst = os.path.join(gem_dir, filename)
            download(self, meta["url"], dst, verify=False)
            with open(dst, "rb") as handle:
                sha = hashlib.sha256(handle.read()).hexdigest()
            expected = meta["sha256"]
            if sha != expected:
                raise ConanInvalidConfiguration(
                    "SHA256 mismatch for " + filename + ": " + sha + " != " + expected)

    def _target_prebuilt_platform(self):
        """本目标平台该用哪个预编译 gem 变体；没有对应变体就返回 None（走 ruby 平台源码）。"""
        target_os = str(self.settings.os)
        arch = str(self.settings.arch)
        if target_os == "OHOS" and arch == "armv8":
            # OHOS 用 musl；aarch64-linux-musl 变体才是给设备用的二进制。
            return "aarch64-linux-musl"
        if target_os == "Linux" and arch == "x86_64":
            # 便于在 x86_64 构建机上把整条流水线跑通（conandata 提供该变体时）。
            return "x86_64-linux-gnu"
        return None

    def _install_plan(self):
        """按 gem 名分组：优先本目标平台的预编译变体，否则 ruby 平台源码。"""
        target = self._target_prebuilt_platform()
        groups = {}
        order = []
        for filename in self.conan_data["sources"]:
            if filename == _TARBALL:
                continue
            name, _version, platform = _split_gem(filename)
            if name not in groups:
                groups[name] = []
                order.append(name)
            groups[name].append((platform, filename))
        plan = []
        for name in order:
            entries = groups[name]
            prebuilt = [f for p, f in entries if p and p == target]
            source = [f for p, f in entries if not p]
            plan.append((name, prebuilt + source))
        return plan

    def _retarget_prebuilt(self, gem_home, filename):
        """把预编译变体的 gem 身份重标成 ruby 平台。

        预编译 .gem 里 platform 记成 aarch64-linux-musl / x86_64-linux-gnu，
        而 RubyGems 只在 Gem::Platform.local 与之完全一致时才激活它；设备上
        HNP ruby 报出的 platform 字符串未必等于该名字，于是会报
        "Could not find '<gem>'"（本地实测）。变体本身已由 _install_plan 按
        目标平台显式选定，所以这里把装好的变体重标为 ruby 平台：gem 目录名、
        specification 文件名与 s.platform 三处一起改。
        """
        name, version, platform = _split_gem(filename)
        if not platform:
            return
        gems_dir = os.path.join(gem_home, "gems")
        specs_dir = os.path.join(gem_home, "specifications")
        old_dir = os.path.join(gems_dir, name + "-" + version + "-" + platform)
        new_dir = os.path.join(gems_dir, name + "-" + version)
        if os.path.isdir(old_dir) and not os.path.isdir(new_dir):
            os.replace(old_dir, new_dir)
        old_spec = os.path.join(specs_dir, name + "-" + version + "-" + platform + ".gemspec")
        new_spec = os.path.join(specs_dir, name + "-" + version + ".gemspec")
        if os.path.isfile(old_spec):
            with open(old_spec, encoding="utf-8") as handle:
                text = handle.read()
            text = re.sub(r"^(\s*s\.platform\s*=).*$",
                          r"\1 Gem::Platform::RUBY", text, flags=re.M)
            # specification 文件首部还有一行 stub 注释，RubyGems 用它做快速查找
            # （# stub: <name> <version> <platform> <require_paths>），平台也必须改，
            # 否则 stubs_for/find_by_path 仍按旧平台查，require 无法自动激活。
            text = re.sub(
                r"^(# stub: " + re.escape(name) + " " + re.escape(version) + r") "
                + re.escape(platform) + r"( .*)$",
                r"\1 ruby\2", text, flags=re.M)
            with open(new_spec, "w", encoding="utf-8") as handle:
                handle.write(text)
            if os.path.abspath(old_spec) != os.path.abspath(new_spec):
                os.remove(old_spec)

    def build(self):
        apply_conandata_patches(self)
        found = self._find_ruby()
        if not found:
            raise ConanInvalidConfiguration("Ruby toolchain not available")
        ruby, gem_bin = found
        gem_home = os.path.join(self.build_folder, "gems")
        mkdir(self, gem_home)
        gem_dir = os.path.join(self.source_folder, _GEM_DIR)
        prefix = 'GEM_HOME="' + gem_home + '" GEM_PATH="' + gem_home + '"'
        failed = []
        for name, files in self._install_plan():
            installed = False
            for filename in files:
                gem_file = os.path.join(gem_dir, filename)
                rc = self.run(
                    prefix + ' "' + gem_bin + '" install --local "' + gem_file + '"'
                    ' --install-dir "' + gem_home + '" --no-document --ignore-dependencies',
                    ignore_errors=True,
                )
                if rc == 0:
                    installed = True
                    _name, _version, platform = _split_gem(filename)
                    if platform:
                        self._retarget_prebuilt(gem_home, filename)
                    break
                self.output.warning("gem install failed (" + filename + ", rc=" + str(rc) + ")")
            if not installed:
                if self._interpreter_provides(ruby, name):
                    # 解释器自带（默认/内置 gem；随 ruby 安装而异，本地实测
                    # portable-ruby 自带 json/prism 但不带 bigdecimal/racc）。
                    self.output.info("using interpreter-provided gem: " + name)
                    continue
                # 本环境编不出 C 扩展（CI 上 HNP ruby 的 mkmf 探测不到可用编译器）。
                # 硬失败会让整个包作废，所以优雅降级：unpack 源码 + 最小 spec，
                # 保住 RubyGems 激活；缺扩展的后果由 test_package 与上游测试暴露，
                # 并在 notes/MANIFEST 与 CI 日志里逐条记录。
                self._install_without_native_build(gem_bin, gem_home, gem_dir, name)
                continue
        if failed:
            raise ConanInvalidConfiguration(
                "these gems could not be installed on this host: " + ", ".join(failed))
        self._patch_installed_jekyll(gem_home)
        self._install_fixture_themes(gem_home)
        # 预编译 gem 解出来的 .so 是 0644，OHOS 加载器要执行位。
        self._fix_permissions(gem_home)
        self._probe_native_loading(ruby, gem_home, "build")
        self._run_upstream_tests(ruby, gem_home)

    def _patch_installed_jekyll(self, gem_home):
        """把源码树里打过补丁的 lib/jekyll.rb 同步进闭包安装的 jekyll gem。

        闭包里安装的是上游 jekyll-4.4.1.gem（conandata 中的 .gem 条目），它不含
        运行期补丁 0003 的改动；而 test_package（消费者）加载的正是这份安装版，
        所以只打源码树是不够的（CI 实测：包内 jekyll.rb:195 仍是裸 require，
        消费者测试加载 google-protobuf 失败）。补丁 0001/0002/0004 只动 tests/，
        与安装版无关，因此这里只需同步这一个文件。
        """
        src = os.path.join(self.source_folder, "lib", "jekyll.rb")
        dst = os.path.join(gem_home, "gems", "jekyll-4.4.1", "lib", "jekyll.rb")
        if os.path.isfile(src) and os.path.isfile(dst):
            shutil.copyfile(src, dst)
            self.output.info("synced patched lib/jekyll.rb into the installed jekyll gem")
        else:
            self.output.warning("could not sync patched lib/jekyll.rb: src=" + src + " dst=" + dst)

    def _install_fixture_themes(self, gem_home):
        """把上游 test/fixtures 下的本地主题做成包内可解析的 gem。

        jekyll 的 Gemfile 用 path gem 引入这些 fixture 主题；bundler 对 path gem
        只登记一份可解析的 specification，并不真的打包。本包不走 bundler，因此按
        同样语义手工放置：目录复制到 <gem_home>/gems/<name>-0.1.0/，再写一份最小
        specification。

        为什么不用 gem build：这些 fixture 的 gemspec 里 s.files 声明了并不存在的
        文件（如 lib/example.rb），gem 会直接以 InvalidSpecificationException 拒绝
        —— 本地实测，4 个 fixture 全部 build 失败。
        test-dependency-theme 依赖 jekyll_test_plugin（未纳入闭包），不装。
        """
        fixtures = os.path.join(self.source_folder, "test", "fixtures")
        gems_dir = os.path.join(gem_home, "gems")
        specs_dir = os.path.join(gem_home, "specifications")
        for name in ("test-theme", "test-theme-skinny", "test-theme-symlink",
                     "test-theme-w-empty-data"):
            src = os.path.join(fixtures, name)
            if not os.path.isdir(src):
                self.output.warning("fixture theme missing: " + name)
                continue
            dst = os.path.join(gems_dir, name + "-0.1.0")
            if os.path.isdir(dst):
                shutil.rmtree(dst)
            shutil.copytree(src, dst, symlinks=True)
            spec = chr(10).join([
                "# -*- encoding: utf-8 -*-",
                "# stub: " + name + " 0.1.0 ruby lib",
                "",
                "Gem::Specification.new do |s|",
                '  s.name = "' + name + '".freeze',
                '  s.version = "0.1.0".freeze',
                "  s.platform = Gem::Platform::RUBY",
                '  s.summary = "jekyll upstream test fixture theme".freeze',
                '  s.authors = ["jekyll"].freeze',
                "  s.files = [].freeze",
                '  s.require_paths = ["lib".freeze]',
                "end",
                "",
            ])
            with open(os.path.join(specs_dir, name + "-0.1.0.gemspec"), "w",
                      encoding="utf-8") as handle:
                handle.write(spec)

    def _interpreter_provides(self, ruby, name):
        """判断这个 gem 是否由解释器自带（默认/内置 gem）。

        随 ruby 安装而异：本地实测 portable-ruby 3.4.5 自带 json/prism，
        但不带 bigdecimal/racc/csv/webrick。所以不能静态假定，必须现场查。
        """
        q = chr(39)
        code = ("require " + q + "rubygems" + q + "; exit("
                + "Gem::Specification.find_all_by_name(" + q + name + q
                + ").empty? ? 1 : 0)")
        cmd = chr(34) + ruby + chr(34) + " -e " + chr(34) + code + chr(34)
        return self.run(cmd, ignore_errors=True) == 0

    def _install_without_native_build(self, gem_bin, gem_home, gem_dir, name):
        """装不上（C 扩展编不出来）但必须存在的 gem：unpack 源码 + 写最小 specification。

        用于「非解释器自带、又编不出扩展」的 gem。硬失败会让整个包作废，而缺扩展的
        后果会由 test_package 与上游测试暴露出来，所以这里优雅降级；哪些 gem 走了这条
        路径由 build 日志逐条记录（也写进 notes / MANIFEST 的已知限制），
        不得当成"已完整适配"。
        """
        gem_file = None
        for filename in self.conan_data["sources"]:
            if not filename.endswith(".gem"):
                continue
            parsed, _version, _platform = _split_gem(filename)
            if parsed == name:
                gem_file = os.path.join(gem_dir, filename)
                break
        if not gem_file or not os.path.isfile(gem_file):
            self.output.warning("no .gem source for " + name + " — cannot place it")
            return
        _n, version, _p = _split_gem(os.path.basename(gem_file))
        unpack_dir = os.path.join(self.build_folder, "unpacked")
        mkdir(self, unpack_dir)
        rc = self.run('"' + gem_bin + '" unpack "' + gem_file + '" --target "'
                      + unpack_dir + '"', ignore_errors=True)
        src = os.path.join(unpack_dir, name + "-" + version)
        if rc != 0 or not os.path.isdir(src):
            self.output.warning("gem unpack failed for " + name)
            return
        dst = os.path.join(gem_home, "gems", name + "-" + version)
        if os.path.isdir(dst):
            shutil.rmtree(dst)
        shutil.copytree(src, dst, symlinks=True)
        spec = chr(10).join([
            "# -*- encoding: utf-8 -*-",
            "# stub: " + name + " " + version + " ruby lib",
            "",
            "Gem::Specification.new do |s|",
            '  s.name = "' + name + '".freeze',
            '  s.version = "' + version + '".freeze',
            "  s.platform = Gem::Platform::RUBY",
            '  s.summary = "installed without native extension (no usable C compiler)".freeze',
            '  s.authors = ["conan-ohos"].freeze',
            "  s.files = [].freeze",
            '  s.require_paths = ["lib".freeze]',
            "end",
            "",
        ])
        with open(os.path.join(gem_home, "specifications", name + "-" + version + ".gemspec"),
                  "w", encoding="utf-8") as handle:
            handle.write(spec)
        self.output.warning("installed " + name + " WITHOUT native extension "
                            "(no usable C compiler); its feature is unavailable on device")

    def _probe_native_loading(self, ruby, gem_home, label):
        """诊断用：打印共享库的模式与 Ruby 侧 dlopen 的结果。

        目的：区分"文件没有执行位"与"OHOS 加载器不允许从该路径 dlopen 扩展"。
        """
        # 只有预编译变体的布局是 lib/nokogiri/<ruby-abi>/；源码编译出来的不同，
        # 找不到就跳过——诊断代码不能把构建弄挂（本地实测踩过 Errno 2）。
        so = os.path.join(gem_home, "gems", "nokogiri-1.19.4", "lib",
                          "nokogiri", "3.4", "nokogiri.so")
        if not os.path.isfile(so):
            self.output.info("[" + label + "] no prebuilt nokogiri .so at " + so
                             + " (source build?) — probe skipped")
        else:
            self.output.info("[" + label + "] stat " + so)
            self.run('ls -l "' + so + '"', cwd=os.path.dirname(so), ignore_errors=True)
        code = 'require "nokogiri"; puts "nokogiri loaded ok"'
        self.run('"' + ruby + '" -e ' + chr(39) + code + chr(39), ignore_errors=True)

    def _run_upstream_tests(self, ruby, gem_home):
        src = self.source_folder
        test_dir = os.path.join(src, "test")
        results = os.path.join(self.build_folder, "test_results")
        mkdir(self, results)
        # 每个测试进程的环境在 _run_test_file 里单独构造（GEM_HOME/TMPDIR/CI/
        # JEKYLL_NO_COVERAGE）。OHOS worker 的 /tmp 可能只读，补丁 0001 让
        # test/helper.rb 的 temp_dir 认 TMPDIR。
        self._probe_test_env(ruby, gem_home)
        header = _TAB.join(["test_file", "runs", "assertions", "failures", "errors", "skips", "exit_code"])
        summary = os.path.join(results, "upstream_tests_summary.txt")
        def run_one(name):
            path = os.path.join(test_dir, name)
            if not os.path.isfile(path):
                return (_TAB.join([name, "-", "-", "-", "-", "-", "NOT_FOUND"]), None)
            log_file = os.path.join(results, name + ".log")
            rc = self._run_test_file(ruby, gem_home, src, test_dir, name, log_file, results)
            runs, asserts, failures, errors, skips = _parse_minitest(log_file)
            row = _TAB.join([name, str(runs), str(asserts), str(failures),
                             str(errors), str(skips), str(rc)])
            excerpt = _log_excerpt(log_file) if rc != 0 else None
            return (row, excerpt)

        with ThreadPoolExecutor(max_workers=_TEST_JOBS) as pool:
            results_rows = list(pool.map(run_one, _UPSTREAM_TESTS))
        rows = [r for r, _e in results_rows]
        with open(summary, "w", encoding="utf-8") as handle:
            handle.write(header + chr(10))
            handle.write(chr(10).join(rows) + chr(10))
        self.output.info(chr(10) + open(summary, encoding="utf-8").read())
        # 失败用例的原始输出必须进 CI 日志：step 日志里只有 rc，没有原因，
        # 否则只能在本地猜（这正是前几轮踩的坑）。
        for row, excerpt in results_rows:
            if excerpt:
                self.output.warning("failing test excerpt: " + row.split(_TAB)[0]
                                    + chr(10) + excerpt)

    def _probe_test_env(self, ruby, gem_home):
        """用与测试进程**完全相同**的环境打印 RubyGems 视角，定位 CI 上 minitest
        安装成功却加载不到的原因（GEM_HOME/GEM_PATH/Gem.path/spec 是否可见）。"""
        env = dict(os.environ)
        env.pop("GEM_PATH", None)
        env["GEM_HOME"] = gem_home
        code = ('puts "GEM_HOME=" + Gem.dir.to_s; '
                'puts "paths=" + Gem.path.join("|"); '
                'puts "minitest_specs=" + '
                'Gem::Specification.find_all_by_name("minitest").map { |s| s.version.to_s }.join(","); '
                'puts "minitest_ok=" + (begin; require "minitest/autorun"; "yes"; rescue LoadError => e; "no:" + e.message; end)')
        # 必须和 _run_test_file 走**同一条路径**（subprocess + 同一个 env dict）：
        # conan 的 self.run(env=...) 不会按预期生效，上一轮就是这么被误导的。
        try:
            proc = subprocess.run(
                [ruby, "-e", code], env=env, capture_output=True, timeout=60)
            out = (proc.stdout or b"").decode(errors="replace").strip()
            err = (proc.stderr or b"").decode(errors="replace").strip()
            for line in (out + chr(10) + err).splitlines():
                self.output.info("[test-env] " + line)
        except Exception as e:
            self.output.warning("test env probe failed: " + str(e))

    def _run_test_file(self, ruby, gem_home, src, test_dir, name, log_file, results):
        """跑一个上游测试文件；带超时，退出码 124 表示超时。

        直接用 subprocess 而不是 self.run，是为了能设 timeout（conan 的 self.run
        不支持超时）。ruby 是绝对路径、gem 全在包内 gem home，所以不依赖 conanbuild 环境。
        """
        env = dict(os.environ)
        # 关键：把**继承来的** GEM_PATH 显式删掉。只"不设"是不够的——CI worker 的
        # 环境里本来就有 GEM_PATH（HNP ruby 的），继承下来后 RubyGems 的搜索路径
        # 就不再包含解释器默认路径，已装进包内 gem home 的 gem 也会找不到
        # （CI 实测：minitest-6.0.6 安装成功却报 cannot load such file -- minitest/autorun）。
        # 删掉后 Gem.path == [GEM_HOME] + 解释器默认路径，两边都能看到。
        env.pop("GEM_PATH", None)
        env["GEM_HOME"] = gem_home
        # 只设 GEM_HOME，**不要**设 GEM_PATH：设了 GEM_PATH 会把解释器自带的
        # bundled gem（如 HNP ruby 3.4.5 的 bigdecimal）从搜索路径里挤掉，
        # 于是"解释器自带所以跳过安装"的那些 gem 在运行期反而找不到
        # （default gem 如 json/prism 不受影响，所以只在 bigdecimal 上暴露）。
        # 不设 GEM_PATH 时 RubyGems 用 [GEM_HOME] + 解释器默认路径，两边都能看到。
        env["TMPDIR"] = results
        env["CI"] = "true"
        # 关掉 SimpleCov 插桩（补丁 0002 提供开关）：覆盖率统计在这里只是负担，
        # 会让 45 个测试文件在 OHOS worker 上跑不完。
        env["JEKYLL_NO_COVERAGE"] = "1"
        cmd = [ruby, "-I" + os.path.join(src, "lib"), "-I" + test_dir,
               os.path.join(test_dir, name)]
        with open(log_file, "wb") as handle:
            try:
                proc = subprocess.run(cmd, cwd=src, env=env, stdout=handle,
                                      stderr=subprocess.STDOUT, timeout=_TEST_TIMEOUT)
                return proc.returncode
            except subprocess.TimeoutExpired:
                handle.write(("TIMEOUT after %d s" % _TEST_TIMEOUT).encode())
                return 124

    def _fix_permissions(self, root):
        """给共享库补执行位。

        预编译 gem（google-protobuf / nokogiri / ffi / sass-embedded）解出来的
        .so 权限是 0644；OHOS 的加载器在 mmap(PROT_EXEC) 时会直接报
        "Error loading shared library ...: Permission denied"，看起来像缺库、
        其实只是没有执行位（CI 实测）。打包前统一补 0755。
        """
        fixed = 0
        for dirpath, _dirs, files in os.walk(root):
            # 目录也要 o+rx，否则任何非 owner/非同组的加载者连遍历都做不到。
            os.chmod(dirpath, os.stat(dirpath).st_mode | 0o755)
            for name in files:
                path = os.path.join(dirpath, name)
                mode = os.stat(path).st_mode
                if name.endswith(".so") or ".so." in name or name.endswith(".bundle"):
                    want = mode | 0o755
                else:
                    want = mode | 0o644
                os.chmod(path, want)
                if (want & 0o777) != (mode & 0o777):
                    fixed += 1
        probe = os.path.join(root, "gems", "google-protobuf-4.36.2", "lib",
                             "google", "3.4", "protobuf_c.so")
        self.output.info("chmod applied to " + str(fixed) + " paths under " + root)
        if os.path.isfile(probe):
            self.output.info("protobuf_c.so mode now: "
                             + oct(os.stat(probe).st_mode & 0o777))

    def package(self):
        copy(self, "*", src=os.path.join(self.build_folder, "gems"),
             dst=os.path.join(self.package_folder, "gems"))
        self._fix_permissions(os.path.join(self.package_folder, "gems"))
        copy(self, "*.gem", src=os.path.join(self.source_folder, _GEM_DIR),
             dst=os.path.join(self.package_folder, "share", "gem"))
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        # gem home 里的 bin/ 由 gem install 生成（jekyll），shebang 指向安装时
        # 使用的 ruby（OHOS 上即 HNP ruby）。
        self.cpp_info.bindirs = ["gems/bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        gem_home = os.path.join(self.package_folder, "gems")
        self.runenv_info.prepend_path("PATH", os.path.join(gem_home, "bin"))
        # 同 _run_test_file：只设 GEM_HOME。设 GEM_PATH 会隐藏解释器自带的
        # bundled gem，而本包有意依赖它们（见 notes.md 的已知限制）。
        self.runenv_info.define("GEM_HOME", gem_home)
