/*
Below is a concise, safe implementation that stores each Browser in its own binary file named "<browser_name>.brs" in a given directory. It includes helpers to save a single browser (atomic via temp-then-rename), load a single browser, list/load all browsers in the directory, and basic memory management. It uses fixed-size integer types and writes lengths so strings are stored as raw bytes (not NUL-terminated in file). Error handling is minimal but clear — return 0 on success, -1 on failure.

Notes:
Per-browser files allow cheap per-browser updates and partial reads.
Still use temp+rename to make saves atomic on POSIX.
For concurrent writers, add file locking (flock) if needed.
For cross-platform path length macro, include limits.h if PATH_MAX isn't available.

Compile with: gcc -std=c11 -Wall -Wextra -o browsers_per_browser browsers_per_browser.c
*/

#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <inttypes.h>
#include <errno.h>
#include <dirent.h>
#include <sys/stat.h>
#include <unistd.h>

typedef enum {
    BROWSER_NONE = -1,
    BROWSER_CHROME = 0,
    BROWSER_EDGE,
    BROWSER_FIREFOX,
    BROWSER_SAFARI,
    BROWSER_OPERA,
    BROWSER_COUNT
} BrowserId;

static const char *browser_names[BROWSER_COUNT] = {
    [BROWSER_CHROME]  = "chrome",
    [BROWSER_EDGE]    = "edge",
    [BROWSER_FIREFOX] = "firefox",
    [BROWSER_SAFARI]  = "safari",
    [BROWSER_OPERA]   = "opera"
};

typedef struct {
    BrowserId id;
    char **items;
    size_t len;
    size_t cap;
} Browser;

static void free_browser(Browser *b) {
    if (!b) return;
    for (size_t i = 0; i < b->len; ++i) free(b->items[i]);
    free(b->items);
    b->items = NULL;
    b->len = b->cap = 0;
    b->id = BROWSER_NONE;
}

static int grow_browser_if_needed(Browser *b, size_t need) {
    if (b->cap >= need) return 0;
    size_t newcap = b->cap ? b->cap * 2 : 4;
    while (newcap < need) newcap *= 2;
    char **tmp = realloc(b->items, newcap * sizeof(*tmp));
    if (!tmp) return -1;
    b->items = tmp;
    b->cap = newcap;
    return 0;
}

int browser_add_item(Browser *b, const char *s) {
    if (!b || !s) return -1;
    if (grow_browser_if_needed(b, b->len + 1) != 0) return -1;
    char *dup = strdup(s);
    if (!dup) return -1;
    b->items[b->len++] = dup;
    return 0;
}

/* Binary file layout per browser:
   - 4 bytes magic "BRS1"
   - uint32_t version (1)
   - int32_t id
   - uint64_t len (number of items)
   - for each item:
       uint64_t bytes_len
       bytes (not NUL-terminated)
*/

/* Helper: build filename "<dir>/<name>.brs" into out (size outlen). */
static int build_filename(const char *dir, const char *name, char *out, size_t outlen) {
    if (snprintf(out, outlen, "%s/%s.brs", dir, name) >= (int)outlen) return -1;
    return 0;
}

/* Atomic save single browser: write to temp file then rename */
int save_browser_to_dir(const char *dir, const Browser *b) {
    if (!dir || !b) return -1;
    if (b->id < 0 || b->id >= BROWSER_COUNT) return -1;

    char path[PATH_MAX];
    if (build_filename(dir, browser_names[b->id], path, sizeof(path)) != 0) return -1;

    /* temp file path */
    char tmp[PATH_MAX];
    if (snprintf(tmp, sizeof(tmp), "%s.tmpXXXXXX", path) >= (int)sizeof(tmp)) return -1;
    int fd = mkstemp(tmp);
    if (fd < 0) return -1;
    FILE *f = fdopen(fd, "wb");
    if (!f) { close(fd); unlink(tmp); return -1; }

    if (fwrite("BRS1", 1, 4, f) != 4) goto write_err;
    uint32_t version = 1;
    if (fwrite(&version, sizeof(version), 1, f) != 1) goto write_err;
    int32_t id = (int32_t)b->id;
    if (fwrite(&id, sizeof(id), 1, f) != 1) goto write_err;
    uint64_t len = (uint64_t)b->len;
    if (fwrite(&len, sizeof(len), 1, f) != 1) goto write_err;

    for (size_t i = 0; i < b->len; ++i) {
        uint64_t ulen = b->items[i] ? (uint64_t)strlen(b->items[i]) : 0;
        if (fwrite(&ulen, sizeof(ulen), 1, f) != 1) goto write_err;
        if (ulen > 0) {
            if (fwrite(b->items[i], 1, (size_t)ulen, f) != ulen) goto write_err;
        }
    }

    if (fflush(f) != 0) goto write_err;
    if (fsync(fileno(f)) != 0) { /* best-effort sync */ }
    fclose(f);

    if (rename(tmp, path) != 0) { unlink(tmp); return -1; }
    return 0;

write_err:
    fclose(f);
    unlink(tmp);
    return -1;
}

