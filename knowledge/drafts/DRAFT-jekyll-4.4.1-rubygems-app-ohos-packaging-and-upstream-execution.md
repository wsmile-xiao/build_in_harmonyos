# DRAFT-jekyll-4.4.1-rubygems-app-ohos-packaging-and-upstream-execution

> 草稿知识项（draft）。**不预占正式 E 编号，禁止直接 promote**。
> 触发事件：`jekyll 4.4.1`（task #7601）。同族先例：`pandocomatic/2.2.0`、`gel/0.3.0`、`msfconsole/4.11.7`、`passenger/6.1.8`。

## 使用说明（何时用）

当要适配的软件**主体是 Ruby**（以 RubyGems 分发：CLI 工具或应用），且出现下面任一症状时用本文：

1. `ruby/3.4.10`（或任意 ruby）在本仓已适配但**未发布**到 ohpcd → 配方 `tool_requires("ruby/...)` 直接卡在依赖解析；
2. 构建期想靠 `bundle install` 解析依赖 → 结果随上游发布漂移、CI 偶发失败；
3. 依赖里有 C 扩展 / 预编译平台 gem，装到设备上却报 `Could not find '<gem>' (~> x.y) among N total gem(s)` 或 `cannot load such file -- <gem>`；
4. 想跑上游测试，但上游测试入口 require 了运行期闭包之外的开发期 gem；
5. `gem build` 上游 fixture 的 gemspec 直接 `Gem::InvalidSpecificationException`；
6. 某些上游用例会联网或挂死（例如 `jekyll new` 会执行 `bundle install`）。

## 适用范围

- 交付主体是 Ruby 代码、以 gem 分发的软件（`package_type = application`）；
- 目标平台是 OHOS（musl/aarch64），但本范式对任何"Ruby 报出的平台字符串与预编译 gem 名字不一致"的目标同样成立；
- 需要在上游测试层面给出真实执行证据（rule4 场景）。

不适用：主体是 C/C++ 而只有少量 Ruby 绑定的库（那属于 gem 的 C 扩展编译问题，见 E312/E313）。

## 输入输出定义

| 项 | 内容 |
|---|---|
| 输入 | 上游 gem 名 + 版本；上游测试入口目录（如 `test/`、`features/`）；目标平台（OHOS/armv8 或构建机平台） |
| 输出 | `conandata.yml`：每个 `.gem` 的 url + sha256（含预编译变体）+ 上游 tag archive；`conanfile.py`：系统 Ruby + `--ignore-dependencies` 安装 + 上游测试执行；包内 `gems/`（gem home）+ `share/gem/`（可复现副本） |
| 关键中间物 | 离线解析出的闭包清单（每个 gem 的每条约束都交叉校验过）；重标后的 specification（目录名/spec 名/`s.platform`/`# stub:` 行四处一致） |
| 判据 | ① 每个源 url 都能下载且 sha256 命中；② `conan create` 里 `gem install` 全部成功；③ 上游测试真的跑起来并有逐用例计数（不是 0/N）；④ `test_package` 用真实最小工程验证产物可用 |

## 示例（本案例实测）

`jekyll 4.4.1`（本地 x86_64 全流程 `conan create` EXIT=0）：

