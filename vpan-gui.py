
import os
import re
import shutil

import http.client
import urllib
import urllib.request
import socket

import time
import datetime

import sys
import threading
import os.path

# import win32clipboard
# import win32con

opt_cookie = ""
opt_max_thr_count = 8
opt_max_thr_view_count = 12
opt_retry_delay_second = 60
opt_timeout_second = 25
opt_monitor_clipboard = False
opt_download_directory = "./Downloading/"

"""
Trivial functions
"""

socket.setdefaulttimeout(opt_timeout_second)

def chomp(str_data_old):
    str_data = "";
    for i in str_data_old:
        if i != '\n' and i != '\r':
            str_data += i;
    return str_data;

def get_http_data(def_server, def_path):
    try:
        conn = http.client.HTTPConnection(def_server)
        conn.request("GET", def_path, headers = {"Cookie" : opt_cookie})
        response = conn.getresponse()
        str_data = response.read()  # This will return entire content.
    except OSError:
        raise RuntimeError
    except socket.gaierror:
        raise RuntimeError
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

def file_exist(path):
    if os.path.isfile(opt_download_directory + path):
        return True
    # nam_list = re.findall("^(.*)/", path)
    # nam = nam_list[0] if nam_list else ""
    # for parent, dirnames, filenames in os.walk(opt_download_directory):
    #     for filename in filenames:
    #         if filename == nam:
    #             shutil.copyfile(os.path.join(parent, filename), opt_download_directory + path)
    #             return True
    return False

def make_file(path):
    nam_list = re.findall("^(.*)/", path)
    path = nam_list[0] if nam_list else ""
    if path != "":
        if not os.path.exists(path):
            os.makedirs(path)
    return True

def DownloadFile(url, web_path, tofile, origsize):
    try:
        f = urllib.request.urlopen(url)
    except socket.timeout:
        raise RuntimeError
    if file_exist(tofile):
        return True
    # No conflictions...
    real_tofile = tofile + ".downloading"
    make_file(opt_download_directory + real_tofile)
    outf = open(opt_download_directory + real_tofile, 'wb')
    c = 0
    print_str = "Downloading..."
    disp_item_modify(web_path, print_str)
    tm_begin = datetime.datetime.now()
    while True:
        if sig_mainstop:
            raise RuntimeError
        try:
            s = f.read(1024*32)
        except socket.timeout:
            raise RuntimeError
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
    singular_real_tofile = re.sub("^.*/", "", real_tofile)
    singular_tofile = re.sub("^.*/", "", tofile)
    try:
        os.rename(opt_download_directory + real_tofile, opt_download_directory + tofile)
    except FileExistsError:
        return True
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
    if len(down_path) < 3:
        return vpan_get_dir(web_path, html_data)
    else:
        DownloadFile(down_path, web_path, disp_arr_name[web_path], down_size)
    return True

def vpan_get_dir(web_path, html_data):
    n_data_list = re.findall("<tbody.*?>(.*?)</tbody>", chomp(html_data))
    n_data = n_data_list[0] if n_data_list else ""
    sub_list_1 = re.findall("href=\"(http://vdisk\\.weibo\\.com/s/.*?)\"", n_data)
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
    try:
        html_data = get_http_data_by_link(web_path)
    except RuntimeError:
        disp_item_remove(web_path)
        disp_item_modify(web_path, "Connection lost.")
        return False
    html_data = html_data.decode("utf-8", "ignore")
    vpan_resolve_name(web_path, html_data)
    isDir = True
    if re.findall("<tbody.*?>(.*?)</tbody>", chomp(html_data)) and not re.findall("\\.(rar|Rar|RAR|zip|Zip|ZIP)", disp_arr_name[web_path]):
        isDir = True
    else:
        isDir = False
    try:
        if not isDir:
            vpan_get_file(web_path, html_data)
        else:
            vpan_get_dir(web_path, html_data)
    except RuntimeError:
        disp_item_remove(web_path)
        disp_item_modify(web_path, "Connection lost.")
        return False
    disp_item_remove(web_path)
    return True

vpres_names = {}

def vpan_get_resolved_name(web_path, html_data):
    global vpres_names
    actual_path = re.sub("\\?(.*)$", "", web_path)
    if actual_path in vpres_names:
        return vpres_names[actual_path]
    nam_list = re.findall("<title>(.*?)</title>", html_data)
    nam = re.sub("_微盘下载", "", nam_list[0]) if nam_list else "Unnamed"
    print(actual_path, nam)
    # Getting hierarchy recursively
    par_link_1 = re.findall("parents_ref=(.*)$", web_path)
    par_link_2 = par_link_1[0] if par_link_1 else ""
    par_link_3 = re.sub(".*,", "", par_link_2)
    if par_link_3 == "":
        vpres_names[actual_path] = nam
        return nam
    par_link = re.sub("s/.*?\\?", "s/" + par_link_3 + "?", web_path)
    if re.findall("parents_ref=.*,", par_link):
        par_link = re.sub("(parents_ref=.*),.*?$", "\\1", par_link)
    else:
        par_link = re.sub("parents_ref=.*$", "", par_link)
    # Getting data and redirecting to higher hierarchy
    try:
        html_data = get_http_data_by_link(par_link)
    except RuntimeError:
        vpres_names[actual_path] = nam
        return nam
    html_data = html_data.decode("utf-8", "ignore")
    par_name = vpan_get_resolved_name(par_link, html_data)
    nam = par_name + "/" + nam if par_name != "" else nam
    vpres_names[web_path] = nam
    return nam

