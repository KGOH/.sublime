import sublime, sublime_plugin
import textwrap
#from ClojureSublimed import cs_common, cs_conn
cs = __import__("Clojure Sublimed")
#TODO: extract-test-var-at-point


def eval_pprint_str(eval):
    node = cs.cs_parser.parse(eval.value)
    string = cs.cs_printer.format(eval.value, node, limit = cs.cs_common.wrap_width(eval.view))
    try:
        node = cs.cs_parser.parse(eval.value)
        string = cs.cs_printer.format(eval.value, node, limit = cs.cs_common.wrap_width(eval.view))
    except:
        string = eval.value
    return string


def format_comment(pprint_str):
    if "\n" in pprint_str:
        first_line, rest_lines = pprint_str.split("\n", 1)
        comment = "\n#_" + first_line + "\n" + textwrap.indent(rest_lines, "  ")  + "\n"
    else:
        comment = " #_" + pprint_str + " "
    return comment


pprint_output_filepath = "/tmp/sublimed_pprint_output.edn"


class MyClojureSublimedEvalToBufferCommand(sublime_plugin.TextCommand):
    """ Pretty prints result into the second buffer """
    def run(self, edit):
        view = self.view
        sel = view.sel()[0]
        if eval := cs.cs_eval.by_region(view, sel):
            with open(pprint_output_filepath, "w") as f:
                f.write(eval_pprint_str(eval))
            view.window().open_file(pprint_output_filepath) 

    def is_enabled(self):
        return cs.cs_conn.ready(self.view.window()) and len(self.view.sel()) == 1


class MyClojureSublimedEvalToCommentCommand(sublime_plugin.TextCommand):
    """ Pretty prints result into comment """
    def run(self, edit):
        view = self.view
        sel = view.sel()[0]
        if eval := cs.cs_eval.by_region(view, sel):
            self.view.insert(edit, eval.region().end(), format_comment(eval_pprint_str(eval)))

    def is_enabled(self):
        return cs.cs_conn.ready(self.view.window()) and len(self.view.sel()) == 1
