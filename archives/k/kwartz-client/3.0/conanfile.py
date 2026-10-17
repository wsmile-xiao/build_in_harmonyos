#!/usr/bin/env python3
"""Conan recipe — kwartz-client 3.0 (Debian "Kwartz client" enrolment tool).

kwartz-client is the client-side enrolment/configuration tool of the French
Kwartz school-server network: a pure POSIX shell + data package with zero
compilation units (Debian `debian/rules` is a bare `dh $@`; `Architecture:
all`; no compiler in Build-Depends). Upstream ships:

  - kwartz-cloud/kwartz-cloud     24-line POSIX sh script (WebDAV desktop
                                  shortcut via zenity/host/nemo)
  - debian/kwartz-install.tpl     172-line POSIX sh TEMPLATE — the package's
                                  main deliverable. Debian's postinst renders
                                  it with gettext-base envsubst, feeding it
                                  the 9 debconf answers (ip_proxy, port_proxy,
                                  proxy_gnome_noproxy, landing_page, proghalt,
                                  unattended_upgrades, login_apt, mdp_apt,
                                  nom_kwartz), into /usr/sbin/kwartz-install.sh
  - desktop/icon/conf/manpage     the usual desktop integration face

Source pin: salsa release tag `debian/3.0-17` — chosen over the bare Debian
orig tarball because the functional body lives in `debian/` (rationale in
conandata.yml header + notes.md; the orig tarball's kwartz-cloud/ subtree is
byte-identical inside the tag snapshot, verified by diff -r).

OHOS adaptation shape (no platform macros anywhere — POSIX capability level):
- package_type "application": kwartz-cloud is a real installed command
  (Debian: /usr/bin/kwartz-cloud), so the R38 commands.json gate applies and
  is satisfied at software level (archives/k/kwartz-client/commands.json).
- no build system, no tool_requires, no conan requires: build closure is
  empty. build() only audits the extracted upstream tree (file set +
  sha256 pins + debconf template-variable contract) — E241 data-package
  fidelity pattern, launchctl-completion/zsdx precedent.
- package() mirrors debian/kwartz-client.install + .manpages placement.
- NO ELF artifacts are produced or signed: every payload file is POSIX
  shell, text or SVG data (test_package asserts the zero-ELF property).
- Honest runtime disclosure (not packaging defects, unmodified upstream):
  OHOS has no debconf/dpkg, so the postinst envsubst rendering never runs —
  the template is shipped verbatim; kwartz-cloud's zenity/host/nemo stack
  is absent, so the enrolment function is unreachable on OHOS. What IS
  verified: the scripts parse under a real shell (bash/5.3 from this repo,
  test_package), the install face is complete, and the template carries
  every debconf variable postinst exports.
"""

import hashlib
import json
import os

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import copy, get


