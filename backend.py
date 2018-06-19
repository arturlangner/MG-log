import os
import sqlite3
import time
import datetime
import json
import traceback

class LogBackend():
    version_string = 'MG-log 0.7'

    field_name = {}
    field_name['callsign'] = 'Callsign'
    field_name['time'] = 'UTC'
    field_name['band'] = 'Band'
    field_name['mode'] = 'Mode'
    field_name['rst_r'] = 'RST R'
    field_name['rst_s'] = 'RST S'
    field_name['qth'] = 'QTH'
    field_name['notes'] = 'Notes'
    field_name['loc'] = 'Locator' #added in 0.7

    field_short_name = {}
    field_short_name['no'] = 'N'
    field_short_name['callsign'] = 'Call'
    field_short_name['time'] = 'UTC'
    field_short_name['band'] = 'Band'
    field_short_name['mode'] = 'Mode'
    field_short_name['rst_r'] = ' R'
    field_short_name['rst_s'] = ' S'
    field_short_name['qth'] = 'QTH'
    field_short_name['notes'] = 'Notes'
    field_short_name['loc'] = 'Loc' #added in 0.7

    field_default = {}
    field_default['callsign'] = ' '
    field_default['time'] = 'NOW'
    field_default['band'] = '20m'
    field_default['mode'] = 'SSB'
    field_default['rst_r'] = '59'
    field_default['rst_s'] = '59'
    field_default['qth'] = ' '
    field_default['notes'] = ' '
    field_default['loc'] = ' ' #added in 0.7

    field_width = {} #field widths in characters
    field_width['no'] = 1
    field_width['callsign'] = 1
    field_width['time'] = 1
    field_width['band'] = 1
    field_width['mode'] = 1
    field_width['rst_r'] = 1
    field_width['rst_s'] = 1
    field_width['qth'] = 1
    field_width['notes'] = 1
    field_width['loc'] = 1 #added in 0.7

    #field_input_width_hint = {}
    #field_input_width_hint['callsign'] = 0.2
    #field_input_width_hint['time'] = None
    #field_input_width_hint['band'] = None
    #field_input_width_hint['mode'] = None
    #field_input_width_hint['rst_r'] = None
    #field_input_width_hint['rst_s'] = None
    #field_input_width_hint['qth'] = 0.2
    #field_input_width_hint['notes'] = 0.2

    field_input_width = {}
    field_input_width['callsign'] = 6
    field_input_width['time'] = 5
    field_input_width['band'] = 4
    field_input_width['mode'] = 4
    field_input_width['rst_r'] = 3.5
    field_input_width['rst_s'] = 3.5
    field_input_width['qth'] = 10
    field_input_width['notes'] = 10
    field_input_width['loc'] = 5 #added in 0.7

    #added 'loc' below in 0.7
    field_enable = ['callsign', 'time', 'band', 'mode', 'rst_r', 'rst_s', 'qth', 'loc', 'notes'] #order has to match SQL query in addEntry(row)

    field_skip = ['rst_s', 'time', 'band', 'mode', 'loc'] #added 'loc' in 0.7

    active_log = 1

    def __init__(self):
        if os.path.exists('/storage/sdcard0'): #we're on an Android system
            print 'DB path : android'
            self.base_dir = '/storage/sdcard0/MG-log'
            if not os.path.exists('/storage/sdcard0/MG-log'):
                print 'creating directory /MG-log'
                os.makedirs('/storage/sdcard0/MG-log/')
        else: #that must be a PC
            home = os.path.expanduser('~')
            print 'DB path home = ', home
            if not os.path.exists(home+'/MG-log'):
                os.makedirs(home+'/MG-log/')
                print 'creating '+home+'/MG-log/'
            self.base_dir = home+'/MG-log'

        self.db_handle = sqlite3.connect(self.base_dir+'/mg-log.sqlite3')


        cursor = self.db_handle.cursor()
        query = 'CREATE TABLE IF NOT EXISTS log_list (id INTEGER PRIMARY KEY NOT NULL, name TEXT NOT NULL);'
        cursor.execute(query)
        #'loc' field added between versions 0.6 -> 1.0
        query = "CREATE TABLE IF NOT EXISTS log_entry (id INTEGER PRIMARY KEY NOT NULL, log INTEGER NOT NULL, callsign TEXT DEFAULT '', time INTEGER NOT NULL, band TEXT DEFAULT '', mode TEXT DEFAULT '', rst_r TEXT DEFAULT '', rst_s TEXT DEFAULT '', qth TEXT DEFAULT '', notes TEXT DEFAULT '', loc TEXT DEFAULT '', FOREIGN KEY (log) REFERENCES log_list(id) );"
        cursor.execute(query)
        query = 'CREATE TABLE IF NOT EXISTS settings (key NOT NULL UNIQUE, value TEXT NOT NULL);'
        cursor.execute(query)

        #--------- MIGRATION FROM DATABASE SCHEMA 0.6 TO 0.7
        #-------- add 'loc' field to an existing database ----
        query = 'PRAGMA table_info(log_entry)'
        cursor = self.db_handle.cursor()
        cursor.execute(query, [])
        rows = cursor.fetchall()
        loc_field_exists = False
        for r in rows:
            if r[1] == 'loc':
                loc_field_exists = True
        if not loc_field_exists:
            print "Adding loc field to existing database",
            query = "ALTER TABLE log_entry ADD COLUMN loc TEXT DEFAULT ''"
            cursor = self.db_handle.cursor()
            cursor.execute(query, [])
            print ' added'
            default = json.dumps(self.field_enable) #the new field has to be added to the field_enable setting
            self.setParameter('field_enable', default)
            print 'Enabling new field'
            default = json.dumps(self.field_default)
            self.setParameter('field_default', default)
            print 'Setting defult value for new field'
        #--------- end of MIGRATION FROM DATABASE SCHEMA 0.6 TO 0.7

        query = 'SELECT COUNT(*) FROM log_list'
        cursor = self.db_handle.cursor()
        cursor.execute(query, [])
        rows = cursor.fetchall()
        c = rows[0][0] #number of logs in the database
        if c < 1:
            query = "INSERT OR IGNORE INTO log_list(id,name) VALUES(1, 'default');"
            cursor.execute(query)

        query = "INSERT OR IGNORE INTO settings(key,value) VALUES('info_text', 'My call: LB9MG\nLOC  JO28UX');"
        cursor.execute(query)

        query = "INSERT OR IGNORE INTO settings(key,value) VALUES('font_size', '15');"
        cursor.execute(query)

        self.db_handle.commit()
        self.loadSettings()

        #self.getLogEntries(1)

    def loadSettings(self):
        #get field_enable:
        try:
            field_enable = json.loads(self.getParameter('field_enable'))
            self.field_enable = field_enable
            print 'Loaded field_enable from the db'
        except Exception:
            print traceback.format_exc()
            default = json.dumps(self.field_enable)
            self.setParameter('field_enable', default)
            print 'Using field_enable defaults'
        #get field_default:
        try:
            field_default = json.loads(self.getParameter('field_default'))
            self.field_default = field_default
            print 'Loaded field_default from the db'
        except Exception:
            print traceback.format_exc()
            default = json.dumps(self.field_default)
            self.setParameter('field_default', default)
            print 'Using field_default defaults'
        #get field_skip:
        try:
            field_skip = json.loads(self.getParameter('field_skip'))
            self.field_skip = field_skip
            print 'Loaded field_skip from the db'
        except Exception:
            print traceback.format_exc()
            default = json.dumps(self.field_skip)
            self.setParameter('field_skip', default)
            print 'Using field_skip defaults'

    def setParameter(self, key, value):
        query = 'INSERT OR REPLACE INTO settings (key,value) VALUES (?, ?);'
        cursor = self.db_handle.cursor()
        cursor.execute(query, [key, value])
        self.db_handle.commit()

    def getParameter(self, key):
        query = 'SELECT value FROM settings WHERE key = ?'
        cursor = self.db_handle.cursor()
        cursor.execute(query, [key])
        rows = cursor.fetchall()
        value = rows[0][0] #there will be only one element returned
        return value

    def getLogEntries(self, limit=25, entry_id=False):
        #get total number of entries per this log
        query = 'SELECT COUNT(*) FROM log_entry WHERE log = ?'
        cursor = self.db_handle.cursor()
        cursor.execute(query, [self.active_log])
        rows = cursor.fetchall()
        count = rows[0][0] #there will be only one element returned
        #get the entries
        query = 'SELECT id, '
        counter = 0
        for i in self.field_enable:
            if counter > 0:
                query = query + ','
            counter += 1
            query = query + ' ' + i
        query = query+' FROM log_entry WHERE log = ? '
        arguments = [self.active_log]
        if entry_id:
            query = query+' AND id = ?'
            arguments.append(entry_id)

        arguments.append(limit)
        query = query+' ORDER BY id DESC LIMIT ?'
        cursor = self.db_handle.cursor()
        cursor.execute(query, arguments)
        rows = cursor.fetchall()
        output = []

        if not entry_id: #return the header only if the function was invoked for the log list
            header_row = {}
            header_row['id'] = 0
            header_row['no'] = self.field_short_name['no']
            self.field_width['id'] = 1
            self.field_width['no'] = len(self.field_short_name['no'])
            for i in self.field_enable:
                header_row[i] = self.field_short_name[i]
                self.field_width[i] = len(self.field_short_name[i])
            output.append(header_row)

        if len(str(count)) > self.field_width['no']:
            self.field_width['no'] = len(str(count))

        for row in rows:
            output_row = {}
            output_row['id'] = row[0] #database id
            output_row['no'] = str(count)  #sequence number in the log
            c = 1 #column counter
            for i in self.field_enable:
                output_row[i] = row[c]
                if len(str(row[c])) > self.field_width[i]:
                    self.field_width[i] = len(str(row[c]))
                c += 1

            try:
                output_row['time'] = datetime.datetime.fromtimestamp(int(output_row['time'])).strftime('%H:%M')
                correct_date_width = True
            except Exception:
                correct_date_width = False

            if correct_date_width:
                self.field_width['time'] = 5
            output.append(output_row)
            count -= 1
        return output

    def selectLog(self, name):
        log_id, dummy = name[1:].split(')', 1)
        self.active_log = int(log_id)

    def exportLog(self, name):
        filename = self.base_dir+'/mglog-export-'+time.strftime('%Y%m%d-%H%M%S')+'.adi'
        f = open(filename, 'w')
        log_id, dummy = name[1:].split(')', 1)
        log_id = int(log_id)
