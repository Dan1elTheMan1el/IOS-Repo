import requests
import json
import markdown
from bs4 import BeautifulSoup
from urllib.parse import urlparse, quote_plus

myApps = json.load(open("resources/my-apps.json"))
scraping = json.load(open("resources/scraping.json"))
readMe = open("resources/README_template.txt").read()
try:
    cachedApps = json.load(open("altstore-repo.json"))["apps"]
except (FileNotFoundError, json.JSONDecodeError, KeyError):
    cachedApps = myApps["apps"]

myAppTable = ""
for app in myApps["apps"]:
    myAppTable += f"|<img src=\"{app['iconURL']}\" alt=\"{app['name']}\" width=\"100\" height=\"100\" style=\"border-radius: 20px\">|[{app['name']}](https://github.com/{app['github']})|{app['versions'][0]['version']}|\n"
readMe = readMe.replace("# MY APPS TABLE", myAppTable)

scrapedAppTable = ""
for repo_info in scraping:
    print(f"Scraping {repo_info['name']}...")

    name = repo_info["name"]
    bundleID = repo_info["bundleID"]
    cachedApp = next((app for app in cachedApps if app.get("bundleIdentifier") == bundleID), {})
    versions = []
    requestFailed = []
    author = cachedApp.get("developerName", "")
    subtitle = cachedApp.get("subtitle", "")
    localizedDescription = cachedApp.get("localizedDescription", "")

    try:
        if "github" in repo_info:
            repo = repo_info["github"]
            dataResponse = requests.get(f"https://api.github.com/repos/{repo}", timeout=15)
            dataResponse.raise_for_status()
            data = dataResponse.json()

            readmeResponse = requests.get(f"https://raw.githubusercontent.com/{repo}/refs/heads/main/README.md", timeout=15)
            readmeResponse.raise_for_status()
            html = markdown.markdown(readmeResponse.text)
            soup = BeautifulSoup(html, 'html.parser')

            author = data["owner"]["login"] if "owner" in data and "login" in data["owner"] else "Unknown"
            subtitle = data.get("description") or ""
            localizedDescription = soup.get_text().strip()

            print("Getting latest release...")
            releasesResponse = requests.get(f"https://api.github.com/repos/{repo}/releases", timeout=15)
            releasesResponse.raise_for_status()
            releases = releasesResponse.json()

            for release in releases:
                version = release["tag_name"].lstrip("v")
                date = release["published_at"]
                markdown_body = markdown.markdown(release.get("body") or "")
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
            dataResponse = requests.get(f"https://{host}/api/v1/repos/{path.lstrip('/')}", timeout=15)
            dataResponse.raise_for_status()
            data = dataResponse.json()

            readmeResponse = requests.get(f"https://{host}/api/v1/repos/{path.lstrip('/')}/media/README.md", timeout=15)
            readmeResponse.raise_for_status()
            html = markdown.markdown(readmeResponse.text)
            soup = BeautifulSoup(html, 'html.parser')

            subtitle = data.get("description") or ""
            localizedDescription = soup.get_text().strip()

            print("Getting latest release...")
            releasesResponse = requests.get(f"https://{host}/api/v1/repos/{path.lstrip('/')}/releases", timeout=15)
            releasesResponse.raise_for_status()
            releases = releasesResponse.json()
            author = releases[0]["author"]["full_name"] if releases and "author" in releases[0] and "full_name" in releases[0]["author"] else "Unknown"

            for release in releases:
                version = release["tag_name"].lstrip("v")
                date = release["published_at"]
                markdown_body = markdown.markdown(release.get("body") or "")
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
        else:
            raise ValueError("unknown repo type")
    except (KeyError, TypeError, ValueError, requests.RequestException) as error:
        print(f"Request failed for {name}: {error}")
        requestFailed.append("metadata")
        versions = cachedApp.get("versions", [])

    print("Downloading icon...")
    if "iconURL" in repo_info:
        try:
            iconResponse = requests.get(repo_info["iconURL"], timeout=15)
            iconResponse.raise_for_status()
            with open("scrapedIcons/" + bundleID + ".png", "wb") as f:
                f.write(iconResponse.content)
            iconURL = "https://raw.githubusercontent.com/Dan1elTheMan1el/IOS-Repo/refs/heads/main/scrapedIcons/" + bundleID + ".png"
        except requests.RequestException as error:
            print(f"Icon request failed for {name}: {error}")
            requestFailed.append("icon")
            iconURL = cachedApp.get("iconURL", "https://raw.githubusercontent.com/Dan1elTheMan1el/IOS-Repo/refs/heads/main/scrapedIcons/empty.png")
    else:
        iconURL = cachedApp.get("iconURL", "https://raw.githubusercontent.com/Dan1elTheMan1el/IOS-Repo/refs/heads/main/scrapedIcons/empty.png")

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
    link = repo_info["gitlab"] if "gitlab" in repo_info else f"https://github.com/{repo_info['github']}"
    version = versions[0]["version"] if versions else ""
    failureNote = " request failed" if requestFailed else ""
    scrapedAppTable += f"|<img src=\"{iconURL}\" alt=\"{name}\" width=\"100\" height=\"100\" style=\"border-radius: 20px\">|[{name}]({link})|{version}{failureNote}|\n"
readMe = readMe.replace("# AUTO SCRAPED TABLE", scrapedAppTable)

print("Saving altstore-repo.json...")
json.dump(myApps, open("altstore-repo.json", "w"), indent=4)

print("Saving README.md...")
with open("README.md", "w") as f:
    f.write(readMe)