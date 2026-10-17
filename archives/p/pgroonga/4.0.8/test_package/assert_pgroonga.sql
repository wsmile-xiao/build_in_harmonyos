-- assert_pgroonga.sql — pgroonga 4.0.8 在 OHOS aarch64 + PostgreSQL 18.3 上的行为断言
--
-- 由 test_package/conanfile.py 以
--   psql -X -q -v ON_ERROR_STOP=1 -h localhost -p <port> -U <role> -d postgres -f <本文件>
-- 驱动。任一断言失败即以 RAISE EXCEPTION 中止 → psql 非零退出 → conan create 失败。
-- 每通过一条断言会打印一行 "ASSERTION_OK: <id>" 供 CI 日志取证。
--
-- 覆盖点：扩展装载（$libdir 重定位）、C 函数可执行、groonga 引擎可达、
--         模块路径无绝对路径泄漏、v1/v2 全文检索、词项前缀、pgroonga_score、
--         jsonb、highlight_html、query_extract_keywords、tokenize、DROP+CREATE。

\set ON_ERROR_STOP on

-- A1 CREATE EXTENSION
--    这是本适配最核心的一条：Conan 打包的 postgresql/18.3 是 DESTDIR 可重定位安装，
--    configure 前缀为空，pgroonga.control 里的 module_pathname='$libdir/pgroonga'
--    无法靠编译期 pkglibdir 解析。PG 18 的 load_external_function 对「简单名」
--    （$libdir/ 后无再出现目录分隔符）会剥掉前缀并交给 dynamic_library_path 搜索，
--    因此只要 extension_control_path 指向本包 share/extension、
--    dynamic_library_path 指向本包 lib，扩展就能装载 —— 无需把产物装进 PG 目录。
CREATE EXTENSION pgroonga;
SELECT 'ASSERTION_OK: A1-create-extension' AS assertion;

-- A2 扩展版本与钉住的 4.0.8 一致
DO $$
DECLARE
  v text;
BEGIN
  SELECT extversion INTO v FROM pg_extension WHERE extname = 'pgroonga';
  IF v IS DISTINCT FROM '4.0.8' THEN
    RAISE EXCEPTION 'A2: pgroonga extversion = % (期望 4.0.8)', v;
  END IF;
END
$$;
SELECT 'ASSERTION_OK: A2-extversion' AS assertion;

-- A3 C 函数真实执行（证明模块已 dlopen 且符号解析成功）
--    pgroonga_escape(int4) → C 符号 pgroonga_escape_int4，纯标量、不碰索引/引擎，
--    因此与 A4 的「groonga 引擎可达」正交：这一条只证明 .so 装载 + 符号解析。
--    期望值取自上游 oracle expected/function/escape/int4.out（292929 → 292929）。
--    注：上游 4.0.8 没有 pgroonga_version()（data/pgroonga.sql 全文无 version
--    函数，只有 pg_extension.extversion 与 status 里的 libgroonga 版本号），
--    故版本一致性由 A2 / A4 承担。
DO $$
DECLARE
  v text;
BEGIN
  v := pgroonga_escape(292929::int4);
  IF v IS DISTINCT FROM '292929' THEN
    RAISE EXCEPTION 'A3: pgroonga_escape(292929::int4) = % (期望 292929)', v;
  END IF;
END
$$;
SELECT 'ASSERTION_OK: A3-c-function' AS assertion;

-- A4 groonga 引擎可达：pgroonga_command('status') 返回码 0 且携带 libgroonga 版本号
--    status 的返回体是 [[返回码, 时间戳, 耗时], {...}]，故取 r::jsonb -> 0 ->> 0。
--    注意必须走 jsonb 的 ->>（json -> n 仍返回 json，PG 里 json 不能直接 ::int，
--    实测 "cannot cast type json to integer"）；- 取元素、->> 取标量文本。
DO $$
DECLARE
  r text;
BEGIN
  r := pgroonga_command('status');
  IF (r::jsonb -> 0 ->> 0)::int <> 0 THEN
    RAISE EXCEPTION 'A4: groonga status 返回码 = %', r::jsonb -> 0 ->> 0;
  END IF;
  IF r !~ '[0-9]+\.[0-9]+\.[0-9]+' THEN
    RAISE EXCEPTION 'A4: groonga status 未携带版本号: %', r;
  END IF;
END
$$;
SELECT 'ASSERTION_OK: A4-groonga-status' AS assertion;

-- A5 路径卫生：所有 C 函数的 probin 必须仍是 $libdir/<module> 形式，
--    不得出现构建机/安装机的绝对路径（否则等于把不可重定位的路径烘焙进 catalog）。
DO $$
DECLARE
  n int;
