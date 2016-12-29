import yaml
import re
import git
import os
import sys
from termcolor import colored, cprint

#import pprint

class WebAppUpdater():
    def __init__(self):
        self._apps = []

    def run(self):
        with open("config/apps.yml", 'r') as ymlfile:
            self._apps = yaml.load(ymlfile)

        command = "check"
        if len(sys.argv) > 1:
            command = sys.argv[1]

        if command == "check":
            self.check_versions("config/installations.yml")
        elif command == "test_run":
            self.check_versions("config/installations-test.yml")
        elif command == "test_prepare":
            self.test_prepare()
        else:
            print("Unknown command")

    def test_prepare(self):
        installations = {}

        for app in self._apps:
            print(app)

            repo_path = os.path.join("test", app + ".git")
            installations[app + "-test"] = {"app":app, "path":repo_path }

            if not os.path.exists(repo_path):
                print("   Cloning repository...")
                repo = git.Repo()
                git.Repo.clone_from(self._apps[app]["url"], repo_path, depth=1)

        with open("config/installations-test.yml", 'w') as outfile:
            yaml.dump(installations, outfile, default_flow_style=False)

    def check_versions(self, configfile):
        with open(configfile, 'r') as ymlfile:
            installations = yaml.load(ymlfile)
            for inst in installations:

                current = self.get_current_version(installations[inst]['app'], installations[inst]['path'])
                latest = self.get_latest_version(installations[inst]['app'])

                color = "red"
                if current == latest:
                    color = "green"

                print("=== " + inst + " ===")
                print("App:     " + installations[inst]['app'])
                print("Path:    " + installations[inst]['path'])
                print("Latest:  " + latest)
                print("Current: " + colored(current, color))
                print()

    def get_current_version(self, app, path):
        file = os.path.join(path, self._apps[app]['current-file'])

        current_version = []

        with open(file, "r", encoding='utf8') as f:
            contents = f.read()
            pattern = self._apps[app]['current-regex']
            if isinstance(pattern, str):
                pattern = [pattern]

            for p in pattern:
                re.compile(p)
                for match in re.finditer(p, contents):
                    current_version.append(match.groups()[0])

        return ".".join(current_version)

    def get_latest_version(self, app):
        app = self._apps[app]
        pattern = re.compile(app['tag-regex'])

        latest_version = ""
        versions = []

        tags = self._get_tags(app['url'])

        for tag in tags:
            if re.match(app['tag-exclude'], tag, flags=re.IGNORECASE) is not None:
                continue
            
            match = pattern.match(tag)
            if match is not None:
                versions.append(match.groups())

        versions.sort(key= lambda row: tuple(0 if item is None or item == "" else (int(item) if item.isdigit() else item) for item in row))

        latest_version = ".".join(filter(None, versions[-1]))
        return latest_version

    def _get_tags(self, url):
        refs = self._lsremote_tags(url)
        tags = []

        for r in refs:
            r = r.replace("refs/tags/", "")
            r = r.replace("^{}", "")

            if not r in tags:
                tags.append(r)

        return tags

    def _lsremote_tags(self, url):
        remote_refs = {}
        g = git.cmd.Git()
        for ref in g.ls_remote("--tags", url).split('\n'):
            hash_ref_list = ref.split('\t')
            remote_refs[hash_ref_list[1]] = hash_ref_list[0]
        return remote_refs

    