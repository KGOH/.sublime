import threading
import sublime
import os
import sublime_plugin
import os.path
import socket
import time
from contextlib import closing

def project_dir(self):
    folders = self.window.folders()

    file = None
    if view := self.window.active_view():
        file = view.file_name() 

    dir = None
    if len(folders) > 0:
        dir = next((f for f in folders if file.startswith(f)), folders[0])
    elif view and file:
        dir = os.path.dirname(file)
    else:
        dir = os.path.expanduser("~")   

    return dir


# def find_free_port():
#     with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
#         s.bind(('', 0))
#         s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
#         return s.getsockname()[1]
# 
# 
# def wait_for_port(port: int, host: str = 'localhost', timeout: float = 5.0):
#     """ MIT License Copyright (c) 2017 Michał Bultrowicz """
#     start_time = time.perf_counter()
#     while True:
#         try:
#             with socket.create_connection((host, port), timeout=timeout):
#                 break
#         except OSError as ex:
#             time.sleep(1)
#             if time.perf_counter() - start_time >= timeout:
#                 raise TimeoutError('Waited too long for the port {} on host {} to start accepting '
#                                    'connections.'.format(port, host)) from ex
# 
# 
# class MyWriteFreeReplPortCommand(sublime_plugin.WindowCommand):
#     def run(self): 
#         dir = project_dir(self)
#         with open(os.path.join(dir,'.repl-port'), 'w') as f:
#             f.write(str(find_free_port())) 
# 
# 
# class MyWaitForReplCommand(sublime_plugin.WindowCommand):
#     def run(self):
#         dir = project_dir(self) 
#         with open(os.path.join(dir,'.repl-port'), 'r') as f:
#             port = int(f.read()) 
#         wait_for_port(port)


class MyClojureJackInCommand(sublime_plugin.WindowCommand):
    def run(self):
        dir = project_dir(self) 
        if os.path.isfile(os.path.join(dir,'project.clj')):
            self.window.run_command(cmd="executor_execute_shell", args={'dir': dir, "command": '''freeport > .repl-port && echo "$(<.repl-port)" &&  lein repl :headless :port $(<.repl-port)'''})
            self.window.run_command(cmd="clojure_sublimed_connect_nrepl_raw", args={"address": 'auto', "timeout": 30})
        else:
            self.window.run_command(cmd="executor_execute_shell", args={'dir': dir, "command": """clojure -A:dev -M -e '(-> (clojure.core.server/start-server {:name "repl" :port 0 :accept (symbol "clojure.core.server/repl") :server-daemon false}) .getLocalPort (doto println) (->> (spit ".repl-port")))'"""})
            self.window.run_command(cmd="clojure_sublimed_connect_socket_repl", args={"address": 'auto', "timeout": 30})
