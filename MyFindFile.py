import sublime
import os
import sublime_plugin
import urllib.parse

new_file = sublime.QuickPanelItem(trigger="    New file", annotation="Creates a new file here")
this_dir = sublime.QuickPanelItem(trigger="    This folder", annotation="Opens this folder in the current window")
this_dir_proj = sublime.QuickPanelItem(trigger="    This folder as project", annotation="Opens this folder in a new window")

class MyFindFileCommand(sublime_plugin.WindowCommand):
    def run(self, only_folders=False):
        home = os.path.expanduser('~')
        start = self.window.extract_variables().get('folder', home)
        path = self.window.extract_variables().get('file_path')
        if path is None and (lsp_uri := self.window.active_view().settings().get("lsp_uri", None)):
            if lsp_uri.startswith("zipfile://"):
                parsed = urllib.parse.urlparse(lsp_uri)
                archive, file = parsed.path.split("::")
                path = archive
        current_file = os.path.relpath(path, start=start) if path else start
        print(start, path, current_file)
        full_path = os.path.normpath(os.path.join(start, current_file))
        current_directory = full_path if os.path.isdir(full_path) else os.path.dirname(full_path)
        self.show_overlay(current_directory + '/', only_folders=only_folders)

    def show_overlay(self, current_directory, only_folders=False):
        listdir = []
        try:
            listdir = os.listdir(current_directory)
        except Exception:
            pass

        dirs = sorted(el + '/' for el in listdir
                      if os.path.isdir(os.path.join(current_directory, el)))
        files = sorted(el for el in listdir
                       if not os.path.isdir(os.path.join(current_directory, el)))
        dir_content = dirs if only_folders else dirs + files
        hidden = [el for el in dir_content if el[0] == "."]
        public = [el for el in dir_content if el[0] != "."]
        file_list = ["../"] + public + hidden + [new_file, this_dir, this_dir_proj]

        on_select=(lambda idx: self.select(current_directory, file_list[idx]) if idx >= 0 else None)
        placeholder = current_directory if len(current_directory) < 83 else "..." + current_directory[-80:] 
        self.window.show_quick_panel(file_list, on_select=on_select, placeholder=placeholder)

    def select(self, current_directory, selected):
        if isinstance(selected, sublime.QuickPanelItem):
            if selected == new_file:
                create_file = (lambda input: self.window.open_file(os.path.join(current_directory, input)))
                supress = (lambda _: None) 
                self.window.show_input_panel("File name:", "", create_file, supress, supress) 
            elif selected == this_dir:
                self.window.run_command(cmd="open_folder_as_project", args={"folder": current_directory})
            elif selected == this_dir_proj:
                self.window.run_command(cmd="new_os_tab")
                self.window.run_command(cmd="open_folder_as_project", args={"folder": current_directory})
        else:
            selected_path = os.path.normpath(os.path.join(current_directory, selected))
            if os.path.isdir(selected_path):
                self.show_overlay(selected_path + '/')
            elif os.path.isfile(selected_path):
                self.window.open_file(selected_path)
            else:
                sublime.status_message("Invalid file path.")