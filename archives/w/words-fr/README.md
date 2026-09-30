# words-fr 2.1

> GNU Aspell French fr-60 word list packaged as architecture-independent UTF-8 data.

## 简介

This package converts the default French fr-60 dictionary from GNU Aspell French 0.50-3 into a normalized, deduplicated UTF-8 word list. It includes the fr-40 and fr-60 additions and does not include optional fr-80 or Swiss lists.

The Conan package installs share/dict/words-fr and exports its path through WORDS_FR_FILE in Conan build and run environments. The upstream Copyright and COPYING files are installed under licenses/.

## OHOS 适配要点

The package contains data only and is architecture independent. The Conan consumer verifies the packaged resource on an OHOS/armv8 profile; its C++ consumer is compiled for HarmonyOS AArch64 and run natively on the supplied AArch64 HarmonyOS runner.

## 依赖

| 依赖 | 版本 | 说明 |
|------|------|------|
| Conan | 2.x | Package and consumer test workflow |
| Python | 3.x | Decode and normalize the upstream CWL dictionaries |

## 功能验证

Run this from the repository root:

    conan create archives/w/words-fr/2.1 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=default --build=missing

## 参考

- [GNU Aspell French dictionary](https://ftp.gnu.org/gnu/aspell/dict/fr/)
- [GNU Aspell](https://aspell.net/)
