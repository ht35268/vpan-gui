
import os
import re

import http.client
import urllib
import urllib.request

import time
import datetime

import sys
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
    str_data = "";
    for i in str_data_old:
        if i != '\n' and i != '\r':
            str_data += i;
    return str_data;

def get_http_data(def_server, def_path):
    conn = http.client.HTTPConnection(def_server)
    conn.request("GET", def_path, headers = {"Cookie" : opt_cookie})
    response = conn.getresponse()
    str_data = response.read()  # This will return entire content.
    return str_data

def get_http_data_by_link(def_path):
    def_path = re.sub("http://", "", def_path)
    def_server = re.sub("^(.*?)/.*$", "\\1", def_path)
    def_path = re.sub("^.*?(/.*)$", "\\1", def_path)
    return get_http_data(def_server, def_path)

def resolve_filename_conflict(name):
    try:
        fl = open(name, "rb")
        fl.close()
    except FileNotFoundError:
        return name
    for i in range(1, 1024):
        nname = re.sub("(\\.[A-Za-z]*)$", " (" + str(i) + ")\\1", name)
        try:
            fl = open(nname, "rb")
            fl.close()
        except FileNotFoundError:
            return nname
    return name

def DownloadFile(url, web_path, tofile, origsize):
    f = urllib.request.urlopen(url)
    # tofile = resolve_filename_conflict(tofile)
    doSomething = False
    try:
        fl = open(tofile, "rb")
        fl.close()
    except FileNotFoundError:
        doSomething = True
    if (doSomething == False):
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
        if len(s) == 0:
                break
        outf.write(s)
        c += len(s)
        tm_end = datetime.datetime.now()
        tm_delta = tm_end - tm_begin
        print_str = "Downloaded " + str(c / 1024 / 1024) + " M of " + origsize + " (" + str(int(c / 1024 / (tm_delta.seconds + 2))) + " kB/s)"
        disp_item_modify(web_path, print_str)
    # Renaming file
    outf.close()
    curDir = os.getcwd()
    for parent, dirnames, filenames in os.walk(curDir):
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
    down_path = down_path_list[0]
    down_path = re.sub("\\\\/", "/", down_path)
    # Preparing to download...
    down_size_list = re.findall("<span class=\"btn_vdisk_size\">(.*?)</span>", html_data)
    down_size_list.append("Unknown size")
    down_size = down_size_list[0]
    DownloadFile(down_path, web_path, disp_arr_name[web_path], down_size)
    return True

def vpan_get_dir(web_path, html_data):
    sub_list_1 = re.findall("href=\"(http://vdisk\\.weibo\\.com/s/.*?)\"", html_data)
    sub_list = []
    for name in sub_list_1:
        found = False
        for name2 in sub_list:
            if name == name2:
                found = True
        if found == False:
            sub_list.append(name)
    for name in sub_list:
        disp_item_insert(name)
    return True

def vpan_get_item(web_path):
    disp_item_modify(web_path, "Getting file headers...")
    html_data = get_http_data_by_link(web_path)
    html_data = html_data.decode("utf-8", "ignore")
    vpan_resolve_name(web_path, html_data)
    if len(re.findall("在线预览", html_data)) > 0:
        vpan_get_file(web_path, html_data)
    else:
        vpan_get_dir(web_path, html_data)
    disp_item_remove(web_path)
    return True

def vpan_resolve_name(web_path, html_data):
    nam_list = re.findall("<title>(.*?)</title>", html_data)
    if len(nam_list) > 0:
        nam = nam_list[0]
        nam = re.sub("_微盘下载", "", nam)
    else:
        nam = "Unnamed"
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
    if disp_arr_name.__contains__(item_addr):
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
        item_stat = disp_arr_stat[item_addr]
        if item_stat == "":
            item_stat = "Completed!"
        print(item_name, "\t", item_stat)
    return True;

def disp_thr_view():
    global disp_arr_stat
    global disp_arr_name
    global disp_thr_state
    max_size = opt_max_list_count
    while True:
        os.system(opt_refresh_function)
        if disp_thr_state == False:
            break
        cur_size = 0
        disp_list = []
        for name in disp_arr_name:
            if cur_size >= max_size:
                break
            if disp_arr_stat[name] == "":
                continue
            cur_size += 1
            disp_list.append(name)
        for name in disp_arr_name:
            if cur_size >= max_size:
                break
            if disp_arr_stat[name] == "":
                cur_size += 1
                disp_list.append(name)
        print("Concurrent downloads: " + str(disp_thr_count))
        print("---------------------------------------------")
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
    stra = "";
    strb = "";
    while (True):
        strb = getText()
        strb.rstrip()
        strb = strb.decode("utf-8", "ignore")
        if (strb == "terminate"):
            disp_thr_state = False
            break
        if strb == "clear":
            disp_item_clear()
        if stra != strb:
            if len(re.findall("vdisk\\.weibo\\.com", strb)) > 0:
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
        if disp_thr_state == False:
            break
        required_thr = max_thr_count - disp_thr_count
        for item_addr in disp_arr_name:
            if (required_thr <= 0):
                break
            item_name = disp_arr_name[item_addr]
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
    thr_view = threading.Thread(target = disp_thr_view, args = [])
    thr_clipmon = threading.Thread(target = disp_thr_clipmon, args = [])
    thr_watcher = threading.Thread(target = disp_thr_watcher, args = [])
    thr_view.start()
    thr_clipmon.start()
    thr_watcher.start()
    while True:
        if disp_thr_state == False:
            break
        time.sleep(opt_sleep_interval)
    return True

disp_func_begin()
