/* Consumer test for the installed islamic-menus XDG data. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static int checks;
static int passed;

static int check(int condition, const char *message)
{
    ++checks;
    if (!condition) {
        fprintf(stderr, "FAIL: %s\n", message);
        return 0;
    }
    ++passed;
    return 1;
}

static char *join_path(const char *left, const char *right)
{
    size_t size = strlen(left) + strlen(right) + 2;
    char *result = (char *)malloc(size);
    if (result != NULL)
        snprintf(result, size, "%s/%s", left, right);
    return result;
}

static char *read_file(const char *path)
{
    FILE *file = fopen(path, "rb");
    long size;
    char *contents;
    if (file == NULL) {
        fprintf(stderr, "FAIL: cannot open packaged resource: %s\n", path);
        return NULL;
    }
    if (fseek(file, 0, SEEK_END) != 0 || (size = ftell(file)) < 0 ||
        fseek(file, 0, SEEK_SET) != 0) {
        fclose(file);
        fprintf(stderr, "FAIL: cannot size packaged resource: %s\n", path);
        return NULL;
    }
    contents = (char *)malloc((size_t)size + 1);
    if (contents == NULL) {
        fclose(file);
        fprintf(stderr, "FAIL: out of memory reading: %s\n", path);
        return NULL;
    }
    if (fread(contents, 1, (size_t)size, file) != (size_t)size) {
        fclose(file);
        free(contents);
        fprintf(stderr, "FAIL: short read from packaged resource: %s\n", path);
        return NULL;
    }
    contents[size] = '\0';
    fclose(file);
    return contents;
}

static int has(const char *text, const char *needle)
{
    return text != NULL && strstr(text, needle) != NULL;
}

static int count_text(const char *text, const char *needle)
{
    int count = 0;
    size_t length = strlen(needle);
    const char *cursor = text;
    while ((cursor = strstr(cursor, needle)) != NULL) {
        ++count;
        cursor += length;
    }
    return count;
}

static int check_directory_and_icon(const char *share, const char *directory_name,
                                    const char *icon_name)
{
    char relative[512];
    char *directory_path;
    char *directory;
    char *icon_path;
    char *icon;
    int ok;

    snprintf(relative, sizeof(relative), "desktop-directories/%s", directory_name);
    directory_path = join_path(share, relative);
    if (directory_path == NULL)
        return check(0, "allocate desktop-directory path");
    directory = read_file(directory_path);
    free(directory_path);
    if (directory == NULL)
        return 0;

    ok = check(has(directory, "[Desktop Entry]") && has(directory, "Type=Directory"),
               "desktop-directory has a Directory desktop entry");
    snprintf(relative, sizeof(relative), "Icon=%s\n", icon_name);
    ok = check(ok && has(directory, relative), "desktop-directory points to its icon") && ok;
    ok = check(has(directory, "Name=") && !has(directory, "_Name="),
               "intltool produced a runtime Name entry") && ok;
    ok = check(has(directory, "Name[ar]="),
               "Arabic desktop-directory translation is installed") && ok;
    ok = check(has(directory, "Name[fr]="),
               "French desktop-directory translation is installed") && ok;
    free(directory);
    if (!ok)
        return 0;

    snprintf(relative, sizeof(relative),
             "icons/hicolor/scalable/categories/%s.svg", icon_name);
    icon_path = join_path(share, relative);
    if (icon_path == NULL)
        return check(0, "allocate icon path");
    icon = read_file(icon_path);
    free(icon_path);
    if (icon == NULL)
        return 0;
    ok = check(has(icon, "<svg") && has(icon, "</svg>"),
               "referenced SVG icon has an SVG document root");
    free(icon);
    return ok;
}

int main(int argc, char **argv)
{
    const char *root;
    char *generic_path;
    char *gnome_path;
    char *share_path;
    char *generic;
    char *gnome;
    int ok = 1;

    if (argc != 2) {
        fprintf(stderr, "usage: %s <islamic-menus package folder>\n", argv[0]);
        return 2;
    }
    root = argv[1];
    generic_path = join_path(root, "etc/xdg/menus/applications-merged/islamic.menu");
    gnome_path = join_path(root,
        "etc/xdg/menus/applications-gnome-merged/islamic.menu");
    if (generic_path == NULL || gnome_path == NULL) {
        fprintf(stderr, "FAIL: cannot allocate menu paths\n");
        free(generic_path);
        free(gnome_path);
        return 1;
    }
    generic = read_file(generic_path);
    gnome = read_file(gnome_path);
    if (generic == NULL || gnome == NULL) {
        free(generic_path);
        free(gnome_path);
        free(generic);
        free(gnome);
        return 1;
    }

    ok = check(strcmp(generic, gnome) == 0,
               "GNOME and generic XDG menu fragments match") && ok;
    ok = check(count_text(generic, "<Menu>") == 3 &&
               count_text(generic, "</Menu>") == 3,
               "menu XML contains three opening and three closing Menu tags") && ok;
    ok = check(has(generic, "<Category>X-Islamic-Software</Category>") &&
               has(generic, "<Not><Category>X-Quran</Category></Not>") &&
               has(generic, "<Category>X-Quran</Category>"),
               "Islamic and Quran categories are routed into separate menus") && ok;
    ok = check(has(generic, "<Directory>Islamic-Software.directory</Directory>") &&
               has(generic, "<Directory>Quran.directory</Directory>"),
               "menu references both packaged desktop-directory entries") && ok;
    free(generic_path);
    free(gnome_path);
    free(generic);
    free(gnome);

    share_path = join_path(root, "share");
    if (share_path == NULL) {
        fprintf(stderr, "FAIL: cannot allocate package share path\n");
        return 1;
    }
    ok = check_directory_and_icon(share_path,
        "Islamic-Software.directory", "icon-islam") && ok;
    ok = check_directory_and_icon(share_path,
        "Quran.directory", "quran-icon") && ok;
    free(share_path);

    if (!ok || passed != checks) {
        fprintf(stderr, "islamic-menus consumer: %d/%d checks passed\n", passed, checks);
        return 1;
    }
    printf("islamic-menus consumer: traversed the Islamic/Quran menu routes, "
           "resolved both directory entries and SVG icons (%d/%d checks passed)\n",
           passed, checks);
    return 0;
}
