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


def insert_code(code, eval_region, sel_region, insert_str):
    global_cursor_pos = sel_region.begin()
    local_cursor_pos = global_cursor_pos - eval_region.begin()
    return code[:local_cursor_pos] + insert_str + code[local_cursor_pos:]


class MyClojureSublimedEvalWithInsertCommand(sublime_plugin.TextCommand):
    """ Evals with insert_str in the cursor position """
    def run(self, edit, insert_str):
        view = self.view
        state = cs_common.get_state(view.window())
        state.conn.eval(view, view.sel(), wrap_fn=(lambda code, eval_region, sel_region: insert_code(code, eval_region, sel_region, insert_str)))

    def is_enabled(self):
        return cs_conn.ready(self.view.window()) and len(self.view.sel()) == 1


def extract_test_var_at_point(view):
    region = view.sel()[0]
    point = region.begin()

    if point >= view.size() or view.substr(sublime.Region(point, point + 1)).isspace():
        while point > 0 and view.substr(sublime.Region(point - 1, point)).isspace():
            point = point - 1

    parsed = cs_parser.parse_tree(view)

    maybe_deftest_node = cs_parser.search(parsed, point, max_depth = 1) 
    test_name_sym = None
    maybe_deftest_sym = maybe_deftest_node.body.children[0]
    if (maybe_deftest_sym.name == "token" and maybe_deftest_sym.text.endswith("deftest")):
      test_name_node = maybe_deftest_node.body.children[1]
      if (test_name_node.name == "meta"):
        test_name_node = test_name_node.body.children[0]

      if (test_name_node.name == "token"):
        test_name_sym = test_name_node.text

      return "#'" + test_name_sym


run_test_var_fstr = """
(let [r (clojure.test/run-test-var %s)]
  (if (and (zero? (:fail r)) (zero? (:error r)))
    r
    (throw (ex-info "Test failed" r))))
"""

class MyClojureSublimedRunTestUnderCursorCommand(sublime_plugin.TextCommand):
    """ Extracts test var in which cursor is in and runs it """
    def run(self, edit):
        test_var = extract_test_var_at_point(self.view)
        window = self.view.window()
        window.run_command(cmd="clojure_sublimed_eval_code",
                           args={"code": run_test_var_fstr%test_var})

    def is_enabled(self):
        return cs_conn.ready(self.view.window())