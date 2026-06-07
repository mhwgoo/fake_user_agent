#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>
#include <stddef.h>
#include <stdbool.h>
#include <time.h>
#include <pthread.h>
#include <errno.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <curl/curl.h>
#include <unistd.h>

static const char *start_page = "http://useragentstring.com/pages/useragentstring.php?name=";
static const char *dir ="./browsers";
static char errbuf[CURL_ERROR_SIZE];

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
    uint8_t pos; // 0 <= pos <256, including the index of "\0", so pos == strlen(buf)
} Text;

typedef struct {
    BrowserId id;
    Text item;
} UA; // one BrowserId, one Text; suitable for fresh mode

typedef struct {
    BrowserId id;
    Text *items;
    uint8_t len;
    uint8_t cap;
} Browser; // one BrowserId, many Texts; suitable for caching

typedef struct {
    Browser *b;
    const char *p;
} Cache;

static int pending_interrupt = 0;
static void sighandler(int dummy)
{
    (void)dummy;
    pending_interrupt = 1;
}

static int rand_int_bound(int n) {
    if (n <= 0) return 0;
    return rand() % n;
}

static uint8_t rand_u8(uint8_t n) {
    if (n == 0) return 0;
    int r = rand_int_bound((int)n);
    return (uint8_t)r;
}

static int case_insensitive_equal(const char *a, const char *b)
{
    unsigned char ca, cb;
    if (!a || !b) return 0;
    while (*a && *b) {
        ca = (unsigned char)*a++;
        cb = (unsigned char)*b++;
        if (tolower(ca) != tolower(cb)) return 0;
    }
    return *a == *b;
}

struct memory {
    char *buf;
    size_t size;
};

static size_t write_data(char *contents, size_t sz, size_t nmemb, void *ctx) // contents is the src to read from, ctx is the destination to write into
{
    size_t realsize = sz * nmemb;
    struct memory *mem = (struct memory *)ctx;
    char *ptr = realloc(mem->buf, mem->size + realsize);
    if(!ptr) {
        printf("not enough memory (realloc returned NULL)\n");
        return 0;
    }
    mem->buf = ptr;
    memcpy(&(mem->buf[mem->size]), contents, realsize);
    mem->size += realsize;
    return realsize;
}

