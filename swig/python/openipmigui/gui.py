# gui.py
#
# main openipmi GUI handling
#
# Author: MontaVista Software, Inc.
#         Corey Minyard <minyard@mvista.com>
#         source@mvista.com
#
# Copyright 2005 MontaVista Software Inc.
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU Lesser General Public License
#  as published by the Free Software Foundation; either version 2 of
#  the License, or (at your option) any later version.
#
#
#  THIS SOFTWARE IS PROVIDED ``AS IS'' AND ANY EXPRESS OR IMPLIED
#  WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF
#  MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED.
#  IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY DIRECT, INDIRECT,
#  INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
#  BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS
#  OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
#  ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR
#  TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE
#  USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
#  You should have received a copy of the GNU Lesser General Public
#  License along with this program; if not, write to the Free
#  Software Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
#
import wx
import wx.gizmos as gizmos
import OpenIPMI
import _domainDialog
import _saveprefs
import _cmdwin
import _oi_logging

init_treenamewidth = 150
init_sashposition = 100
init_bsashposition = 400
init_windowwidth = 400
init_windowheight = 500
init_logevents = False
init_fullevents = False

refresh_timer_time = 10000

id_st = 100

class IPMITreeDummyItem:
    def __init__(self):
        return

    pass

class IPMITreeCtrl(gizmos.TreeListCtrl):
    def __init__(self, parent):
        gizmos.TreeListCtrl.__init__(self, parent)
        self.AddColumn("Name")
        self.AddColumn("Value")
        self.SetMainColumn(0)
        self.SetColumnWidth(0, init_treenamewidth)
        self.SetColumnWidth(1, 800)
        return

    def OnCompareItems(self, item1, item2):
        t1 = self.GetItemText(item1)
        t2 = self.GetItemText(item2)
        self.log.WriteText('compare: ' + t1 + ' <> ' + t2 + '\n')
        if t1 < t2: return -1
        if t1 == t2: return 0
        return 1

    pass

class IPMICloser:
    def __init__(self, ui, count):
        self.ui = ui
        self.count = count
        return
    
    def domain_cb(self, domain):
        domain.close(self)
        return

    def domain_close_done_cb(self):
        self.count = self.count - 1
        if (self.count == 0):
            _cmdwin.init_history = self.ui.cmdwindow.history
            self.ui.Destroy()
            pass
        return
    pass

class IPMIGUI_Timer(wx.Timer):
    def __init__(self, ui):
        wx.Timer.__init__(self)
        self.ui = ui
        self.Start(refresh_timer_time, oneShot=True)
        return

    def Notify(self):
        self.ui.Timeout()
        self.Start(refresh_timer_time, oneShot=True)
        return

    pass

