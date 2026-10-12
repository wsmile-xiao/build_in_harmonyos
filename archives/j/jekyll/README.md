# jekyll HarmonyOS PC 适配

本目录包含 jekyll 4.4.1 的 HarmonyOS PC Conan 适配。jekyll 是纯 Ruby 的静态站点
生成器：配方把上游 gem 与它的完整依赖闭包（52 个 gem，全部 url+sha256 固定）装进
包内 gem home，用 HarmonyOS PC 构建环境自带的系统 Ruby（HNP）执行安装，并在
`conan create` 里跑上游 Minitest 测试（45 个文件 / 993 个用例）。

## 为什么不用 conan 的 ruby 包

`ruby/3.4.10` 已在本仓适配（`archives/r/ruby/3.4.10`）但**未发布**到 ohpcd 制品仓；
本仓对 Ruby 软件的既有范式是使用构建环境自带的系统 Ruby（`/data/service/hnp/bin/ruby`），
见 `archives/p/pandocomatic/2.2.0`（注释里明确记录了这一事实）、`archives/g/gel/0.3.0`、
`archives/m/msfconsole/4.11.7`、`archives/p/passenger/6.1.8`。

## 源码形态

同时使用两种上游产物，二者用途不同：

- **RubyGem**（`jekyll-4.4.1.gem`）与 52 个依赖 gem：用于安装交付；
- **GitHub tag archive**（`v4.4.1.tar.gz`）：jekyll 的 gemspec 只把 `(exe|lib|rubocop)/`
  打进 gem，**gem 里没有 `test/`**，所以上游测试必须用 tag archive。

详见 `4.4.1/notes.md`。
