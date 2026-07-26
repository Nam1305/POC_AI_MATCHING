import json
import time
import urllib.request
import urllib.error
from pathlib import Path

API_URL = "https://api.stackexchange.com/2.3/tags"
API_KEY = "rl_jhttsMQSyHxneGGpPzxvmLxyt"
SITE = "stackoverflow"
PAGE_SIZE = 100
START_PAGE = 1
SLEEP_SECONDS = 2

OUTPUT_FILE = Path(__file__).parent / "so_raw_data.json"


def fetch_page(page: int) -> dict:
    params = f"?site={SITE}&pagesize={PAGE_SIZE}&page={page}&key={API_KEY}"
    url = API_URL + params
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req) as resp:
        raw = resp.read()
    return json.loads(raw)


def is_collective_tag(item: dict) -> bool:
    return bool(item.get("collectives"))


def main():
    all_items = []
    page = START_PAGE

    while True:
        try:
            data = fetch_page(page)
        except urllib.error.HTTPError as e:
            print(f"Page {page} FAILED: HTTP {e.code}")
            break
        except urllib.error.URLError as e:
            print(f"Page {page} FAILED: {e.reason}")
            break

        items = data.get("items", [])
        filtered = [item for item in items if not is_collective_tag(item)]
        all_items.extend(filtered)
        print("OK")

        if not data.get("has_more", False):
            break

        page += 1
        time.sleep(SLEEP_SECONDS)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(all_items, f, ensure_ascii=False, indent=2)

    print(f"Done. Wrote {len(all_items)} items to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