/* Load single browser from file into out (out must be initialized or zeroed). */
int load_browser_from_dir(const char *dir, BrowserId id, Browser *out) {
    if (!dir || !out) return -1;
    if (id < 0 || id >= BROWSER_COUNT) return -1;

    char path[PATH_MAX];
    if (build_filename(dir, browser_names[id], path, sizeof(path)) != 0) return -1;

    FILE *f = fopen(path, "rb");
    if (!f) return -1;
    char magic[4];
    if (fread(magic, 1, 4, f) != 4) { fclose(f); return -1; }
    if (memcmp(magic, "BRS1", 4) != 0) { fclose(f); return -1; }
    uint32_t version = 0;
    if (fread(&version, sizeof(version), 1, f) != 1) { fclose(f); return -1; }
    if (version != 1) { fclose(f); return -1; }

    int32_t fid = 0;
    if (fread(&fid, sizeof(fid), 1, f) != 1) { fclose(f); return -1; }
    uint64_t len = 0;
    if (fread(&len, sizeof(len), 1, f) != 1) { fclose(f); return -1; }
    if (fid != (int32_t)id) { fclose(f); return -1; }

    out->id = id;
    out->items = NULL;
    out->len = out->cap = 0;
    if (len > 0) {
        if (grow_browser_if_needed(out, (size_t)len) != 0) { fclose(f); return -1; }
        for (uint64_t j = 0; j < len; ++j) {
            uint64_t ulen = 0;
            if (fread(&ulen, sizeof(ulen), 1, f) != 1) { fclose(f); return -1; }
            char *buf = malloc((size_t)ulen + 1);
            if (!buf) { fclose(f); return -1; }
            if (ulen > 0) {
                if (fread(buf, 1, (size_t)ulen, f) != ulen) { free(buf); fclose(f); return -1; }
            }
            buf[ulen] = '\0';
            out->items[out->len++] = buf;
        }
    }
    fclose(f);
    return 0;
}

/* Load all browsers present in the directory (skips missing files). */
int load_all_browsers_from_dir(const char *dir, Browser *out_array /* length BROWSER_COUNT */) {
    if (!dir || !out_array) return -1;
    for (size_t i = 0; i < BROWSER_COUNT; ++i) free_browser(&out_array[i]);

    for (size_t i = 0; i < BROWSER_COUNT; ++i) {
        Browser tmp = { .id = BROWSER_NONE, .items = NULL, .len = 0, .cap = 0 };
        if (load_browser_from_dir(dir, (BrowserId)i, &tmp) == 0) {
            out_array[i] = tmp; /* move ownership */
        } else {
            /* missing or failed: leave as empty */
            free_browser(&tmp);
        }
    }
    return 0;
}

/* Example usage */
#ifdef EXAMPLE_MAIN
int main(void) {
    const char *dir = "./browsers";
    mkdir(dir, 0755);

    Browser b = { .id = BROWSER_CHROME, .items = NULL, .len = 0, .cap = 0 };
    browser_add_item(&b, "http://example.com");
    browser_add_item(&b, "http://example.org");

    if (save_browser_to_dir(dir, &b) != 0) {
        fprintf(stderr, "save failed: %s\n", strerror(errno));
    }

    free_browser(&b);

    Browser loaded = { .id = BROWSER_NONE, .items = NULL, .len = 0, .cap = 0 };
    if (load_browser_from_dir(dir, BROWSER_CHROME, &loaded) == 0) {
        for (size_t i = 0; i < loaded.len; ++i) puts(loaded.items[i]);
        free_browser(&loaded);
    } else {
        fprintf(stderr, "load failed\n");
    }

    Browser all[BROWSER_COUNT] = {0};
    load_all_browsers_from_dir(dir, all);
    for (size_t bi = 0; bi < BROWSER_COUNT; ++bi) free_browser(&all[bi]);

    return 0;
}
#endif
