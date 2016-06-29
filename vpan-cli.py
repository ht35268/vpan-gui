#coding=utf-8

import os
import re

import urllib
import urllib.request

import time
import datetime

import threading
import os.path
import win32clipboard
import win32con

opt_cookie = ""
opt_max_thr_count = 10
opt_max_list_count = 20
opt_sleep_interval = 1.0
opt_refresh_function = "clear" # clear for linux and cls for windows

def chomp(str_data_old):
    return str_data_old.replace('\r','').replace('\n','')


def get_http_data(_, def_path):
    return urllib.request.urlopen(
        urllib.request.Request(def_path, headers = {"Cookie" : opt_cookie})
    ).read()

def get_http_data_by_link(def_path):
    if '://' not in def_path:
        def_path='http://'+def_path
    return get_http_data(None, def_path)

def resolve_filename_conflict(name):
    if not os.path.exists(name):
        return name
    for i in range(1, 1024):
        nname = re.sub("(\\.[A-Za-z]*)$", " ({0})\\1".format(str(i)), name)
        if not os.path.exists(nname):
            return nname
    return name

def DownloadFile(url, web_path, tofile, origsize):
    f = urllib.request.urlopen(url)
    # tofile = resolve_filename_conflict(tofile)
    if os.path.exists(tofile):
        return True
    # No conflictions...
    real_tofile = tofile + ".downloading"
    outf = open(real_tofile, 'wb')
    c = 0
    print_str = "Downloading..."
    disp_item_modify(web_path, print_str)
    tm_begin = datetime.datetime.now()
    while True:
        s = f.read(1024*32)
        if not s:
             break
        outf.write(s)
        c += len(s)
        tm_end = datetime.datetime.now()
        tm_delta = tm_end - tm_begin
        print_str = "Downloaded %s M of %s (%d kB/s)"%(c / 1024 / 1024, origsize,c / 1024 / (tm_delta.seconds + 2))
        disp_item_modify(web_path, print_str)
    # Renaming file
    outf.close()
    for parent, dirnames, filenames in os.walk('.'):
        for filename in filenames:
            if filename == real_tofile:
                os.rename(os.path.join(parent, real_tofile), os.path.join(parent, tofile))
    return True

"""
Core functions
"""

def vpan_get_file(web_path, html_data):
    down_path_list = re.findall("\"download_list\":\\[\"(.*?)\"", html_data)
    down_path_list.append("")
    down_path = down_path_list[0].replace(r'\/','/')
    # Preparing to download...
    down_size_list = re.findall("<span class=\"btn_vdisk_size\">(.*?)</span>", html_data)
    down_size_list.append("Unknown size")
    down_size = down_size_list[0]
    DownloadFile(down_path, web_path, disp_arr_name[web_path], down_size)
    return True

def vpan_get_dir(_, html_data):
    sub_list_1 = re.findall("href=\"(http://vdisk\\.weibo\\.com/s/.*?)\"", html_data)
    sub_list = []
    for name in sub_list_1:
        for name2 in sub_list:
            if name == name2:
                break
        else:
            sub_list.append(name)
    for name in sub_list:
        disp_item_insert(name)
    return True

def vpan_get_item(web_path):
    disp_item_modify(web_path, "Getting file headers...")
    html_data = get_http_data_by_link(web_path).decode("utf-8", "ignore")
    vpan_resolve_name(web_path, html_data)
    if re.findall("在线预览", html_data):
        vpan_get_file(web_path, html_data)
    else:
        vpan_get_dir(web_path, html_data)
    disp_item_remove(web_path)
    return True

def vpan_resolve_name(web_path, html_data):
    nam_list = re.findall("<title>(.*?)</title>", html_data)
    nam = re.sub("_微盘下载", "", nam_list[0]) if nam_list else "Unnamed"
    global disp_arr_name
    disp_arr_name[web_path] = nam
    return True

"""
Core threaing functions
"""

disp_arr_stat = {}
disp_arr_name = {}

disp_thr_state = True
disp_thr_count = 0

def disp_item_modify(item_addr, item_prop):
    global disp_arr_stat
    global disp_arr_name
    disp_arr_stat[item_addr] = item_prop
    return True

def disp_item_insert(item_addr):
    global disp_arr_stat
    global disp_arr_name
    if item_addr in disp_arr_name:
        return True
    disp_arr_name[item_addr] = "Unknown name"
    disp_arr_stat[item_addr] = "Pending"
    return True

def disp_item_remove(item_addr):
    global disp_arr_stat
    global disp_arr_name
    global disp_thr_count
    disp_arr_stat[item_addr] = ""
    disp_thr_count -= 1
    return True

def disp_item_clear():
    global disp_arr_stat
    global disp_arr_name
    global disp_thr_count
    disp_arr_stat.clear()
    disp_arr_name.clear()
    disp_thr_count = 0
    return True

def disp_thr_func_post_view(list_of_names):
    global disp_arr_stat
    global disp_arr_name
    for item_addr in list_of_names:
        item_name = disp_arr_name[item_addr]
        item_stat = disp_arr_stat[item_addr] or "Completed!"
        print(item_name, "\t", item_stat)
    return True


def disp_thr_view():
    global disp_arr_stat
    global disp_arr_name
    global disp_thr_state
    max_size = opt_max_list_count
    while True:
        os.system(opt_refresh_function)
        if not disp_thr_state:
            break
        cur_size = 0
        disp_list = []
        for name in disp_arr_name:
            if cur_size >= max_size:
                break
            if not disp_arr_stat[name]:
                continue
            cur_size += 1
            disp_list.append(name)
        for name in disp_arr_name:
            if cur_size >= max_size:
                break
            if not disp_arr_stat[name]:
                cur_size += 1
                disp_list.append(name)
        print("Concurrent downloads:", disp_thr_count)
        print("-"*45)
        disp_thr_func_post_view(disp_list)
        time.sleep(opt_sleep_interval)
    return True

def getText():
    win32clipboard.OpenClipboard()
    d = win32clipboard.GetClipboardData(win32con.CF_TEXT)
    win32clipboard.CloseClipboard()
    return d

def disp_thr_clipmon():
    global disp_thr_state
    global disp_arr_name
    global disp_arr_stat
    stra = ""
    while True:
        strb = getText().rstrip().decode("utf-8", "ignore")
        if strb == "terminate":
            disp_thr_state = False
            break
        if strb == "clear":
            disp_item_clear()
        if stra != strb:
            if re.findall("vdisk\\.weibo\\.com", strb):
                disp_item_insert(strb)
        stra = strb
        time.sleep(opt_sleep_interval)
    return True

def disp_thr_watcher():
    global disp_thr_count
    global disp_thr_state
    max_thr_count = opt_max_thr_count
    my_thr_list = []
    while True:
        if not disp_thr_state:
            break
        required_thr = max_thr_count - disp_thr_count
        for item_addr in disp_arr_name:
            if required_thr <= 0:
                break
            item_stat = disp_arr_stat[item_addr]
            if item_stat != "Pending":
                continue
            required_thr -= 1
            my_thr = threading.Thread(target = vpan_get_item, args = [item_addr])
            my_thr.start()
            my_thr_list.append(my_thr)
            disp_thr_count += 1
        time.sleep(opt_sleep_interval)
    return True

def disp_func_begin():
    global disp_thr_state
    threading.Thread(target = disp_thr_view).start()
    threading.Thread(target = disp_thr_clipmon).start()
    threading.Thread(target = disp_thr_watcher).start()
    while disp_thr_state:
        time.sleep(opt_sleep_interval)
    return True

disp_func_begin()
