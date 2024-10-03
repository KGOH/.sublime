import sublime
import sublime_plugin
import subprocess
import re

class MySqlCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        cursor_pos = self.view.sel()[0].begin()

        expr_sep = "----"
        var_sep = "---$"
        connection_string_sep =  expr_sep + "$"

        connection_string_pos = self.find_line_starting_with_dashes(cursor_pos, connection_string_sep, -1)

        if connection_string_pos is None:
            #sublime.message_dialog("No matching --- lines found")
            print("No connection string")
            return

        upper_bound = self.find_line_starting_with_dashes(cursor_pos, expr_sep, -1)
        lower_bound = self.find_line_starting_with_dashes(self.view.line(cursor_pos).end()+1, expr_sep, +1) or self.view.size()

        sql_region = sublime.Region(self.view.line(upper_bound).end()+1, self.view.line(lower_bound).begin())
        sql_query = self.view.substr(sql_region).strip()

        vars = [[[re.compile('\\$' + var[len(var_sep):])
                 , val.strip()]
                 for var, val in [l.split(' ', 1)]][0]
                for l in sql_query.splitlines()
                if l.startswith(var_sep)]

        for var, val in vars + vars:
            sql_query = re.sub(var, val, sql_query)

        connection_region  = sublime.Region(self.view.line(connection_string_pos).begin(), self.view.line(connection_string_pos).end())
        client, connection = [s.strip() for s in self.view.substr(connection_region)[len(connection_string_sep):].split(":", 1)]
        client = client.lower()

        sql_file_path = self.write_to_temp_file(sql_query)
        sql_cmd, sql_out_path = self.build_sql_command(client, connection, sql_file_path)

        #print("client>>>", client, "\nconnection>>>", repr(connection), "\nexpr>>>", repr(sql_query))
        #print(sql_cmd, sql_out_path)

        output = self.run_command(sql_cmd)
        self.display_result(sql_cmd, output, sql_out_path)

    def find_line_starting_with_dashes(self, position, search, dir=1):
        line = self.view.line(position)

        while (line.begin() >= 0) and (line.end() <= self.view.size()):
            cur = line.end() if dir == 1 else line.begin()
            if self.view.substr(line).strip().startswith(search):
                return cur
            line = self.view.line(cur + dir)
        return None

    def write_to_temp_file(self, sql_query):
        tmp_file = "/tmp/sql_input.sql"
        with open(tmp_file, 'w') as f:
            f.write(sql_query)
        return tmp_file

    def build_sql_command(self, db_client, db_header, sql_file_path):
        tmp_file = "/tmp/sql_output.sql"
        sql_cmd = None
        if "ch" == db_client:
            password = "--password ${CLICKHOUSE_KEY}" if not "--password" in db_header                                          else ""
            fmt      = "--output-format PrettyCompact" if (not '--output-format' in db_header) and (not '--format' in db_header) else ""
            sql_cmd = f"~/clickhouse client {db_header} {password} {fmt} --queries-file {sql_file_path} > {tmp_file}"
        elif "pg" == db_client:
            sql_cmd = f"psql {db_header} -f {sql_file_path} -o {tmp_file}"

        if sql_cmd is None:
            raise NotImplementedError

        return sql_cmd, tmp_file

    def run_command(self, cmd):
        print("$", cmd)
        ret = None
        try:
            output = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT).decode("utf-8")
            ret = output
        except subprocess.CalledProcessError as e:
            ret = e.output.decode("utf-8")
        print(ret)
        return ret

    def display_result(self, cmd, output, out_file):
        res_file = "/tmp/sql_res.sql"
        with open(out_file, 'r') as f:
            sql_output = f.read()
        cmd_comment = f"-- $ {cmd}"
        output_comment = '\n'.join('-- '+l for l in output.splitlines())
        result_text = f"{cmd_comment}\n{output_comment}\n----------- Result ------------\n{sql_output}\n-----------  End   ------------\n\n"
        with open(res_file, 'w') as f:
            f.write(result_text)
        view = self.view.window().open_file(res_file)
