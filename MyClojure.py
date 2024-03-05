import sublime, sublime_plugin
import textwrap
cs = __import__("Clojure Sublimed")
cs_eval = cs.cs_eval
cs_common = cs.cs_common
cs_conn = cs.cs_conn
cs_parser = cs.cs_parser
cs_printer = cs.cs_printer


def eval_pprint_str(eval):
    node = cs_parser.parse(eval.value)
    string = cs_printer.format(eval.value, node, limit = cs_common.wrap_width(eval.view))
    try:
        node = cs_parser.parse(eval.value)
        string = cs_printer.format(eval.value, node, limit = cs_common.wrap_width(eval.view))
    except:
        string = eval.value
    return string


def format_comment(pprint_str):
    if "\n" in pprint_str:
        first_line, rest_lines = pprint_str.split("\n", 1)
        comment = "\n#_" + first_line + "\n" + textwrap.indent(rest_lines, "  ") + "\n"
    else:
        comment = " #_" + pprint_str
    return comment


class MyClojureSublimedEvalToCommentCommand(sublime_plugin.TextCommand):
    """ Pretty prints result into comment """
    def run(self, edit):
        view = self.view
        for sel in view.sel():
            if eval := cs_eval.by_region(view, sel):
                self.view.insert(edit, eval.region().end(), format_comment(eval_pprint_str(eval)))

    def is_enabled(self):
        return cs_conn.ready(self.view.window())


def insert_code(code, insert_str, **kwargs):
    global_cursor_pos = kwargs["selected_region"].begin()
    local_cursor_pos = global_cursor_pos - kwargs["eval_region"].begin()
    with_inserted_code = code[:local_cursor_pos] + insert_str + code[local_cursor_pos:]
    return with_inserted_code


class MyClojureSublimedEvalWithInsertCommand(sublime_plugin.TextCommand):
    """ Evals with insert_str in the cursor position """
    def run(self, edit, insert_str):
        view = self.view
        state = cs_common.get_state(view.window())
        state.conn.eval(view, view.sel(), transform_fn=(lambda code, **kwargs: insert_code(code, insert_str, **kwargs)))

    def is_enabled(self):
        return cs_conn.ready(self.view.window()) and len(self.view.sel()) == 1