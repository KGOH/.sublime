#import sublime, sublime_plugin
#from ClojureSublimed import cs_common, cs_conn, 
#
#
##extract-test-var-at-point
#class ClojureSublimedEval(sublime_plugin.TextCommand):
#    """ Eval selected code or topmost form is selection is collapsed """
#    def run(self, edit):
#        state = cs_common.get_state(self.view.window())
#        state.conn.eval(self.view, self.view.sel())
#
#    def is_enabled(self):
#        return cs_conn.ready(self.view.window())
