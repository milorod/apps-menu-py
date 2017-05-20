#!/usr/bin/env python2

import os
import sys
import getopt
import re
import locale
import fnmatch
import io
import json
import shutil
import subprocess
import gtk
import pygtk
pygtk.require("2.0")


rebuild = False
dodebug = False
loading = False
apps_data = None
categ_data = None

basexpmf = u'/* XPM */\n'\
    'static char *default[] = {\n'\
    '/* columns rows colors chars-per-pixel */\n'\
    '"22 22 2 1 ",\n'\
    '"  c firebrick",\n'\
    '". c None",\n'\
    '/* pixels */\n'\
    '"......................",\n'\
    '"......................",\n'\
    '"......................",\n'\
    '"......................",\n'\
    '"......................",\n'\
    '"......................",\n'\
    '"......................",\n'\
    '"......................",\n'\
    '"........... ..........",\n'\
    '".........     ........",\n'\
    '".........     ........",\n'\
    '"........       .......",\n'\
    '".........     ........",\n'\
    '".........     ........",\n'\
    '"........... ..........",\n'\
    '"......................",\n'\
    '"......................",\n'\
    '"......................",\n'\
    '"......................",\n'\
    '"......................",\n'\
    '"......................",\n'\
    '"......................"\n'\
    '};\n'
menuxpmf = u'/* XPM */\n'\
    'static char *menu[] = {\n'\
    '/* columns rows colors chars-per-pixel */\n'\
    '"32 32 8 1 ",\n'\
    '"  c black",\n'\
    '". c #07EC07EC07EC",\n'\
    '"X c #3A393A393A39",\n'\
    '"o c #CE36CE36CE36",\n'\
    '"O c #DB1EDB1EDB1E",\n'\
    '"+ c #E0A3E0A3E0A3",\n'\
    '"@ c white",\n'\
    '"# c None",\n'\
    '/* pixels */\n'\
    '"################################",\n'\
    '"################################",\n'\
    '"################################",\n'\
    '"################################",\n'\
    '"################################",\n'\
    '"###                           ##",\n'\
    '"##.XO+++++++++++++++++++++++OX.#",\n'\
    '"## o@@@@@@@@@@@@@@@@@@@@@@@@@o #",\n'\
    '"## o@@@@@@@@@@@@@@@@@@@@@@@@@o #",\n'\
    '"##.XO+++++++++++++++++++++++OX.#",\n'\
    '"###                           ##",\n'\
    '"################################",\n'\
    '"################################",\n'\
    '"###                           ##",\n'\
    '"##.XO+++++++++++++++++++++++OX.#",\n'\
    '"## o@@@@@@@@@@@@@@@@@@@@@@@@@o #",\n'\
    '"## o@@@@@@@@@@@@@@@@@@@@@@@@@o #",\n'\
    '"##.XO+++++++++++++++++++++++OX.#",\n'\
    '"###                           ##",\n'\
    '"################################",\n'\
    '"################################",\n'\
    '"###                           ##",\n'\
    '"##.XO+++++++++++++++++++++++OX.#",\n'\
    '"## o@@@@@@@@@@@@@@@@@@@@@@@@@o #",\n'\
    '"## o@@@@@@@@@@@@@@@@@@@@@@@@@o #",\n'\
    '"##.XO+++++++++++++++++++++++OX.#",\n'\
    '"###                           ##",\n'\
    '"################################",\n'\
    '"################################",\n'\
    '"################################",\n'\
    '"################################",\n'\
    '"################################"\n'\
    '};\n'

sendmenuicon = False


def usage():
    print("Usage: %s [ -h -r -d ]" % (sys.argv[0]))
    print("-h | --help        this help\n"
          "-r | --rebuild     rebuild apps cache\n"
          "-d | --debug       print debug info")


try:
    opts, args = getopt.getopt(sys.argv[1:], 'rdhi', ['rebuild', 'debug',
                               'help', 'icon'])
except getopt.GetoptError as err:
    print(err)
    usage()
    sys.exit(2)