class KwartzClientConan(ConanFile):
    name = "kwartz-client"
    version = "3.0"
    description = ("Configuration of a Kwartz client — POSIX shell enrolment "
                   "tool (kwartz-cloud WebDAV shortcut + kwartz-install "
                   "template) of the French Kwartz school-server network")
    license = "GPL-2.0-or-later"
    homepage = "https://usb.freeduc.org"
    url = ""  # CI fills this
    topics = ("debian", "posix-shell", "ldap", "samba", "school-network")

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    # Extracted-tree audit pins (sha256 of the packaged install face,
    # recomputed from the pinned salsa debian/3.0-17 snapshot).
    PAYLOAD_SHA256 = {
        "kwartz-cloud/kwartz-cloud":
            "eb6a383d1986ab4185e44178ba690946f1c552246bb922cb0edca5b6480d7da2",
        "kwartz-cloud/kwartz-cloud.1":
            "957ca291ce9ee617defdc7462c79d41de1f7b6685a276dae5760dc952600e845",
        "kwartz-cloud/kwartz-cloud.conf":
            "55ec64a463f1b014084a86461c7f7fc2b2461ccb298e3ec8345b9ff119a5a3c9",
        "kwartz-cloud/kwartz-cloud.desktop":
            "5fc423839b64d1983c3a5a95a3574681413855b033817900be2514652cfbef7f",
        "kwartz-cloud/kwartz-cloud.svg":
            "0efff07ad2bd1471b95fa8cecc0cc327021f4f2dbfa7412f3332b36b66171a76",
        "debian/kwartz-install.tpl":
            "5fc6f8e7581290a531291195d751a680ecf71c46db05f3f6c52b26af310fb8c9",
        "debian/copyright":
            "1e2156c6a93ea2a843f7dd79bdec481ceb2cb088715f714067d18ca8fca016c0",
    }

    # Source-only face pins: debconf control flow (config/templates/postinst)
    # and the build rules. These files are audited, not packaged: they are
    # dpkg/debconf glue that cannot run on OHOS (no dpkg), but they define
    # the data flow the packaged template must satisfy.
    SOURCEFACE_SHA256 = {
        "debian/kwartz-client.postinst":
            "5ebec551cb688a60d3473fe7d3b23c73018a544cca461c3f9e673026a4267fec",
        "debian/kwartz-client.config":
            "2c450d698365e345161be1d5bcb98b87fd6fd687f87571d292a3a9c1b137a253",
        "debian/kwartz-client.templates":
            "03ff09ffb44577d17c14b639a510a34e551b0b076d19da50d76421fccdea5d49",
        "debian/rules":
            "9e4a977c95a3ead6971b95b0eed5be68108815d5bfb27dac9f7f5f100f6db1aa",
    }

    # The 9 debconf variables postinst exports (db_get kwartz/<var>) before
    # rendering kwartz-install.tpl with envsubst (verified against the pinned
    # postinst content). landing_page is the one variable the template does
    # NOT reference (postinst-only); the other 8 must appear in the template.
    DEBCONF_VARS = (
        "ip_proxy", "port_proxy", "proxy_gnome_noproxy", "landing_page",
        "proghalt", "unattended_upgrades", "login_apt", "mdp_apt",
        "nom_kwartz",
    )
    TPL_VARS = (
        "ip_proxy", "port_proxy", "proxy_gnome_noproxy", "proghalt",
        "unattended_upgrades", "login_apt", "mdp_apt", "nom_kwartz",
    )

    EXPECTED_FILES = (
        ".gitignore",
        "README.md",
        "debian/changelog",
        "debian/control",
        "debian/copyright",
        "debian/kwartz-client.config",
        "debian/kwartz-client.install",
        "debian/kwartz-client.manpages",
        "debian/kwartz-client.postinst",
        "debian/kwartz-client.postrm",
        "debian/kwartz-client.templates",
        "debian/kwartz-install.tpl",
        "debian/rules",
        "debian/po/POTFILES.in",
        "debian/po/ca.po",
        "debian/po/de.po",
        "debian/po/es.po",
        "debian/po/fr.po",
        "debian/po/it.po",
        "debian/po/nl.po",
        "debian/po/pt.po",
        "debian/po/pt_BR.po",
        "debian/po/templates.pot",
        "debian/source/format",
        "kwartz-cloud/kwartz-cloud",
        "kwartz-cloud/kwartz-cloud.1",
        "kwartz-cloud/kwartz-cloud.conf",
        "kwartz-cloud/kwartz-cloud.desktop",
        "kwartz-cloud/kwartz-cloud.svg",
        "kwartz-cloud/kwartz-cloud.xml",
    )

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "kwartz-client requires a POSIX target (Linux or OHOS)"
            )

    def layout(self):
        from conan.tools.layout import basic_layout
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        """Data-package integrity audit (E241 pattern, launchctl precedent).

        Nothing is compiled: this method machine-checks the extracted tree —
        exact upstream file set, per-file sha256 pins for the packaged face
        and the debconf source-only face, and the template-variable contract
        between postinst and kwartz-install.tpl. It also emits the
        machine-readable upstream-test discovery marker (upstream has zero
        tests — full evidence chain in test_package/MANIFEST.yml,
        EXCLUDED-TESTS.md and UPSTREAM-TESTS-EVIDENCE.json).
        """
        srcdir = self.source_folder

        def sha256_of(rel):
            with open(os.path.join(srcdir, rel), "rb") as fh:
                return hashlib.sha256(fh.read()).hexdigest()

        # 1. exact upstream file set (exclude conan-generated env scripts —
        #    runtime derivatives, not recipe inputs; knowledge E403/mlton).
        #    Conan 2.29 lays them out under <source>/build-release/conan/
        #    (aggregated env scaffolding), so exclude that build subtree and
        #    any of the known generated basenames at any depth.
        conan_generated = {
            "conanbuild.sh", "conanbuildenv.sh", "conanrun.sh",
            "conanrunenv.sh", "deactivate_conanbuild.sh",
            "deactivate_conanbuildenv.sh", "deactivate_conanrun.sh",
            "deactivate_conanrunenv.sh",
        }
        actual = set()
        for root, _dirs, files in os.walk(srcdir):
            for fname in files:
                rel = os.path.relpath(os.path.join(root, fname), srcdir)
                rel = rel.replace("\\", "/")
                if rel.split("/")[0] == "build-release":
                    continue
                if rel.split("/")[-1] in conan_generated:
                    continue
                actual.add(rel)
        expected = set(self.EXPECTED_FILES)
        if actual != expected:
            raise ConanException(
                "unexpected upstream file set: missing=%s extra=%s"
                % (sorted(expected - actual), sorted(actual - expected))
            )

        # 2. per-file sha256 pins (packaged face + debconf source-only face).
        for group in (self.PAYLOAD_SHA256, self.SOURCEFACE_SHA256):
            for rel, pinned in group.items():
                digest = sha256_of(rel)
                if digest != pinned:
                    raise ConanException(
                        f"{rel}: sha256 {digest} != pinned {pinned}"
                    )

        # 3. debconf contract: postinst must db_get/export all 9 variables.
        postinst = open(os.path.join(
            srcdir, "debian", "kwartz-client.postinst"), encoding="utf-8"
        ).read()
        for var in self.DEBCONF_VARS:
            if f"db_get kwartz/{var}" not in postinst:
                raise ConanException(
                    f"postinst does not db_get kwartz/{var}"
                )

        # 4. template contract: kwartz-install.tpl must reference the 8
        #    envsubst variables ($var or ${var} form; landing_page is
        #    postinst-only by upstream design and asserted absent nowhere).
        tpl = open(os.path.join(
            srcdir, "debian", "kwartz-install.tpl"), encoding="utf-8"
        ).read()
        import re
        for var in self.TPL_VARS:
            if not re.search(r"\$" + re.escape(var) + r"\b|\$\{" +
                             re.escape(var) + r"\b", tpl):
                raise ConanException(
                    f"kwartz-install.tpl does not reference ${var}"
                )

        # 5. emit the NO_UPSTREAM_TESTS discovery marker (see
        #    test_package/UPSTREAM-TESTS-EVIDENCE.json for the full chain).
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps({
            "status": "not_applicable",
            "framework": "none",
            "command": "n/a",
            "discovered": 0,
            "executed": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "discovery": "NO_UPSTREAM_TESTS",
            "evidence": [
                "salsa debian/3.0-17 tree (30 files, machine-checked above): "
                "no tests/ directory, no debian/tests (autopkgtest), "
                "no *_test.* files",
                "debian/rules is a bare 'dh $@' (sha256-pinned): no check or "
                "test override target",
                "no build system of any kind (no Makefile/CMake/Meson; "
                "Architecture: all, zero compilation units)",
                "all payload files are POSIX shell scripts, text, man or SVG "
                "data — no test runner entry point exists",
            ],
        }, sort_keys=True))

    def package(self):
        # Mirror debian/kwartz-client.install + debian/kwartz-client.manpages
        # placement (Debian /usr → package-relative).
        sf = self.source_folder
        pf = self.package_folder
        placements = [
            ("kwartz-cloud/kwartz-cloud", "bin"),
            ("kwartz-cloud/kwartz-cloud.svg", os.path.join("share", "icons")),
            ("kwartz-cloud/kwartz-cloud.desktop",
             os.path.join("share", "applications")),
            ("kwartz-cloud/kwartz-cloud.conf", "etc"),
            ("debian/kwartz-install.tpl",
             os.path.join("share", "doc", "kwartz-client")),
            ("kwartz-cloud/kwartz-cloud.1",
             os.path.join("share", "man", "man1")),
        ]
        for src_rel, dst_rel in placements:
            src = os.path.join(sf, *src_rel.split("/"))
            dst = os.path.join(pf, *dst_rel.split("/"))
            if not os.path.isfile(src):
                raise ConanException(f"payload file missing: {src}")
            copy(self, os.path.basename(src), src=os.path.dirname(src),
                 dst=dst, keep_path=False)
        # License face: debian/copyright is the GPL-2+ notice shipped by the
        # Debian package; retained per Conan licenses/ convention.
        copy(self, "copyright", src=os.path.join(sf, "debian"),
             dst=os.path.join(pf, "licenses"), keep_path=False)
        # kwartz-cloud is a shell script, not an ELF: exec bit only, no
        # OHOS binary signing (nothing to sign).
        os.chmod(os.path.join(pf, "bin", "kwartz-cloud"), 0o755)

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.resdirs = ["share"]
        self.runenv_info.prepend_path(
            "PATH", os.path.join(self.package_folder, "bin")
        )
