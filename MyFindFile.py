import sublime
import os
import sublime_plugin
import urllib.parse
import Folder2Project.folder2project


def current_folder_from_lsp_uri(view):
    if lsp_uri := view.settings().get("lsp_uri"):
        if lsp_uri.startswith("zipfile://"):
            parsed = urllib.parse.urlparse(lsp_uri)
            archive, file = parsed.path.split("::")
            path = archive
            return path


def make_full_path(start, path):
    # NOTE: I don't remember why I do relpath and then normpath, looks redundand
    current_file = os.path.relpath(path, start=start) if path else start
    return os.path.normpath(os.path.join(start, current_file)) 


def get_current_folder(window):
    home = os.path.expanduser('~')
    start = window.extract_variables().get('folder', home) 
    path =  window.extract_variables().get('file_path') \
            or current_folder_from_lsp_uri(window.active_view())
    full_path = make_full_path(start, path) 
    current_folder = full_path if os.path.isdir(full_path) else os.path.dirname(full_path)
    return current_folder


def safe_listdir(path):
    try:
        return os.listdir(path)
    except Exception as e:
        return []


def make_file_list(path, only_folders=False):
    listdir = safe_listdir(path)

    dirs = sorted(el + '/' for el in listdir if os.path.isdir(os.path.join(path, el)))
    files = sorted(el for el in listdir if not os.path.isdir(os.path.join(path, el)))

    dir_content = dirs if only_folders else dirs + files
    hidden = [el for el in dir_content if el[0] == "."]
    public = [el for el in dir_content if el[0] != "."] 

    return public + hidden


def shorten_str_left(str, max_len, ellipsis="..."):
    if len(str) <= max_len:
        return str
    else:
        return ellipsis + str[-(max_len-len(ellipsis)):] 


def safe_readlines(filename):
    if not os.path.exists(filename):
        return []
    else: 
        with open(filename, 'r') as file:
            return file.readlines()


FOLDER_HISTORY_FILE = os.path.join(sublime.packages_path(), 'User', 'FolderHistory.txt')


def dedupe(seq):
    seen = set()
    seen_add = seen.add
    return [x for x in seq if not (x in seen or seen_add(x))]


def read_log_folder_history():
    return safe_readlines(FOLDER_HISTORY_FILE) 


def write_log_folder_history(folder):
    new_history = dedupe([folder + "\n"] + read_log_folder_history())[:100]
    with open(FOLDER_HISTORY_FILE, 'w') as file:
        file.writelines(new_history)


def open_folder(window, folder_path, new_window=False):
    if new_window:
        window.run_command(cmd="new_os_tab")
        window = sublime.active_window() 
    Folder2Project.folder2project.open_folder_as_project(window, folder_path)
    write_log_folder_history(folder_path)
    sublime.set_timeout_async(delay=50, callback=(lambda: window.run_command(cmd="show_overlay", args={"overlay": "goto", "show_files": True})))
     

def new_file_dialog(window, path):
    create_file = (lambda input: window.open_file(os.path.join(current_folder, input)))
    supress = (lambda _: None) 
    window.show_input_panel("File name:", "", create_file, supress, supress) 


class MyRecentFoldersCommand(sublime_plugin.WindowCommand):
    def run(self, new_window=False):
        els = read_log_folder_history()
        def on_select(idx):
            if idx >= 0:
                open_folder(self.window, els[idx].strip(), new_window=new_window)
        self.window.show_quick_panel(els, on_select=on_select)


class MyFindFileCommand(sublime_plugin.WindowCommand):
    NEW_FILE = sublime.QuickPanelItem(trigger="    New file", annotation="Creates a new file here")
    THIS_DIR = sublime.QuickPanelItem(trigger="    This folder", annotation="Opens this folder in the current window")
    THIS_DIR_PROJ = sublime.QuickPanelItem(trigger="    This folder as project", annotation="Opens this folder in a new window")

    def run(self, only_folders=False):
        self.show_find_file_overlay(get_current_folder(self.window) + '/', only_folders=only_folders)

    def show_find_file_overlay(self, current_folder, only_folders=False):
        file_list = make_file_list(current_folder, only_folders) 
        els = ["../"] + file_list + [self.NEW_FILE, self.THIS_DIR, self.THIS_DIR_PROJ]
        def on_select(idx):
            if idx >= 0:
                self.select_find_file(current_folder, els[idx])
        placeholder = shorten_str_left(current_folder, 80)
        self.window.show_quick_panel(els, on_select=on_select, placeholder=placeholder)

    def select_find_file(self, current_folder, selected):
        if selected == self.NEW_FILE:
            new_file_dialog(self.window, current_folder)
        elif selected == self.THIS_DIR:
            open_folder(self.window, current_folder)
        elif selected == self.THIS_DIR_PROJ:
            open_folder(self.window, current_folder, new_window=True)
        else:
            selected_path = os.path.normpath(os.path.join(current_folder, selected))
            if os.path.isdir(selected_path):
                self.show_find_file_overlay(selected_path + '/')
            elif os.path.isfile(selected_path):
                self.window.open_file(selected_path)
            else:
                sublime.status_message("Invalid file path.")