for opt, arg in opts:
    if opt in ('-h', '--help'):
        usage()
        sys.exit(2)
    elif opt in ('-r', '--rebuild'):
        rebuild = True
    elif opt in ('-d', '--debug'):
        dodebug = True
    elif opt in ('-i', '--icon'):   # for tint2
        sendmenuicon = True
    else:
        usage()
        sys.exit(2)

home = os.environ['HOME']
if "XDG_CACHE_HOME" in os.environ:
    cachedir = os.environ['XDG_CACHE_HOME']
else:
    cachedir = os.path.join(home, ".cache")
if not dodebug:
    img_cache_path = os.path.join(cachedir, "apps-menu")
else:
    img_cache_path = os.path.join(cachedir, "apps-menu-debug")

menuicon = os.path.join(img_cache_path, "menu.xpm")
if sendmenuicon:
        print(menuicon + "\n\n")
        sys.exit(0)

baseicon = os.path.join(img_cache_path, "default.xpm")
json_cache = os.path.join(img_cache_path, 'data.json')
iconpaths = ("/usr/share/icons",
             "/usr/share/pixmaps",
             os.path.join(home, ".icons"),
             os.path.join(home, ".local/share/icons"),
             "/usr/local/share/icons")

if os.path.exists('/usr/bin/i3-sensible-terminal'):
    aterm = ["i3-sensible-terminal", "-e"]
else:
    aterm = ["xterm", "-e"]

if rebuild:
    if os.path.isdir(img_cache_path):
        shutil.rmtree(img_cache_path)
else:
    if os.path.isfile(json_cache):
        with open(json_cache) as f:
            json_data = json.load(f)
            apps_data = json_data["apps"]
            categ_data = json_data["categories"]


def iter_idling(label, text):
    if label:
        label.set_text(text)
    while gtk.events_pending():
        gtk.main_iteration(False)


