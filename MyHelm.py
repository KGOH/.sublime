import sublime
import os
import sublime_plugin

new_file = sublime.QuickPanelItem(trigger="    New file", annotation="Create a file here")
new_dir = sublime.QuickPanelItem(trigger="    New directory", annotation="Create a directory here")

class MyHelmCommand(sublime_plugin.WindowCommand):
    def run(self):
        home = os.path.expanduser('~')
        start = self.window.extract_variables().get('folder', home)
        path = self.window.extract_variables().get('file_path')
        current_file = os.path.relpath(path, start=start) if path else start
        print(start, path, current_file)
        full_path = os.path.normpath(os.path.join(start, current_file))
        current_directory = full_path if os.path.isdir(full_path) else os.path.dirname(full_path)
        self.show_overlay(current_directory + '/')

    def show_overlay(self, current_directory):
        listdir = []
        try:
            listdir = os.listdir(current_directory)
        except Exception:
            pass

        dirs = sorted(el + '/' for el in listdir
                      if os.path.isdir(os.path.join(current_directory, el)))
        files = sorted(el for el in listdir
                       if not os.path.isdir(os.path.join(current_directory, el)))
        dir_content = dirs + files 
        hidden = [el for el in dir_content if el[0] == "."]
        public = [el for el in dir_content if el[0] != "."]
        file_list = ["../"] + public + hidden + [new_file] #+ [new_dir]

        on_select=(lambda idx: self.select(current_directory, file_list[idx]) if idx >= 0 else None)
        placeholder = current_directory if len(current_directory) < 83 else "..." + current_directory[-80:] 
        self.window.show_quick_panel(file_list, on_select=on_select, placeholder=placeholder)

    def select(self, current_directory, selected):
        if isinstance(selected, sublime.QuickPanelItem):
            if selected == new_file:
                create_file = (lambda input: self.window.open_file(os.path.join(current_directory, input)))
                supress = (lambda _: None) 
                self.window.show_input_panel("File name:", "", create_file, supress, supress) 
        else:
            selected_path = os.path.normpath(os.path.join(current_directory, selected))
            if os.path.isdir(selected_path):
                self.show_overlay(selected_path + '/')
            elif os.path.isfile(selected_path):
                self.window.open_file(selected_path)
            else:
                sublime.status_message("Invalid file path.")