import requests
import json
import markdown
from bs4 import BeautifulSoup
from urllib.parse import urlparse, quote_plus
from moehub_scrape import scrape_all_apps

_moehub_cache = {}

myApps = json.load(open("resources/my-apps.json"))
scraping = json.load(open("resources/scraping.json"))
readMe = open("resources/README_template.txt").read()

myAppTable = ""
for app in myApps["apps"]:
    myAppTable += f"|<img src=\"{app['iconURL']}\" alt=\"{app['name']}\" width=\"100\" height=\"100\" style=\"border-radius: 20px\">|[{app['name']}](https://github.com/{app['github']})|{app['versions'][0]['version']}|\n"
readMe = readMe.replace("# MY APPS TABLE", myAppTable)

scrapedAppTable = ""
for repo_info in scraping:
    print(f"Scraping {repo_info['name']}...")

    name = repo_info["name"]
    versions = []

    if "github" in repo_info:
        repo = repo_info["github"]
        data = requests.get(f"https://api.github.com/repos/{repo}").json()

        readme = requests.get(f"https://raw.githubusercontent.com/{repo}/refs/heads/main/README.md").text
        html = markdown.markdown(readme)
        soup = BeautifulSoup(html, 'html.parser')

        author = data["owner"]["login"] if "owner" in data and "login" in data["owner"] else "Unknown"
        subtitle = data["description"]
        localizedDescription = soup.get_text().strip()

        print("Getting latest release...")
        releases = requests.get(f"https://api.github.com/repos/{repo}/releases").json()

        for release in releases:
            version = release["tag_name"].lstrip("v")
            date = release["published_at"]
            markdown_body = markdown.markdown(release["body"])
            html_body = BeautifulSoup(markdown_body, 'html.parser')
            downloadURL = ""
            for asset in release["assets"]:
                if asset["browser_download_url"].endswith(".ipa"):
                    downloadURL = asset["browser_download_url"]
                    size = asset["size"]
                    break
            if downloadURL == "":
                continue
            versions.append({
                "version": version,
                "date": date,
                "localizedDescription": html_body.get_text(),
                "downloadURL": downloadURL,
                "size": size
            })
    elif "gitlab" in repo_info:
        host = urlparse(repo_info["gitlab"]).netloc
        path = urlparse(repo_info["gitlab"]).path
        data = requests.get(f"https://{host}/api/v1/repos/{path.lstrip('/')}").json()

        readme = requests.get(f"https://{host}/api/v1/repos/{path.lstrip('/')}/media/README.md").text
        html = markdown.markdown(readme)
        soup = BeautifulSoup(html, 'html.parser')

        subtitle = data["description"]
        localizedDescription = soup.get_text().strip()

        print("Getting latest release...")
        releases = requests.get(f"https://{host}/api/v1/repos/{path.lstrip('/')}/releases").json()
        author = releases[0]["author"]["full_name"] if "author" in releases[0] and "full_name" in releases[0]["author"] else "Unknown"

        for release in releases:
            version = release["tag_name"].lstrip("v")
            date = release["published_at"]
            markdown_body = markdown.markdown(release["body"])
            html_body = BeautifulSoup(markdown_body, 'html.parser')
            downloadURL = ""
            for asset in release["assets"]:
                if asset["name"].endswith(".ipa"):
                    downloadURL = asset["browser_download_url"]
                    size = asset["size"]
                    break
            if downloadURL == "":
                continue
            versions.append({
                "version": version,
                "date": date,
                "localizedDescription": html_body.get_text(),
                "downloadURL": downloadURL,
                "size": size
            })
    elif "moehub" in repo_info:
        print("Scraping via Moe's App Hub...")
        url = repo_info["moehub"]
        if url not in _moehub_cache:
            app_configs = [r for r in scraping if r.get("moehub") == url]
            _moehub_cache[url] = scrape_all_apps(url, app_configs)
        all_apps = _moehub_cache[url]

        matched = None
        for app in all_apps:
            if app["bundleID"] == repo_info["bundleID"] or app["name"].lower() == repo_info["name"].lower():
                matched = app
                break
        if not matched:
            print(f"  Could not find {repo_info['name']} on Moe's App Hub")
            continue

        name = matched["name"]
        author = repo_info.get("developerName", "Moe's App Hub")
        subtitle = matched.get("category", "")
        localizedDescription = matched.get("description", "")

        if matched["version"]:
            versions.append({
                "version": matched["version"],
                "date": matched.get("updated", ""),
                "localizedDescription": localizedDescription,
                "downloadURL": matched["downloadURL"],
                "size": matched["size"]
            })
    else:
        print(f"Unknown repo type for {repo_info['name']}")
        continue

    bundleID = repo_info["bundleID"]

    print("Downloading icon...")
    icon_source = repo_info.get("iconURL", "")
    if not icon_source and "moehub" in repo_info and matched:
        icon_source = matched.get("iconURL", "")
    if icon_source:
        try:
            icon = requests.get(icon_source).content
            with open("scrapedIcons/" + bundleID + ".png", "wb") as f:
                f.write(icon)
            iconURL = "https://raw.githubusercontent.com/Dan1elTheMan1el/IOS-Repo/refs/heads/main/scrapedIcons/" + bundleID + ".png"
        except:
            iconURL = "https://raw.githubusercontent.com/Dan1elTheMan1el/IOS-Repo/refs/heads/main/scrapedIcons/empty.png"
    else:
        iconURL = "https://raw.githubusercontent.com/Dan1elTheMan1el/IOS-Repo/refs/heads/main/scrapedIcons/empty.png"

    app = {
        "name": name,
        "bundleIdentifier": bundleID,
        "developerName": author,
        "subtitle": subtitle,
        "localizedDescription": localizedDescription,
        "iconURL": iconURL,
        "versions": versions
    }

    myApps["apps"].append(app)
    link = repo_info.get("gitlab") or (f"https://github.com/{repo_info['github']}" if "github" in repo_info else repo_info.get("moehub", ""))
    scrapedAppTable += f"|<img src=\"{iconURL}\" alt=\"{name}\" width=\"100\" height=\"100\" style=\"border-radius: 20px\">|[{name}]({link})|{versions[0]['version']}|\n"
readMe = readMe.replace("# AUTO SCRAPED TABLE", scrapedAppTable)

print("Saving altstore-repo.json...")
json.dump(myApps, open("altstore-repo.json", "w"), indent=4)

print("Saving README.md...")
with open("README.md", "w") as f:
    f.write(readMe)