BEGIN
  SELECT count(*) INTO n FROM pg_proc WHERE probin = '$libdir/pgroonga';
  IF n <= 0 THEN
    RAISE EXCEPTION 'A5: 不存在 probin = $libdir/pgroonga 的函数';
  END IF;
  SELECT count(*) INTO n
    FROM pg_proc
   WHERE probin LIKE '/%' OR probin LIKE '%/%/%';
  IF n <> 0 THEN
    RAISE EXCEPTION 'A5: 发现 % 个含绝对路径的 probin', n;
  END IF;
END
$$;
SELECT 'ASSERTION_OK: A5-module-pathname' AS assertion;

-- A6 全文检索端到端（v1 默认 opclass）
CREATE TABLE memos (
  id integer PRIMARY KEY,
  content text
);
INSERT INTO memos VALUES
  (1, 'PostgreSQL is a RDBMS.'),
  (2, 'Groonga is fast full text search engine.'),
  (3, 'PGroonga is a PostgreSQL extension that uses Groonga.');
CREATE INDEX memos_content_idx ON memos USING pgroonga (content);
DO $$
DECLARE
  ids integer[];
BEGIN
  SET LOCAL enable_seqscan = off;
  SELECT array_agg(id ORDER BY id) INTO ids
    FROM memos WHERE content &@ 'Groonga';
  IF ids IS DISTINCT FROM ARRAY[2, 3] THEN
    RAISE EXCEPTION 'A6: content &@ Groonga -> % (期望 {2,3})', ids;
  END IF;
END
$$;
SELECT 'ASSERTION_OK: A6-full-text-search' AS assertion;

-- A7 查询语法 &@~ 命中预期行
DO $$
DECLARE
  ids integer[];
BEGIN
  SET LOCAL enable_seqscan = off;
  SELECT array_agg(id ORDER BY id) INTO ids
    FROM memos WHERE content &@~ 'rdbms OR engine';
  IF ids IS DISTINCT FROM ARRAY[1, 2] THEN
    RAISE EXCEPTION 'A7: content &@~ -> % (期望 {1,2})', ids;
  END IF;
END
$$;
SELECT 'ASSERTION_OK: A7-query-syntax' AS assertion;

-- A8 pgroonga_score 打分函数（索引扫描路径下必须 > 0）
DO $$
DECLARE
  s double precision;
BEGIN
  SET LOCAL enable_seqscan = off;
  SELECT max(pgroonga_score(tableoid, ctid)) INTO s
    FROM memos WHERE content &@ 'Groonga';
  IF s IS NULL OR s <= 0 THEN
    RAISE EXCEPTION 'A8: pgroonga_score = %', s;
  END IF;
END
$$;
SELECT 'ASSERTION_OK: A8-score' AS assertion;

-- A9 词项检索 + 前缀匹配（v2 term search ops，&^）
CREATE TABLE tags (
  id integer,
  name text
);
INSERT INTO tags VALUES
  (1, 'PostgreSQL'),
  (2, 'Groonga'),
  (3, 'PGroonga'),
  (4, 'pglogical');
CREATE INDEX tags_name_idx ON tags
  USING pgroonga (name pgroonga_text_term_search_ops_v2);
DO $$
DECLARE
  names text[];
BEGIN
  SET LOCAL enable_seqscan = off;
  SELECT array_agg(name ORDER BY id) INTO names
    FROM tags WHERE name &^ 'PGro';
  IF names IS DISTINCT FROM ARRAY['PGroonga'] THEN
    RAISE EXCEPTION 'A9: name &^ PGro -> % (期望 {PGroonga})', names;
  END IF;
END
$$;
SELECT 'ASSERTION_OK: A9-term-search' AS assertion;

-- A10 jsonb 检索（v2 jsonb ops）
--     断言的是「jsonb 索引把 JSON 里的各个字符串值都纳入了检索」，因此查询词
--     取一个**作为独立词**出现在两行里、且在第三行里完全不存在**的词**：
--     'postgresql' 命中第 1 行（title 与 content 各一处）与第 3 行（content
--     的 "PGroonga is a PostgreSQL extension."），第 2 行不含该词。
--     这个取值与分词器无关：无论默认分词器是按词边界还是按 n-gram 切分，
--     "PostgreSQL" 都含该词而 "PGroonga"/"Groonga" 都不含，故结果稳定。
--     （反例：早先写 'groonga' 并期望 {2,3}，实测只回 {2}——第 3 行的
--     "PGroonga" 是一个不可再分的词，不含独立的 groonga，CI #62641 实测。）
CREATE TABLE docs (
  id integer,
  record jsonb
);
INSERT INTO docs VALUES
  (1, '{"title": "PostgreSQL", "content": "PostgreSQL is a RDBMS."}'),
  (2, '{"title": "Groonga", "content": "Groonga is fast full text search engine."}'),
  (3, '{"title": "PGroonga", "content": "PGroonga is a PostgreSQL extension."}');
CREATE INDEX docs_record_idx ON docs
  USING pgroonga (record pgroonga_jsonb_ops_v2);
DO $$
DECLARE
  ids integer[];