static CURL *make_handle(struct memory *mem, const char *url)
{
    CURL *curl = curl_easy_init();
    curl_easy_setopt(curl, CURLOPT_URL, url); // curl_easy_setopt defined in curl/lib/setopt.c
    curl_easy_setopt(curl, CURLOPT_WRITEFUNCTION, write_data);
    curl_easy_setopt(curl, CURLOPT_WRITEDATA, mem);
    curl_easy_setopt(curl, CURLOPT_ERRORBUFFER, errbuf);
    curl_easy_setopt(curl, CURLOPT_ACCEPT_ENCODING, "");
    curl_easy_setopt(curl, CURLOPT_FOLLOWLOCATION, 1L);
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

static int fetch_html(struct memory *html, const char *browser_name)
{
    CURLcode result;
    result = curl_global_init(CURL_GLOBAL_ALL);
    if (result != CURLE_OK) return (int)result;

    char url[256];
    snprintf(url, sizeof url, "%s%s", start_page, browser_name);

    CURL *curl = make_handle(html, url);
    errbuf[0] = '\0';
    result = curl_easy_perform(curl);
    if (result != CURLE_OK) {
        size_t len = strlen(errbuf);
        fprintf(stderr, "\nlibcurl: (%d) ", result);
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

    curl_easy_cleanup(curl);
    curl_global_cleanup();
    return 0;
}

static void *parse(Text out_texts[], uint8_t *out_count, UA *out_ua, uint8_t *out_random_number)
{
    if (out_ua == NULL) return NULL;

    struct memory *mem;
    mem = malloc(sizeof(*mem));
    mem->size = 0;
    mem->buf = malloc(1);

    if (fetch_html(mem, browser_names[out_ua->id]) != 0 ) {
        free(mem->buf);
        free(mem);
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
                else { text.pos++; invalid = 1; }
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

    uint8_t random_number = rand_u8(text_index);
    *out_random_number = random_number;
    strncpy(out_ua->item.buf, texts[random_number].buf, texts[random_number].pos + 1);
    out_ua->item.pos = texts[random_number].pos;

    free(mem->buf);
    free(mem);

    if (out_texts == NULL) return out_ua;

    *out_count = text_index;
    for (uint8_t i = 0; i < text_index; ++i) {
        strncpy(out_texts[i].buf, texts[i].buf, texts[i].pos + 1);
        out_texts[i].pos = texts[i].pos;
    }
    return out_texts;
}

static int delete_cache()
{
    printf("Cache has been deleted.\n");
    return 0;
}

static int make_dir(const char *path)
{
    if (mkdir(path, 0755) == 0) return 0;
    if (errno == EEXIST) return 1;
    perror("mkdir");
    return -1;
}

static void *download_cache(void *arg)
{
    Cache *pa = (Cache*)arg;
    Browser *b = pa->b;
    const char *path = pa->p;
    if (make_dir(dir) == -1) return NULL;

    char temp[128];
    snprintf(temp, sizeof(temp), "%s/%s.tmpXXXXXX", dir, browser_names[b->id]);
    int fd = mkstemp(temp);
    if (fd < 0) { perror("mkstemp"); return NULL; }
    FILE *f = fdopen(fd, "wb");
    if (!f) { perror("fdopen"); close(fd); unlink(temp); return NULL; }

    if (fwrite("BRS1", 1, 4, f) != 4) { perror("fwrite(BRS1)"); goto write_err; }

    uint16_t version = 1;
    if (fwrite(&version, sizeof(version), 1, f) != 1) { perror("fwrite(version)"); goto write_err; }

    uint8_t id = b->id;
    if (fwrite(&id, sizeof(id), 1, f) != 1) { perror("fwrite(id)"); goto write_err; }

    uint8_t len = b->len;
    if (fwrite(&len, sizeof(len), 1, f) != 1) { perror("fwrite(len)"); goto write_err; }

    for (uint8_t i = 0; i < b->len; ++i) {
	Text text = b->items[i]; // b-> items is a pointer, b->items[i] is a value.
        if (fwrite(&text.pos, sizeof(text.pos), 1, f) != 1) { perror("fwrite(text.pos)"); goto write_err; }

	// compact approach
        // if (fwrite(text.buf, 1, text.pos + 1, f) != text.pos + 1) { perror("fwrite(text.buf)"); goto write_err; }

	// fixed-size approach
        if (fwrite(text.buf, 1, MAX_TEXT_LEN, f) != MAX_TEXT_LEN) { perror("fwrite(text.buf)"); goto write_err; }
    }

    if (fflush(f) != 0) { perror("fflush"); goto write_err; }
    if (fsync(fileno(f)) != 0) { perror("fsync"); goto write_err; }
    fclose(f);

    if (rename(temp, path) != 0) { perror("rename"); unlink(temp); return NULL; }
    return arg;

write_err:
    fclose(f);
    unlink(temp);
    return NULL;
}

static int read_cache(const char *path, UA *ua)
{
    if (!ua) return -1;
    FILE *f = fopen(path, "rb");
    if (!f) { perror("fopen"); return -1; }

    char magic[4];
    if (fread(magic, 1, 4, f) != 4) { perror("fread(magic)"); fclose(f); return -1; }
    if (memcmp(magic, "BRS1", 4) != 0) { puts("ERROR: magic codes don't match"); fclose(f); return -1; }

    uint16_t version = 0;
    if (fread(&version, sizeof(version), 1, f) != 1) { perror("fread(version)"); fclose(f); return -1; }
    if (version != 1) { puts("ERROR: version numbers don't match"); fclose(f); return -1; }

    uint8_t fid = 0;
    if (fread(&fid, sizeof(fid), 1, f) != 1) { perror("fread(id)"); fclose(f); return -1; }
    if (fid != ua->id) { puts("ERROR: brower ids don't match"); fclose(f); return -1; }

    uint8_t len = 0;
    if (fread(&len, sizeof(len), 1, f) != 1) { perror("fread(len)"); fclose(f); return -1; }

    if (len <= 0) { puts("cache file has lenth 0"); fclose(f); return -1; }

    // compact approach
    // for (uint8_t i = 0; i < b->len; ++i) {
    //     if (fread(&b->items[i].pos, sizeof(b->items[i].pos), 1, f) != 1) { perror("fread(item.pos)"); return -1; }
    //     if (fread(&b->items[i].buf, 1, b->items[i].pos + 1, f) != b->items[i].pos + 1) { perror("fread(item.buf)"); return -1; }
    // }

    // fixed-size approach
    uint8_t random_number = rand_u8(len);
    if (random_number > 0) {
	if (fseek(f, (long)((MAX_TEXT_LEN + 1)*random_number), SEEK_CUR) != 0) { perror("fseek"); fclose(f); return -1; }
    }
    if (fread(&ua->item.pos, sizeof(ua->item.pos), 1, f) != 1) { perror("fread(pos)"); fclose(f); return -1; }
    if (fread(&ua->item.buf, 1, MAX_TEXT_LEN, f) != MAX_TEXT_LEN) { perror("fread(buf)"); fclose(f); return -1; }

    fclose(f);
    return (int)random_number;
}

static BrowserId get_browser(char *arg)
{
    if (case_insensitive_equal(arg, "browser")) {
        uint8_t random_number = rand_u8(BROWSER_COUNT);
        return (BrowserId)random_number;
    }

    for (BrowserId b = 0; b < BROWSER_COUNT; b++) {
        if (case_insensitive_equal(arg, browser_names[b])) return b;
    }

    return BROWSER_NONE;
}

static void usage(const char *message)
{
    puts("fakeua - get a radndom and valid browser user-agent string - v1.0");
    puts("USAGE: fakeua <subcommand>");
    puts("SUBCOMMANDS:");
    puts("  browser [name] [-f]  No name or specify a name from chrome, edge, firefox, safari, opera (case insensitive) with '-f' disabling use of cache");
    puts("  download             First download to a cache file if not any or update with lastest User-Agent values");
    puts("  delete               Delete the cache file if any");
    puts("  help                 Show this help message and exit");
    if (message) fprintf(stderr, "%s", message);
}

int main(int argc, char *argv[])
{
    const char *program = argv[0];
    const char *subcommand = argv[1];
    if (argv[1] == NULL) { usage("ERROR: no subcommand is provided\n"); return 1; }
    if (case_insensitive_equal(subcommand, "help")) { usage(NULL); return 0; }
    if (case_insensitive_equal(subcommand, "delete")) { delete_cache(); return 0; }
    if (case_insensitive_equal(subcommand, "download")) { download_cache(NULL); return 0; }
    if (!case_insensitive_equal(subcommand, "browser")) { usage("ERROR: wrong subcommand is provided\n"); return 1; }

    time_t t = time(NULL);
    if (t == (time_t)-1) { perror("time"); return 1; }
    srand((unsigned)t);

    bool is_fresh = case_insensitive_equal(argv[argc - 1], "-f");
    char *arg = is_fresh ? argv[argc - 2] : argv[argc - 1];
    BrowserId browserid = get_browser(arg);
    if (browserid == BROWSER_NONE) { usage("ERROR: wrong browser name is provided\n"); return 1; }
    UA random_ua = { .id = browserid, .item = { .buf = {0}, .pos = 0 } };
    uint8_t random_number;

    if (is_fresh) {
	if (parse(NULL, NULL, &random_ua, &random_number) == NULL) return 1;
	printf("random '%s' ua at [%d]:\n", browser_names[random_ua.id], random_number);
        printf("%s\n", random_ua.item.buf);
        return 0;
    }

    Browser browser = { .id = browserid, .items = NULL, .len = 0, .cap = 0 };
    char path[128];
    snprintf(path, sizeof(path), "%s/%s.brs", dir, browser_names[browserid]);

    if (!fopen(path, "r")) {
        size_t byte_size = MAX_UA_NUM * sizeof *browser.items;
        browser.items = malloc(byte_size);
        if (!browser.items) {
            printf("not enough memory (malloc returned NULL)\n");
            return 1;
        }
        memset(browser.items, 0, byte_size);
        browser.cap = (uint8_t)MAX_UA_NUM;

        if (parse(browser.items, &browser.len, &random_ua, &random_number) == NULL) { free(browser.items); return 1; }

	pthread_t th;
        int created = 0;
	Cache pa = { .b = &browser, .p = path };
        if (pthread_create(&th, NULL, download_cache, &pa) == 0) created = 1;

	printf("random '%s' ua at [%d]:\n", browser_names[random_ua.id], random_number);
        printf("%s\n", random_ua.item.buf);
        printf("===============\n");
        for (uint8_t i = 0; i < browser.len; ++i) {
            printf("[%d] %s\n", i, browser.items[i].buf);
        }

        if (created) pthread_join(th, NULL);
        free(browser.items);
        return 0;
    }


    int result = read_cache(path, &random_ua);
    if (result == -1) return 1;

    printf("random '%s' ua at [%d]:\n", browser_names[random_ua.id], result);
    printf("%s\n", random_ua.item.buf);
    // printf("browser is %s, len is %d\n", browser_names[browser.id], browser.len);
    // for (uint8_t i = 0; i < browser.len; ++i) {
    //     printf("[%d] %s\n", i, browser.items[i].buf);
    //     printf("[%d] %s[%d]\n", i, browser.items[i].buf, browser.items[i].pos);
    // }
    return 0;
}

// clang -Wall -Wextra -Wunused-function -Wunused-variable -Wunused-parameter fakeua.c -lcurl -o fakeua
