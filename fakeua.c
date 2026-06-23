#include <stdio.h>
#include <stdlib.h>
#include <stddef.h>
#include <stdbool.h>
#include <string.h>
#include <ctype.h>
#include <time.h>
#include <errno.h>
#include <fts.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <unistd.h>
#include <curl/curl.h>

static const char *start_page = "https://useragentstring.com/pages/useragentstring.php?name=";
static char errbuf[CURL_ERROR_SIZE];
char *dir ="./browsers";

typedef enum {
    BROWSER_NONE = -1,   /* sentinel for "unset" */
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

#define MAX_UA_NUM 50
#define MAX_TEXT_LEN 256

typedef struct {
    char buf[MAX_TEXT_LEN]; // including "\0", the last char: `text.buf[text.pos] = '\0';`
    uint8_t pos; // 0 <= pos <256, including the index of "\0", pos == strlen(buf)
} Text;

typedef struct {
    BrowserId id;
    Text item;
} UA; // one BrowserId, one Text

typedef struct {
    BrowserId id;
    Text items[MAX_UA_NUM];
    uint8_t len;
} Browser; // one BrowserId, many Texts

/*
typedef struct {
    BrowserId id;
    Text *items;
    uint8_t len;
    uint8_t cap;
} Browser;
*/

struct memory {
    char *buf;
    size_t size;
};

typedef struct {
    Browser *b;
    const char *path;
} Cache;

static int pending_interrupt = 0;
static void sighandler(int dummy)
{
    (void)dummy;
    pending_interrupt = 1;
}

static int rand_int_bound(int n)
{
    if (n <= 0) return 0;
    return rand() % n;
}

static uint8_t rand_u8(uint8_t n)
{
    if (n == 0) return 0;
    int r = rand_int_bound((int)n);
    return (uint8_t)r;
}

static int str_ci_equal(const char *a, const char *b)
{
    if (!a || !b) return 0;
    while (*a && *b) {
        if (tolower((unsigned char)*a++) != tolower((unsigned char)*b++)) return 0;
    }
    return *a == *b;
}

static BrowserId get_browserid_by_namestr(char *browsername)
{
    for (BrowserId b = 0; b < BROWSER_COUNT; b++) {
        if (str_ci_equal(browsername, browser_names[b])) return b;
    }
    return BROWSER_NONE;
}

static int read_filenames(BrowserId filenames[], uint8_t *len)
{
    if (!filenames) return -1;
    FTS *ftsp = fts_open(&dir, FTS_PHYSICAL | FTS_NOCHDIR, NULL);
    if (ftsp == NULL) {
        perror("fts_open");
        return -1;
    }

    FTSENT *parent = fts_read(ftsp);
    if (parent->fts_errno == ENOENT) {
        return -1;
    } else if (parent != NULL && parent->fts_info == FTS_D) {
        uint8_t index = 0;
        FTSENT *child = fts_children(ftsp, 0);
        while (child != NULL && index < BROWSER_COUNT) {
            char *ext = strstr(child->fts_name, ".");
            *ext = '\0';
            BrowserId id = get_browserid_by_namestr(child->fts_name);
            if (id != BROWSER_NONE) {
                filenames[id] = id;
                index++;
            } else filenames[index++] = BROWSER_NONE;
            child = child->fts_link;
        }
        if (len) *len = index;
    }
    return 0;
}

static BrowserId get_browserid_from_argstr(char *arg)
{
    if (str_ci_equal(arg, "browser")) {
        BrowserId fns[BROWSER_COUNT];
        uint8_t fns_len = 0;
        if (read_filenames(fns, &fns_len) != -1) {
            uint8_t random_number = rand_u8(fns_len);
            return fns[random_number];
        }
        uint8_t random_number = rand_u8(BROWSER_COUNT);
        return (BrowserId)random_number;
    }

    return get_browserid_by_namestr(arg);
}

static size_t write_data(char *contents, size_t sz, size_t nmemb, void *ctx) // contents is the src to read from, ctx is the destination to write into
{
    size_t realsize = sz * nmemb;
    struct memory *mem = (struct memory *)ctx;
    char *ptr = realloc(mem->buf, mem->size + realsize);
    if(!ptr) {
        puts("ERROR: not enough memory (realloc returned NULL)");
        return 0;
    }
    mem->buf = ptr;
    memcpy(&(mem->buf[mem->size]), contents, realsize);
    mem->size += realsize;
    return realsize;
}

static CURL *make_handle(const char *url)
{
    CURL *curl = curl_easy_init();

    struct memory *mem;
    mem = malloc(sizeof(*mem));
    if (mem == NULL) return NULL;
    mem->size = 0;
    mem->buf = malloc(1);

    curl_easy_setopt(curl, CURLOPT_WRITEFUNCTION, write_data); // curl_easy_setopt defined in curl/lib/setopt.c
    curl_easy_setopt(curl, CURLOPT_WRITEDATA, mem); // curl_easy_cleanup(curl) later will free mem
    curl_easy_setopt(curl, CURLOPT_PRIVATE, mem);   // curl_easy_cleanup(curl) later will free mem

    curl_easy_setopt(curl, CURLOPT_URL, url);
    curl_easy_setopt(curl, CURLOPT_FOLLOWLOCATION, 1L);
    curl_easy_setopt(curl, CURLOPT_ERRORBUFFER, errbuf);
    curl_easy_setopt(curl, CURLOPT_ACCEPT_ENCODING, "");
    curl_easy_setopt(curl, CURLOPT_REDIR_PROTOCOLS_STR, "http,https");
    curl_easy_setopt(curl, CURLOPT_AUTOREFERER, 1L);
    curl_easy_setopt(curl, CURLOPT_MAXREDIRS, 10L);
    curl_easy_setopt(curl, CURLOPT_TIMEOUT_MS, 20000L);
    curl_easy_setopt(curl, CURLOPT_CONNECTTIMEOUT_MS, 2000L);
    curl_easy_setopt(curl, CURLOPT_MAXFILESIZE_LARGE, (curl_off_t)1024 * 1024 * 1024);
    curl_easy_setopt(curl, CURLOPT_COOKIEFILE, "");
    curl_easy_setopt(curl, CURLOPT_USERAGENT, "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/29.0.1547.62 Safari/537.36");
    curl_easy_setopt(curl, CURLOPT_HTTPAUTH, CURLAUTH_ANY);
    curl_easy_setopt(curl, CURLOPT_UNRESTRICTED_AUTH, 1L);
    curl_easy_setopt(curl, CURLOPT_PROXYAUTH, CURLAUTH_ANY);
    curl_easy_setopt(curl, CURLOPT_EXPECT_100_TIMEOUT_MS, 0L);
    return curl;
}

static void *parse(struct memory *mem, Text out_texts[], uint8_t *out_count, UA *out_ua)
{
    if (!mem || !mem->buf || mem->size < 100) {
        puts("ERROR: not valid html doc");
        return NULL;
    }

    const char *p = mem->buf;

    uint8_t cap = (out_texts == NULL) ? rand_u8(MAX_UA_NUM) + 1 : MAX_UA_NUM;
    Text texts[cap];
    uint8_t text_index = 0;

    while (*p && text_index < cap) {
        if (*p != '<') {
            p++;
            continue;
        }

        const char *q = p + 1; // 此时*p='<', *q=<的char
        while (isspace((unsigned char)*q)) q++;
        if (tolower((unsigned char)*q) != 'a') {
            p = q;
            continue;
        }

        // *q='a',  p='<'
        q++;
        while (*q && *q != '>') q++;

        // *q = '>'
        q++;
        Text text = {0};

        if (*q == '<' && *(q + 1) == '/' && *(q + 2) == 'a' && *(q + 3) == '>') {
            p = q + 4;
            continue;
        }

        bool invalid = 0;
        while (*q) {
            if (*q != '<') {
                // If text in <> doesn't start with "Mozilla/" (not a UA), just let the pointer run past the whole of it.
                if (text.pos == 0 && *q == 'M') text.buf[text.pos++] = *q;
                else if (text.pos == 1 && *q == 'o' && text.buf[text.pos - 1] != 0) text.buf[text.pos++] = *q;
                else if (text.pos == 2 && *q == 'z' && text.buf[text.pos - 1] != 0) text.buf[text.pos++] = *q;
                else if (text.pos == 3 && *q == 'i' && text.buf[text.pos - 1] != 0) text.buf[text.pos++] = *q;
                else if (text.pos == 4 && *q == 'l' && text.buf[text.pos - 1] != 0) text.buf[text.pos++] = *q;
                else if (text.pos == 5 && *q == 'l' && text.buf[text.pos - 1] != 0) text.buf[text.pos++] = *q;
                else if (text.pos == 6 && *q == 'a' && text.buf[text.pos - 1] != 0) text.buf[text.pos++] = *q;
                else if (text.pos == 7 && *q == '/' && text.buf[text.pos - 1] != 0) text.buf[text.pos++] = *q;
                else if (text.pos >= 8 && text.buf[text.pos - 1] != 0) text.buf[text.pos++] = *q;
                else {
                    text.pos++;
                    invalid = 1;
                }
                q++;
                continue;
            } else if (*q == '<' && *(q + 1) == '/' && *(q + 2) == 'a' && *(q + 3) == '>') {
                q++;
                break;
            } else {
                q++;
                while (*q != '>') q++;
                q++;
                continue;
            }
        }

        p = q;
        if (invalid) continue;
        text.buf[text.pos] = '\0';
        texts[text_index++] = text;
        continue;
    }

    if (out_ua) {
        uint8_t random_number = rand_u8(text_index);
        strncpy(out_ua->item.buf, texts[random_number].buf, texts[random_number].pos + 1);
        out_ua->item.pos = texts[random_number].pos;
        return out_ua;
    }

    if (out_count) *out_count = text_index;
    if (out_texts) {
        for (uint8_t i = 0; i < text_index; ++i) {
            strncpy(out_texts[i].buf, texts[i].buf, texts[i].pos + 1);
            out_texts[i].pos = texts[i].pos;
        }
    }
    return out_texts;
}

int fetch_ua(const char *url, UA *ua)
{
    CURLcode result;
    result = curl_global_init(CURL_GLOBAL_ALL);
    if (result != CURLE_OK) return (int)result;

    CURL *curl = make_handle(url);
    if (curl == NULL) return -1;

    errbuf[0] = '\0';
    result = curl_easy_perform(curl);
    if (result != CURLE_OK) {
        size_t len = strlen(errbuf);
        fprintf(stderr, "Connection failure: %s : libcurl: (%d) ", url, result);
        if (len) fprintf(stderr, "%s%s", errbuf, ((errbuf[len - 1] != '\n') ? "\n" : ""));
        else fprintf(stderr, "%s\n", curl_easy_strerror(result));
        return (int)result;
    }

    long res_status;
    char *res_url;
    curl_easy_getinfo(curl, CURLINFO_RESPONSE_CODE, &res_status);
    curl_easy_getinfo(curl, CURLINFO_EFFECTIVE_URL, &res_url);

    if (res_status != 200) {
        printf("HTTP %d: %s\n", (int)res_status, res_url);
        return -1;
    }

    struct memory *mem;
    curl_easy_getinfo(curl, CURLINFO_PRIVATE, &mem);

    void *parse_res = parse(mem, NULL, NULL, ua);

    curl_easy_cleanup(curl); // in easy mode (not multi mode), curl_easy_cleanup(curl) frees mem
    curl_global_cleanup();
    return parse_res ? 0 : -1;
}

void deletes()
{
    FTS *ftsp = fts_open(&dir, FTS_PHYSICAL | FTS_NOCHDIR, NULL);
    if (ftsp == NULL) {
        perror("fts_open");
        exit(1);
    }

    FTSENT *node;
    while ((node = fts_read(ftsp)) != NULL) {
        if (node->fts_info == FTS_NS) {
            if (node->fts_errno == ENOENT) {
                fprintf(stderr, "ERROR: The path '%s' does not exist.\n", node->fts_path);
            } else {
                fprintf(stderr, "ERROR: accessing '%s': %s\n", node->fts_path, strerror(node->fts_errno));
            }

            if (node->fts_level == 0) {
                fts_close(ftsp);
                exit(1);
            }
        } else if (node->fts_info == FTS_DNR) {
            fprintf(stderr, "ERROR: '%s' exists but is not readable: %s\n", node->fts_path, strerror(node->fts_errno));
            if (node->fts_level == 0) {
                fts_close(ftsp);
                exit(1);
            }
        } else if (node->fts_info == FTS_F) {
            if (unlink(node->fts_path) != 0) perror("unlink");
        } else if (node->fts_info == FTS_DP) {
            if (rmdir(node->fts_path) != 0) perror("rmdir");
        }
    }

    fts_close(ftsp);
    exit(0);
}

static int make_dir(const char *path)
{
    if (mkdir(path, 0755) == 0) return 0;
    if (errno == EEXIST) return 1;
    perror("mkdir");
    return -1;
}

void *dump_a_browser(void *arg) // accomodate multi-thread needs
{
    Cache *pa = (Cache*)arg;
    Browser *b = pa->b;
    const char *path = pa->path;
    if (make_dir(dir) == -1) return NULL;

    char temp[128];
    snprintf(temp, sizeof temp, "%s/%s.tmpXXXXXX", dir, browser_names[b->id]);
    int fd = mkstemp(temp);
    if (fd < 0) {
        perror("mkstemp");
        return NULL;
    }
    FILE *f = fdopen(fd, "wb");
    if (!f) {
        perror("fdopen");
        close(fd);
        unlink(temp);
        return NULL;
    }

    printf("dumping browser [%s]\n", browser_names[b->id]);
    if (fwrite("BRS", 1, 3, f) != 3) {
        perror("fwrite(BRS)");
        goto write_err;
    }

    uint8_t version = 1;
    if (fwrite(&version, sizeof(version), 1, f) != 1) {
        perror("fwrite(version)");
        goto write_err;
    }

    uint8_t id = b->id;
    if (fwrite(&id, sizeof(id), 1, f) != 1) {
        perror("fwrite(id)");
        goto write_err;
    }

    uint8_t len = b->len;
    if (fwrite(&len, sizeof(len), 1, f) != 1) {
        perror("fwrite(len)");
        goto write_err;
    }

    for (uint8_t i = 0; i < b->len; ++i) {
        Text text = b->items[i]; // b-> items is a pointer, b->items[i] is a value.
        if (fwrite(&text.pos, sizeof(text.pos), 1, f) != 1) {
            perror("fwrite(text.pos)");
            goto write_err;
        }

        // compact approach
        // if (fwrite(text.buf, 1, text.pos + 1, f) != text.pos + 1) { perror("fwrite(text.buf)"); goto write_err; }

        // fixed-size approach
        if (fwrite(text.buf, 1, MAX_TEXT_LEN, f) != MAX_TEXT_LEN) {
            perror("fwrite(text.buf)");
            goto write_err;
        }
    }

    if (fflush(f) != 0) {
        perror("fflush");
        goto write_err;
    }
    if (fsync(fileno(f)) != 0) {
        perror("fsync");
        goto write_err;
    }
    fclose(f);

    if (rename(temp, path) != 0) {
        perror("rename");
        unlink(temp);
        return NULL;
    }
    return arg;

write_err:
    fclose(f);
    unlink(temp);
    return NULL;
}

void dumps(void)
{
    if (curl_global_init(CURL_GLOBAL_ALL) != CURLE_OK) exit(1);

    signal(SIGINT, sighandler);
    CURLM *multi = curl_multi_init();
    if (!multi) {
        curl_global_cleanup();
        exit(1);
    }

    bool has_dir = 1;
    BrowserId fns[BROWSER_COUNT];
    if (read_filenames(fns, NULL) == -1) {
        if (make_dir(dir) == -1) exit(1);
        has_dir = 0;
    }

    for (BrowserId b = 0; b < BROWSER_COUNT; b++) {
        if (has_dir && b == fns[b]) {
            printf("[%s] already there, skip\n", browser_names[b]);
            continue;
        }

        char url[256];
        snprintf(url, sizeof url, "%s%s", start_page, browser_names[b]);
        CURL *curl = make_handle(url);
        if (curl == NULL) {
            curl_multi_cleanup(multi);
            curl_global_cleanup();
            exit(1);
        }
        curl_multi_add_handle(multi, curl);
    }

    int complete = 0;
    int still_running = 1;
    int msgs_left;
    while (still_running && !pending_interrupt) {
        int numfds = 0;
        curl_multi_wait(multi, NULL, 0, 1000, &numfds);
        curl_multi_perform(multi, &still_running);

        CURLMsg *m = NULL;
        while((m = curl_multi_info_read(multi, &msgs_left))) { // loop over each handle
            if(m->msg == CURLMSG_DONE) {
                CURL *curl = m->easy_handle;
                char *res_url;
                curl_easy_getinfo(curl, CURLINFO_EFFECTIVE_URL, &res_url); // if not CURLE_OK, res_url is set to be request url

                struct memory *mem;
                curl_easy_getinfo(curl, CURLINFO_PRIVATE, &mem);

                Browser browser = {0};
                if(m->data.result == CURLE_OK) {
                    long res_status;
                    curl_easy_getinfo(curl, CURLINFO_RESPONSE_CODE, &res_status);
                    if (res_status == 200) {
                        printf("[%d] HTTP %d: %s\n", complete, (int)res_status, res_url);
                        char *browser_name = NULL;
                        for (BrowserId b = 0; b < BROWSER_COUNT; b++) {
                            char *ptr = strstr(res_url, browser_names[b]);
                            if (str_ci_equal(ptr, browser_names[b])) {
                                browser_name = ptr;
                                break;
                            }
                        }

                        if (browser_name != NULL) {
                            BrowserId browserid = get_browserid_by_namestr(browser_name);
                            browser.id = browserid;
                            printf("parsing browser [%s]\n", browser_name);
                            if (parse(mem, browser.items, &browser.len, NULL) != NULL) {
                                char path[128];
                                snprintf(path, sizeof path, "%s/%s.brs", dir, browser_name);
                                Cache pa = { .b = &browser, .path = path };
                                dump_a_browser(&pa);
                            }
                        } else printf("Failed to extract a valid browser name from response url : %s\n", res_url);
                    } else printf("[%d] HTTP %d: %s\n", complete, (int)res_status, res_url);
                } else {
                    size_t len = strlen(errbuf);
                    fprintf(stderr, "[%d] Connection failure: %s : libcurl: (%d) ", complete, res_url, m->data.result);
                    if (len) fprintf(stderr, "%s%s", errbuf, ((errbuf[len - 1] != '\n') ? "\n" : ""));
                    else fprintf(stderr, "%s\n", curl_easy_strerror(m->data.result));
                }

                curl_multi_remove_handle(multi, curl);
                curl_easy_cleanup(curl);
                free(mem->buf);
                free(mem);
                complete++;
            }
        }
    }

    curl_multi_cleanup(multi);
    curl_global_cleanup();
    exit(0);
}

int load_ua(const char *path, UA *ua)
{
    if (!path || !ua) return -1;
    FILE *f = fopen(path, "rb");
    if (!f) {
        perror("fopen");
        return -1;
    }

    char magic[3];
    if (fread(magic, 1, 3, f) != 3) {
        perror("fread(magic)");
        fclose(f);
        return -1;
    }
    if (memcmp(magic, "BRS", 3) != 0) {
        puts("ERROR: magic codes don't match");
        fclose(f);
        return -1;
    }

    uint8_t version = 0;
    if (fread(&version, sizeof(version), 1, f) != 1) {
        perror("fread(version)");
        fclose(f);
        return -1;
    }
    if (version != 1) {
        puts("ERROR: version numbers don't match");
        fclose(f);
        return -1;
    }

    uint8_t fid = 0;
    if (fread(&fid, sizeof(fid), 1, f) != 1) {
        perror("fread(id)");
        fclose(f);
        return -1;
    }
    if (fid != ua->id) {
        puts("ERROR: broswer ids don't match");
        fclose(f);
        return -1;
    }

    uint8_t len = 0;
    if (fread(&len, sizeof(len), 1, f) != 1) {
        perror("fread(len)");
        fclose(f);
        return -1;
    }

    if (len <= 0) {
        puts("ERROR: cache file has lenth 0");
        fclose(f);
        return -1;
    }

    // compact approach
    // for (uint8_t i = 0; i < b->len; ++i) {
    //     if (fread(&b->items[i].pos, sizeof(b->items[i].pos), 1, f) != 1) { perror("fread(item.pos)"); return -1; }
    //     if (fread(&b->items[i].buf, 1, b->items[i].pos + 1, f) != b->items[i].pos + 1) { perror("fread(item.buf)"); return -1; }
    // }

    // fixed-size approach
    uint8_t rand_num = rand_u8(len);
    if (rand_num > 0) {
        if (fseek(f, (long)((MAX_TEXT_LEN + 1)*rand_num), SEEK_CUR) != 0) {
            perror("fseek");
            fclose(f);
            return -1;
        }
    }
    if (fread(&ua->item.pos, sizeof(ua->item.pos), 1, f) != 1) {
        perror("fread(pos)");
        fclose(f);
        return -1;
    }
    if (fread(&ua->item.buf, 1, MAX_TEXT_LEN, f) != MAX_TEXT_LEN) {
        perror("fread(buf)");
        fclose(f);
        return -1;
    }

    fclose(f);
    return 0;
}

static void usage(const char *message)
{
    puts("fakeua - get a radndom and valid browser user-agent string - v1.0");
    puts("USAGE: fakeua <subcommand>");
    puts("SUBCOMMANDS:");
    puts("  browser [name] [-f]  Optional name from chrome, edge, firefox, safari, opera (case insensitive) with optional '-f' disabling use of cache");
    puts("  dump                 Dump user-agent data to binary files as caches by browser name");
    puts("  delete               Delete caches if any");
    puts("  help                 Show this help message and exit");
    if (message) {
        fprintf(stderr, "%s\n", message);
        exit(1);
    }
    exit(0);
}

int main(int argc, char *argv[])
{
    // const char *program = argv[0];
    const char *subcommand = argv[1];
    if (argv[1] == NULL) usage("ERROR: no subcommand is provided");
    if (str_ci_equal(subcommand, "help")) usage(NULL);
    if (str_ci_equal(subcommand, "delete")) deletes();
    if (str_ci_equal(subcommand, "dump")) dumps();
    if (!str_ci_equal(subcommand, "browser")) usage("ERROR: wrong subcommand is provided");

    time_t t = time(NULL);
    if (t == (time_t) - 1) {
        perror("time");
        return 1;
    }
    srand((unsigned)t);

    bool is_fresh = str_ci_equal(argv[argc - 1], "-f");
    char *arg = is_fresh ? argv[argc - 2] : argv[argc - 1];
    BrowserId browserid = get_browserid_from_argstr(arg);
    if (browserid == BROWSER_NONE) usage("ERROR: wrong browser name is provided\n");

    UA ua = { .id = browserid, .item = { .buf = {0}, .pos = 0 } };

    char path[128];
    snprintf(path, sizeof path, "%s/%s.brs", dir, browser_names[browserid]);

    if (is_fresh || !fopen(path, "r")) {
        snprintf(path, sizeof path, "%s%s", start_page, browser_names[browserid]);
        if (fetch_ua(path, &ua) != 0) return 1;
    } else {
        if (load_ua(path, &ua) != 0) return 1;
        printf("loading browser [%s] cache\n", browser_names[browserid]);
    }

    printf("%s\n", ua.item.buf);
    return 0;
}

// clang -Wall -Wextra -Wunused-function -Wunused-variable -Wunused-parameter fakeua.c -lcurl -o fakeua
