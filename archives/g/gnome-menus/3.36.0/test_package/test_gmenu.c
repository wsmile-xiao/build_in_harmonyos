/* test_gmenu.c — gnome-menus 3.36.0 test_package 实质测试（消费者视角，R34）。
 *
 * 在沙箱 XDG 目录（临时目录）里构造一份可解析的 applications.menu +
 * 应用条目 + 子菜单目录文件，完整走通 GMenuTree 的解析/解析后遍历路径
 * （与 alacarte 使用同一 API 面），并对每一步做真实断言：
 * 任何断言失败 → 打印 [FAIL] 且以非零码退出 → conan create 失败。
 *
 * 覆盖的 API（libgnome-menu-3 导出符号，链接失败即暴露 ABI 问题）：
 *   gmenu_tree_new / gmenu_tree_load_sync / gmenu_tree_get_canonical_menu_path
 *   gmenu_tree_get_root_directory / gmenu_tree_directory_get_name
 *   gmenu_tree_directory_get_menu_id / gmenu_tree_directory_iter / gmenu_tree_iter_next
 *   gmenu_tree_iter_get_directory / gmenu_tree_iter_get_entry
 *   gmenu_tree_entry_get_app_info / gmenu_tree_entry_get_desktop_file_id
 *   gmenu_tree_get_entry_by_id / gmenu_tree_item_unref
 */
#define GMENU_I_KNOW_THIS_IS_UNSTABLE 1
#include <gnome-menus-3.0/gmenu-tree.h>
#include <glib-object.h>
#include <glib/gstdio.h>
#include <gio/gio.h>
#include <stdio.h>

static unsigned assertions = 0;
static unsigned failures = 0;

#define CHECK(cond, ...)                                  \
    do {                                                  \
        ++assertions;                                     \
        if (cond) {                                       \
            printf("[PASS] ");                            \
            printf(__VA_ARGS__);                          \
            printf("\n");                                 \
        } else {                                          \
            printf("[FAIL] ");                            \
            printf(__VA_ARGS__);                          \
            printf("\n");                                 \
            ++failures;                                   \
        }                                                 \
        fflush(stdout);                                   \
    } while (0)

/* 最小可用菜单：根菜单 Applications 下含一个 Accessories 子菜单，
 * 用 <DefaultAppDirs/> / <DefaultDirectoryDirs/> 让条目目录来自 XDG_DATA_DIRS
 * （测试里指向沙箱），从而条目集合确定、可断言。 */
static const char *MENU_XML =
    "<?xml version=\"1.0\"?>\n"
    "<Menu>\n"
    "  <Name>Applications</Name>\n"
    "  <DefaultAppDirs/>\n"
    "  <DefaultDirectoryDirs/>\n"
    "  <Menu>\n"
    "    <Name>Accessories</Name>\n"
    "    <Directory>ohos-test.directory</Directory>\n"
    "    <Include>\n"
    "      <Category>Utility</Category>\n"
    "    </Include>\n"
    "  </Menu>\n"
    "</Menu>\n";

static const char *APP_DESKTOP =
    "[Desktop Entry]\n"
    "Type=Application\n"
    "Name=OHOS Test App\n"
    "Exec=/bin/true\n"
    "Icon=ohos-test\n"
    "Categories=Utility;\n";

static const char *DIR_DESKTOP =
    "[Desktop Entry]\n"
    "Type=Directory\n"
    "Name=Accessories\n"
    "Icon=utilities-terminal\n";

static gboolean
write_text(const char *path, const char *text)
{
    GError *error = NULL;
    if (!g_file_set_contents(path, text, -1, &error)) {
        fprintf(stderr, "cannot write %s: %s\n", path,
                error ? error->message : "unknown");
        g_clear_error(&error);
        return FALSE;
    }
    return TRUE;
}

/* 在 dir 下写 name 文件（内部管理路径内存，避免调用方重复释放） */
static gboolean
write_in_dir(const char *dir, const char *name, const char *text)
{
    gchar *path = g_build_filename(dir, name, NULL);
    gboolean ok = write_text(path, text);
    g_free(path);
    return ok;
}

