import yaml
import re
import git
import os
import sys
import hashlib
import time
import json
from termcolor import colored, cprint

#import pprint

class WebAppUpdater():
    def __init__(self):
        self._apps = []
        self._testdir = "test"
        self._configdir = "config"
        self._cachedir = "cache"
        self._cache_age = 3600

    def run(self):
        with open("config/apps.yml", 'r') as ymlfile:
            self._apps = yaml.load(ymlfile)

        command = "check"
        if len(sys.argv) > 1:
            command = sys.argv[1]

        if command == "check":
            self.check_versions(os.path.join(self._configdir, "installations.yml"))
        elif command == "test_run":
            self.check_versions(os.path.join(self._configdir, "installations-test.yml"))
        elif command == "test_prepare":
            self.test_prepare()
        else:
            print("Unknown command")

    def test_prepare(self):
        installations = {}

        if not os.path.exists(self._testdir):
            os.makedirs(self._testdir)

        for app in self._apps:
            print(app)

            repo_path = os.path.join(self._testdir, app + ".git")
            installations[app + "-test"] = {"app":app, "path":repo_path }

            if not os.path.exists(repo_path):
                print("   Cloning repository...")
                repo = git.Repo()
                git.Repo.clone_from(self._apps[app]["url"], repo_path, depth=1)

        with open(s.path.join(self._configdir, "installations-test.yml"), 'w') as outfile:
            yaml.dump(installations, outfile, default_flow_style=False)

    def check_versions(self, configfile):
        with open(configfile, 'r') as ymlfile:
            installations = yaml.load(ymlfile)
            for inst in installations:

                print("=== " + inst + " ===")
                print(" App:     " + installations[inst]['app'])
                print(" Path:    " + installations[inst]['path'])

                current = self.get_current_version(installations[inst]['app'], installations[inst]['path'])
                latest = self.get_latest_version(installations[inst]['app'])

                compare = self._compare_versions(current, latest)
                if compare < 0:
                    print(" Version: " + colored(self._format_version(current), "red") + " < " + self._format_version(latest))
                elif compare == 0:
                    print(" Version: " + colored(self._format_version(current), "green"))
                elif compare > 0:
                    print(" Version: " + colored(self._format_version(current), "yellow") + " > " + self._format_version(latest))

                print()

    def _format_version(self, version):
        s = ""
        for n in version:
            if len(s) > 0:
                if n.isdigit():
                    s += "."
                else:
                    s += "-"
            s += n

        return s

    def _compare_versions(self, v1, v2):
        for i in range(0, min(len(v1), len(v2))):
            if (not v1[i].isdigit()) or not (v2[i].isdigit()):
                break

            if int(v1[i]) > int(v2[i]):
                return 1
            elif int(v1[i]) < int(v2[i]):
                return -1
            
        return 0

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
                    current_version.extend(match.groups())

        return [x for x in current_version if x is not None and x is not ""]

    def get_latest_version(self, app):
        app = self._apps[app]
        pattern = re.compile(app['tag-regex'])

        versions = []

        tags = self._get_tags(app['url'])

        for tag in tags:
            if re.match(app['tag-exclude'], tag, flags=re.IGNORECASE) is not None:
                continue
            
            match = pattern.match(tag)
            if match is not None:
                versions.append(match.groups())

        versions.sort(key= lambda row: tuple(0 if item is None or item == "" else (int(item) if item.isdigit() else item) for item in row))

        return [x for x in versions[-1] if x is not None and x is not ""]

    def _get_tags(self, url):
        refs = self._lsremote_tags_cached(url)
        tags = []

        for r in refs:
            r = r.replace("refs/tags/", "")
            r = r.replace("^{}", "")

            if not r in tags:
                tags.append(r)

        return tags

    def _lsremote_tags_cached(self, url):
        key = hashlib.sha1(url.encode()).hexdigest()

        if not os.path.exists(self._cachedir):
            os.makedirs(self._cachedir)
        cachefile = os.path.join(self._cachedir, key)

        if os.path.isfile(cachefile):
            if os.path.getmtime(cachefile) > time.time() - self._cache_age:
                with open(cachefile, "r", encoding='utf8') as f:
                    data = f.read()
                    return json.loads(data)

        data = self._lsremote_tags(url)
        
        with open(cachefile, "w", encoding='utf8') as f:
            jdata = json.dumps(data)
            f.write(jdata)

        return data

    def _lsremote_tags(self, url):
        remote_refs = {}
        g = git.cmd.Git()
        for ref in g.ls_remote("--tags", url).split('\n'):
            hash_ref_list = ref.split('\t')
            remote_refs[hash_ref_list[1]] = hash_ref_list[0]
        return remote_refs

    