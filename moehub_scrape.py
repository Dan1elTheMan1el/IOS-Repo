import re
import json
import cloudscraper
from bs4 import BeautifulSoup

def scrape_app_from_card(card, base_app):
    name = base_app.get("name", "")
    bundle_id = base_app.get("bundleID", "")
    icon_url = base_app.get("iconURL", "")
    if not name:
        name = card.get("data-name", "").strip()
    if not name:
        h3 = card.find("h3")
        if h3:
            name = h3.get_text(strip=True)

    version_span = card.select_one(".app-meta-row span:first-child")
    version = version_span.get_text(strip=True).lstrip("v") if version_span else ""

    size_span = card.select_one(".app-meta-row span:nth-child(2)")
    file_size_str = size_span.get_text(strip=True) if size_span else ""

    filename_div = card.select_one(".filename-info")
    filename = filename_div.get_text(strip=True) if filename_div else ""

    desc_p = card.select_one(".app-description")
    description = desc_p.get_text(strip=True) if desc_p else ""

    category_div = card.select_one(".app-category")
    category = category_div.get_text(strip=True) if category_div else ""

    download_link = card.select_one("a.app-action.primary")
    download_url = ""
    if download_link:
        download_url = download_link.get("href", "")

    img = card.select_one(".app-icon img")
    if not icon_url and img:
        icon_url = img.get("src", "")

    size_bytes = 0
    if file_size_str:
        size_num = re.search(r"([\d.]+)\s*(MB|GB|KB)", file_size_str, re.I)
        if size_num:
            val = float(size_num.group(1))
            unit = size_num.group(2).upper()
            if unit == "GB":
                size_bytes = int(val * 1024 * 1024 * 1024)
            elif unit == "MB":
                size_bytes = int(val * 1024 * 1024)
            elif unit == "KB":
                size_bytes = int(val * 1024)

    updated_date = card.get("data-updated", "")

    return {
        "name": name,
        "bundleID": bundle_id,
        "version": version,
        "description": description,
        "category": category,
        "downloadURL": download_url,
        "iconURL": icon_url,
        "size": size_bytes,
        "filename": filename,
        "updated": updated_date
    }

def fetch_page(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    }

    scraper = cloudscraper.create_scraper()
    resp = scraper.get(url, headers=headers, timeout=30)
    if resp.status_code == 200:
        return resp.text

    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url, timeout=30000)
            content = page.content()
            browser.close()
            return content
    except ImportError:
        pass
    except Exception as e:
        print(f"  Playwright also failed: {e}")

    raise Exception(
        f"Failed to fetch {url}: HTTP {resp.status_code}. "
        "The site is behind CloudFlare. Try:\n"
        "1. Install playwright: pip install playwright && playwright install chromium\n"
        "2. Or use Wayback Machine: set use_wayback=True in config\n"
        "3. Or manually provide cached HTML"
    )

def scrape_all_apps(main_url, apps_config):
    html = fetch_page(main_url)

    soup = BeautifulSoup(html, "html.parser")
    cards = soup.select("div.app-card")
    if not cards:
        print("Warning: No .app-card elements found. Site structure may have changed.")
        return []

    results = []
    seen_urls = set()
    app_config_map = {}
    for cfg in apps_config:
        key = (cfg.get("name", "").lower(), cfg.get("bundleID", ""))
        app_config_map[key] = cfg

    for card in cards:
        card_name = card.get("data-name", "").strip().lower()
        h3 = card.find("h3")
        card_heading = h3.get_text(strip=True).lower() if h3 else ""

        matched_cfg = None
        for (cfg_name, cfg_bid), cfg in app_config_map.items():
            if not cfg_name and not cfg_bid:
                continue
            if cfg_name:
                cn = cfg_name.lower()
                if card_name == cn or card_heading == cn:
                    matched_cfg = cfg
                    break
                if card_name.startswith(cn) or card_heading.startswith(cn):
                    matched_cfg = cfg
                    break
            if cfg_bid and card.get("data-bundle"):
                if card["data-bundle"] == cfg_bid:
                    matched_cfg = cfg
                    break
        if not matched_cfg and apps_config:
            continue

        base = matched_cfg or {}
        app_data = scrape_app_from_card(card, base)
        if app_data["downloadURL"] and app_data["downloadURL"] not in seen_urls:
            seen_urls.add(app_data["downloadURL"])
            results.append(app_data)

    return results

def convert_to_altstore_format(apps, source_name, source_icon):
    altstore_apps = {}
    for app in apps:
        bid = app["bundleID"]
        if not bid:
            bid = "com.moehub." + re.sub(r"[^a-zA-Z0-9]", "", app["name"]).lower()
            app["bundleID"] = bid

        versions = []
        if app["version"] and app["downloadURL"]:
            versions.append({
                "version": app["version"],
                "date": app["updated"] or "",
                "localizedDescription": app.get("description", ""),
                "downloadURL": app["downloadURL"],
                "size": app["size"]
            })

        if bid in altstore_apps:
            altstore_apps[bid]["versions"].extend(versions)
            continue

        altstore_apps[bid] = {
            "name": app["name"],
            "bundleIdentifier": bid,
            "developerName": "Moe's App Hub",
            "subtitle": app.get("category", ""),
            "localizedDescription": app.get("description", ""),
            "iconURL": app.get("iconURL", source_icon),
            "versions": versions
        }

    return {
        "name": source_name,
        "iconURL": source_icon,
        "apps": list(altstore_apps.values())
    }

if __name__ == "__main__":
    import sys
    url = sys.argv[1] if len(sys.argv) > 1 else "https://moe.mohkg1017.pro"
    config_path = sys.argv[2] if len(sys.argv) > 2 else "resources/moehub-apps.json"
    output_path = sys.argv[3] if len(sys.argv) > 3 else "moehub-output.json"

    with open(config_path) as f:
        config = json.load(f)

    apps = scrape_all_apps(url, config.get("apps", []))
    result = convert_to_altstore_format(
        apps,
        config.get("name", "Moe's App Hub"),
        config.get("iconURL", "")
    )

    with open(output_path, "w") as f:
        json.dump(result, f, indent=2)

    print(f"Scraped {len(apps)} apps, saved to {output_path}")