#FIXME: add 'loc' field
        query = 'SELECT callsign, time, band, mode, rst_r, rst_s, qth, loc, notes FROM log_entry WHERE log = ? ORDER BY id DESC;'
        cursor = self.db_handle.cursor()
        cursor.execute(query, [log_id])
        rows = cursor.fetchall()

        f.write('<adif_ver:5>3.0.4\n')
        f.write(self.adifize('programid', self.version_string)+'\n')
        f.write('<eoh>\n')

        for row in rows:
            f.write(self.adifize('CALL', row[0])+'\n')
            #TODO: time
            complex_date = datetime.datetime.fromtimestamp(int(row[1]))
            d = complex_date.strftime('%Y%m%d')
            f.write(self.adifize('QSO_DATE', d) + '\n')
            t = complex_date.strftime('%H%M')
            f.write(self.adifize('TIME_ON', t)+'\n')
            f.write(self.adifize('BAND', row[2])+'\n')
            f.write(self.adifize('MODE', row[3])+'\n')
            f.write(self.adifize('RST_RCVD', row[4])+'\n')
            f.write(self.adifize('RST_SENT', row[5])+'\n')
            f.write(self.adifize('QTH', row[6])+'\n')
            f.write(self.adifize('GRIDSQUARE', row[7])+'\n')
            f.write(self.adifize('COMMENT', row[8])+'\n')
            f.write('<EOR>\n')

        f.close()
        return filename

    def adifize(self, name, value):
        return '<'+name+':'+str(len(value))+'>'+value

    def addEntry(self, arguments):
        try:
            cursor = self.db_handle.cursor()
            if arguments[1].upper() == 'NOW': #FIXME: ugly hardcoded index
                arguments[1] = int(datetime.datetime.utcnow().strftime('%s'))
            else:
                requested_time = arguments[1]
                calendar_day = datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d')
                calendar_day = calendar_day+' '+requested_time
                new_timestamp = time.mktime(datetime.datetime.strptime(calendar_day, '%Y-%m-%d %H:%M').timetuple())
                arguments[1] = new_timestamp
            query = 'INSERT INTO log_entry (log, callsign, time, band, mode, rst_r, rst_s, qth, loc, notes) VALUES ('+str(self.active_log)+', ?, ?, ?, ?, ?, ?, ?, ?, ?);' #SQL injection ;)
            cursor.execute(query, arguments)
            self.db_handle.commit()
        except Exception:
            self.popupCallback('Wrong time format!\n\nQSO not saved', title='Problem')

    def editEntry(self, entry_id, arguments):
        try:
            cursor = self.db_handle.cursor()
            #handle date
            if arguments[1].upper() == 'NOW': #FIXME: ugly hardcoded index
                arguments[1] = int(datetime.datetime.utcnow().strftime('%s'))
            else:
                requested_time = arguments[1]
                query = 'SELECT time FROM log_entry WHERE id = ?'
                cursor = self.db_handle.cursor()
                cursor.execute(query, [entry_id])
                rows = cursor.fetchall()
                original_time = rows[0][0]
                calendar_day = datetime.datetime.fromtimestamp(int(original_time)).strftime('%Y-%m-%d')
                calendar_day = calendar_day+' '+requested_time
                new_timestamp = time.mktime(datetime.datetime.strptime(calendar_day, '%Y-%m-%d %H:%M').timetuple())
                arguments[1] = new_timestamp
            cursor = self.db_handle.cursor()
            #added 'loc' in 0.7
            query = 'UPDATE log_entry SET callsign = ?, time = ?, band = ?, mode = ?, rst_r = ?, rst_s = ?, qth = ?, loc = ?, notes = ? WHERE id = ?;'
            arguments.append(entry_id)
            cursor.execute(query, arguments)
            self.db_handle.commit()
        except Exception:
            print traceback.format_exc()
            self.popupCallback('Wrong time format!\n\nQSO not modified', title='Problem')

    def getLogList(self):
        query = 'SELECT id,name FROM log_list ORDER BY id'
        cursor = self.db_handle.cursor()
        cursor.execute(query)
        rows = cursor.fetchall()
        logs = []
        for row in rows:
            log_label = '('+str(row[0])+') '+row[1]
            logs.append(log_label)
        return logs

    def newLog(self, name):
        query = 'INSERT INTO log_list (name) VALUES (?)'
        cursor = self.db_handle.cursor()
        cursor.execute(query, [name])
        self.db_handle.commit()

    def deleteLog(self, name):
        log_id, dummy = name[1:].split(')', 1)
        log_id = int(log_id)

        query = 'SELECT COUNT(*) FROM log_list'
        cursor = self.db_handle.cursor()
        cursor.execute(query, [])
        rows = cursor.fetchall()
        c = rows[0][0] #number of logs in the database
        if c < 2: #there must be at least one log in the database (otherwise the app will crash or something...)
            return False
        query = 'DELETE FROM log_entry WHERE log = ?'
        cursor = self.db_handle.cursor()
        cursor.execute(query, [log_id])
        query = 'DELETE FROM log_list WHERE id = ?'
        cursor = self.db_handle.cursor()
        cursor.execute(query, [log_id])
        self.db_handle.commit()
        return True

    def getFieldNames(self):
        return self.field_name.keys()

    def getFieldLabel(self, name):
        return self.field_name[name]

    def getFieldWidthHint(self, name):
        return self.field_input_width_hint[name]

    def getFieldInputWidth(self, name):
        return self.field_input_width[name]

    def getFieldDefault(self, name):
        print "key = ", name
        print self.field_default
        return self.field_default[name]

    def getEnabledFields(self):
        return self.field_enable

    def getFieldWidths(self):
        return self.field_width

    def getSkipFields(self):
        return self.field_skip
