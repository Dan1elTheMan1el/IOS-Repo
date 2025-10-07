import requests
import json

myApps = json.load(open("my-apps.json"))

repos = ["leminlimez/Pocket-Poster"]

for repo in repos:
    data = requests.get(f"https://api.github.com/repos/{repo}").json()
    readme = requests.get(f"https://raw.githubusercontent.com/{repo}/refs/heads/main/README.md").text

    name = data["name"]
    # bundleId
    author = data["owner"]["login"]
    subtitle = data["description"]
    localizedDescription = readme
    iconURL = data["owner"]["avatar_url"] # Maybe change to app icon later
    # tintColor
    # category
    # screenshots
    versions = []

    releases = requests.get(f"https://api.github.com/repos/{repo}/releases").json()

    for release in releases:
        version = release["tag_name"]
        date = release["published_at"]
        changelog = release["body"]
        downloadURL = release["assets"][0]["browser_download_url"]
        size = release["assets"][0]["size"]
        versions.append({
            "version": version,
            "date": date,
            "localizedDescription": changelog,
            "downloadURL": downloadURL,
            "size": size
        })
    
    app = {
        "name": name,
        "bundleId": "com.test.com",
        "developerName": author,
        "subtitle": subtitle,
        "localizedDescription": localizedDescription,
        "iconURL": iconURL,
        "versions": versions
    }

    myApps["apps"].append(app)

json.dump(myApps, open("test-repo.json", "w"), indent=4)