class IPMIGUI(wx.Frame):
    def __init__(self, mainhandler):
        wx.Frame.__init__(self, None, -1, "IPMI GUI",
                          size=wx.Size(init_windowwidth, init_windowheight))

        self.mainhandler = mainhandler

        self.logevents = init_logevents
        self.fullevents = init_fullevents
        OpenIPMI.cmdlang_set_evinfo(self.fullevents)
        
        menubar = wx.MenuBar()
        
        filemenu = wx.Menu()
        filemenu.Append(wx.ID_EXIT, "E&xit\tCtrl-Q", "Exit")
        wx.EVT_MENU(self, wx.ID_EXIT, self.quit);
        item = filemenu.Append(id_st+1, "&Open Domain\tCtrl-O", "Open Domain")
        wx.EVT_MENU(self, id_st+1, self.openDomain);
        item = filemenu.Append(id_st+2, "&Save Prefs\tCtrl-S", "Save Prefs")
        wx.EVT_MENU(self, id_st+2, self.savePrefs);
        menubar.Append(filemenu, "&File")
        
        viewmenu = wx.Menu()
        item = viewmenu.Append(id_st+3, "&Expand All\tCtrl-E", "Expand All")
        wx.EVT_MENU(self, id_st+3, self.ExpandAll);
        item = viewmenu.Append(id_st+4,"&Collapse All\tCtrl-C", "Collapse All")
        wx.EVT_MENU(self, id_st+4, self.CollapseAll);
        menubar.Append(viewmenu, "&View")

        self.settingsmenu = wx.Menu()
        self.EnabEvent = self.settingsmenu.AppendCheckItem(id_st+5,
                                                           "Enable Events",
                                                           "Enable Events")
        wx.EVT_MENU(self, id_st+5, self.EnableEvents);
        self.settingsmenu.Check(id_st+5, self.logevents)
        self.EnabEvent = self.settingsmenu.AppendCheckItem(id_st+6,
                                                           "Full Event Info",
                                                           "Full Event Info")
        wx.EVT_MENU(self, id_st+6, self.FullEventInfo);
        self.settingsmenu.Check(id_st+6, self.fullevents)
        menubar.Append(self.settingsmenu, "&Settings")

        self.SetMenuBar(menubar)

        self.bsplitter = wx.SplitterWindow(self, -1)
        self.bsplitter.SetMinimumPaneSize(10)

        self.splitter = wx.SplitterWindow(self.bsplitter, -1)
        self.splitter.SetMinimumPaneSize(10)

        self.tree = IPMITreeCtrl(self.splitter)
        self.treeroot = self.tree.AddRoot("Domains")
        self.tree.SetPyData(self.treeroot, self)
        self.setup_item(self.treeroot, active=True)

        self.logwindow = wx.TextCtrl(self.splitter, -1,
                                     style=(wx.TE_MULTILINE
                                            | wx.TE_READONLY
                                            | wx.HSCROLL))
        self.logcount = 0
        self.maxloglines = 1000

        self.splitter.SplitVertically(self.tree, self.logwindow)
        self.splitter.SetSashPosition(init_sashposition)

        self.bpanel = wx.Panel(self.bsplitter, -1)
        bpsizer = wx.BoxSizer(wx.VERTICAL)
        self.cmdwindow = _cmdwin.CommandWindow(self.bpanel)
        bpsizer.Add(self.cmdwindow, 1, wx.ALIGN_CENTRE | wx.ALL | wx.GROW, 2)
        self.bpanel.SetSizer(bpsizer)
        self.bsplitter.SplitHorizontally(self.splitter, self.bpanel)
        self.bsplitter.SetSashPosition(init_bsashposition)

        wx.EVT_TREE_ITEM_RIGHT_CLICK(self.tree, -1, self.TreeMenu)
        wx.EVT_TREE_ITEM_EXPANDED(self.tree, -1, self.TreeExpanded)

        wx.EVT_CLOSE(self, self.OnClose)
        
        self.CreateStatusBar(1)
        self.SetStatusText("Welcome to the OpenIPMI GUI!", 0)

        self.Show(True)

        self.last_scan = None
        self.timer = IPMIGUI_Timer(self)
        return

    def ReportError(self, str):
        self.SetStatusText(str, 0)
        return
    
    def Timeout(self):
        if self.last_scan != None:
            next = self.last_scan
        else:
            next = self.tree.GetFirstVisibleItem()
            pass
        callcount = 0
        checkcount = 0
        while (callcount < 100) and (checkcount < 1000) and next.IsOk():
            data = self.tree.GetPyData(next)
            if (data != None) and (hasattr(data, "DoUpdate")):
                callcount = callcount + 1
                data.DoUpdate()
                pass
            next = self.tree.GetNextVisible(next)
            checkcount = checkcount + 1
            pass
            
        if next.IsOk():
            self.last_scan = next
        else:
            self.last_scan = None
            pass
        return
        
    def quit(self, event):
        self.Close(True)
        return

    def OnClose(self, event):
        self.closecount = len(self.mainhandler.domains)
        if (self.closecount == 0):
            _cmdwin.init_history = self.cmdwindow.history
            self.Destroy()
            return
        closer = IPMICloser(self, self.closecount)
        ds = self.mainhandler.domains.values()
        for v in ds:
            v.domain_id.to_domain(closer)
            pass
        return

    def openDomain(self, event):
        dialog = _domainDialog.OpenDomainDialog(self.mainhandler)
        dialog.CenterOnScreen();
        dialog.Show(True);
        return

    def savePrefs(self, event):
        self.mainhandler.savePrefs()
        return

    def ExpandItem(self, item):
        (child, cookie) = self.tree.GetFirstChild(item)
        while child.IsOk():
            if self.tree.ItemHasChildren(child):
                self.tree.Expand(child)
                self.ExpandItem(child)
                pass
            (child, cookie) = self.tree.GetNextChild(item, cookie)
            pass
        return
        
    def ExpandAll(self, event):
        self.tree.Expand(self.treeroot)
        self.ExpandItem(self.treeroot)
        return
        
    def CollapseItem(self, item):
        (child, cookie) = self.tree.GetFirstChild(item)
        while child.IsOk():
            if self.tree.ItemHasChildren(child):
                self.tree.Collapse(child)
                self.CollapseItem(child)
                pass
            (child, cookie) = self.tree.GetNextChild(item, cookie)
            pass
        return
        
    def CollapseAll(self, event):
        self.CollapseItem(self.treeroot)
        return
        
    def EnableEvents(self, event):
        self.logevents = self.settingsmenu.IsChecked(id_st+5)
        return
    
    def FullEventInfo(self, event):
        self.fullevents = self.settingsmenu.IsChecked(id_st+6)
        OpenIPMI.cmdlang_set_evinfo(self.fullevents)
        return
    
    def new_log(self, log):
        newlines = log.count('\n') + 1
        self.logwindow.AppendText(log + "\n")
        self.logcount += newlines
        while (self.logcount > self.maxloglines):
            end = self.logwindow.GetLineLength(0)
            self.logwindow.Remove(0, end+1)
            self.logcount -= 1
            pass
        return

    def setup_item(self, item, active=False):
        data = self.tree.GetPyData(item)
        data.active = active
        data.num_warning = 0
        data.num_severe = 0
        data.num_critical = 0
        if (not active):
            self.tree.SetItemTextColour(item, wx.LIGHT_GREY)
            pass
        return

    def cleanup_item(self, item):
        data = self.tree.GetPyData(item)
        if (data == None):
            return
        parent = self.tree.GetItemParent(item)
        if not parent.IsOk():
            return
        while (data.num_warning > 0):
            data.num_warning = data.num_warning - 1;
            self.decr_item_warning(parent); 
            pass
        while (data.num_severe > 0):
            data.num_severe = data.num_severe - 1;
            self.decr_item_severe(parent); 
            pass
        while (data.num_critical > 0):
            data.num_critical = data.num_critical - 1;
            self.decr_item_critical(parent); 
            pass
        return

    def add_domain(self, d):
        d.name_str = str(d)
        d.treeroot = self.tree.AppendItem(self.treeroot, d.name_str)
        self.tree.SetPyData(d.treeroot, d)
        self.setup_item(d.treeroot, active=True)
        d.entityroot = self.tree.AppendItem(d.treeroot, "Entities")
        self.tree.SetPyData(d.entityroot, IPMITreeDummyItem())
        self.setup_item(d.entityroot, active=True)
        d.mcroot = self.tree.AppendItem(d.treeroot, "MCs")
        self.tree.SetPyData(d.mcroot, IPMITreeDummyItem())
        self.setup_item(d.mcroot, active=True)
        d.conns = self.tree.AppendItem(d.treeroot, "Connections")
        self.tree.SetPyData(d.conns, IPMITreeDummyItem())
        self.setup_item(d.conns, active=True)
        self.tree.Expand(self.treeroot)
        return

    def prepend_item(self, o, name, value, data=None, parent=None):
        if (data == None):
            data = IPMITreeDummyItem()
            pass
        data.name_str = name
        if (parent == None):
            parent = o.treeroot
            pass
        item = self.tree.PrependItem(parent, name + ":")
        if (value == None):
            self.tree.SetItemTextColour(item, wx.LIGHT_GREY)
        else:
            self.tree.SetItemText(item, value, 1)
            self.tree.SetItemTextColour(item, wx.BLACK)
            pass
        self.tree.SetPyData(item, data)
        return item

    def append_item(self, o, name, value, data=None, parent=None):
        if (data == None):
            data = IPMITreeDummyItem()
            pass
        data.name_str = name
        if (parent == None):
            parent = o.treeroot
            pass
        item = self.tree.AppendItem(parent, name + ":")
        if (value == None):
            self.tree.SetItemTextColour(item, wx.LIGHT_GREY)
        else:
            self.tree.SetItemText(item, value, 1)
            self.tree.SetItemTextColour(item, wx.BLACK)
            pass
        self.tree.SetPyData(item, data)
        return item

    def set_item_text(self, item, value):
        data = self.tree.GetPyData(item)
        name = data.name_str
        if (value == None):
            self.tree.SetItemText(item, "", 1)
            self.tree.SetItemTextColour(item, wx.LIGHT_GREY)
            pass
        else:
            self.tree.SetItemText(item, value, 1)
            if (hasattr(data, "active")):
                if (data.active):
                    self.set_item_color(item)
                    pass
                pass
            else:
                self.set_item_color(item)
                pass
            pass
        return

    def set_item_inactive(self, item):
        data = self.tree.GetPyData(item)
        data.active = False
        self.tree.SetItemTextColour(item, wx.LIGHT_GREY)
        return

    def set_item_color(self, item):
        if (data.num_critical > 0):
            self.tree.SetItemTextColour(item, wx.BLUE)
            return
        if (data.num_severe > 0):
            self.tree.SetItemTextColour(item, wx.RED)
            return
        if (data.num_warning > 0):
            self.tree.SetItemTextColour(item, wx.NamedColour('YELLOW'))
            return
        self.tree.SetItemTextColour(item, wx.BLACK)
        return
        
    def set_item_active(self, item):
        data = self.tree.GetPyData(item)
        data.active = True
        self.set_item_color(item)
        return
        
    def incr_item_warning(self, item):
        parent = self.tree.GetItemParent(item)
        if parent.IsOk():
           self.incr_item_warning(parent); 
           pass
        data = self.tree.GetPyData(item)
        if (data == None):
            return
        data.num_warning = data.num_warning + 1
        if (not data.active):
            return
        if (data.num_critical > 0):
            return
        if (data.num_severe > 0):
            return
        if (data.num_warning == 1):
            self.tree.SetItemTextColour(item, wx.NamedColour('YELLOW'))
            pass
        return
        
    def decr_item_warning(self, item):
        parent = self.tree.GetItemParent(item)
        if parent.IsOk():
           self.decr_item_warning(parent);
           pass
        data = self.tree.GetPyData(item)
        if (data == None):
            return
        data.num_warning = data.num_warning - 1
        if (not data.active):
            return
        if (data.num_critical > 0):
            return
        if (data.num_severe > 0):
            return
        if (data.num_warning > 0):
            return
        self.tree.SetItemTextColour(item, wx.BLACK)
        return
        
    def incr_item_severe(self, item):
        parent = self.tree.GetItemParent(item)
        if parent.IsOk():
           self.incr_item_severe(parent); 
        data = self.tree.GetPyData(item)
        if (data == None):
            return
        data.num_severe = data.num_severe + 1
        if (not data.active):
            return
        if (data.num_critical > 0):
            return
        if (data.num_severe == 1):
            self.tree.SetItemTextColour(item, wx.RED)
        
    def decr_item_severe(self, item):
        parent = self.tree.GetItemParent(item)
        if parent.IsOk():
           self.decr_item_severe(parent); 
           pass
        data = self.tree.GetPyData(item)
        if (data == None):
            return
        data.num_severe = data.num_severe - 1
        if (not data.active):
            return
        if (data.num_critical > 0):
            return
        if (data.num_severe > 0):
            return
        if (data.num_warning > 0):
            self.tree.SetItemTextColour(item, wx.NamedColour('YELLOW'))
            return
        self.tree.SetItemTextColour(item, wx.BLACK)
        return
        
    def incr_item_critical(self, item):
        parent = self.tree.GetItemParent(item)
        if parent.IsOk():
           self.incr_item_critical(parent); 
           pass
        data = self.tree.GetPyData(item)
        if (data == None):
            return
        data.num_critical = data.num_critical + 1
        if (not data.active):
            return
        if (data.num_critical == 1):
            self.tree.SetItemTextColour(item, wx.BLUE)
            pass
        return
        
    def decr_item_critical(self, item):
        parent = self.tree.GetItemParent(item)
        if parent.IsOk():
           self.decr_item_critical(parent); 
           pass
        data = self.tree.GetPyData(item)
        if (data == None):
            return
        data.num_critical = data.num_critical - 1
        if (not data.active):
            return
        if (data.num_critical > 0):
            return
        if (data.num_severe > 0):
            self.tree.SetItemTextColour(item, wx.RED)
            return
        if (data.num_warning > 0):
            self.tree.SetItemTextColour(item, wx.NamedColour('YELLOW'))
            return
        self.tree.SetItemTextColour(item, wx.BLACK)
        return
        
    def get_item_pos(self, item):
        rect = self.tree.GetBoundingRect(item)
        if (rect == None):
            return None
        # FIXME - why do I have to add 25?
        return wx.Point(rect.GetLeft(), rect.GetBottom()+25)

    def TreeMenu(self, event):
        item = event.GetItem()
        data = self.tree.GetPyData(item)
        if (data != None) and (hasattr(data, "HandleMenu")):
            data.HandleMenu(event)
            pass
        return

    # FIXME - expand of parent doesn't affect children...
    def TreeExpanded(self, event):
        item = event.GetItem()
        data = self.tree.GetPyData(item)
        if (data != None) and (hasattr(data, "HandleExpand")):
            data.HandleExpand(event)
            pass
        return

    def remove_domain(self, d):
        if (hasattr(d, "treeroot")):
            self.tree.Delete(d.treeroot)
            self.cleanup_item(d.treeroot)
            pass
        return

    def add_connection(self, d, c):
        parent = d.conns
        c.name_str = str(c)
        c.treeroot = self.tree.AppendItem(parent, c.name_str)
        self.tree.SetPyData(c.treeroot, c)
        self.setup_item(c.treeroot, active=True)
        return
        
    def add_port(self, c, p):
        parent = c.treeroot
        p.name_str = str(p)
        p.treeroot = self.tree.AppendItem(parent, p.name_str)
        self.tree.SetPyData(p.treeroot, p)
        self.setup_item(p.treeroot, active=True)
        return
        
    def add_entity(self, d, e, parent=None):
        if (parent == None):
            parent = d.entityroot
        else:
            parent = parent.treeroot
            pass
        e.name_str = str(e)
        e.treeroot = self.tree.AppendItem(parent, e.name_str)
        self.tree.SetPyData(e.treeroot, e)
        self.setup_item(e.treeroot)
        e.sensorroot = self.tree.AppendItem(e.treeroot, "Sensors")
        self.tree.SetPyData(e.sensorroot, IPMITreeDummyItem())
        self.setup_item(e.sensorroot, active=True)
        e.controlroot = self.tree.AppendItem(e.treeroot, "Controls")
        self.tree.SetPyData(e.controlroot, IPMITreeDummyItem())
        self.setup_item(e.controlroot, active=True)
        return

    def reparent_entity(self, d, e, parent):
        if (parent == None):
            parent = d.entityroot
        else:
            parent = parent.treeroot
            pass
        ntreeroot = self.tree.AppendItem(parent, e.name_str)
        self.tree.SetPyData(ntreeroot, self.tree.GetPyData(e.treeroot))
        nsensorroot = self.tree.AppendItem(ntreeroot, "Sensors")
        self.tree.SetPyData(nsensorroot, self.tree.GetPyData(e.sensorroot))
        ncontrolroot = self.tree.AppendItem(ntreeroot, "Controls")
        self.tree.SetPyData(ncontrolroot, self.tree.GetPyData(e.controlroot))

        e.treeroot = ntreeroot
        e.sensorroot = nsensorroot
        e.controlroot = ncontrolroot
        return
    
    def remove_entity(self, e):
        if (hasattr(e, "treeroot")):
            self.tree.Delete(e.treeroot)
            self.cleanup_item(e.treeroot)
            pass
        return

    def add_mc(self, d, m):
        m.name_str = str(m)
        m.treeroot = self.tree.AppendItem(d.mcroot, m.name_str)
        self.tree.SetPyData(m.treeroot, m)
        self.setup_item(m.treeroot)
        return

    def remove_mc(self, m):
        if (hasattr(m, "treeroot")):
            self.tree.Delete(m.treeroot)
            self.cleanup_item(m.treeroot)
            pass
        return

    def add_sensor(self, e, s):
        s.name_str = str(s)
        s.treeroot = self.tree.AppendItem(e.sensorroot, s.name_str)
        self.tree.SetPyData(s.treeroot, s)
        self.setup_item(s.treeroot, active=True)
        return

    def remove_sensor(self, s):
        if (hasattr(s, "treeroot")):
            self.tree.Delete(s.treeroot)
            self.cleanup_item(s.treeroot)
            pass
        return

    def add_control(self, e, c):
        c.name_str = str(c)
        c.treeroot = self.tree.AppendItem(e.controlroot, c.name_str)
        self.tree.SetPyData(c.treeroot, c)
        self.setup_item(c.treeroot, active=True)
        return

    def remove_control(self, c):
        if (hasattr(c, "treeroot")):
            self.tree.Delete(c.treeroot)
            self.cleanup_item(c.treeroot)
            pass
        return

    # XML preferences handling
    def getTag(self):
        return "guiparms"

    def SaveInfo(self, doc, elem):
        (width, height) = self.GetSize()
        elem.setAttribute("windowwidth", str(width))
        elem.setAttribute("windowheight", str(height))
        elem.setAttribute("sashposition", str(self.splitter.GetSashPosition()))
        elem.setAttribute("bsashposition", str(self.bsplitter.GetSashPosition()))
        elem.setAttribute("treenamewidth", str(self.tree.GetColumnWidth(0)))
        elem.setAttribute("logevents", str(self.logevents))
        elem.setAttribute("fullevents", str(self.fullevents))
        return
    pass

