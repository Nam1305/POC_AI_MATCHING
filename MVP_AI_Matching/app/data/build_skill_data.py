import json
import time
import urllib.request
import urllib.error
import urllib.parse
from pathlib import Path

API_URL = "https://api.stackexchange.com/2.3/tags/{tags}/synonyms"
API_KEY = "rl_jhttsMQSyHxneGGpPzxvmLxyt"
SITE = "stackoverflow"
PAGE_SIZE = 100
BATCH_SIZE = 20
SLEEP_SECONDS = 1

INPUT_FILE = Path(__file__).parent / "so_raw_data.json"
OUTPUT_FILE = Path(__file__).parent / "skill_data.json"


def fetch_synonyms(tag_names: list[str], page: int = 1) -> dict:
    encoded = ";".join(urllib.parse.quote(t, safe="") for t in tag_names)
    url = API_URL.format(tags=encoded)
    url += f"?site={SITE}&pagesize={PAGE_SIZE}&page={page}&key={API_KEY}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req) as resp:
        raw = resp.read()
    return json.loads(raw)


def chunked(items: list, size: int):
    for i in range(0, len(items), size):
        yield items[i:i + size]


def main():
    with open(INPUT_FILE, encoding="utf-8") as f:
        tags = json.load(f)

    result = {}
    synonym_tags = []

    for tag in tags:
        name = tag["name"]
        if tag.get("has_synonyms"):
            synonym_tags.append(name)
            result[name] = name
        else:
            result[name] = None

    for batch in chunked(synonym_tags, BATCH_SIZE):
        page = 1
        while True:
            try:
                data = fetch_synonyms(batch, page)
            except urllib.error.HTTPError as e:
                print(f"Batch {batch} FAILED: HTTP {e.code}")
                break
            except urllib.error.URLError as e:
                print(f"Batch {batch} FAILED: {e.reason}")
                break

            for item in data.get("items", []):
                result[item["from_tag"]] = item["to_tag"]

            print("OK")

            if not data.get("has_more", False):
                break
            page += 1
            time.sleep(SLEEP_SECONDS)

        time.sleep(SLEEP_SECONDS)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"Done. Wrote {len(result)} entries to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
