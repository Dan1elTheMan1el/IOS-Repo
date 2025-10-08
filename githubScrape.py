import requests
import json
import zipfile
import os
import plistlib
import pyipng

myApps = json.load(open("my-apps.json"))

repos = ["leminlimez/Pocket-Poster"]

for repo in repos:
    data = requests.get(f"https://api.github.com/repos/{repo}").json()
    readme = requests.get(f"https://raw.githubusercontent.com/{repo}/refs/heads/main/README.md").text

    author = data["owner"]["login"]
    subtitle = data["description"]
    localizedDescription = readme
    versions = []

    releases = requests.get(f"https://api.github.com/repos/{repo}/releases").json()

    for release in releases:
        version = release["tag_name"].replace("v", "")
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
    
    latestURL = releases[0]["assets"][0]["browser_download_url"]
    ipaFile = requests.get(latestURL)
    with open("latest.ipa", "wb") as f:
        f.write(ipaFile.content)
    with zipfile.ZipFile("latest.ipa", "r") as zip_ref:
        zip_ref.extractall("latest_ipa_unzipped")
    
    app_dirs = [f for f in os.listdir("latest_ipa_unzipped/Payload/") if f.endswith(".app")][0]
    name = app_dirs.replace(".app", "")

    plist = plistlib.load(open(f"latest_ipa_unzipped/Payload/{app_dirs}/Info.plist", "rb"))
    bundleID = plist["CFBundleIdentifier"]

    icons = [f for f in os.listdir(f"latest_ipa_unzipped/Payload/{app_dirs}") if f.endswith(".png")]
    largest_icon = max(
        icons,
        key=lambda icon: os.path.getsize(os.path.join(f"latest_ipa_unzipped/Payload/{app_dirs}", icon))
    )
    icon = open(os.path.join(f"latest_ipa_unzipped/Payload/{app_dirs}", largest_icon), "rb").read()
    icon = pyipng.convert(icon)
    with open(f"scrapedIcons/{bundleID}.png", "wb") as f:
        f.write(icon)
    iconURL = f"https://raw.githubusercontent.com/Dan1elTheMan1el/IOS-Repo/refs/heads/main/scrapedIcons/{bundleID}.png"

    app = {
        "name": name,
        "bundleIdentifier": bundleID,
        "developerName": author,
        "subtitle": subtitle,
        "localizedDescription": localizedDescription,
        "iconURL": iconURL,
        "versions": versions
    }

    os.remove("latest.ipa")
    os.system("rm -rf latest_ipa_unzipped")

    myApps["apps"].append(app)
    
json.dump(myApps, open("altstore-repo.json", "w"), indent=4)