def vpan_resolve_name(web_path, html_data):
    nam = vpan_get_resolved_name(web_path, html_data)
    global disp_arr_name
    disp_arr_name[web_path] = nam
    return True

def vpan_resolve_name_force(web_path):
    global disp_thr_view_count
    disp_item_modify(web_path, "Resolving filename...")
    try:
        html_data = get_http_data_by_link(web_path)
    except RuntimeError:
        disp_item_modify(web_path, "Connection lost.")
        disp_thr_view_count -= 1
        return False
    html_data = html_data.decode("utf-8", "ignore")
    vpan_resolve_name(web_path, html_data)
    # testing if exists
    if file_exist(disp_arr_name[web_path]):
        disp_arr_stat[web_path] = ""
    disp_thr_view_count -= 1
    disp_item_modify(web_path, "Pending")
    return True

"""
Core threaing functions
"""

disp_arr_stat = {}
disp_arr_name = {}
disp_list_add = []
disp_list_remove = []

disp_thr_state = True
disp_thr_count = 0
disp_thr_view_count = 0

def disp_item_modify(item_addr, item_prop):
    global disp_arr_stat
    global disp_arr_name
    disp_arr_stat[item_addr] = item_prop
    return True

def disp_item_insert_pend(item_addr):
    global disp_arr_stat
    global disp_arr_name
    if item_addr in disp_arr_name:
        return True
    disp_arr_name[item_addr] = "Unknown name"
    disp_arr_stat[item_addr] = "Pending"
    return True

def disp_item_insert(item_addr):
    disp_list_add.append(item_addr)
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
    global disp_list_add
    global disp_list_remove
    global disp_thr_count
    try:
        for name in disp_arr_name:
            if disp_arr_stat[name] == "":
                disp_list_remove.append(name)
    except KeyError:
        return True
    return True

def disp_item_reset():
    global disp_arr_stat
    global disp_arr_name
    global disp_list_add
    global disp_list_remove
    global disp_thr_count
    try:
        for name in disp_arr_name:
            if disp_arr_stat[name] == "Connection lost.":
                disp_item_modify(name, "Pending")
    except KeyError:
        return True
    return True

def disp_item_apply():
    global disp_arr_stat
    global disp_arr_name
    global disp_list_add
    global disp_list_remove
    global disp_thr_count
    my_arr_stat = {}
    my_arr_name = {}
    for name in disp_arr_name:
        exists = False
        for mame in disp_list_remove:
            if name == mame:
                exists = True
        if exists:
            continue
        my_arr_name[name] = disp_arr_name[name]
        my_arr_stat[name] = disp_arr_stat[name]
    disp_arr_stat.clear()
    disp_arr_name.clear()
    disp_arr_stat = my_arr_stat
    disp_arr_name = my_arr_name
    for name in disp_list_add:
        disp_item_insert_pend(name)
    disp_list_add.clear()
    disp_list_remove.clear()
    return True

disp_thr_view_time_count = 0

def disp_thr_view():
    global disp_thr_state
    global disp_thr_view_time_count
    global tree
    disp_thr_view_time_count += 1
    if disp_thr_view_time_count % 5 != 0:
        return True
    my_disp_arr_name = list()
    for i in disp_arr_name:
        my_disp_arr_name.append(i)
    my_arr = list()
    my_disp_arr_name.sort()
    indexer = ["ownload", "header", "name", "lost", "ending"]
    for idxer in indexer:
        for name in my_disp_arr_name:
            if re.findall(idxer, disp_arr_stat[name]):
                my_arr.append(name)
    for name in my_disp_arr_name:
        found = False
        if re.findall("(ownload|header|name|lost|ending)", disp_arr_stat[name]):
            found = True
        if found:
            continue
        my_arr.append(name)
    tree.delete(*tree.get_children())
    for item_addr in my_arr:
        item_name = disp_arr_name[item_addr]
        item_stat = disp_arr_stat[item_addr]
        if item_stat == "":
            item_stat = "Completed!"
        tree.insert('','end',text = item_name,values = (item_addr, item_stat))
    return True

def getText():
    try:
        win32clipboard.OpenClipboard()
        d = win32clipboard.GetClipboardData(win32con.CF_TEXT)
        win32clipboard.CloseClipboard()
    except TypeError:
        return ""
    return d.rstrip().decode("utf-8", "ignore")

stra = "";
strb = "";

