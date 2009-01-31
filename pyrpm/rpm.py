# -*- coding: iso-8859-15 -*-
# -*- Mode: Python; py-ident-offset: 4 -*-
# vim:ts=4:sw=4:et
'''
pyrpm module

$Id$
'''
__revision__ = '$Rev$'[6:-2]

from StringIO import StringIO
import struct
import binascii
from pyrpm import rpmdefs
import re

class Entry(object):
    ''' RPM Header Entry
    '''
    def __init__(self, entry, store):
        self.entry = entry
        self.store = store

        self.switch = { rpmdefs.RPM_DATA_TYPE_CHAR:            self.__readchar,
                        rpmdefs.RPM_DATA_TYPE_INT8:            self.__readint8,
                        rpmdefs.RPM_DATA_TYPE_INT16:           self.__readint16,
                        rpmdefs.RPM_DATA_TYPE_INT32:           self.__readint32,
                        rpmdefs.RPM_DATA_TYPE_INT64:           self.__readin64,
                        rpmdefs.RPM_DATA_TYPE_STRING:          self.__readstring,
                        rpmdefs.RPM_DATA_TYPE_BIN:             self.__readbin,
                        rpmdefs.RPM_DATA_TYPE_I18NSTRING_TYPE: self.__readstring}

        self.store.seek(entry[2])
        self.value = self.switch[entry[1]]()
        self.tag = entry[0]

    def __str__(self):
        return str(self.tag) + '-' + str(self.value)

    def __repr__(self):
        return str(self.tag)+'-'+ str(self.value)

    def __readchar(self, offset=1):
        ''' store is a pointer to the store offset
        where the char should be read
        '''
        data = self.store.read(offset)
        fmt = '!'+str(offset)+'c'
        value = struct.unpack(fmt, data)
        return value

    def __readint8(self, offset=1):
        ''' int8 = 1byte
        '''
        return self.__readchar(offset)

    def __readint16(self, offset=1):
        ''' int16 = 2bytes
        '''
        data = self.store.read(offset*2)
        fmt = '!'+str(offset)+'i'
        value = struct.unpack(fmt, data)
        return value

    def __readint32(self, offset=1):
        ''' int32 = 4bytes
        '''
        data = self.store.read(offset*4)
        fmt = '!'+str(offset)+'i'
        value = struct.unpack(fmt, data)
        return value

    def __readin64(self, offset=1):
        ''' int64 = 8bytes
        '''
        data = self.store.read(offset*4)
        fmt = '!'+str(offset)+'l'
        value = struct.unpack(fmt, data)
        return value

    def __readstring(self):
        string = ''
        while True:
            char = self.__readchar()
            if char[0] == '\x00': # read until \0
                break
            string += char[0]
        return string

    def __readbin(self):
        if self.entry[0] == rpmdefs.RPMSIGTAG_MD5:
            data = self.store.read(rpmdefs.MD5_SIZE)
            value = struct.unpack('!'+rpmdefs.MD5_SIZE+'s', data)
            return value
        elif self.entry[0] == rpmdefs.RPMSIGTAG_PGP:
            data = self.store.read(rpmdefs.PGP_SIZE)
            value = struct.unpack('!'+rpmdefs.PGP_SIZE+'s', data)
            return value

class Header(object):
    ''' RPM Header Structure
    '''
    def __init__(self, header, entries , store):
        '''
        '''
        self.header = header
        self.entries = entries
        self.store = store
        self.pentries = []
        self.rentries = []

        self.__readentries()


    def __readentry(self, entry):
        ''' [4bytes][4bytes][4bytes][4bytes]
               TAG    TYPE   OFFSET  COUNT
        '''
        entryfmt = '!llll'
        entry = struct.unpack(entryfmt, entry)
        if entry[0] < rpmdefs.RPMTAG_MIN_NUMBER or entry[0] > rpmdefs.RPMTAG_MAX_NUMBER:
            return None
        return entry

    def __readentries(self):
        for e in self.entries:
            entry = self.__readentry(e)
            if entry:
                if entry[0] in rpmdefs.RPMTAGS:
                    self.pentries.append(entry)

        for e in self.pentries:
            er = Entry(e, self.store)
            if er:
                self.rentries.append(er)

class RPMError(BaseException):
    pass

class RPM(object):

    def __init__(self, rpm):
        ''' rpm - StringIO.StringIO | file
        '''
        if isinstance(rpm, file):
            self.rpmfile = StringIO(rpm.read())
        elif isinstance(rpm, StringIO):
            self.rpmfile = rpm
        else:
            raise RPMError('file format not suported')
        self.__entries = []
        self.__headers = []

        self.__readheaders()

    def __readheader(self, header):
        ''' reads the header-header section
        [3bytes][1byte][4bytes][4bytes][4bytes]
          MN      VER   UNUSED  IDXNUM  STSIZE
        '''
        headerfmt = '!3sc4sll'
        if not len(header)==16:
            raise RPMError('invalid header size')

        header = struct.unpack(headerfmt, header)
        magic_num = binascii.b2a_hex(header[0])

        if not magic_num == rpmdefs.RPM_HEADER_MAGIC_NUMBER:
            raise RPMError('invalid RPM header')

        return header

    def __readheaders(self):
        rpm = self.rpmfile
        regexp = re.compile('\x8e\xad\xe8')
        matches = regexp.finditer(self.rpmfile.buf)
        counter = 0
        for match in matches:
            if counter == 2:
                break
            counter += 1
            header_start = match.start() #save header position
            rpm.seek(header_start)
            header = rpm.read(16)
            header = self.__readheader(header)
            entries = []
            for e in range(header[3]):
                entry = rpm.read(16)
                entries.append(entry)
            store = StringIO(rpm.read(header[4]))
            self.__headers.append(Header(header, entries, store))

        for header in self.__headers:
            for entry in header.rentries:
                self.__entries.append(entry)

    def __iter__(self):
        for entry in self.__entries:
            yield entry

    def __getitem__(self, item):
        for entry in self:
            if entry.tag == item:
                if not isinstance(entry.value, tuple):
                    return entry.value

    def package(self):
        return self[rpmdefs.RPMTAG_NAME]

    def fullname(self):
        name = self[rpmdefs.RPMTAG_NAME]
        version = self[rpmdefs.RPMTAG_VERSION]
        release = self[rpmdefs.RPMTAG_RELEASE]
        return '-'.join([name, version, release, ])

    def filename(self):
        name = self.fullname()
        arch = self[rpmdefs.RPMTAG_ARCH]
        return '.'.join([name, arch, 'rpm', ])
