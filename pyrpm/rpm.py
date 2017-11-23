# -*- coding: utf-8 -*-
# -*- Mode: Python; py-ident-offset: 4 -*-
# vim:ts=4:sw=4:et
'''
PyRPM
=====

PyRPM is a pure python, simple to use, module to read information from a RPM file.

'''

import struct
from io import BytesIO

from pyrpm import rpmdefs


def find_magic_number(data, magic_number):
    ''' attempts to find a magic number in a stream of bytes
    returns the start position where the magic number was found
    or None if not found
    '''
    base = data.tell()
    while True:
        chunk = data.read(len(magic_number))
        if not chunk or len(chunk) != len(magic_number):
            return None
        if chunk == magic_number:
            return base
        base += 1
        data.seek(base)


class Entry(object):
    ''' RPM Header Entry
    '''
    def __init__(self, entry, store):
        self.entry = entry
        self.store = store

        self.switch = {rpmdefs.RPM_DATA_TYPE_CHAR:            self.__readchar,
                       rpmdefs.RPM_DATA_TYPE_INT8:            self.__readint8,
                       rpmdefs.RPM_DATA_TYPE_INT16:           self.__readint16,
                       rpmdefs.RPM_DATA_TYPE_INT32:           self.__readint32,
                       rpmdefs.RPM_DATA_TYPE_INT64:           self.__readint64,
                       rpmdefs.RPM_DATA_TYPE_STRING:          self.__readstring,
                       rpmdefs.RPM_DATA_TYPE_BIN:             self.__readbin,
                       rpmdefs.RPM_DATA_TYPE_I18NSTRING_TYPE: self.__readstring}

        self.store.seek(entry[2])
        self.value = self.switch[entry[1]]()
        self.tag = entry[0]

    def __str__(self):
        return "(%s, %s)" % (self.tag, self.value, )

    def __repr__(self):
        return "<Entry %r %r>" % (self.tag, self.value, )

    def __readchar(self, offset=1):
        ''' store is a pointer to the store offset
        where the char should be read
        '''
        data = self.store.read(offset)
        if len(data) != offset:
            return ""
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

    def __readint64(self, offset=1):
        ''' int64 = 8bytes
        '''
        data = self.store.read(offset*4)
        fmt = '!'+str(offset)+'l'
        value = struct.unpack(fmt, data)
        return value

    def __readstring(self):
        ''' read a string entry
        '''
        string = b''
        while True:
            char = self.__readchar()
            if len(char) == 0 or char[0] == b'\x00':  # read until '\0'
                break
            string += char[0]
        return string.decode('utf-8')

    def __readbin(self):
        ''' read a binary entry
        '''
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
    def __init__(self, header, entries, store):
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
        if entry[0] < rpmdefs.RPMTAG_MIN_NUMBER or\
                entry[0] > rpmdefs.RPMTAG_MAX_NUMBER:
            return None
        return entry

    def __readentries(self):
        ''' read a rpm entry
        '''
        for entry in self.entries:
            entry = self.__readentry(entry)
            if entry:
                if entry[0] in rpmdefs.RPMTAGS:
                    self.pentries.append(entry)

        for pentry in self.pentries:
            entry = Entry(pentry, self.store)
            if entry:
                self.rentries.append(entry)


class RPMError(BaseException):
    pass


class RPM(object):

    def __init__(self, rpm):
        ''' rpm - StringIO.StringIO | file
        '''
        if hasattr(rpm, 'read'):  # if it walk like a duck..
            self.rpmfile = rpm
        else:
            raise ValueError('invalid initialization: '
                             'StringIO or file expected received %s'
                             % (type(rpm), ))
        self.binary = None
        self.source = None
        self.__entries = dict()
        self.__headers = []

        self.__readlead()
        offset = self.__read_sigheader()
        self.__readheaders(offset)

    def __readlead(self):
        ''' reads the rpm lead section

            struct rpmlead {
               unsigned char magic[4];
               unsigned char major, minor;
               short type;
               short archnum;
               char name[66];
               short osnum;
               short signature_type;
               char reserved[16];
               } ;
        '''
        lead_fmt = '!4sBBhh66shh16s'
        data = self.rpmfile.read(96)
        value = struct.unpack(lead_fmt, data)

        magic_num = value[0]
        ptype = value[3]

        if magic_num != rpmdefs.RPM_LEAD_MAGIC_NUMBER:
            raise RPMError('wrong magic number this is not a RPM file')

        if ptype == 1:
            self.binary = False
            self.source = True
        elif ptype == 0:
            self.binary = True
            self.source = False
        else:
            raise RPMError('wrong package type this is not a RPM file')

    def __read_sigheader(self):
        ''' read signature header

            ATN: this will not return any usefull information
            besides the file offset
        '''
        start = find_magic_number(self.rpmfile, rpmdefs.RPM_HEADER_MAGIC_NUMBER)
        if not start:
            raise RPMError('invalid RPM file, signature header not found')
        # return the offsite after the magic number
        return start + len(rpmdefs.RPM_HEADER_MAGIC_NUMBER)

    def __readheader(self, header):
        ''' reads the header-header section
        [3bytes][1byte][4bytes][4bytes][4bytes]
          MN      VER   UNUSED  IDXNUM  STSIZE
        '''
        headerfmt = '!3sc4sll'
        if not len(header) == 16:
            raise RPMError('invalid header size')

        header = struct.unpack(headerfmt, header)
        magic_num = header[0]
        if magic_num != rpmdefs.RPM_HEADER_MAGIC_NUMBER:
            raise RPMError('invalid RPM header')
        return header

    def __readheaders(self, offset):
        ''' read information headers
        '''
        # lets find the start of the header
        self.rpmfile.seek(offset)
        start = find_magic_number(self.rpmfile, rpmdefs.RPM_HEADER_MAGIC_NUMBER)
        # go back to the begining of the header
        self.rpmfile.seek(start)
        header = self.rpmfile.read(16)
        header = self.__readheader(header)
        entries = []
        for entry in range(header[3]):
            _entry = self.rpmfile.read(16)
            entries.append(_entry)
        store = BytesIO(self.rpmfile.read(header[4]))
        self.__headers.append(Header(header, entries, store))

        for header in self.__headers:
            for entry in header.rentries:
                self.__entries[entry.tag] = entry

    def __iter__(self):
        for entry in self.__entries:
            yield entry

    def __getitem__(self, item):
        entry = self.__entries.get(item, None)
        return entry.value if entry else None

    def name(self):
        return self[rpmdefs.RPMTAG_NAME]

    def description(self):
        return self[rpmdefs.RPMTAG_DESCRIPTION]

    def package(self):
        name = self[rpmdefs.RPMTAG_NAME]
        version = self[rpmdefs.RPMTAG_VERSION]
        return '-'.join([name, version, ])

    def filename(self):
        package = self.package()
        release = self[rpmdefs.RPMTAG_RELEASE]
        name = '-'.join([package, release, ])
        arch = self[rpmdefs.RPMTAG_ARCH]
        if self.binary:
            return '.'.join([name, arch, 'rpm', ])
        else:
            return '.'.join([name, arch, 'src.rpm', ])
