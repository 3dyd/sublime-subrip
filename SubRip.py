import re
import sublime
import sublime_plugin

ts_pattern = re.compile("^\s*(?:(\d*:)?(\d*:))?(\d*)(,\d*)?\s*$")


def expand(view, point, selector):
    if not view.match_selector(point, selector):
        raise ValueError(
            "point %d does not match selector %s" % (point, selector))

    region = sublime.Region(point, point + 1)
    while region.a >= 0 and view.match_selector(region.a - 1, selector):
        region.a -= 1
    while view.match_selector(region.b, selector):
        region.b += 1

    return region


def find_backward(point, view, selector):
    while point >= 0 and not view.match_selector(point, selector):
        point -= 1
    if point < 0:
        return None

    region = expand(view, point, selector)
    text = view.substr(region)

    return text


def has_sel(view, empty_means_yes):
    if len(view.sel()) == 0:
        return False
    if len(view.sel()) > 1:
        return True
    if not view.sel()[0].empty():
        return True
    return empty_means_yes == view.sel()[0].empty()


def ms_to_ts(ms):
    if ms < 0:
        ms = 0
    h = (ms / 1000 / 60 / 60)
    if h > 99 or h < -99:
        raise ValueError("too big shift: %d msec" % ms)
    m = (ms / 1000 / 60) % 60
    s = (ms / 1000) % 60
    ms %= 1000

    ts = "%02d:%02d:%02d,%03d" % (h, m, s, ms)

    return ts


def run_for_selector(view, region, selector, callback, *args):
    point = region.begin()
    while point <= region.end():
        if view.match_selector(point, selector):
            target = expand(view, point, selector)
            callback(target, *args)
            point = target.b
        else:
            point += 1


def ts_to_ms(ts):
    match = ts_pattern.match(ts)
    if not match:
        sublime.status_message("unexpected timestamp format")
        return

    ms = 0
    if match.group(1) and len(match.group(1)) > 1:
        ms += int(match.group(1)[:-1]) * 3600 * 1000
    if match.group(2) and len(match.group(2)) > 1:
        ms += int(match.group(2)[:-1]) * 60 * 1000
    if match.group(3):
        ms += int(match.group(3)) * 1000
    if match.group(4) and len(match.group(4)) > 1:
        ms += int(match.group(4)[1:])

    return ms


class SubripApplyShift(sublime_plugin.TextCommand):
    def run(self, edit, offset):
        if has_sel(self.view, False):
            for region in self.view.sel():
                self.run_in_region(region, edit, offset)
        else:
            region = sublime.Region(0, self.view.size())
            self.run_in_region(region, edit, offset)

    def run_in_region(self, region, edit, offset):
        selector = "meta.timestamp.subrip"
        run_for_selector(self.view, region, selector, self.shift, edit, offset)

    def shift(self, region, edit, offset):
        timestamp = self.view.substr(region)
        ms = ts_to_ms(timestamp)
        ms += offset
        timestamp = ms_to_ts(ms)
        self.view.replace(edit, region, str(timestamp))


class SubripAutoCue(sublime_plugin.TextCommand):
    def run(self, edit):
        if len(self.view.sel()) != 1 or not self.view.sel()[0].empty():
            return

        point = self.view.sel()[0].a
        settings = sublime.load_settings("SubRip.sublime-settings")
        if not settings.get("auto_cue"):
            self.view.insert(edit, point, "\n")
            return

        ts = find_backward(point, self.view, "meta.timestamp.subrip")
        if not ts:
            ts = "00:00:00,000"

        snippet = \
            "\n0\n${{1:{0}}}:${{2:{1}}}:${{3:{2}}},${{4:{3}}}" \
            " --> ${{5:{0}}}:${{6:{1}}}:${{7:{2}}},${{8:{3}}}\n" \
            .format(ts[0:2], ts[3:5], ts[6:8], ts[9:12])

        self.view.run_command('insert_snippet', {"contents": snippet})
        self.view.run_command('subrip_recount')


class SubripRecount(sublime_plugin.TextCommand):
    def run(self, edit):
        selector = "meta.counter.subrip"
        regions = self.view.find_by_selector(selector)
        counter = len(regions)
        # loop backward not to deal with the cases when region length changes
        for region in reversed(regions):
            self.view.replace(edit, region, str(counter))
            counter -= 1


class SubripRemoveCue(sublime_plugin.TextCommand):
    def remove(self, region, edit):
        # remove also empty line after cue
        region.b += 1
        self.view.erase(edit, region)

        self.view.run_command('subrip_recount')

    def run(self, edit):
        if has_sel(self.view, True):
            for region in self.view.sel():
                self.run_in_region(region, edit)
        else:
            region = sublime.Region(0, self.view.size())
            self.run_in_region(region, edit)

    def run_in_region(self, region, edit):
        selector = "meta.cue.subrip"
        run_for_selector(self.view, region, selector, self.remove, edit)


class SubripShift(sublime_plugin.WindowCommand):
    def on_done(self, text):
        if text[:1] == "-":
            offset = - ts_to_ms(text[1:])
        else:
            offset = ts_to_ms(text)
        if offset:
            view = self.window.active_view()
            view.run_command('subrip_apply_shift', {'offset': offset})

    def run(self):
        self.window.show_input_panel("Shift by", "", self.on_done, None, None)
