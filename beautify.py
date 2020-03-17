import ast
from collections import OrderedDict

import mdpopups
import sublime
import sublime_plugin

from .lib import simplejson as json

settings = None


class BeautifyBaseCommand:
    json_force_sort = False


class BeautifyJsonCommand(BeautifyBaseCommand, sublime_plugin.TextCommand):
    def run(self, edit, regions=None):
        if regions is not None:
            self.regions = (sublime.Region(*range) for range in regions)
        elif (len(self.view.sel()) == 1
              and not self.view.sel()[0].empty()) or len(self.view.sel()) > 1:
            self.regions = self.view.sel()
        else:
            self.regions = [sublime.Region(0, self.view.size())]

        for region in self.regions:
            validated_json, err = BeautifyValidateCommand(
                self.view).json_validate(self.view.substr(region), False)
            if err:
                continue

            sorting = settings.get("json").get("sort_keys")

            beautified_json, err = self.json_beautify(
                validated_json, sorting)
            if err:
                mdpopups.show_popup(self.view, str(err))
                continue
            self.view.replace(edit, region, beautified_json)

    def json_beautify(self, parsed_json, sort):
        beautified_json = None
        if BeautifyBaseCommand.json_force_sort:
            sort = BeautifyBaseCommand.json_force_sort
        try:
            beautified_json = json.dumps(parsed_json,
                                         sort_keys=sort,
                                         indent=2)
        except Exception as ex:
            return parsed_json, ex
        return beautified_json, None


class BeautifyValidateCommand(sublime_plugin.TextCommand):
    def run(self, edit, regions=None):
        self.phantom_set = sublime.PhantomSet(
            self.view, "beautify_diagnostics")
        if regions is not None:
            self.regions = (sublime.Region(*range) for range in regions)
        elif (len(self.view.sel()) == 1
              and not self.view.sel()[0].empty()) or len(self.view.sel()) > 1:
            self.regions = self.view.sel()
        else:
            self.regions = [sublime.Region(0, self.view.size())]
        phantoms = []
        for region in self.regions:
            validated_json, err = BeautifyValidateCommand(
                self.view).json_validate(self.view.substr(region), False)
            if err:
                severity = "error"
                content = self.create_phantom_html(
                    "<p class='additional'>" + str(err) + "</p>", severity)
                phantoms.append(sublime.Phantom(
                    region,
                    content,
                    sublime.LAYOUT_BELOW,
                    self.navigate
                ))
                self.phantom_set.update(phantoms)

    def navigate(self, href: str) -> None:
        if href == "hide":
            self.clear()

    def clear(self) -> None:
        self.phantom_set.update([])

    def create_phantom_html(self, content: str, severity: str) -> str:
        stylesheet = sublime.load_resource("Packages/LSP/phantoms.css")
        return """<body id=inline-error>
                    <style>{}</style>
                    <div class="{}-arrow"></div>
                    <div class="{} container">
                        <div class="toolbar">
                            <a href="hide">×</a>
                        </div>
                        <div class="content">{}</div>
                    </div>
                </body>""".format(stylesheet, severity, severity, content)

    def json_validate(self, parsed_json, ast_eval=None):
        validated_json = None
        try:
            if ast_eval:
                validated_json, err = self._ast_literal(parsed_json)
                if err is not None:
                    return None, err
            else:
                validated_json = json.loads(
                    parsed_json, object_pairs_hook=OrderedDict)
        except ValueError as ex:
            return validated_json, ex
        return validated_json, None

    def _ast_literal(self, parsed_content):
        try:
            validated_content = ast.literal_eval(parsed_content)
            return validated_content, None
        except Exception as ex:
            return None, ex


def plugin_loaded():
    global settings
    settings = sublime.load_settings("Beautify.sublime-settings")
