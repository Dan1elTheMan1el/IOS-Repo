import requests
import json
import markdown
from bs4 import BeautifulSoup

myApps = json.load(open("my-apps.json"))
scraping = json.load(open("scraping.json"))

for repo_info in scraping:
    print(f"Scraping {repo_info['name']}...")
    repo = repo_info["github"]
    data = requests.get(f"https://api.github.com/repos/{repo}").json()

    readme = requests.get(f"https://raw.githubusercontent.com/{repo}/refs/heads/main/README.md").text
    html = markdown.markdown(readme)
    soup = BeautifulSoup(html, 'html.parser')

    name = repo_info["name"]
    author = data["owner"]["login"] if "owner" in data and "login" in data["owner"] else "Unknown"
    subtitle = data["description"]
    localizedDescription = soup.get_text(separator="\n")
    versions = []

    print("Getting latest release...")
    releases = requests.get(f"https://api.github.com/repos/{repo}/releases").json()

    for release in releases:
        version = release["tag_name"].replace("v", "")
        date = release["published_at"]
        markdown_body = markdown.markdown(release["body"])
        html_body = BeautifulSoup(markdown_body, 'html.parser')
        for asset in release["assets"]:
            if asset["browser_download_url"].endswith(".ipa"):
                downloadURL = asset["browser_download_url"]
                size = asset["size"]
                break
        versions.append({
            "version": version,
            "date": date,
            "localizedDescription": html_body.get_text(separator="\n"),
            "downloadURL": downloadURL,
            "size": size
        })

    bundleID = repo_info["bundleID"]

    print("Downloading icon...")
    if "iconURL" in repo_info:
        icon = requests.get(repo_info["iconURL"]).content
        with open("scrapedIcons/" + bundleID + ".png", "wb") as f:
            f.write(icon)
        iconURL = "https://raw.githubusercontent.com/Dan1elTheMan1el/IOS-Repo/refs/heads/main/scrapedIcons/" + bundleID + ".png"
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

print("Saving altstore-repo.json...")
json.dump(myApps, open("altstore-repo.json", "w"), indent=4)