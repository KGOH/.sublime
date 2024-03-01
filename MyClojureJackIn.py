import threading
import sublime
import os
import sublime_plugin
import os.path

class MyClojureJackInCommand(sublime_plugin.WindowCommand):
    def run(self):
        dir = None
        if len(self.window.folders()) > 0:
            dir = self.window.folders()[0]
        elif (view := self.window.active_view()) and (file := self.view.file_name()):
            dir = os.path.dirname(file)
        else:
            dir = os.path.expanduser("~")   

        if os.path.isfile(os.path.join(dir,'deps.edn')):
            self.window.run_command(cmd="executor_execute_shell", args={"command": 'freeport > .repl-port && echo "$(<.repl-port)" && clojure  -X clojure.core.server/start-server :name repl :port "$(<.repl-port)" :accept clojure.core.server/repl :server-daemon false'})
        elif os.path.isfile(os.path.join(dir,'project.clj')):
            self.window.run_command(cmd="executor_execute_shell", args={"command": 'freeport > .repl-port && echo "$(<.repl-port)" && LEIN_JVM_OPTS=-Dclojure.server.repl="{:port,$(<.repl-port),:accept,clojure.core.server/repl}" lein repl :headless'})
        else:
            1/0

        threading.Timer(3.0, lambda: self.window.run_command(cmd="clojure_sublimed_connect_socket_repl", args={"address": 'auto'})).start()
        