def load_data(label=None):
    global apps_data, loading, categ_data
    if loading:
        return
    loading = True
    iter_idling(label, "searching desktop files")
    clocale = locale.getdefaultlocale()
    clocale = re.sub(r'@.*', '', clocale[0])
    suffixes = [clocale]
    clocale = re.sub(r'_.*', '', clocale)
    suffixes.append(clocale)
    if 'XDG_DATA_HOME' in os.environ:
        xdg_data_home = os.environ['XDG_DATA_HOME']
    else:
        xdg_data_home = os.path.join(home, ".local/share")
    if 'XDG_DATA_DIRS' in os.environ:
        xdg_data_dirs = os.environ['XDG_DATA_DIRS']
    else:
        xdg_data_dirs = '/usr/local/share:/usr/share'

    searchdirs = [os.path.join(xdg_data_home, "applications")]
    for dir in xdg_data_dirs.split(':'):
        searchdirs.append(os.path.join(dir, "applications"))

    # find all .desktop files
    desktops = {}
    for searchdir in searchdirs:
        for root, subFolders, filenames in os.walk(searchdir):
            for filename in fnmatch.filter(filenames, '*.desktop'):
                    if filename not in desktops:
                        desktops[filename] = os.path.join(root, filename)

    iter_idling(label, "inspecting files")
    # inspect .desktop files
    apps = {}
    for fname in desktops:
        fpath = desktops[fname]
        apps[fname] = {}
        apps[fname]['_location'] = fpath
        names = {}
        with io.open(fpath, 'r', encoding='utf8') as f:
            if dodebug:
                print('reading', fpath)
            content = f.readlines()
            if len(content) < 1:
                f.close()
                continue
            dentry = False
            for line in content:
                if len(line) < 1 or line[0] == '#':
                    continue
                if line.startswith('[Desktop Entry]'):
                    dentry = True
                    continue
                elif dentry and line[0] == '[':
                    dentry = False
                    continue
                if dentry:
                    m = re.match("([A-Za-z0-9]+(?:\[[^]]+\])?)\s*=\s*(.*)",
                                 line)
                    if m:
                        k = m.groups()[0]
                        v = m.groups()[1]
                        if k.startswith('Name'):
                            names[k] = v
                        elif k in ('Exec', 'TryExec', 'Path', 'Type', 'Icon',
                                   'Categories'):
                            apps[fname][k] = v
                        elif k in ('NoDisplay', 'Hidden', 'StartupNotify',
                                   'Terminal'):
                            apps[fname][k] = True if v == 'true' else False
            for suff in suffixes:
                if "Name[" + suff + "]" in names:
                    apps[fname]["Name"] = names["Name[" + suff + "]"]
                    break
            if 'Name' not in apps[fname]:
                apps[fname]['Name'] = names['Name']

    if not os.path.exists(img_cache_path):
        os.makedirs(img_cache_path)
    if not os.path.exists(baseicon):
        with io.open(baseicon, 'w') as f:
            f.write(basexpmf)
            f.close()
    if not os.path.exists(menuicon):
        with io.open(menuicon, 'w') as f:
            f.write(menuxpmf)
            f.close()

    def findincon(app):
        icon_cached = baseicon
        if 'Icon' in app:
            icname = app['Icon']
            if icname.startswith('/'):
                if os.path.isfile(icname):  # icon defined with full path
                    icon_cached = icname
            else:
                d_icon_cached = img_cache_path + "/" + icname + '.png'
                if os.path.isfile(d_icon_cached):  # icon already cached
                    icon_cached = d_icon_cached
                else:
                    extensions = ['.png', '.svg', '.xpm', '.jpg', '.gif']
                    for icondir in iconpaths:
                        for root, subFolders, filenames in os.walk(icondir):
                            for filename in filenames:
                                if filename == icname:
                                    icon_cached = os.path.join(root, filename)
                                elif any(filename == icname + e
                                         for e in extensions):
                                    icon_cached = os.path.join(root, filename)
        return icon_cached

    def is_exe(fpath):
        return os.path.isfile(fpath) and os.access(fpath, os.X_OK)

    def exe_path(exe):
        aexe = exe.split(' ')
        if len(aexe) > 1 and aexe[1].startswith('%'):
            exe = aexe[0]
        fexe = None
        if aexe[0].startswith('/'):
            if is_exe(aexe[0]):
                fexe = exe
        else:
            for p in os.environ['PATH'].split(':'):
                if is_exe(os.path.join(p, aexe[0])):
                    fexe = os.path.join(p, exe)
                    break
        return fexe

    iter_idling(label, "collecting apps")
    choices = {}
    categs = {}
    for app in apps:
        if dodebug:
            print("evaluating", app)
        if 'Type' not in apps[app] or apps[app]['Type'] != 'Application':
            continue
        elif 'Exec' not in apps[app] and 'TryExec' not in apps[app]:
            continue
        elif 'NoDisplay' in apps[app] and apps[app]['NoDisplay']:
            continue
        elif 'Hidden' in apps[app] and apps[app]['Hidden']:
            continue
        name = apps[app]["Name"]
        executable = None
        if 'TryExec' in apps[app]:
            executable = exe_path(apps[app]['TryExec'])
        elif 'Exec' in apps[app]:
            executable = exe_path(apps[app]['Exec'])

        if executable is None:
            continue
        else:
            apps[app]['_exec'] = executable
        iname = name
        i = 1
        while iname in choices:
            i = i + 1
            iname = name + " (" + str(i) + ')'
        choices[iname] = app
        apps[app]['_choice'] = iname
        icon = findincon(apps[app])
        if icon.startswith(img_cache_path):
            apps[app]['_icon'] = icon
        else:
            filename = os.path.basename(icon)
            (fbase, fext) = os.path.splitext(filename)
            icname = fbase + ".png"
            ic_ch = os.path.join(img_cache_path, icname)
            pixbuf = gtk.gdk.pixbuf_new_from_file(icon)
            scaled_buf = pixbuf.scale_simple(20, 20, gtk.gdk.INTERP_BILINEAR)
            scaled_buf.save(ic_ch, 'png')
            apps[app]['_icon'] = ic_ch
        choices[apps[app]['_choice']] = apps[app]
        if 'Categories' in apps[app]:
            acat = apps[app]['Categories'].split(';')
            for cat in acat:
                if cat == "":
                    continue
                if cat in categs:
                    categs[cat]['catlist'].append(iname)
                else:
                    categs[cat] = {}
                    categs[cat]['catname'] = cat
                    categs[cat]['catlist'] = [iname]
    if dodebug:
        print("== Apps==")
        print(unicode(json.dumps(choices, ensure_ascii=False)))
        print("== Categories==")
        print(unicode(json.dumps(categs, ensure_ascii=False)))
        print("== Sorting...")
    iter_idling(label, "sorting")
    sortedchoices = []
    for key in sorted(choices.iterkeys()):
        sortedchoices.append(choices[key])
    sortedcategs = []
    for key in sorted(categs.iterkeys()):
        sortedcategs.append(categs[key])
    json_data = {}
    json_data["apps"] = sortedchoices
    json_data["categories"] = sortedcategs