```bash
# ① 离线解析闭包（rubygems.org API，BFS + 逐条约束交叉校验 → 0 冲突）
#    运行期 36 + 上游测试闭包 16 = 52 个 gem
# ② conandata 固定 url+sha256；对含 C 扩展的 gem 同时 vendor 预编译变体
#    nokogiri / ffi / google-protobuf / sass-embedded 都有 aarch64-linux-musl 变体
# ③ 用系统 Ruby 安装（构建期不解析依赖）
GEM_HOME="$gem_home" GEM_PATH="$gem_home" \
  /data/service/hnp/bin/gem install --local "$f" \
  --install-dir "$gem_home" --no-document --ignore-dependencies

# ④ 预编译变体必须重标 gem 身份——四处都要改，只改 s.platform 不够：
#    gems/<name>-<ver>-<plat>/  ->  gems/<name>-<ver>/
#    specifications/<name>-<ver>-<plat>.gemspec -> <name>-<ver>.gemspec
#    s.platform = Gem::Platform::RUBY
#    # stub: <name> <ver> <plat> lib  ->  # stub: <name> <ver> ruby lib
#    （漏改 stub 行：require "nokogiri" 失败，但 gem "nokogiri"; require 成功）
#    实测对照：
#      ruby -e 'require "nokogiri"'                     -> LoadError: cannot load such file -- nokogiri
#      ruby -e 'gem "nokogiri"; require "nokogiri"'     -> 1.19.4
#      ruby -e 'p Gem::Specification.find_by_path("nokogiri")'  -> nil（修好后为 nokogiri-1.19.4）

# ⑤ 上游测试入口的隐藏硬依赖：jekyll 的 test/helper.rb 无条件
#    require "nokogiri" + minitest-reporters/minitest-profile/rspec-mocks/
#    shoulda-context/simplecov → 这些必须一起 vendor
# ⑥ 上游测试要用 tag archive：jekyll 的 gemspec 只把 (exe|lib|rubocop)/ 打进 gem，
#    jekyll-4.4.1.gem 里没有 test/
# ⑦ path gem fixture（test/fixtures/test-theme*）不能用 gem build：
#    gem build test-theme.gemspec
#      -> Gem::InvalidSpecificationException: ["lib/example.rb"] are not files
#    按 bundler 的 path gem 语义手工放置：目录复制到 gems/<name>-0.1.0/ + 最小 spec
# ⑧ 逐用例超时（conan 的 self.run 不支持超时，用 subprocess.run(timeout=300)）：
#    test_new_command.rb 会执行 bundle install（联网）而挂死

# 结果：45 个上游 Minitest 文件 / 993 个用例 / 963 通过 = 97.0%
conan create archives/j/jekyll/4.4.1 -pr:h/-pr:b=default -c tools.build:skip_test=False   # EXIT=0
```

## 查重差异表（与最相近条目逐条比）

| 条目 | 它讲什么 | 本条目差异 |
|---|---|---|
| `E312` | 某项目（groonga 系）里 gem/bundle 的测试链与 run-test.sh | 那条是"单个项目的 gem 测试怎么跑"；本条是"Ruby 应用打包 + 上游测试执行"的**范式**，含平台 gem 重标这类 RubyGems 内部机制 |
| `E313` | gem 的 C 扩展编译（msgpack, extconf, stdckdint, musl） | 那条解决"扩展编不过"；本条解决"扩展/预编译二进制**装得上但要能激活**"，以及闭包自证与上游测试入口 |
| `DRAFT-ruby-minitest-legacy-spelling` | Ruby 侧一个命名拼写坑 | 无重叠 |
| `E108` / `E174` | OHOS 缺 GNU `install` 命令 | 无重叠（相似度 0.07 属噪声） |

## 验证证据

- `tasks/jekyll-4.4.1-2026-09-30/logs/001-gem-closure.log`：闭包解析（36）
- `002-gem-closure-verify.log`：逐条约束来源与交叉校验（0 冲突）
- `003-full-closure.log`：含测试闭包的 52 个 gem + musl 预编译可用性
- `004-gem-download-verify.log`：**57/57 源下载并 sha256 命中**
- `005-upstream-tests.log`：逐文件 runs/assertions/failures/errors（993 / 963 通过）
- `006-local-create.log`：完整 `conan create`（EXIT=0，消费者测试渲染出站点）

## 平台侧修法建议（若有）

- 若制品仓能发布 `ruby`（`archives/r/ruby/3.4.10` 已在仓内），本类问题的一半会消失：可用 `tool_requires("ruby/...)` 精确控制解释器版本，而不是依赖构建环境自带的系统 Ruby；
- RubyGems 以 spec 记录的 platform 严格匹配来激活 gem，这对"目标 libc 与 gem 平台名不一致"（OHOS musl 是典型）是长期摩擦点；在适配层重标 identity 是可行解，但建议在 notes/manifest 里显式记录"用了哪个平台的预编译二进制"。
