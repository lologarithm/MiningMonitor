import urllib2
import json
from datetime import datetime
import time
import sys, os
import curses

from models import SiteStats

ERROR_STR = ""
USE_CURSES = True

try:
    main_window = curses.initscr()
    curses.noecho()
    curses.cbreak()
    curses.curs_set(0)
    curses.resizeterm(40, 100)
    main_window.nodelay(1)
    main_window.clear()
except curses.error:
    # Use Print!
    USE_CURSES = False

def main():
    monitor_stats = setup_stats()
    start_time = datetime.now()
    do_it = True
    while do_it:
        loop_time = time.time()
        clear_screen()
        print_screen(1,1,"Started At: {}".format(start_time))
        print_screen(39,1,"(Q)uit", False)
        height_offset = 4
        for monitor in monitor_stats:
            assert isinstance(monitor, SiteStats)
            try:
                stats, hashrate, workers = get_wml_stats(monitor.api_key)
            except Exception as ex:
                do_it = False
                ERROR_STR = ex
            monitor.total_hash_rate += hashrate
            monitor.hash_samples += 1
            monitor.stats = stats
            monitor.height = max(7, len(stats['workers']) - 4)

            if workers:
                for w in workers:
                    monitor.dead_workers[w] = datetime.now()
            for dw in monitor.dead_workers.keys():
                if (datetime.now() - monitor.dead_workers[dw]).total_seconds() > 300:
                    del monitor.dead_workers[dw]

            write_stats(height_offset, monitor.name, hashrate, monitor.total_hash_rate / monitor.hash_samples, monitor.dead_workers, stats)
            height_offset += monitor.height + 2

        while time.time() - loop_time < 30 and do_it:
            char = main_window.getch()
            if char == 113:
                do_it = False


def read_config():
    return json.loads(open('config.json', 'r').read())


def setup_stats():
    config = read_config()
    monitors = []
    for entry in config['monitors']:
        monitors.append(SiteStats(entry['name'], entry['key']))
    return monitors

def print_there(x, y, text):
    sys.stdout.write("\x1b7\x1b[%d;%df%s\x1b8" % (x, y, text))
    sys.stdout.flush()


def write_stats(screen_offset, title, last_hashrate, avg_hash, dead_workers, stats):
    print_screen(screen_offset + 0,1, title)
    print_screen(screen_offset + 1,1, "#"*99)
    print_screen(screen_offset + 2,1, " Current Hashrate: {}".format(round(last_hashrate)))
    print_screen(screen_offset + 3,1, " Average Hashrate: {}".format(round(avg_hash)))
    print_screen(screen_offset + 5,1, "Dead Workers(in past five minutes)")
    w_ind = 0
    for worker in stats['workers']:
        print_screen(screen_offset + 2 + w_ind, 50, "{}:\t{}".format(worker, stats['workers'][worker]['hashrate']))
        w_ind += 1
    w_ind = 0
    for dw in dead_workers:
        print_screen(screen_offset + w_ind + 6, 1, "  " + dw)
        w_ind += 1
    print_screen(screen_offset + w_ind + 6, 1, "#"*99)
    if USE_CURSES:
        main_window.refresh()


def get_wml_stats(api_key):
    stats = fetch_stats(api_key)
    hashrate = 0
    dead_workers = []
    for worker in stats['workers']:
        hashrate += float(stats['workers'][worker]['hashrate'])
        if stats['workers'][worker]['alive'] != "1":
            dead_workers.append(worker)
    return (stats, hashrate, dead_workers)

def fetch_stats(api_key):
    string_stats= urllib2.urlopen("http://www.wemineltc.com/api?api_key={}".format(api_key)).read()
    json_stats = json.loads(string_stats)
    return json_stats


def clear_screen():
    if USE_CURSES:
        main_window.clear()
    else:
        os.system('clear')

def print_screen(y, x, str, print_if_console=True):
    if USE_CURSES:
        main_window.addstr(y, x, str)
    elif print_if_console:
        print(str)

try:
    main()
except Exception as ex:
    ERROR_STR = ex

if USE_CURSES:
    curses.nocbreak()
    curses.echo()
    curses.endwin()
    curses.curs_set(1)

if ERROR_STR:
    print(ERROR_STR)