# save apps_data as json file
    if dodebug:
        print("== Saving data")
    with io.open(json_cache, 'w', encoding='utf8') as f:
        f.write(unicode(json.dumps(json_data, ensure_ascii=False)))
    apps_data = sortedchoices
    categ_data = sortedcategs
    loading = False
    iter_idling(label, "done")
    if dodebug:
        print("== Done")


def msgDialog(txt):
    message = gtk.MessageDialog(buttons=gtk.BUTTONS_OK)
    message.set_markup(txt)
    message.run()
    message.destroy()


class RebuildWait():
    # GTK Window
    def __init__(self):
        self.window = gtk.Dialog()
        self.window.set_modal(gtk.TRUE)
        self.window.set_size_request(400, 40)
        self.window.set_title("Rebuilding...please wait...")
        self.label = gtk.Label()
        self.label.set_text("..working...")
        self.window.vbox.pack_start(self.label, True, True, 0)
        self.window.set_position(gtk.WIN_POS_CENTER_ALWAYS)
        self.window.set_resizable(False)
        self.window.show_all()

    def destroy(self):
        self.window.destroy()


class PyApp(gtk.Window):
    def create_model(self, catefilter=None):
        global apps_data, categ_data
        store = gtk.ListStore(gtk.gdk.Pixbuf, str)
        choices = []
        addit = False if catefilter else True
        for app in apps_data:
            if catefilter:
                try:
                    apcats = app["Categories"].split(';')
                except (TypeError, KeyError) as e:
                    apcats = []
                addit = catefilter in apcats
            if addit:
                choices.append((app['_icon'], app['_choice']))
                pixbuf = gtk.gdk.pixbuf_new_from_file(app['_icon'])
                store.append([pixbuf, app['_choice']])
        choices.sort(key=lambda v: v[1].lower())
        if self.prg is not None:
            self.prg.destroy()
            self.prg = None
        return store

    def __init__(self):
        global categ_data, apps_data
        self.all_categories = "-- All --"
        super(PyApp, self).__init__()
        self.set_size_request(350, 450)
        self.set_position(gtk.WIN_POS_CENTER)
        self.set_wmclass("apps-menu.py", "Apps-menu")
        self.connect("destroy", gtk.main_quit)
        self.set_title("Desktop Apps")
        self.vbox = gtk.VBox(False, 8)
        self.prg = None

# menu bar
        if apps_data is None or categ_data is None:
            self.prg = RebuildWait()
            load_data(self.prg.label)
            iter_idling(self.prg.label, "adding icons")
        mb = gtk.MenuBar()
        filemenu = gtk.Menu()
        filem = gtk.MenuItem("_File", True)
        filem.set_submenu(filemenu)
        about = gtk.MenuItem("_About Apps Menu", True)
        about.connect("activate", self.about)
        filemenu.append(about)
        rebuild = gtk.MenuItem("_Rebuild List", True)
        rebuild.connect("activate", self.rebuild_list)
        filemenu.append(rebuild)
        filemenu.append(gtk.SeparatorMenuItem())
        exit = gtk.MenuItem("_Exit (Ctrl-q)", True)
        exit.connect("activate", gtk.main_quit)
        filemenu.append(exit)
        mb.append(filem)
        # add categories menu
        if dodebug:
            print(unicode(json.dumps(categ_data, ensure_ascii=False)))
        catemenu = gtk.Menu()
        catem = gtk.MenuItem("_Categories", True)
        catem.set_submenu(catemenu)
        ccatm = gtk.MenuItem(self.all_categories, True)
        ccatm.connect("activate", self.set_category, self.all_categories)
        catemenu.append(ccatm)
        for ccat in categ_data:
            ccatm = gtk.MenuItem(ccat["catname"], True)
            ccatm.connect("activate", self.set_category, ccat["catname"])
            catemenu.append(ccatm)
        mb.append(catem)
        self.vbox.pack_start(mb, False, False, 0)

