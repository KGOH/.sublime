import threading
import sublime
import os
import sublime_plugin
import os.path
import socket
import time
import json
from contextlib import closing
from collections import deque

def project_dir(window, view):
    folders = window.folders()

    file = None
    if view:
        file = view.file_name()

    dir = None
    if len(folders) > 0:
        dir = next((f for f in folders if file.startswith(f)), folders[0])
    elif view and file:
        dir = os.path.dirname(file)
    else:
        dir = os.path.expanduser("~")

    return dir


def current_dir(view):
    file = None
    if view:
        file = os.path.dirname(view.file_name())
    return file


def find_file_between(start_path, stop_path, filenames):
    start_path = os.path.normpath(start_path)
    stop_path = os.path.normpath(stop_path)

    if not start_path.startswith(stop_path):
        raise ValueError("stop_path must be a parent of start_path")

    current_path = start_path

    while True:
        for filename in filenames:
            file_path = os.path.join(current_path, filename)
            if os.path.isfile(file_path):
                return current_path

        if current_path == stop_path:
            return None

        current_path = os.path.dirname(current_path)


def bfs_find_file(start_path, filenames):
    start_path = os.path.normpath(start_path)
    queue = deque([start_path])
    while queue:
        current_path = queue.popleft()
        for filename in filenames:
            file_path = os.path.join(current_path, filename)
            if os.path.isfile(file_path):
                return current_path
        try:
            for entry in os.listdir(current_path):
                full_path = os.path.join(current_path, entry)
                if os.path.isdir(full_path):
                    queue.append(full_path)
        except PermissionError:
            continue
    return None


def find_proj_dir(window, view):
    dir = project_dir(window, view)
    cur = current_dir(view)
    proj = find_file_between(cur, dir, ["deps.edn", "project.clj"]) \
           or bfs_find_file(dir, ["deps.edn", "project.clj"]) \
           or dir
    return proj


def find_free_port():
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind(('', 0))
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return s.getsockname()[1]


def read_cache(cache_file):
  with open(cache_file, 'r') as cache:
      try:
          res = json.load(cache)
      except:
          pass
  return res or {}


def cache(cache_file, data):
  cache_data = read_cache(ALIAS_HISTORY_FILE)
  cache_data.update(data)
  with open(cache_file, 'w') as cache:
      json.dump(cache_data, cache, ensure_ascii=False, indent=2)


ALIAS_HISTORY_FILE = os.path.join(sublime.packages_path(), 'User', 'AliasHistory.txt')


class AliasInputHandler(sublime_plugin.TextInputHandler):
    def __init__(self, proj):
        self.proj = proj

    def name(self):
        return "alias"

    def initial_text(self):
        return read_cache(ALIAS_HISTORY_FILE).get(self.proj, ':dev:test')

    def confirm(self, value):
        cache(ALIAS_HISTORY_FILE, {self.proj: value})


class MyClojureJackInCommand(sublime_plugin.TextCommand):
    def run(self, edit, alias):
        view = self.view
        window = view.window()

        dir = find_proj_dir(window, view)
        port = find_free_port()

        aliases = "-A"+alias if bool(alias.strip()) else ""

        if os.path.isfile(os.path.join(dir,'project.clj')):
            window.run_command(cmd="executor_execute_shell", args={'dir': dir, "command": f'''lein repl :headless :port {port}'''})
            window.run_command(cmd="clojure_sublimed_connect_nrepl_raw", args={"address": f'localhost:{port}', "timeout": 30})
        else:
            #window.run_command(cmd="executor_execute_shell", args={'dir': dir, "command": f"""clojure {aliases} -M -e '(-> (clojure.core.server/start-server {:name "repl" :port 0 :accept (symbol "clojure.core.server/repl") :server-daemon false}) .getLocalPort (doto println) (->> (spit ".repl-port")))'"""})
            window.run_command(cmd="executor_execute_shell", args={'dir': dir, "command": f"""clojure {aliases} -X clojure.core.server/start-server :name repl :port "{port}" :accept clojure.core.server/repl :server-daemon false"""})
            window.run_command(cmd="clojure_sublimed_connect_socket_repl", args={"address": f'localhost:{port}', "timeout": 30})

    def input(self, args):
        dir = find_proj_dir(self.view.window(), self.view)
        if os.path.exists(os.path.join(dir, "deps.edn")):
            return AliasInputHandler(dir)
        else:
            return AliasInputHandler(dir) # TODO

