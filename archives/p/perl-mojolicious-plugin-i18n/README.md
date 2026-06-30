# perl-mojolicious-plugin-i18n

Internationalization Plugin for Mojolicious.

## Description

Mojolicious::Plugin::I18N is an internationalization plugin for the Mojolicious web framework.
It provides localization support using I18N::LangTags for language detection.

Features:
- Multi-language translation via Locale::Maketext lexicons
- Automatic language detection from Accept-Language header
- URL-based language switching (e.g. /en/, /zh/)
- Host-based language detection
- Language fallback to default language

## Version

1.6

## Dependencies

- Perl >= 5.10.1
- Mojolicious >= 5 (tested with 9.42)
- I18N::LangTags >= 0.35 (tested with 0.45)

## Build

```bash
perl Makefile.PL PREFIX=$PREFIX
make
make test
make install
```

## OpenHarmony Adaptation

- **Build system**: perl (ExtUtils::MakeMaker)
- **Module type**: Pure Perl (no C/XS code)
- **Patches**: None required
- **SELinux**: No restrictions (pure Perl, no .so loading)
- **Build mode**: Mode B (manual, due to Mode A product detection limitation)

## Installation Verification

```bash
perl -MMojolicious::Plugin::I18N -e 'print $Mojolicious::Plugin::I18N::VERSION'
# Output: 1.6
```

## License

Artistic License 2.0