# scroll window
        self.sw = gtk.ScrolledWindow()
        self.sw.set_shadow_type(gtk.SHADOW_ETCHED_IN)
        self.sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        self.vbox.pack_start(self.sw, True, True, 0)

# create treeview
        store = self.create_model()
        self.treeView = gtk.TreeView(store)
        self.treeView.connect("row-activated", self.on_activated)
        self.treeView.set_rules_hint(True)
        self.sw.add(self.treeView)
        self.create_columns(self.treeView)
        # set single selection mode so that return can be used for app launch
        treesel = self.treeView.get_selection()
        treesel.set_mode(gtk.SELECTION_SINGLE)

        # run
        self.statusbar = gtk.Statusbar()
        self.vbox.pack_start(self.statusbar, False, False, 0)
        self.add(self.vbox)
        self.connect("key-press-event", self.on_window_key_press_event)
        self.show_all()

    def create_columns(self, treeView):
        (COL_PIXBUF, COL_STRING) = range(2)
        rendererPb = gtk.CellRendererPixbuf()
        column = gtk.TreeViewColumn(u'\u25CB', rendererPb, pixbuf=COL_PIXBUF)
        column.set_sort_column_id(0)
        treeView.append_column(column)
        rendererText = gtk.CellRendererText()
        column = gtk.TreeViewColumn("Name", rendererText, text=1)
        column.set_sort_column_id(1)
        treeView.append_column(column)

    def on_activated(self, widget, row, col):
        global dodebug
        model = widget.get_model()
        text = model[row][1]
        self.statusbar.push(0, text)
        choice = model[row][1]
        print(choice)
        for app in apps_data:
            if choice == app['_choice']:
                aexe = app['_exec'].split(' ')
                if dodebug:
                    print(app['_exec'])
                    print(app['_location'])
                    print(aexe)
                if 'Terminal' in app and app['Terminal']:
                    aexe = aterm + aexe
                subprocess.Popen(aexe)
                sys.exit(0)

    def on_window_key_press_event(self, window, event):
        keyname = gtk.gdk.keyval_name(event.keyval)
        if dodebug:
            print("Key %s (%d) was pressed" % (keyname, event.keyval))
            print("state: %s" % (event.state))
            if event.state & gtk.gdk.CONTROL_MASK:
                print("Control was being held down")
            if event.state & gtk.gdk.MOD1_MASK:
                print("Alt was being held down")
            if event.state & gtk.gdk.SHIFT_MASK:
                print("Shift was being held down")
        if event.state & gtk.gdk.CONTROL_MASK and keyname == "q":
            gtk.main_quit()

    def about(self, widget):
        about = gtk.AboutDialog()
        about.set_program_name("Apps Menu")
        about.set_version("0.1")
        about.set_copyright("by felisk - License MIT")
        about.set_comments("A menu of installed desktop applications\n"
                           "best used with i3wm")
        # about.set_website("http://www.zetcode.com")
        about.set_logo(gtk.gdk.pixbuf_new_from_file(menuicon))
        about.run()
        about.destroy()

    def rebuild_list(self, widget):
        global apps_data, categ_data
        shutil.rmtree(img_cache_path)
        apps_data = None
        categ_data = None
        store = self.create_model()
        self.treeView.set_model(store)
        msgDialog("Rebuild Done")

    def set_category(self, widget, cate):
        global dodebug
        if dodebug:
            print(cate)
        if cate == self.all_categories:
            store = self.create_model()
            self.set_title("Desktop Apps]")
        else:
            store = self.create_model(cate)
            self.set_title("Desktop Apps [" + cate + "]")
        self.treeView.set_model(store)


PyApp()
gtk.main()
