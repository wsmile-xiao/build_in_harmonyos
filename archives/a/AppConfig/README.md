# AppConfig

AppConfig is a set of Perl modules for reading configuration files and
parsing command line arguments.

The package is distributed on CPAN as `AppConfig` and installs the
`AppConfig.pm` module plus its submodules under `AppConfig/`.

## Usage

```perl
use AppConfig qw(:argcount);

my $config = AppConfig->new(
    { GLOBAL => { ARGCOUNT => ARGCOUNT_ONE } },
    "name",
    "verbose" => { ARGCOUNT => ARGCOUNT_NONE },
);

$config->args(qw(--name demo --verbose));
print $config->name;
```

## OpenHarmony PC Notes

- Pure Perl module; no XS code and no native library output.
- Runtime is provided through the `perl/5.42.2` Conan package.
- Consumers receive `PERL5LIB` from the package runtime environment.