def GetAttrInt(attr, default):
    try:
        return int(attr.nodeValue)
    except Exception, e:
        _oi_logging.error("Error getting init parm " + attr.nodeName +
                          ": " + str(e))
        return default

def GetAttrBool(attr, default):
    if (attr.nodeValue.lower() == "true") or (attr.nodeValue == "1"):
        return True
    elif (attr.nodeValue.lower() == "false") or (attr.nodeValue == "0"):
        return False
    else:
        _oi_logging.error ("Error getting init parm " + attr.nodeName)
        pass
    return default

class _GUIRestore(_saveprefs.RestoreHandler):
    def __init__(self):
        _saveprefs.RestoreHandler.__init__(self, "guiparms")
        return

    def restore(self, node):
        global init_windowheight
        global init_windowwidth
        global init_sashposition
        global init_bsashposition
        global init_treenamewidth
        global init_fullevents
        global init_logevents
        
        for i in range(0, node.attributes.length):
            attr = node.attributes.item(i)
            if (attr.nodeName == "windowwidth"):
                init_windowwidth = GetAttrInt(attr, init_windowwidth)
            elif (attr.nodeName == "windowheight"):
                init_windowheight = GetAttrInt(attr, init_windowheight)
            elif (attr.nodeName == "sashposition"):
                init_sashposition = GetAttrInt(attr, init_sashposition)
            elif (attr.nodeName == "bsashposition"):
                init_sashposition = GetAttrInt(attr, init_bsashposition)
            elif (attr.nodeName == "treenamewidth"):
                init_treenamewidth = GetAttrInt(attr, init_treenamewidth)
            elif (attr.nodeName == "logevents"):
                init_logevents = GetAttrBool(attr, init_logevents)
            elif (attr.nodeName == "fullevents"):
                init_fullevents = GetAttrBool(attr, init_fullevents)
                pass
            pass
        return
    pass

_GUIRestore()
    