BEGIN
  SET LOCAL enable_seqscan = off;
  SELECT array_agg(id ORDER BY id) INTO ids
    FROM docs WHERE record &@ 'postgresql';
  SET LOCAL enable_seqscan = on;
  IF ids IS DISTINCT FROM ARRAY[1, 3] THEN
    RAISE EXCEPTION 'A10: record &@ postgresql -> % (期望 {1,3})', ids;
  END IF;
END
$$;
SELECT 'ASSERTION_OK: A10-jsonb' AS assertion;

-- A11 pgroonga_highlight_html：关键词高亮标签
DO $$
DECLARE
  v text;
BEGIN
  v := pgroonga_highlight_html('PostgreSQL is a RDBMS.', ARRAY['RDBMS']);
  IF position('<span class="keyword">RDBMS</span>' in v) = 0 THEN
    RAISE EXCEPTION 'A11: highlight_html = %', v;
  END IF;
END
$$;
SELECT 'ASSERTION_OK: A11-highlight-html' AS assertion;

-- A12 pgroonga_query_extract_keywords：查询语法解析
--     输入与 oracle 直接取自上游 function/query-extract-keywords/multiple
--     （'Groonga PostgreSQL' → {PostgreSQL,Groonga}，隐式 AND）。
DO $$
DECLARE
  k text[];
BEGIN
  k := pgroonga_query_extract_keywords('Groonga PostgreSQL');
  IF array_length(k, 1) IS DISTINCT FROM 2 THEN
    RAISE EXCEPTION 'A12: query_extract_keywords = %', k;
  END IF;
  IF NOT ('Groonga' = ANY(k) AND 'PostgreSQL' = ANY(k)) THEN
    RAISE EXCEPTION 'A12: query_extract_keywords 关键字集合 = %', k;
  END IF;
END
$$;
SELECT 'ASSERTION_OK: A12-extract-keywords' AS assertion;

-- A13 pgroonga_tokenize：groonga 内置分词器（TokenNgram，非插件）
--     ★ pgroonga_tokenize 返回的是 **token 数组**，不是 SETOF token：
--     直接 `SELECT count(*) FROM pgroonga_tokenize(...)` 数到的是「1 个数组值」
--     （CI #62668 实测 n = 1，旧断言 1 < 5 失败）。上游自己的写法是
--     `SELECT unnest(pgroonga_tokenize(...)) AS token`，见钉版
--     sql/function/tokenize/tokenizer.sql；必须先 unnest 展开再数。
--     期望值逐字取自钉版 oracle expected/function/tokenize/tokenizer.out：
--     'This is a pen.' + TokenNgram → 14 片，position 0..13，value 依次为
--     Th/hi/is/s␠/␠i/is/s␠/␠a/a␠/␠p/pe/en/n./.，首片 force_prefix_search=false。
DO $$
DECLARE
  n int;
  first_value text;
  first_prefix boolean;
BEGIN
  SELECT count(*) INTO n
    FROM (
      SELECT unnest(pgroonga_tokenize('This is a pen.',
                                      'tokenizer', 'TokenNgram')) AS token
    ) AS tokens;
  IF n <> 14 THEN
    RAISE EXCEPTION 'A13: TokenNgram 分词片数 = % (期望 14)', n;
  END IF;
  SELECT (token::jsonb) ->> 'value',
         ((token::jsonb) ->> 'force_prefix_search')::boolean
    INTO first_value, first_prefix
    FROM (
      SELECT unnest(pgroonga_tokenize('This is a pen.',
                                      'tokenizer', 'TokenNgram')) AS token
    ) AS tokens
   WHERE ((token::jsonb) ->> 'position')::int = 0;
  IF first_value IS DISTINCT FROM 'Th' OR first_prefix IS DISTINCT FROM false THEN
    RAISE EXCEPTION 'A13: 首片 = % (force_prefix_search = %)，期望 Th/false',
                    first_value, first_prefix;
  END IF;
END
$$;
SELECT 'ASSERTION_OK: A13-tokenize' AS assertion;

-- A14 可逆性：DROP EXTENSION CASCADE 后重新 CREATE 仍可用
--     （验证扩展不依赖任何一次性/不可重放的安装副作用）
DROP EXTENSION pgroonga CASCADE;
CREATE EXTENSION pgroonga;
DO $$
DECLARE
  v text;
BEGIN
  SELECT extversion INTO v FROM pg_extension WHERE extname = 'pgroonga';
  IF v IS DISTINCT FROM '4.0.8' THEN
    RAISE EXCEPTION 'A14: 重建后 extversion = %', v;
  END IF;
  IF pgroonga_escape(292929::int4) IS DISTINCT FROM '292929' THEN
    RAISE EXCEPTION 'A14: 重建后 pgroonga_escape(292929::int4) = %',
                    pgroonga_escape(292929::int4);
  END IF;
END
$$;
SELECT 'ASSERTION_OK: A14-recreate' AS assertion;
