import urllib2
import json
from datetime import datetime
import time
import sys
import os
import cPickle as pickle

ERROR_STR = ""
USE_CURSES = True
UPDATE_RATE = 60


try:
    import curses
except:
    USE_CURSES = False
from models import SiteStats


CONNECTION_ERR = "Connection Error. (R)etry in: {} seconds "
NEXT_UPDATE = "Next Update In: {} seconds or (R)etry now"
UPDATING = "Updating Monitor: {}"
if USE_CURSES:
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
    try:
        with open('saved_stats', 'rb') as stat_file:
            monitor_stats = pickle.load(stat_file)
        _, UPDATE_RATE = setup_stats(False)
    except:
        monitor_stats, UPDATE_RATE = setup_stats(True)
    start_time = datetime.now()
    do_it = True
    backoff = 1
    while do_it:
        loop_time = time.time()
        clear_screen()
        print_screen(1, 1, "Started At: {}".format(start_time))
        print_screen(38, 1, "-"*98)
        print_screen(39, 1, "(Q)uit", False)
        height_offset = 4
        index = 0
        while index < len(monitor_stats):
            monitor = monitor_stats[index]
            assert isinstance(monitor, SiteStats)
            try:
                print_screen(39, 10, UPDATING.format(monitor.name))
                stats = fetch_stats(monitor.api_key)
                backoff = 1
            except Exception as ex:
                backoff_time = time.time()
                while (time.time() - backoff_time) < backoff and do_it:
                    print_screen(39, 10, CONNECTION_ERR.format(round(backoff-(time.time() - backoff_time))))
                    if USE_CURSES:
                        char = main_window.getch()
                        if char == 113 or char == 81:
                            do_it = False
                        elif char == 114 or char == 82:
                            break
                        else:
                            time.sleep(.1)
                    else:
                        time.sleep(1)
                print_screen(39, 10, " "*80)
                backoff *= 2
                if backoff > 60:
                    backoff = 60
                continue
            monitor.last_hashrate = float(stats['total_hashrate'])
            time_diff = time.time() - loop_time
            monitor.total_hash_rate += monitor.last_hashrate * time_diff
            monitor.hash_samples += time_diff
            monitor.stats = stats
            monitor.ltc = float(stats['confirmed_rewards'])
            monitor.shares = int(stats['round_shares'])
            monitor.est_ltc = float(stats['round_estimate'])

            for w in stats['workers']:
                if stats['workers'][w]['alive'] != "1":
                    monitor.dead_workers[w] = datetime.now()
            for dw in monitor.dead_workers.keys():
                if (datetime.now() - monitor.dead_workers[dw]).total_seconds() > 300:
                    del monitor.dead_workers[dw]

            for w in stats['workers']:
                if w not in monitor.worker_stats:
                    monitor.worker_stats[w] = {'total_hashrate': 0.0, 'hash_samples': 0.0, 'last_hashrate': 0.0}
                monitor.worker_stats[w]['total_hashrate'] += float(stats['workers'][w]['hashrate']) * time_diff
                monitor.worker_stats[w]['hash_samples'] += time_diff
                monitor.worker_stats[w]['last_hashrate'] = float(stats['workers'][w]['hashrate'])

            monitor.height = max(7 + len(monitor.dead_workers), len(stats['workers']) - 3)
            write_stats(height_offset, monitor)
            height_offset += monitor.height + 2
            index += 1

        pickle.dump( monitor_stats, open("saved_stats", "wb"))
        
        while time.time() - loop_time < UPDATE_RATE and do_it:
            if USE_CURSES:
                print_screen(39, 10, NEXT_UPDATE.format(round(UPDATE_RATE - (time.time() - loop_time))))
                char = main_window.getch()
                if char == 113 or char == 81:
                    do_it = False
                elif char == 114 or char == 82:
                    print_screen(39, 10, " "*80)
                    break
                else:
                    time.sleep(.35)
                    print_screen(39, 10, " "*80)
            else:
                time.sleep(5)


def read_config():
    try:
        return json.loads(open('local_config.json', 'rb').read())
    except:
        return json.loads(open('config.json', 'rb').read())


def setup_stats(read_monitors):
    config = read_config()
    monitors = []
    if read_monitors:
        for entry in config['monitors']:
            monitors.append(SiteStats(entry['name'], entry['key']))
    update_rate = int(config['update_rate'])
    return monitors, update_rate


def print_there(x, y, text):
    sys.stdout.write("\x1b7\x1b[%d;%df%s\x1b8" % (x, y, text))
    sys.stdout.flush()


def write_stats(screen_offset, monitor):
    print_screen(screen_offset + 0,1, monitor.name)
    print_screen(screen_offset + 0,len(monitor.name)+4, "Confirmed LTC: {}  Estimated LTC: {}  Round Shares: {}".format(round(monitor.ltc, 4), round(monitor.est_ltc, 4), monitor.shares))
    print_screen(screen_offset + 1,1, "*"*99)
    print_screen(screen_offset + 2,1, " Current Hashrate: {}".format(round(monitor.last_hashrate)))
    print_screen(screen_offset + 3,1, " Average Hashrate: {}".format(round(monitor.total_hash_rate / monitor.hash_samples)))
    print_screen(screen_offset + 2, 50, "Worker Name   \tLast\t(Average)")
    aw_ind = 0
    for worker in monitor.worker_stats.keys():
        avg_hash = round(monitor.worker_stats[worker]['total_hashrate'] / monitor.worker_stats[worker]['hash_samples'])
        print_screen(screen_offset + 3 + aw_ind, 50,
                     "{}:\t{}\t({})".format(worker, monitor.worker_stats[worker]['last_hashrate'], avg_hash))
        aw_ind += 1

    print_screen(screen_offset + 5,1, "Dead Workers(in past five minutes)")
    w_ind = 0
    for dw in monitor.dead_workers:
        print_screen(screen_offset + w_ind + 6, 1, "  " + dw)
        w_ind += 1
    print_screen(screen_offset + max(aw_ind-3, w_ind) + 6, 1, "*"*99)
    if USE_CURSES:
        main_window.refresh()

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
