import re
import sublime
import sublime_plugin

pattern = re.compile("^(?:(\d+:)?(\d+:))?(\d+)?(,\d+)?$")


def expand(view, pos, selector):
    if not view.match_selector(pos, selector):
        raise ValueError("pos %d does not match selector %s" % (pos, selector))

    region = sublime.Region(pos, pos + 1)
    while region.a >= 0 and view.match_selector(region.a - 1, selector):
        region.a -= 1
    while view.match_selector(region.b, selector):
        region.b += 1

    return region


def has_sel(view, empty_means_yes):
    if len(view.sel()) == 0:
        return False
    if len(view.sel()) > 1:
        return True
    if not view.sel()[0].empty():
        return True
    return empty_means_yes == view.sel()[0].empty()


def ms_to_ts(ms):
    h = (ms / 1000 / 60 / 60)
    if h > 99 or h < -99:
        raise ValueError("too big shift: %d msec" % ms)
    m = (ms / 1000 / 60) % 60
    s = (ms / 1000) % 60
    ms %= 1000

    ts = "%02d:%02d:%02d,%03d" % (h, m, s, ms)

    return ts


def run_for_selector(view, region, selector, callback, *args):
    pos = region.begin()
    while pos <= region.end():
        if view.match_selector(pos, selector):
            target = expand(view, pos, selector)
            callback(target, *args)
            pos = target.b
        else:
            pos += 1


def ts_to_ms(ts):
    match = pattern.match(ts)
    if not match:
        sublime.status_message("unexpected timestamp format")
        return

    ms = 0
    if match.group(1):
        ms += int(match.group(1)[:-1]) * 3600 * 1000
    if match.group(2):
        ms += int(match.group(2)[:-1]) * 60 * 1000
    if match.group(3):
        ms += int(match.group(3)) * 1000
    if match.group(4):
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


class SubripRecount(sublime_plugin.TextCommand):
    def run(self, edit):
        selector = "meta.counter.subrip"
        regions = self.view.find_by_selector(selector)
        counter = 1
        for region in regions:
            self.view.replace(edit, region, str(counter))
            counter += 1


class SubripRemoveCue(sublime_plugin.TextCommand):
    def remove(self, region, edit):
        self.view.erase(edit, region)

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
        offset = ts_to_ms(text)
        if offset:
            view = self.window.active_view()
            view.run_command('subrip_apply_shift', {'offset': offset})

    def run(self):
        self.window.show_input_panel("Shift by", "", self.on_done, None, None)
