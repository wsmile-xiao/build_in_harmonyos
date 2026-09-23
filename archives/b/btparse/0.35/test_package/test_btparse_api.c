/* test_btparse_api.c — btparse 0.35 test_package 消费者测试.
 *
 * 通过公共 API (btparse.h) 实测 5 组能力, 共 18 项断言:
 *   1. bt_parse_entry_s 字符串解析 (AST/metatype/type/key)
 *   2. bt_next_field 字段遍历
 *   3. bt_postprocess_entry/bt_postprocess_field/bt_next_value 后处理取值
 *   4. bt_split_name/bt_format_name 姓名切分与格式化
 *   5. bt_add_macro_text/bt_macro_text/bt_delete_macro 宏管理
 * 任一断言失败以退出码 1 结束, 使 conan test_package 失败。
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "btparse.h"

static int total = 0;
static int failed = 0;

static void check(int cond, const char *what)
{
   total++;
   if (!cond)
     {
      failed++;
      printf("  FAIL #%d: %s\n", total, what);
     }
}

int main(void)
{
   boolean status = FALSE;
   char entry_text[] =
      "@article{cruz2026,\n"
      "  author = \"de la Cruz, Maria and Smith, John Paul\",\n"
      "  title = \"BibTeX Parsing on {HarmonyOS} PC\",\n"
      "  year = 2026\n"
      "}\n";
   /* bt_split_list 内部复制字符串 (items 指向副本), 无需可写副本 */
   char names_text[] = "de la Cruz, Maria and Smith, John Paul";

   bt_initialize();

   /* 1. 字符串条目解析 */
   AST *entry = bt_parse_entry_s(entry_text, "test.bib", 1, BTO_MINIMAL, &status);
   check(entry != NULL, "bt_parse_entry_s 返回 AST");
   check(status == TRUE, "解析状态为 TRUE");
   check(bt_entry_metatype(entry) == BTE_REGULAR, "metatype 为 BTE_REGULAR");
   check(bt_entry_type(entry) != NULL && strcmp(bt_entry_type(entry), "article") == 0,
         "entry type = article");
   check(bt_entry_key(entry) != NULL && strcmp(bt_entry_key(entry), "cruz2026") == 0,
         "entry key = cruz2026");

   /* 2. 字段遍历 */
   char *fname = NULL;
   AST *field;
   int nfields = 0, has_author = 0, has_title = 0, has_year = 0;
   for (field = bt_next_field(entry, NULL, &fname); field;
        field = bt_next_field(entry, field, &fname))
     {
      nfields++;
      if (strcmp(fname, "author") == 0) has_author = 1;
      if (strcmp(fname, "title") == 0)  has_title = 1;
      if (strcmp(fname, "year") == 0)
        {
         bt_nodetype vtype;
         char *vtext = NULL;
         AST *value = bt_next_value(field, NULL, &vtype, &vtext);
         has_year = 1;
         /* BTO_MINIMAL 下 year 值节点文本即为 "2026" (实测 nodetype 为 BTAST_STRING,
          * 节点类型枚举非稳定 API 契约, 只断言取值行为) */
         check(value != NULL && vtext != NULL && strcmp(vtext, "2026") == 0,
               "year 值 = 2026");
        }
     }
   check(nfields == 3, "字段数 = 3");
   check(has_author, "author 字段存在");
   check(has_title, "title 字段存在");
   check(has_year, "year 字段存在");

   /* 3. 后处理与取值 */
   bt_postprocess_entry(entry, BTO_FULL);
   for (field = bt_next_field(entry, NULL, &fname); field;
        field = bt_next_field(entry, field, &fname))
     {
      if (strcmp(fname, "year") == 0)
        {
         bt_nodetype vtype;
         char *vtext = NULL;
         AST *value = bt_next_value(field, NULL, &vtype, &vtext);
         check(value != NULL && vtext != NULL && strcmp(vtext, "2026") == 0,
               "后处理后 year 值仍为 2026");
        }
        if (strcmp(fname, "title") == 0)
        {
         char *ptext = bt_postprocess_field(field, BTO_FULL, FALSE);
         check(ptext != NULL && strstr(ptext, "HarmonyOS") != NULL,
               "title 后处理保留 HarmonyOS 字样");
         if (ptext)
             free(ptext);
        }
      }

   /* 4. 姓名切分与格式化 (对齐上游 dumpnames.c: 分隔符为 "and") */
   bt_stringlist *namelist = bt_split_list(names_text, "and", "test.bib", 1, "names");
   check(namelist != NULL && namelist->num_items == 2, "按 and 切分出 2 个姓名");
   bt_name_format *fmt = bt_create_name_format("fvl", FALSE);
   check(fmt != NULL, "创建姓名格式 fvl");
   if (namelist != NULL && namelist->num_items == 2 && fmt != NULL)
     {
      bt_name *nm = bt_split_name(namelist->items[0], NULL, 0, 0);
      check(nm != NULL, "bt_split_name 切分姓名部件");
      if (nm)
        {
         char *formatted = bt_format_name(nm, fmt);
         /* 默认 fvl 格式 von/last 之间为 BTJ_MAYTIE, 输出含 tie 字符 "~" */
         check(formatted != NULL && strcmp(formatted, "Maria de~la Cruz") == 0,
               "格式化 [0] = Maria de~la Cruz");
         if (formatted)
             free(formatted);
         bt_free_name(nm);
        }
     }
   if (fmt)
       bt_free_name_format(fmt);
   if (namelist)
       bt_free_list(namelist);

   /* 5. 宏管理 */
   bt_add_macro_text("ieeetool", "IEEE Transactions on Tools", "test.bib", 1);
   {
      char *text = bt_macro_text("ieeetool", "test.bib", 1);
      check(text != NULL && strcmp(text, "IEEE Transactions on Tools") == 0,
            "宏定义后可读回");
   }
   bt_delete_macro("ieeetool");
   check(bt_macro_text("ieeetool", "test.bib", 1) == NULL, "宏删除后不可读");

   bt_free_ast(entry);
   bt_cleanup();

   printf("btparse consumer test: TOTAL=%d PASS=%d FAIL=%d\n",
          total, total - failed, failed);
   return failed ? 1 : 0;
}
