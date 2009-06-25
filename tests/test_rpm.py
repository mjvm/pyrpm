# -*- coding: iso-8859-15 -*-
# -*- Mode: Python; py-ident-offset: 4 -*-
# vim:ts=4:sw=4:et
'''
High level pyrpm tests

$Id$
'''
__revision__ = '$Rev$'[6:-2]

import unittest
from pyrpm.rpm import RPM
from pyrpm import rpmdefs
from cStringIO import StringIO

class RPMTest(unittest.TestCase):

    def setUp(self):

        self.rpm = RPM(file('tests/Eterm-0.9.3-5mdv2007.0.src.rpm'))
        self.rpm = StringIO('')

    def test_entries(self):

        description = '''Eterm is a color vt102 terminal emulator intended as a replacement for Xterm.\nIt is designed with a Freedom of Choice philosophy, leaving as much power,\nflexibility, and freedom as possible in the hands of the user.\n\nIt is designed to look good and work well, but takes a feature-rich approach\nrather than one of minimalism while still maintaining speed and efficiency.\n\nIt works on any windowmanager/desktop environment, although it is designed\nto work and integrate best with Enlightenment.'''

        self.assertEqual(self.rpm[rpmdefs.RPMTAG_NAME], 'Eterm')
        self.assertEqual(self.rpm[rpmdefs.RPMTAG_VERSION], '0.9.3')
        self.assertEqual(self.rpm[rpmdefs.RPMTAG_RELEASE], '5mdv2007.0')
        self.assertEqual(self.rpm[rpmdefs.RPMTAG_ARCH], 'i586')
        self.assertEqual(self.rpm[rpmdefs.RPMTAG_COPYRIGHT], 'BSD')
        self.assertEqual(self.rpm[rpmdefs.RPMTAG_DESCRIPTION], description)

    def test_package_type(self):
        self.assertEqual(self.rpm.binary, False)
        self.assertEqual(self.rpm.source, True)

    def test_name(self):
        self.assertEqual(self.rpm.name(), 'Eterm')

    def test_package(self):
        self.assertEqual(self.rpm.package(), 'Eterm-0.9.3')

    def test_filename(self):
        self.assertEqual(self.rpm.filename(), 'Eterm-0.9.3-5mdv2007.0.i586.src.rpm')


class RPMStringIOTest(RPMTest):

    def setUp(self):

        self.rpm = RPM(StringIO(file('tests/Eterm-0.9.3-5mdv2007.0.src.rpm').read()))