int
main(void)
{
    GError *error = NULL;
    GMenuTree *tree = NULL;
    GMenuTreeDirectory *root = NULL;
    GMenuTreeIter *iter = NULL;
    gchar *tmp = NULL, *cfg = NULL, *dat = NULL, *menus = NULL, *apps = NULL;
    gchar *dirs = NULL;
    unsigned n_subdirs = 0, n_root_entries = 0, n_entries = 0;
    int rc = 1;

    tmp = g_dir_make_tmp("gmenu-test-XXXXXX", &error);
    if (tmp == NULL) {
        fprintf(stderr, "g_dir_make_tmp failed: %s\n",
                error ? error->message : "unknown");
        g_clear_error(&error);
        return 1;
    }
    CHECK(TRUE, "sandbox temp dir created: %s", tmp);

    /* 隔离 XDG 搜索路径：只留沙箱目录，条目集合因此确定。
     * 必须在任何 GLib XDG 目录查询前设置（g_get_*_dir 有进程内缓存）。 */
    cfg = g_build_filename(tmp, "config", NULL);
    dat = g_build_filename(tmp, "data", NULL);
    g_setenv("XDG_CONFIG_HOME", cfg, TRUE);
    g_setenv("XDG_CONFIG_DIRS", cfg, TRUE);
    g_setenv("XDG_DATA_HOME", dat, TRUE);
    g_setenv("XDG_DATA_DIRS", dat, TRUE);
    g_unsetenv("XDG_MENU_PREFIX");

    menus = g_build_filename(cfg, "menus", NULL);
    apps = g_build_filename(dat, "applications", NULL);
    dirs = g_build_filename(dat, "desktop-directories", NULL);
    g_mkdir_with_parents(menus, 0755);
    g_mkdir_with_parents(apps, 0755);
    g_mkdir_with_parents(dirs, 0755);

    if (!write_in_dir(menus, "applications.menu", MENU_XML)) goto out;
    if (!write_in_dir(apps, "ohos-test-app.desktop", APP_DESKTOP)) goto out;
    if (!write_in_dir(dirs, "ohos-test.directory", DIR_DESKTOP)) goto out;

    CHECK(TRUE, "sandbox menu/apps/directories written under %s", tmp);

    /* ── 1. 菜单查找（XDG 解析路径）── */
    tree = gmenu_tree_new("applications.menu", GMENU_TREE_FLAGS_NONE);
    CHECK(tree != NULL, "gmenu_tree_new(\"applications.menu\") != NULL");
    if (tree == NULL) goto out;

    /* ── 2. 同步加载（解析 XML + 布局解析）── */
    if (!gmenu_tree_load_sync(tree, &error)) {
        CHECK(FALSE, "gmenu_tree_load_sync() == TRUE (error: %s)",
              error ? error->message : "unknown");
        goto out;
    }
    CHECK(TRUE, "gmenu_tree_load_sync() == TRUE");

    /* ── 3. 规范化路径落在沙箱内（证明走的是被测的 XDG 查找）── */
    {
        const char *canon = gmenu_tree_get_canonical_menu_path(tree);
        CHECK(canon != NULL && g_strstr_len(canon, -1, menus) != NULL,
              "canonical menu path inside sandbox: %s", canon ? canon : "(null)");
    }

    /* ── 4. 根目录 ── */
    root = gmenu_tree_get_root_directory(tree);
    CHECK(root != NULL, "gmenu_tree_get_root_directory() != NULL");
    if (root == NULL) goto out;

    CHECK(g_strcmp0(gmenu_tree_directory_get_name(root), "Applications") == 0,
          "root directory name == \"Applications\" (got \"%s\")",
          gmenu_tree_directory_get_name(root));
    CHECK(g_strcmp0(gmenu_tree_directory_get_menu_id(root), "Applications") == 0,
          "root menu id == \"Applications\" (got \"%s\")",
          gmenu_tree_directory_get_menu_id(root));

    /* ── 5. 遍历：子菜单 + 条目 ── */
    iter = gmenu_tree_directory_iter(root);
    CHECK(iter != NULL, "gmenu_tree_directory_iter(root) != NULL");
    if (iter == NULL) goto out;

    {
        GMenuTreeItemType type;
        while ((type = gmenu_tree_iter_next(iter)) != GMENU_TREE_ITEM_INVALID) {
            if (type == GMENU_TREE_ITEM_DIRECTORY) {
                GMenuTreeDirectory *sub = gmenu_tree_iter_get_directory(iter);
                ++n_subdirs;
                CHECK(sub != NULL, "iter yielded a submenu");
                if (sub == NULL) continue;
                CHECK(g_strcmp0(gmenu_tree_directory_get_name(sub),
                                "Accessories") == 0,
                      "submenu name == \"Accessories\" (got \"%s\")",
                      gmenu_tree_directory_get_name(sub));
                CHECK(gmenu_tree_directory_get_desktop_file_path(sub) != NULL,
                      "submenu .directory resolved: %s",
                      gmenu_tree_directory_get_desktop_file_path(sub));
                CHECK(g_strcmp0(gmenu_tree_directory_get_menu_id(sub),
                                "Accessories") == 0,
                      "submenu menu id == \"Accessories\" (got \"%s\")",
                      gmenu_tree_directory_get_menu_id(sub));

                /* 条目按 Include/<Category>Utility 归入本子菜单 → 在此遍历 */
                {
                    GMenuTreeIter *subiter = gmenu_tree_directory_iter(sub);
                    GMenuTreeItemType subtype;
                    CHECK(subiter != NULL, "gmenu_tree_directory_iter(submenu) != NULL");
                    while (subiter != NULL &&
                           (subtype = gmenu_tree_iter_next(subiter))
                               != GMENU_TREE_ITEM_INVALID) {
                        if (subtype == GMENU_TREE_ITEM_ENTRY) {
                            GMenuTreeEntry *entry =
                                gmenu_tree_iter_get_entry(subiter);
                            GDesktopAppInfo *ainfo;
                            ++n_entries;
                            CHECK(entry != NULL, "submenu iter yielded an entry");
                            if (entry == NULL) continue;
                            ainfo = gmenu_tree_entry_get_app_info(entry);
                            CHECK(ainfo != NULL, "entry GDesktopAppInfo != NULL");
                            if (ainfo != NULL) {
                                CHECK(g_strcmp0(
                                          g_app_info_get_name(G_APP_INFO(ainfo)),
                                          "OHOS Test App") == 0,
                                      "entry display name == \"OHOS Test App\" (got \"%s\")",
                                      g_app_info_get_name(G_APP_INFO(ainfo)));
                                CHECK(g_app_info_get_executable(
                                          G_APP_INFO(ainfo)) != NULL,
                                      "entry Exec resolved: %s",
                                      g_app_info_get_executable(G_APP_INFO(ainfo)));
                            }
                            CHECK(g_strcmp0(
                                      gmenu_tree_entry_get_desktop_file_id(entry),
                                      "ohos-test-app.desktop") == 0,
                                  "entry desktop file id == \"ohos-test-app.desktop\" (got \"%s\")",
                                  gmenu_tree_entry_get_desktop_file_id(entry));
                            gmenu_tree_item_unref(entry);
                        }
                    }
                    if (subiter != NULL) gmenu_tree_iter_unref(subiter);
                }
                gmenu_tree_item_unref(sub);
            } else if (type == GMENU_TREE_ITEM_ENTRY) {
                /* 条目不直接挂在根下（按 Include 规则归入 Accessories） */
                ++n_root_entries;
                gmenu_tree_item_unref(gmenu_tree_iter_get_entry(iter));
            }
        }
    }
    CHECK(n_subdirs == 1, "exactly 1 submenu in root (got %u)", n_subdirs);
    CHECK(n_root_entries == 0,
          "no entries directly under root (got %u)", n_root_entries);
    CHECK(n_entries == 1,
          "exactly 1 entry collected from Accessories submenu (got %u)", n_entries);
    gmenu_tree_iter_unref(iter);
    iter = NULL;

    /* ── 6. 按 id 直查条目（alacarte 的用法）── */
    {
        GMenuTreeEntry *byid =
            gmenu_tree_get_entry_by_id(tree, "ohos-test-app.desktop");
        CHECK(byid != NULL, "gmenu_tree_get_entry_by_id(\"ohos-test-app.desktop\") != NULL");
        if (byid != NULL) {
            CHECK(gmenu_tree_entry_get_app_info(byid) != NULL,
                  "entry-by-id has GDesktopAppInfo");
            gmenu_tree_item_unref(byid);
        }
    }

    /* ── 7. 二次读取路径稳定性（重复取根目录不崩、仍非 NULL）── */
    {
        GMenuTreeDirectory *root2 = gmenu_tree_get_root_directory(tree);
        CHECK(root2 != NULL, "gmenu_tree_get_root_directory() stable on re-read");
        if (root2 != NULL) gmenu_tree_item_unref(root2);
    }

    rc = (failures == 0) ? 0 : 1;

out:
    if (iter != NULL) gmenu_tree_iter_unref(iter);
    if (root != NULL) gmenu_tree_item_unref(root);
    if (tree != NULL) g_object_unref(tree);

    /* 清理沙箱（按文件→目录自底向上；失败忽略，临时目录由系统回收） */
    if (menus != NULL) {
        gchar *f = g_build_filename(menus, "applications.menu", NULL);
        g_remove(f);
        g_free(f);
    }
    if (apps != NULL) {
        gchar *f = g_build_filename(apps, "ohos-test-app.desktop", NULL);
        g_remove(f);
        g_free(f);
    }
    if (dirs != NULL) {
        gchar *f = g_build_filename(dirs, "ohos-test.directory", NULL);
        g_remove(f);
        g_free(f);
    }
    if (menus != NULL) { g_rmdir(menus); g_free(menus); }
    if (apps != NULL)  { g_rmdir(apps);  g_free(apps); }
    if (dirs != NULL)  { g_rmdir(dirs);  g_free(dirs); }
    if (cfg != NULL)   { g_rmdir(cfg);   g_free(cfg); }
    if (dat != NULL)   { g_rmdir(dat);   g_free(dat); }
    if (tmp != NULL)   { g_rmdir(tmp);   g_free(tmp); }
    g_clear_error(&error);

    printf("[SUMMARY] assertions=%u failures=%u\n", assertions, failures);
    if (rc == 0)
        printf("test_gmenu OK\n");
    else
        printf("test_gmenu FAILED\n");

    /* 便于 test_package 事后核验断言计数（CI 证据链）：设了 GMENU_TEST_LOG 就落盘 */
    {
        const char *log = g_getenv("GMENU_TEST_LOG");
        if (log != NULL && log[0] != '\0') {
            gchar *line = g_strdup_printf("[SUMMARY] assertions=%u failures=%u\n",
                                          assertions, failures);
            FILE *fp = fopen(log, "a");
            if (fp != NULL) {
                fputs(line, fp);
                fclose(fp);
            }
            g_free(line);
        }
    }
    return rc;
}
