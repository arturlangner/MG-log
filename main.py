#!/usr/bin/python
import json
import time
import os
import traceback
from kivy.app import App
from kivy.uix.stacklayout import StackLayout
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.spinner import Spinner
from kivy.uix.splitter import Splitter
from kivy.uix.label import Label
from kivy.clock import Clock
from kivy.uix.button import Button
from kivy.uix.slider import Slider
from kivy.uix.textinput import TextInput
from kivy.uix.checkbox import CheckBox
#from kivy.uix.image import Image
from kivy.uix.popup import Popup
from kivy.lang import Builder
from kivy.core.window import Window
from kivy.uix.tabbedpanel import TabbedPanel
from kivy.uix.tabbedpanel import TabbedPanelItem
from kivy.uix.scrollview import ScrollView
from kivy.effects.scroll import ScrollEffect

#custom
import backend

class LogApp(App):
    backend = backend.LogBackend()

    field_enable = backend.getEnabledFields()
    field_skip = backend.getSkipFields()

    field_widget = {} #used to lookup text field based on name
    field_widget_reverse_dict = {} #inverse dictionary used to lookup name based on text field object
    default_value_field_widget = {}
    field_auto_skip_checkbox = {}
    field_width_setting_field = {}

    color_red = [0xFF/0xFF, 0x80/0xFF, 0x80/0xFF, 0.9]
    color_white = [1, 1, 1, 1]

    current_field_index = 0
    edit_id = 0

    def build(self):
        size = self.backend.getParameter('font_size')
        kv = self.kvConfigString(size)
        Builder.load_string(kv)
        Window.bind(on_draw=self.widthChange)
        self.main_window = BoxLayout()
        self.main_window.add_widget(self.constructMainWindow())
        return self.main_window

    def kvConfigString(self, size):
        kv = '<Root>:\n\tfont_size: dp('+size+')\n'
        kv = kv+'<Label>:\n\tfont_size: dp('+size+')\n'
        kv = kv+'<TextInput>:\n\tfont_size: dp('+size+')\n'
        #kv='#:set default_font_size "'+size+'dp"'
        return kv

    def getFieldHeight(self, n=1):
        return str(n*int(self.global_font_size)+20)+'dp'
        #return '25'

    def getFieldWidth(self, n=1):
        return str((n*int(self.global_font_size))-5)+'dp'

    def constructMainWindow(self):
        self.global_font_size = self.backend.getParameter('font_size')
        self.main_tabbed_panel = TabbedPanel(do_default_tab=False, size_hint=(1, 1))
        self.main_tabbed_panel.softinput_mode = 'scale'

        #-------------- settings tab ---------------------
        settings_tab = TabbedPanelItem(text='Settings')
        sv = ScrollView(size_hint=(1, 1), effect_cls=ScrollEffect, bar_width=5) #, size=(300, 300)
        #settings_box=BoxLayout(orientation='vertical',size_hint=(1, None),spacing=10,height=1000)#height='1100dp'
        settings_box = StackLayout(orientation='lr-tb', size_hint=(1, None), height=3000)

        #-----------settings: log picker  ----------
        log_picker_box = BoxLayout(orientation='vertical', size_hint=(1, None), height=self.getFieldHeight(3))
        log_picker_box.add_widget(Label(text='Select log', size_hint=(1, 1)))
        self.log_select_spinner = Spinner(text='default', values=('default'), size_hint=(1, 1))
        log_picker_box.add_widget(self.log_select_spinner)
        settings_box.add_widget(log_picker_box)

        settings_box.add_widget(Label(text='', size_hint=(1, None), height='25sp'))#spacer
        #-----------settings: new log ----------
        new_log_row_box = BoxLayout(orientation='horizontal', size_hint=(1, None), height=self.getFieldHeight())
        create_log_help_button = Button(text='Create log (?)', size_hint=(0.5, 1), is_focusable=False)
        new_log_row_box.add_widget(create_log_help_button)
        create_log_help_button.bind(on_press=self.createLogHelpButtonCallback)
        self.new_log_name_field = TextInput(text='', multiline=False, write_tab=False, keyboard_suggestions=False, size_hint=(1, None), height=self.getFieldHeight(), on_text_validate=self.newLogButtonCallback)
        new_log_row_box.add_widget(self.new_log_name_field)
        settings_box.add_widget(new_log_row_box)

        settings_box.add_widget(Label(text='', size_hint=(1, None), height='25sp'))#spacer
        #-----------settings: info field ----------
        info_field_box = BoxLayout(orientation='horizontal', size_hint=(1, None), height=self.getFieldHeight())
        info_field_help_button = Button(text='Info field text (?)', size_hint=(0.5, 1), is_focusable=False)
        info_field_box.add_widget(info_field_help_button)
        info_field_help_button.bind(on_press=self.infoFieldHelpButtonCallback)
        self.info_field_input = TextInput(text=self.backend.getParameter('info_text').replace('\n', '#'), multiline=False, write_tab=False, keyboard_suggestions=False, size_hint=(1, 1), on_text_validate=self.infoTextButtonCallback)
        info_field_box.add_widget(self.info_field_input)
        settings_box.add_widget(info_field_box)
        #--------------------------------

        settings_box.add_widget(Label(text='', size_hint=(1, None), height='25sp'))#spacer
        #-----------settings: core log fields ----------
        settings_box.add_widget(Label(text='Field settings', size_hint=(1, None), height=self.getFieldHeight()))

        description_box = BoxLayout(orientation='horizontal', size_hint=(1, None), height=self.getFieldHeight())
        description_box.add_widget(Label(text='Field', size_hint=(1, None), height=self.getFieldHeight()))

        default_field_button = Button(text='Default value (?)', size_hint=(1, None), height=self.getFieldHeight(), is_focusable=False)
        default_field_button.bind(on_press=self.callbackDefaultValueHelpPopup)
        description_box.add_widget(default_field_button)
        skip_cursor_button = Button(text='Skip (?)', size_hint=(1, None), height=self.getFieldHeight(), is_focusable=False)
        skip_cursor_button.bind(on_press=self.callbackAutoCursorHelpPopup)
        description_box.add_widget(skip_cursor_button)

        settings_box.add_widget(description_box)

        for i in self.field_enable:
            #field label
            field_box = BoxLayout(orientation='horizontal', size_hint=(1, None), height=self.getFieldHeight())
            field_box.add_widget(Label(text=self.backend.getFieldLabel(i), size_hint=(1, 1)))
            #default value field
            self.default_value_field_widget[i] = TextInput(valign='middle', text=self.backend.getFieldDefault(i), multiline=False, write_tab=False, keyboard_suggestions=False, size_hint=(1, 1))
            self.default_value_field_widget[i].bind(on_text_validate=self.saveDefaultValues)
            field_box.add_widget(self.default_value_field_widget[i])

            #skip checkbox setup and bind
            self.field_auto_skip_checkbox[i] = CheckBox(size_hint=(1, 1))
            if i in self.field_skip:
                self.field_auto_skip_checkbox[i].active = True
            self.field_auto_skip_checkbox[i].bind(active=self.saveSkipCheckboxes)
            field_box.add_widget(self.field_auto_skip_checkbox[i])
            settings_box.add_widget(field_box)


        settings_box.add_widget(Label(text='', size_hint=(1, None), height=self.getFieldHeight()))#spacer
        #-------settings: font size slider
        settings_box.add_widget(Label(text='Font size', size_hint=(1, None), height=self.getFieldHeight()))
        fontsize_box = BoxLayout(orientation='horizontal', size_hint=(1, None), height=self.getFieldHeight())
        self.font_size_slider = Slider(min=5, max=35, value=float(self.global_font_size))
        self.font_size_slider.bind(value=self.fontSliderValueChange)
        self.font_size_label = Label(text=self.global_font_size, size_hint=(None, 1))
        fontsize_box.add_widget(self.font_size_slider)
        fontsize_box.add_widget(self.font_size_label)
        settings_box.add_widget(fontsize_box)

        settings_box.add_widget(Label(text='', size_hint=(1, None), height='25sp'))#spacer
        #-------settings: delete log box
        delete_log_box = BoxLayout(orientation='vertical', size_hint=(1, None), height=self.getFieldHeight(3))
        delete_log_box.add_widget(Label(text='Delete log', size_hint=(1, 1)))
        delete_log_row_box = BoxLayout(orientation='horizontal', size_hint=(1, None), height=self.getFieldHeight(1))
        self.log_delete_spinner = Spinner(text='default', values=('default'), size_hint=(1, 1))
        delete_log_row_box.add_widget(self.log_delete_spinner)

        delete_log_inner_box = BoxLayout(orientation='horizontal', size_hint=(1, None), height=self.getFieldHeight(1))
        delete_log_inner_box.add_widget(Label(text='Unlock', halign='right', size_hint=(0.5, None), height=self.getFieldHeight()))
        self.unlock_delete_log_checkbox = CheckBox(size_hint=(0.5, 1))
        delete_log_inner_box.add_widget(self.unlock_delete_log_checkbox)
        delete_log_row_box.add_widget(delete_log_inner_box)

        delete_button = Button(text='Delete', size_hint=(1, 1), is_focusable=False)
        delete_button.bind(on_press=self.deleteButtonCallback)

        delete_log_row_box.add_widget(delete_button)
        delete_log_box.add_widget(delete_log_row_box)
        settings_box.add_widget(delete_log_box)

        settings_box.add_widget(Label(text='', size_hint=(1, None), height='25sp'))#spacer

        #dummy spacer
        #settings_box.add_widget(Label(text='',size_hint=(1, None),height=400))

        sv.add_widget(settings_box)
        settings_tab.add_widget(sv)

        #-------------- logging tab ----------------------
        self.log_tab = TabbedPanelItem(text='Log')
        fl = FloatLayout()
        log_tab_layout = AnchorLayout(anchor_x='left', anchor_y='top')

        log_input_layout = StackLayout(orientation='lr-tb', size_hint=(1, 1))
        self.info_label = Label(text=self.backend.getParameter('info_text'), size_hint=(0.3, None), height=self.getFieldHeight(2))
        log_input_layout.add_widget(self.info_label)

        for i in self.field_enable:
            field_box = BoxLayout(orientation='vertical', size_hint=(None, None), width=self.getFieldWidth(self.backend.getFieldInputWidth(i)), height=self.getFieldHeight(3))
            #field_box=BoxLayout(orientation='vertical',size_hint=(self.backend.getFieldWidthHint(i),None),height=self.getFieldHeight(3))
            field_box.add_widget(Label(text=self.backend.getFieldLabel(i), size_hint=(1, None), height=self.getFieldHeight(1)))
            self.field_widget[i] = TextInput(text=self.backend.getFieldDefault(i), multiline=False, write_tab=False, keyboard_suggestions=False, size_hint=(1, None), height=self.getFieldHeight(1))
            self.field_widget_reverse_dict[self.field_widget[i]] = i
            self.field_widget[i].bind(on_text_validate=self.textFieldCallback)
            field_box.add_widget(self.field_widget[i])
            log_input_layout.add_widget(field_box)

        self.save_button = Button(text='SAVE', size_hint=(0.2, None), height=self.getFieldHeight(3), is_focusable=False)
        self.save_button.bind(on_press=self.saveButtonCallback)
        log_input_layout.add_widget(self.save_button)

        self.edit_button = Button(text='EDIT', size_hint=(None, None), height=self.getFieldHeight(3), is_focusable=False)
        self.edit_button.bind(on_press=self.editButtonCallback)
        log_input_layout.add_widget(self.edit_button)

        log_tab_layout.add_widget(log_input_layout)

        bottom_layout = AnchorLayout(anchor_x='left', anchor_y='bottom')
        s = Splitter(sizable_from='top', size_hint=(1, 0.1), min_size=25)
        bottom_layout.add_widget(s)

        sv = ScrollView(size_hint=(1, 0.5), size=(300, 100), effect_cls=ScrollEffect)
        self.log_list = TextInput(text='', font_size=self.backend.getParameter('font_size')+'dp', font_name='DejaVuSansMono.ttf', size=(2000, 3000), size_hint=(None, None))
        sv.add_widget(self.log_list)
        s.add_widget(sv)

        fl.add_widget(log_tab_layout)
        fl.add_widget(bottom_layout)
        self.log_tab.add_widget(fl)

        #-------------- export tab ----------------------
        export_tab = TabbedPanelItem(text='Export')
        export_box = BoxLayout(orientation='vertical', size_hint=(1, 0.5), spacing=25)
        export_box.add_widget(Label(text='Select log for export', size_hint=(1, 0.3)))
        self.log_export_select_spinner = Spinner(text='default', values=('default', 'Home', 'Work', 'Other', 'Custom'), size_hint=(1, 0.3))
        export_box.add_widget(self.log_export_select_spinner)
        export_button = Button(text='Export to ADIF', size_hint=(1, 0.3), is_focusable=False)
        export_button.bind(on_press=self.exportLog)
        export_box.add_widget(export_button)
        export_tab.add_widget(export_box)
        #------------------------------------------------

        #------------- about tab ------------------------
        about_tab = TabbedPanelItem(text='About')
        about_box = BoxLayout(orientation='vertical', size_hint=(1, 1))
        about = self.backend.version_string+'\n\nby LB9MG\n\nwww.lb9mg.no\n\nlog@lb9mg.no\n\nLog database is stored in\n/storage/sdcard0/MG-log/mg-log.sqlite3\n\n\nTo edit an entry:\nplace the cursor on a line\n and press EDIT.'
        about_box.add_widget(Label(text=about, halign='center', size_hint=(1, 1)))
        about_tab.add_widget(about_box)
        #------------------------------------------------

        #adding all tabs in the right order
        self.main_tabbed_panel.add_widget(self.log_tab)
        self.main_tabbed_panel.add_widget(settings_tab)
        self.main_tabbed_panel.add_widget(export_tab)
        self.main_tabbed_panel.add_widget(about_tab)

        self.updateLogList()
        self.selectLog()
        self.log_select_spinner.bind(text=self.selectLog)
        self.backend.popupCallback = self.helpPopup
        self.field_widget[self.field_enable[0]].focus = True #focus in the first field

        return self.main_tabbed_panel

    def setFontSize(self, size):
        size = str(int(self.font_size_slider.value))
        self.backend.setParameter('font_size', size)
        kv = self.kvConfigString(size)
        self.main_window.clear_widgets()
        Builder.load_string(kv)
        self.main_window.add_widget(self.constructMainWindow())

    def fontSliderValueChange(self, *dummy):
        text = str(int(self.font_size_slider.value))
        self.font_size_label.text = text
        Clock.unschedule(self.setFontSize)
        Clock.schedule_once(self.setFontSize, 1.7)

    def on_pause(self, *dummy):
        return True

    def setWhiteFieldBackground(self, *dummy):
        self.field_widget[self.field_enable[0]].background_color = self.color_white
        self.field_widget[self.field_enable[0]].focus = True
        return False

    def widthChange(self, *dummy):
        self.main_tabbed_panel.tab_width = 0.99*(self.main_tabbed_panel.size[0]/4)

    def infoTextButtonCallback(self, *dummy):
        text_with_newline = self.info_field_input.text.replace('#', '\n')
        self.backend.setParameter('info_text', text_with_newline)
        self.info_label.text = text_with_newline

    def exportLog(self, *dummy):
        filename = self.backend.exportLog(self.log_export_select_spinner.text)
        msg = 'Exported to file :\n'+filename
        self.helpPopup(msg, title='Export')

    def saveDefaultValues(self, *dummy):
        default_values = {}
        for i in self.default_value_field_widget:
            default_values[i] = self.default_value_field_widget[i].text
        self.backend.setParameter('field_default', json.dumps(default_values))

    def saveSkipCheckboxes(self, *dummy):
        skip_list = []
        for i in self.field_auto_skip_checkbox:
            if self.field_auto_skip_checkbox[i].active:
                skip_list.append(i)
        self.backend.setParameter('field_skip', json.dumps(skip_list))
        self.field_skip = skip_list

    def selectLog(self, *dummy):
        self.backend.selectLog(self.log_select_spinner.text)
        self.updateLog()

    def newLogButtonCallback(self, *dummy):
        name = self.new_log_name_field.text
        if len(name) > 0:
            self.backend.newLog(name)
            logs = self.backend.getLogList()
            self.log_select_spinner.values = tuple(logs)
            self.log_select_spinner.text = logs[-1]
            self.log_export_select_spinner.values = tuple(logs)
            self.log_export_select_spinner.text = logs[-1]
            self.log_delete_spinner.values = tuple(logs)
            self.log_delete_spinner.text = logs[-1]
            self.selectLog()
            self.helpPopup('New log has been created', title='New log')

    def updateLogList(self):
        logs = self.backend.getLogList()
        self.log_select_spinner.text = logs[0]
        self.log_select_spinner.values = tuple(logs)
        self.log_export_select_spinner.text = logs[0]
        self.log_export_select_spinner.values = tuple(logs)
        self.log_delete_spinner.text = logs[0]
        self.log_delete_spinner.values = tuple(logs)

    def createLogHelpButtonCallback(self, instance):
        self.helpPopup('Type new log name and\npress enter when\nyou are done.')

    def infoFieldHelpButtonCallback(self, instance):
        self.helpPopup('Contents of this field are shown in the log entry screen.\nYou can place your current callsign,\nQTH locator or place you are operating from.\n It can make spelling details about your station easier.\n\nUse # for newline.\n\nPress enter when\nyou are done.')

    def callbackDefaultValueHelpPopup(self, instance):
        self.helpPopup('It is the value that will\nbe filled by default.\n\nUse NOW for current time in the UTC field.\n\nAfter change you have to restart the application.\n\nPress enter when\nyou are done.')

    def callbackAutoCursorHelpPopup(self, instance):
        self.helpPopup('When you enter new QSO details\nand press ENTER the cursor will be moved\nto the next field. It will skip the fields checked below.\n\nCheck the fields that do not change often\n(eg. band and mode).\n\nAfter the last field is typed and ENTER pressed,\nthe QSO will be added to the log.\n\nChecked fields will also not be cleared after adding a QSO.')

    def helpPopup(self, help_text, title='Help'):
        content = BoxLayout(orientation='vertical', size_hint=(1, 1))
        close_button = Button(text='Close', size_hint=(1, 0.2), is_focusable=False)
        content.add_widget(Label(text=help_text, halign='center'))
        content.add_widget(close_button)
        popup = Popup(title=title, content=content, auto_dismiss=False)
        # bind the on_press event of the button to the dismiss function
        close_button.bind(on_press=popup.dismiss)
        # open the popup
        popup.open()

    def textFieldCallback(self, *args):
        field = args[0] #there should be only one argument
        name = self.field_widget_reverse_dict[args[0]]
        self.current_field_index = self.field_enable.index(name)
        if self.current_field_index < len(self.field_enable)-1:
            next_index = self.findNextAvailableField(self.current_field_index)
            if next_index >= 0:
                self.field_widget[self.field_enable[next_index]].focus = True
            else:
                self.saveButtonCallback()
        else:
            self.saveButtonCallback()

    def findNextAvailableField(self, min=0):
        next_index = min
        found = False
        while next_index < len(self.field_enable)-1:
            next_index += 1
            if self.field_enable[next_index] in self.field_skip:
                pass
            else:
                found = True
                break
        if found:
            return next_index
        else:
            return -1

    def log(self, text):
        self.log_list.text = self.log_list.text + "\n" + text

    def updateLog(self):
        widths = self.backend.getFieldWidths()
        data = self.backend.getLogEntries()
        counter_format = '|%'+str(widths['no'])+'s|'
        output_text = ''

        self.entry_id_list = []
        row_len = 0
        for row in data:
            self.entry_id_list.append(row['id'])
            output_row = counter_format % row['no'] #first 'border' and qso counter
            for column in self.field_enable:
                frmt = '%'+str(widths[column])+'s|'
                addon = frmt % row[column]
                output_row = output_row+addon
            output_text = output_text+'\n'+output_row
            row_len = len(output_row)
        last_row = '\n+'
        for i in range(1, row_len-1):
            last_row = last_row+'-'
        last_row = last_row+'+'
        output_text = output_text + last_row
        self.entry_id_list.append(-1) #the last row will have a magic number
        self.log_list.text = output_text[1:] #get rid of the first newline

    def saveButtonCallback(self, *dummy_args):
        #check if the callsign is not empty
        if len(self.field_widget[self.field_enable[0]].text) < 2:
            self.field_widget[self.field_enable[0]].background_color = self.color_red
            self.field_widget[self.field_enable[0]].focus = True
            Clock.schedule_once(self.setWhiteFieldBackground, 0.8)
            return

        #read data from text fields
        row = []
        for i in self.field_enable:
            row.append(self.field_widget[i].text.strip())

        if self.edit_id > 0:
            self.backend.editEntry(self.edit_id, row)
        else:
            self.backend.addEntry(row)

        #restore default values
        if self.edit_id > 0: #this was edited, restore ALL fields
            for i in self.field_enable:
                self.field_widget[i].text = self.backend.getFieldDefault(i)
        else: #this was a new entry, selected fields
            for i in self.field_enable:
                if i not in self.field_skip:
                    self.field_widget[i].text = self.backend.getFieldDefault(i)

        #move back to the first field
        #first_index = self.findNextAvailableField(-1); #start looking from the beginning
        #if first_index >= 0:
        #    self.field_widget[self.field_enable[first_index]].focus=True

        self.updateLog() #update log view
        self.edit_id = False
        self.field_widget[self.field_enable[0]].focus = True

    def editButtonCallback(self, *args):
        col, row = self.log_list.cursor
        if row < len(self.entry_id_list):
            self.edit_id = self.entry_id_list[row]
            if self.edit_id == -1 or self.edit_id == 0: #if the first or the last line is 'selected' (or not selected at all) - fetch the first QSO
                self.edit_id = self.entry_id_list[1]

            if self.edit_id > 0:
                data = self.backend.getLogEntries(limit=1, entry_id=self.edit_id)
                entry = data[0]
                for i in self.field_enable:
                    self.field_widget[i].text = entry[i]
                self.field_widget[self.field_enable[0]].focus = True #set first field focus

    def deleteButtonCallback(self, *dummy):
        if self.unlock_delete_log_checkbox.active:
            r = self.backend.deleteLog(self.log_delete_spinner.text)
            if r:
                self.helpPopup('Log has been deleted', title='Delete log')
                self.updateLogList()
                self.selectLog()
            else:
                self.helpPopup('There must be at least\none log in the database.\n\nLog has NOT been deleted', title='Delete log')

if __name__ == '__main__':
    base_dir = ''
    if os.path.exists('/storage/sdcard0'): #we're on an Android system
        print 'DB path : android'
        base_dir = '/storage/sdcard0/MG-log'
        if not os.path.exists('/storage/sdcard0/MG-log'):
            print 'creating directory /MG-log'
            os.makedirs('/storage/sdcard0/MG-log/')
    else: #that must be a PC
        home = os.path.expanduser('~')
        print 'DB path home=', home
        if not os.path.exists(home+'/MG-log'):
            os.makedirs(home+'/MG-log/')
            print 'creating '+home+'/MG-log/'
        base_dir = home+'/MG-log'
        print base_dir
    try:
        LogApp().run()
    except Exception:
        print 'Writing crash log to %s' % base_dir
        t = traceback.format_exc()
        crash_log_file = open(base_dir+'/crash-'+str(time.time())+'.txt', 'w')
        crash_log_file.write(t)
        crash_log_file.close()