def disp_thr_clipmon():
    global disp_thr_state
    global stra
    global strb
    strb = getText()
    if stra != strb:
        if len(re.findall("vdisk\\.weibo\\.com", strb)) > 0:
            disp_item_insert(strb)
    stra = strb
    return True

def disp_thr_watcher():
    global disp_thr_count
    global disp_thr_state
    max_thr_count = opt_max_thr_count
    if disp_thr_state == False:
        return True
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
        disp_thr_count += 1
    return True

def disp_thr_saver():
    lastins = open("saved.log", "w", encoding="utf-8")
    lastprnt = ""
    for name in disp_arr_name:
        lastprnt += name + "\n"
    lastins.write(lastprnt)
    lastins.close()
    return True

def disp_thr_resolve():
    max_thr_count = opt_max_thr_view_count
    global disp_thr_view_count
    required_thr = max_thr_count - disp_thr_view_count
    for item_addr in disp_arr_name:
        if required_thr <= 0:
            return True
        item_name = disp_arr_name[item_addr]
        item_stat = disp_arr_stat[item_addr]
        if item_stat != "Pending":
            continue
        if item_name != "Unknown name":
            continue
        required_thr -= 1
        disp_thr_view_count += 1
        my_thr = threading.Thread(target = vpan_resolve_name_force, args = [item_addr])
        my_thr.start()
    return True

mm_tm_begin = datetime.datetime.now()

def my_mainloop():
    global mm_tm_begin
    disp_thr_watcher()
    if opt_monitor_clipboard == True:
        disp_thr_clipmon()
    disp_thr_view()
    disp_thr_saver()
    disp_thr_resolve()
    disp_item_apply()
    gui.after(300, my_mainloop)
    mm_tm_end = datetime.datetime.now()
    mm_tm_delta = (mm_tm_end - mm_tm_begin).seconds
    if mm_tm_delta > opt_retry_delay_second:
        mm_tm_begin = mm_tm_end
        disp_item_reset()
    return True

"""
Gui functions
"""

from tkinter import *
from tkinter import filedialog, messagebox, simpledialog
from tkinter.ttk import *

"""
Inserting data
"""

try:
    lastins = open("saved.log", "r", encoding="utf-8")
    last_dat = lastins.read()
    # last_dat = ""
    lastins.close()
except FileNotFoundError:
    last_dat = ""
last_line = ""
for chr in last_dat:
    if chr == "\n":
        if len(last_line) > 0:
            last_line = chomp(last_line)
            disp_item_insert(last_line)
            last_line = ""
    else:
        last_line += chr

sig_mainstop = False

gui = Tk()
gui.after(300, my_mainloop)
gui.title("vpan-gui")

gui.rowconfigure(1,weight=1)
gui.columnconfigure(2,weight=1)

def my_add_addr():
    addr = simpledialog.askstring('Enter new address','Address (if using pages, use ADDRESS~PAGEBEGIN~PAGEEND)')
    if type(addr) != str:
        addr = ""
    if len(re.findall("vdisk\\.weibo\\.com", addr)) <= 0:
        return False
    if len(re.findall("~", addr)) > 0:
        address = re.findall("^(.*?)~.*?~.*?$", addr)[0]
        pagebegin = int(re.findall("^.*?~(.*?)~.*?$", addr)[0])
        pageend = int(re.findall("^.*?~.*?~(.*?)$", addr)[0])
        for i in range(pagebegin, pageend + 1):
            disp_item_insert(address + "?page=" + str(i))
    else:
        disp_item_insert(addr)
    return True

def my_move_files():
    path = simpledialog.askstring('Target directory','Directory:')
    if type(path) != str:
        return True
    if not os.path.exists(path):
        os.makedirs(path)
    for name in disp_arr_name:
        if disp_arr_stat[name] != "":
            continue
        fln = disp_arr_name[name]
        try:
            shutil.move(fln, path + "/" + fln)
        except FileNotFoundError:
            continue
    return True

Button(gui,text='Clear completed',command = disp_item_clear).grid(row=0,column=0)
Button(gui,text='Add address',command = my_add_addr).grid(row=0,column=1)
Button(gui,text='Move completed files',command = my_move_files).grid(row=0,column=2)
Button(gui,text='Reset erroneous',command = disp_item_reset).grid(row=0,column=3)

tree_f=Frame(gui)
tree_f.grid(row=1,column=0,columnspan=3,sticky='nswe')
tree_f.rowconfigure(0,weight=1)
tree_f.columnconfigure(0,weight=1)

tree=Treeview(tree_f,columns=('trurl','trstat'))
tree.grid(row=0,column=0,sticky='nswe')
tree_sbar=Scrollbar(tree_f,orient=VERTICAL,command=tree.yview)
tree_sbar.grid(row=0,column=1,sticky='ns')
tree['yscrollcommand'] = tree_sbar.set

tree.column('#0',width=300)
tree.column('trurl',width=350)
tree.column('trstat',width=250)
tree.heading('#0',text='Filename')
tree.heading('trurl',text='URL')
tree.heading('trstat',text='Status')

mainloop()

sig_mainstop = True
exit(0)
