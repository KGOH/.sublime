import sublime, sublime_plugin
import textwrap
import re
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


def on_select(self, eval, idx):
    eval.erase()
    if idx > -1:
        select_nth = "(do (ps.sc/letsc-select-nth! %s) (symbol \"#%s selected\"))"%(idx, idx)
        self.view.window().run_command(cmd="clojure_sublimed_eval_code", args={"code": select_nth})



def my_on_success_callback(self): 
    def callback(eval):
        try:
            outer_vec_body = cs_parser.parse(eval.value).children[0].body
            selected_ep_id_text = outer_vec_body.children[0].text
            selected_ep_id = None if selected_ep_id_text == 'nil' else int(selected_ep_id_text)
            vls = cs_parser.parse(eval.value).children[0].body.children[1].body.children
            i_width = len(str(len(vls)))
            els = [("i: {i:>{i_width}}, {rev_i:>{rev_i_width}};    v: {v}").format(i=i, i_width=i_width, rev_i=-len(vls)+i, rev_i_width=i_width+1, v=str(cs_parser.as_obj(ch, eval.value))) for i, ch in enumerate(vls)]
            selected_index = selected_ep_id if selected_ep_id is not None else len(els) - 1
            self.view.window().show_quick_panel(els, selected_index=selected_index, flags=sublime.QuickPanelFlags.MONOSPACE_FONT, on_select=(lambda idx: on_select(self, eval, idx)))
        except Exception as e:
            print(e)
            pass
    return callback


class MyClojureSublimedSelectCommand(sublime_plugin.TextCommand):
    """  """
    def run(self, edit):
        state = cs_common.get_state(self.view.window())
        letsc_start_fstr = "(ps.sc/letsc-select-start-no-mark! (quote %s))"
        state.conn.eval(self.view, self.view.sel(), transform_fn=(lambda code, **kwargs: letsc_start_fstr%code), on_finish=my_on_success_callback(self))


    def is_enabled(self):
        return cs_conn.ready(self.view.window())


class ObjNode:
    def __init__(self, node, obj, string):
        self.node = node
        self.obj = obj
        self.string = string

    def __eq__(self, other):
        return str(self) == str(self)

    def __hash__(self):
        return hash(self.string)

    def __str__(self):
        return(self.string)


def to_obj(node, string):
    if 'token' == node.name and node.text:
        s = node.text
        if 'true' == s:
            result = True
        elif 'false' == s:
            result = False
        elif 'nil' == s:
            result = None
        elif ':' == s[0]:
            result = s
        elif re.fullmatch(r'[+-]?[0-9]*\.[0-9]*([eE][+-]?\d+)?', s):
            result = float(s)
        elif re.fullmatch(r'[+-]?[0-9]+', s):
            result = int(s)
        else:
            result = string[node.start:node.end]
    elif 'string' == node.name and node.body:
        result = re.sub(r'\\[\\"rntfb]', cs_parser.unescape, node.body.text)
    elif 'string' == node.name:
        result = ''
    elif 'source' == node.name:
        result = [to_obj(ch, string) for ch in node.children] 
    elif 'parens' == node.name:
        result = tuple(to_obj(ch, string) for ch in node.body.children)
    elif 'brackets' == node.name:
        result = [to_obj(ch, string) for ch in node.body.children]
    elif 'braces' == node.name and node.open.text == '#{':
        result = {to_obj(ch, string) for ch in node.body.children}
    elif 'braces' == node.name and node.open.text == '{':
        result = {to_obj(k_ch, string): to_obj(v_ch, string) for k_ch, v_ch in cs_parser.partition(node.body.children, 2)} 
    else:
        result = string[node.start:node.end]
    return ObjNode(obj=result, node=node, string=string[node.start:node.end])


def regions_intersect(a_begin, a_end, b_begin, b_end): 
    return a_begin <= b_end and a_end >= b_end



def search_by_line(node, line_region, pred = lambda x: True, max_depth = 1000):
    """
    Search inside node what’s the deepest node that starts at the specified line.
    Stops at max_depth and if pred evals to true.
    If multiple nodes touch around pos, checks all for pred, returns the first that returns true.
    """
    if max_depth <= 0 or not node.children:
        if pred(node):
            return node
        else:
            return None
    els = node.body.children if node.body else node.children
    for child in els:
        if (line_region.begin() <= child.start <= line_region.end()) and (pred(child)):
            return child
        if regions_intersect(child.start, child.end, line_region.begin(), line_region.end()):
            if res := search_by_line(child, line_region, pred = pred, max_depth = max_depth - 1):
                return res
        elif line_region.end() < child.start:
            break


def my_test_report_callback(self):
    def callback(eval):
        try:
            if "failure" == eval.status:
                view = eval.view
                parsed_view = cs_parser.parse_tree(view)

                eval_obj = to_obj(cs_parser.parse(eval.value), eval.value).obj[0]

                if reports := eval_obj.obj.get(":reports"): 
                    if fails := reports.obj.get(":fail"):
                        for fail in fails.obj:
                            line = fail.obj[":line"].obj
                            line_region = view.line(view.text_point(line-1, 0))

                            found_expr = search_by_line(parsed_view, line_region)
                            found_region = sublime.Region(found_expr.start, found_expr.end)

                            highlight_region = found_region

                            h_eval = cs_eval.Eval(view, highlight_region)
                            h_value = str(fail.obj[":actual"])
                            h_eval.update("failure", h_value, region=highlight_region)

                if errors := reports.obj.get(":error"):
                    print(len(errors.obj), errors.obj[0])
                    print(">>", repr(eval.value))


        except Exception as e:
            print(e)

    return callback 


clojure_sublimed_middleware_test = '''
(ns clojure-sublimed.middleware.test
  (:require [clojure.test]
            [clojure.string]))

(defn append-report! [m]
  (let [t (:type m)
        stripped-m (-> m 
                     (dissoc :type :file :expected :message))]
    (when clojure.test/*report-counters*
      (dosync 
        (commute clojure.test/*report-counters* update-in [:reports (:type m)] (fnil conj []) stripped-m)))))

(defn process-error [{:as m :keys [file actual]}]
  (println '>>>>>>>>>>> 
    file
    (some->>
      (.getStackTrace ^Throwable actual)
      (map #(clojure.string/includes? (.getClassName ^StackTraceElement %) file))
      #_#_first
      .getLineNumber))
  (assoc m :actual (.getMessage actual)))

(defmulti report :type)
(defmethod report :default [_])
(defmethod report :error [m] (append-report! (process-error m))) 
(defmethod report :fail [m] (append-report! m)) 
'''


# NOTE: important to be all at the same line as deftest because reports will refer to errors by line
with_report_fstr = \
'''(do''' \
''' (require '[clojure-sublimed.middleware.test])''' \
''' (let [clojure-test-report clojure.test/report]''' \
'''  (with-bindings {#'clojure.test/report (fn [m] (clojure-test-report m) (clojure-sublimed.middleware.test/report m))}''' \
'''    %s)))'''
print(with_report_fstr)


class MyClojureSublimedRunTestCommand(sublime_plugin.TextCommand):
    def run(self, edit, run_test_xform):
        state = cs_common.get_state(self.view.window())

        state.conn.eval_status(clojure_sublimed_middleware_test, 'user')

        state.conn.eval(
            self.view,
            self.view.sel(), 
            transform_fn=cs_eval.format_code_fn(with_report_fstr%run_test_xform), 
            on_finish=my_test_report_callback(self)
        )


    def is_enabled(self):
        return cs_conn.ready(self.view.window())
