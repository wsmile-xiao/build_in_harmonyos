#!/usr/bin/env python3
"""Deterministic integrity validator for the furo theme package
(furo-2024.8.6-py3-none-any.whl contents).

furo is a pure-asset Sphinx theme: the official wheel carries the built
theme (80 files under furo/) plus dist-info metadata and nothing needs to
be compiled -- so, following the data/source-package exemption pattern
(pari-seadata-big, agnostic-lizard), build()/test() verify byte-level
integrity instead of running a compiler: every pinned file must exist
with the exact (size, sha256); no missing, no extra entries.

Usage:
    verify_furo.py --source-root <unpacked wheel tree>
    verify_furo.py --package-root <installed package folder>
"""

import argparse
import hashlib
import os
import sys


PINNED_FILES = {
    "furo-2024.8.6.dist-info/LICENSE": (1078, "eead43859a75f77da25f85b9a1493523283476624a11dff7a3a8f08018485cd1"),
    "furo-2024.8.6.dist-info/METADATA": (5929, "ec57d5d61bbb67c38e35ea93e9e1941dcaa6ab6ccea01a17c1eb448e8c4bbafe"),
    "furo-2024.8.6.dist-info/RECORD": (7963, "dd8359598e82a1c3ecbaa3d5ef3f2348b829e5ccd0ea2056cf476f00812177b5"),
    "furo-2024.8.6.dist-info/WHEEL": (101, "a0c5c1ece335d317b03fe421a744a6ea057224f0e00eba0d5f91cddeea65d721"),
    "furo-2024.8.6.dist-info/entry_points.txt": (32, "4b0a5ae07e23f0c83c8eb714cbfd5ba84e42789d90d58c65c3f4744514d676ab"),
    "furo/__init__.py": (12712, "c4d709525c98b864ae6580d7ea6f95dbb8cb2ba8bf3f58d5840e146e4ebb1818"),
    "furo/_demo_module.py": (2040, "544d92f97d1c15760ccb38c1a90a23e675243eaf9b494e4b8c15d7c5a16e5a07"),
    "furo/assets/scripts/furo.js": (5083, "1b539e9185bedc6e48a974ef0f4171586e2fd5fd1f8830c0e7fb5891fc02d16f"),
    "furo/assets/scripts/gumshoe-patched.js": (12995, "8d04dcba564a487e3a956fd43f6bde02e2619ebc3fdd7d160236c4f2eea8c8d5"),
    "furo/assets/styles/_scaffold.sass": (10092, "53d4a0dc7ea0fcea6e54e4f806472c02a07850d6e3280e83c19b9db86b0abfbb"),
    "furo/assets/styles/_shame.sass": (309, "9e8ac1821494937cf2d624aedcdf1e87c4c3ccdf912cdf0645e736a23be68887"),
    "furo/assets/styles/base/_index.sass": (78, "fe03be6bc2680cf85692f14e0687726e55e1c0cf9be3a98ca22ff3d880b16665"),
    "furo/assets/styles/base/_print.sass": (1406, "75b17a96889848a882964da1c782410c609f678880947910b4bfa3b044ba361b"),
    "furo/assets/styles/base/_screen-readers.sass": (387, "9b07ea4f99ac6097909be80fc624052892687137b51225b572441603aaf4091c"),
    "furo/assets/styles/base/_theme.sass": (1490, "acde7df8da16492ee8f055ff2db76a920a452b36401506592bb4c1c8118524ec"),
    "furo/assets/styles/base/_typography.sass": (1986, "ecc1ef98aaf60b90ee011a2ea3f90a9592a49c2d659ff3b08285d38670fff22d"),
    "furo/assets/styles/components/_footer.sass": (1978, "f9af5f4531b9f14fb3ab8fc18175f45aa1564a97c05ce95f5d3588534f283162"),
    "furo/assets/styles/components/_index.sass": (80, "e5982e94c39a505a67bf90b01afc8c6afce43bf0d4c523e7a39d44980167ab2f"),
    "furo/assets/styles/components/_search.sass": (328, "a8ad20733bf572e24c67ee59267f2871505cba78b59877641fe4a1c7607f7f3e"),
    "furo/assets/styles/components/_sidebar.sass": (6138, "a772c2a7ff9432993f0cb6e129b0a6dc0f6e1c336955fb259610f175d7a4c237"),
    "furo/assets/styles/components/_table_of_contents.sass": (1835, "6340d9e22ad635a21de19c936710c6588dd82bd27803b6b5f3e8e916b816347d"),
    "furo/assets/styles/content/_admonitions.sass": (1945, "7d069844a12b2eaa977151df2a868d94b19c024b3a6493190e446c28c439c305"),
    "furo/assets/styles/content/_api.sass": (2835, "d8cef9db83ded26eeb04b9a16af8e9fad680463c3a8465b6432b74978df2ccb3"),
    "furo/assets/styles/content/_blocks.sass": (140, "4f936f99e84ce35654dc3cbff8c88dca37d02704ea2a7e9d5245ebfb0348d431"),
    "furo/assets/styles/content/_captions.sass": (385, "e8770d62e227d2b6d3e735023a1834b81eeb1008f795e0ff1f3c58dc2fd918e1"),
    "furo/assets/styles/content/_code.sass": (3231, "20e8ef59e72dd864076eb355216f12440dd2afdde82619f67350448d810e28f8"),
    "furo/assets/styles/content/_footnotes.sass": (856, "db27450fd713a61533c0268140d66faf41867c3ee04027c5e93aa83e5c795498"),
    "furo/assets/styles/content/_gui-labels.sass": (210, "02209394a1cb07ea71c926486c012f791c95f0322769e15ee109f9a822ee2566"),
    "furo/assets/styles/content/_images.sass": (571, "5b7303c387eced408c097c91c17f293c0567eb32a27fb245d724cc7db7eab200"),
    "furo/assets/styles/content/_index.sass": (279, "0fd612a04734ede7e234974372e2ff5ec75b5bc83c5c0978bde051142c239edd"),
    "furo/assets/styles/content/_indexes.sass": (312, "60fc97b6bea77acfe0e1b1d9720412cc2282bb03f29b8f94663427515be6a28c"),
    "furo/assets/styles/content/_lists.sass": (1090, "c934ece757d8ad26baabf5d01775ff51fef2e82c75bcc6bbc9ace76c466dcff5"),
    "furo/assets/styles/content/_math.sass": (320, "9ada1dd3604af5cf7acd42cc404b04b75f3b51d5c78b41f836833df7bee4d808"),
    "furo/assets/styles/content/_misc.sass": (1139, "5193a1e180c4d267ff4dd6e9aec95e1f0368e10d1b3e8e2add9d939d3cf7c9e7"),
    "furo/assets/styles/content/_rubrics.sass": (318, "bf17d6ce36a084a68f7c72d1df2635ccb194978c1c44c5b21f1631a0d6461fa4"),
    "furo/assets/styles/content/_sidebar.sass": (562, "1fe730be049b2800360ca2f04df38ea023bc04b779b771659b198fba026babbc"),
    "furo/assets/styles/content/_tables.sass": (966, "3340053bf78ddba1c00c3387c2c9dfb0f60c0ea57a97df3ec5eca28ea5b2e3ec"),
    "furo/assets/styles/content/_target.sass": (1927, "e9cb4517f16a86394a31c3136dffd4c2b6ee59583c74f048000332cd3438a41e"),
    "furo/assets/styles/extensions/_copybutton.sass": (907, "e2e5cfc22d17ec498548b174177b52acb55dead4ef8ebe6030b9036016316ef4"),
    "furo/assets/styles/extensions/_index.sass": (120, "219f6b7f42b8bf37d603f3118658236b7310b82d7a259b4c14a6adf3ff115312"),
    "furo/assets/styles/extensions/_readthedocs.sass": (1774, "724bf0160b8d2a9012a8a7f6088ef2ff311bf466d69761aebe727487fd56b272"),
    "furo/assets/styles/extensions/_sphinx-design.sass": (1895, "a172b070cef8d95c865efd79a39a0c9e66f1b4bc2af478a313145a9713e214b5"),
    "furo/assets/styles/extensions/_sphinx-inline-tabs.sass": (832, "b4613229717ae47d22c075e8490b0da3d9e6e091c016f8b24e2144907c00278b"),
    "furo/assets/styles/extensions/_sphinx-panels.sass": (604, "649cb99b8791010924653a1e3e9861177a764123473fe20b5604f5598498fa7d"),
    "furo/assets/styles/furo-extensions.sass": (21, "9173626f6a40a1c99f56f7f86c7b3774aa7f791f117e418d9c2b1698e5068c30"),
    "furo/assets/styles/furo.sass": (136, "823581b4620abaf9cbe9ac848807a2ac01ecbc37131f1ac47ec299491b7c7f29"),
    "furo/assets/styles/variables/_admonitions.scss": (1386, "6c028d0b654930e31606c0b73816e4ddf0d8306a12267dfa8b18ce2afa10b730"),
    "furo/assets/styles/variables/_colors.scss": (7251, "41c1c745060346b1c56318c0523ec1d20ef30de550f0a7774061347696a8a9f8"),
    "furo/assets/styles/variables/_fonts.scss": (1411, "59ae70f5f9d0fcdf26e3a33506597016c52d1c0ed956508751ae8cc4868954bd"),
    "furo/assets/styles/variables/_icons.scss": (3396, "9a625142cbc0bc56460dac055127fbbbfadbbc7bb7cbfe0a7ab4db780e7dc55e"),
    "furo/assets/styles/variables/_index.sass": (177, "e6284126282307b1a1ceebfc5c9d23b3bbc924da88ede7fb1a3ef52a729e010b"),
    "furo/assets/styles/variables/_layout.scss": (458, "1a243c122ec85db91a0c4f1677673e94d29536785f9a04ea984f138ecfa5672d"),
    "furo/assets/styles/variables/_spacing.scss": (1211, "f44f33a993f470b379ffba973c2f622b747f04219f3afcff2590bfc60607ad6a"),
    "furo/navigation.py": (2831, "46402848d42113391afe151fcb9ce8c9f55030acfee5f2c4bf6eb9a807abd7bb"),
    "furo/sphinxext.py": (2425, "1ac0f75b9d97bd6954a7d92437d66f5ac0811647cebabc1b4e44ffed635b0c4b"),
    "furo/theme/furo/base.html": (3245, "968339b1a3e55f5c792cd43dcaa0f064719110fe0ee8632f16a6822c94507358"),
    "furo/theme/furo/components/edit-this-page.html": (993, "32160f44926e19f774bbac9a7bc14214ddac748aa8306a7ff72e11c1171be77a"),
    "furo/theme/furo/components/view-this-page.html": (1006, "bf0edb862d94275f53bcf8b096fc0aa40cafca23ad477a7b6e3989091bdaf28a"),
    "furo/theme/furo/domainindex.html": (1792, "80cdeb273c00f8be4a1b485a6b658f73304f3e539c10fd07c38fe26b2908e9c5"),
    "furo/theme/furo/genindex.html": (1683, "e8de4997983f6996d0682dc22ec86671efa2a324c3ca844a0cb2d8d1c62622c3"),
    "furo/theme/furo/globaltoc.html": (298, "f812a11f9b19d61fcb2818101424e89a17560c010eae6f230c295e02597df42a"),
    "furo/theme/furo/layout.html": (506, "b084adb1136a21a801a501716289203d8dbe64234c68903fbf6ecc8aa4d6d592"),
    "furo/theme/furo/localtoc.html": (297, "a0fc86ebd10113b474815c2eab2bc46b3f7e724aae33976556d547baf0d32029"),
    "furo/theme/furo/page.html": (12444, "3d0b1e78e95c2417ead8da0eff4c9997d8680f8196fc46a328e81dca295d16f9"),
    "furo/theme/furo/partials/_head_css_variables.html": (870, "0a75ba610a57fa465091aa40b3d045bd2c47e08aedc51b83981644cf549d63e4"),
    "furo/theme/furo/partials/icons.html": (6330, "011252a5f029c5469b589debeceff03b3c6212bf7fb692d8d11dc1b7cb6c14bf"),
    "furo/theme/furo/search.html": (861, "95755b01ed85cf27bb1e6dc82647e96b7e7283c29be7fb5b187ed765fcf15f71"),
    "furo/theme/furo/sidebar/brand.html": (1076, "f469de2a0e77c2dbdb95958b414fdd36e085c2e743003ce17c37027d59cdc239"),
    "furo/theme/furo/sidebar/ethical-ads.html": (267, "f7c1a53689361074ea4097408e9f1cee3834af1b05e06186cf40824a7df47c33"),
    "furo/theme/furo/sidebar/navigation.html": (63, "276383fe9ec54080f23e9150e0289c073f9733c00a5ce6b06c1ac9643d285e2b"),
    "furo/theme/furo/sidebar/rtd-versions.html": (1174, "e524ba4bbe21f768e22e3997219d9241ab4d748f12a5f790a234a67b10399463"),
    "furo/theme/furo/sidebar/scroll-end.html": (7, "5eb51658c4ff035fecdeb4c269efb2d33a67ac9928a2a6c2d2d9a14630a0ec35"),
    "furo/theme/furo/sidebar/scroll-start.html": (29, "08f24167d446e111da7f87640ecba2fab01ddf4c0a95137e7412551a54de8bec"),
    "furo/theme/furo/sidebar/search.html": (350, "d0cc1cbc08f56a5473af0c083edf2232554f068de2f3e73f304f4be946060887"),
    "furo/theme/furo/sidebar/variant-selector.html": (1171, "96ff94076a739d0bb90ac14c361209ba3f53d28590ebbc6731423d6632b20b99"),
    "furo/theme/furo/static/.gitignore": (112, "3c91b9ad388c85787f1a0560bd259a179ad5566937722b0cf3016a09335b3b28"),
    "furo/theme/furo/static/scripts/furo-extensions.js": (0, "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"),
    "furo/theme/furo/static/scripts/furo.js": (5319, "4ff61921d6560078ea458d40d54286767c3cac9d53f02795a189a418b1c3eed9"),
    "furo/theme/furo/static/scripts/furo.js.LICENSE.txt": (187, "3eba718c98abe0ad8dd4401edc9ddfabf979f9bb9b8ac446460b61b03694970d"),
    "furo/theme/furo/static/scripts/furo.js.map": (28762, "3fe7ce370104d6774687fa251c2d90d5442c9e93483843b433123154bbd2cc3b"),
    "furo/theme/furo/static/styles/furo-extensions.css": (5519, "76989c00796f8808a63b839007e5d31dd0368c0d3d16482f0a5c2fd6a3c48392"),
    "furo/theme/furo/static/styles/furo-extensions.css.map": (7762, "b7b578ce9d52a32c205df1ae973f68efeb2f64c05352d77a156470c7a8a2a254"),
    "furo/theme/furo/static/styles/furo.css": (51069, "3932765ee1695b20119162fdd5d2811b01456b9cb3cd07a51cdc81270d83871f"),
    "furo/theme/furo/static/styles/furo.css.map": (76649, "8ee58ebc609d30feeb6c08145d20405286d96aced8a7e276075b5a84c2752ce8"),
    "furo/theme/furo/theme.conf": (615, "739c64808c90918dedc7b2bf3e679c06f4dc7bc8b7c2cdcfad72fb323bda8d09"),
}


