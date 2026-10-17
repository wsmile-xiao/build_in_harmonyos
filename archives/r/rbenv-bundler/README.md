# rbenv-bundler

An rbenv plugin that makes shims aware of bundle installation paths.

## Description

rbenv-bundler is a plugin for [rbenv](https://github.com/rbenv/rbenv) that allows rbenv shims to automatically use the correct bundler-installed gem executables. When enabled, running `bundle exec` is no longer necessary — rbenv will automatically pick up the correct gem executables from your project's bundle.

## Usage

```bash
# Enable the plugin
rbenv bundler on

# Disable the plugin
rbenv bundler off
```

## Dependencies

- [rbenv](https://github.com/rbenv/rbenv)
- Ruby 1.8.7+ with the Bundler gem

## License

Apache License 2.0
