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


def to_obj(node, string):
    if 'token' == node.name and node.text:
        s = node.text
        if 'true' == s:
            return True
        elif 'false' == s:
            return False
        elif 'nil' == s:
            return None
        elif ':' == s[0]:
            return s
        elif re.fullmatch(r'[+-]?[0-9]*\.[0-9]*([eE][+-]?\d+)?', s):
            return float(s)
        elif re.fullmatch(r'[+-]?[0-9]+', s):
            return int(s)
        else:
            text = string[node.start:node.end]
    elif 'string' == node.name and node.body:
        text = re.sub(r'\\[\\"rntfb]', cs_parser.unescape, node.body.text)
    elif 'string' == node.name:
        text = ''
    elif 'source' == node.name:
        return [to_obj(ch, string) for ch in node.children] 
    elif 'parens' == node.name:
        return tuple(to_obj(ch, string) for ch in node.body.children)
    elif 'brackets' == node.name:
        return [to_obj(ch, string) for ch in node.body.children]
    elif 'braces' == node.name and node.open.text == '#{':
        return {to_obj(ch, string) for ch in node.body.children}
    elif 'braces' == node.name and node.open.text == '{':
        return {to_obj(k_ch, string): to_obj(v_ch, string) for k_ch, v_ch in cs_parser.partition(node.body.children, 2)} 
    else:
        text = string[node.start:node.end]
    return text


def my_test_report_callback(self):
    def callback(eval):
        try:
            if "failure" == eval.status:
                view = eval.view
                #parsed_view = cs_parser.parse_tree(view)

                eval_obj = to_obj(cs_parser.parse(eval.value), eval.value)[0]
                results = eval_obj[":results"]
                this_ns_results = list(results.values())[0]
                this_test_result = list(this_ns_results.values())[0]
                to_highlight = [{"type": r[":type"], "line": r[":line"], "expected": r[":expected"].strip(), "actual": r[":actual"].strip()}
                                for r in this_test_result 
                                if ":pass" != r[":type"]] 

                for h in to_highlight:
                    highlight_region = view.line(sublime.Region(view.text_point(h["line"]-1, 0), view.text_point(h["line"], 0)))
                    h_eval = cs_eval.Eval(view, highlight_region)
                    h_value = "- %s | + %s"%(h["expected"], h["actual"])
                    h_eval.update("failure", h_value, region=highlight_region)

        except Exception as e:
            print(e)

    return callback 


class MyClojureSublimedRunTestCommand(sublime_plugin.TextCommand):
    """  """
    def run(self, edit):
        state = cs_common.get_state(self.view.window())
        run_test_xform = "(do %code (require '[cider.nrepl.middleware.test]) (cider.nrepl.middleware.test/test-nss '{%ns [%symbol]}))"
        state.conn.eval(self.view, self.view.sel(), transform_fn=cs_eval.format_code_fn(run_test_xform), on_finish=my_test_report_callback(self))


    def is_enabled(self):
        return cs_conn.ready(self.view.window())