def verify(root):
    failures = []
    for rel, (size, digest) in PINNED_FILES.items():
        path = os.path.join(root, *rel.split("/"))
        if not os.path.isfile(path):
            failures.append(f"MISSING  {rel}")
            continue
        data = open(path, "rb").read()
        if len(data) != size:
            failures.append(f"SIZE     {rel}: got {len(data)}, pinned {size}")
            continue
        actual = hashlib.sha256(data).hexdigest()
        if actual != digest:
            failures.append(f"SHA256   {rel}: got {actual}, pinned {digest}")
    for dirpath, _dirnames, filenames in os.walk(root):
        # conan 在 source_folder 内创建 build-release 构建目录(生成器脚本等),
        # 不属于 wheel 清单,剪枝后再扫 EXTRA
        _dirnames[:] = [d for d in _dirnames if d not in ("build-release", "build", "test_package")]
        for name in filenames:
            full = os.path.join(dirpath, name)
            rel = os.path.relpath(full, root).replace(os.sep, "/")
            if rel not in PINNED_FILES:
                failures.append(f"EXTRA    {rel}")
    return failures


def locate_package_root(argument_value):
    # 安装布局把 wheel 载荷嵌在 share/python/site-packages 下(CI 66151 实测
    # 包根直扫 = 173 EXTRA):候选含该前缀与 site-packages 本身,以
    # furo/__init__.py 为判据。
    root = os.path.abspath(argument_value)
    cands = [
        os.path.join(root, "share", "python", "site-packages"),
        root,
    ]
    for cand in cands:
        if os.path.isfile(os.path.join(cand, "furo", "__init__.py")):
            return cand
    raise SystemExit(
        f"furo theme tree not found under {root!r} "
        "(looked for share/python/site-packages/furo and ./furo)")


def main():
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--source-root")
    group.add_argument("--package-root")
    args = parser.parse_args()
    if args.package_root:
        root = locate_package_root(args.package_root)
    else:
        root = os.path.abspath(args.source_root)
    failures = verify(root)
    checked = len(PINNED_FILES)
    if failures:
        for line in failures:
            print(f"FAIL {line}", file=sys.stderr)
        raise SystemExit(f"furo integrity check failed: {len(failures)} problem(s) out of {checked} pinned files")
    print(f"furo integrity OK: {checked}/{checked} pinned files byte-identical ({root})")


if __name__ == "__main__":
    main()
