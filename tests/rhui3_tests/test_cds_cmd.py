'''CDS management tests for the CLI'''

from os.path import basename
import random

import logging
import nose
import stitches
from stitches.expect import Expect

from rhui3_tests_lib.rhui_cmd import RHUICLI
from rhui3_tests_lib.rhuimanager import RHUIManager
from rhui3_tests_lib.util import Util

logging.basicConfig(level=logging.DEBUG)

CONNECTION = stitches.Connection("rhua.example.com", "root", "/root/.ssh/id_rsa_test")

CDS_HOSTNAMES = Util.get_cds_hostnames()

def setup():
    '''
    announce the beginning of the test run
    '''
    print("*** Running %s: *** " % basename(__file__))

def test_01_init():
    '''
    log in to RHUI
    '''
    RHUIManager.initial_run(CONNECTION)

def test_02_list_cds():
    '''
    check if there are no CDSs
    '''
    cds_list = RHUICLI.list(CONNECTION, "cds")
    nose.tools.eq_(cds_list, [])

def test_03_add_cds():
    '''
    add all known CDSs
    '''
    for cds in CDS_HOSTNAMES:
        status = RHUICLI.add(CONNECTION, "cds", cds, unsafe=True)
        nose.tools.ok_(status, msg="unexpected %s installation status: %s" % (cds, status))

def test_04_list_cds():
    '''
    check if the CDSs have been added
    '''
    cds_list = RHUICLI.list(CONNECTION, "cds")
    nose.tools.eq_(cds_list, CDS_HOSTNAMES)

def test_05_reinstall_cds():
    '''
    add one of the CDSs again by reinstalling it
    '''
    # choose a random CDS hostname from the list
    cds = random.choice(CDS_HOSTNAMES)
    status = RHUICLI.reinstall(CONNECTION, "cds", cds)
    nose.tools.ok_(status, msg="unexpected %s reinstallation status: %s" % (cds, status))

def test_06_list_cds():
    '''
    check if the CDSs are still tracked, and nothing extra has appeared
    '''
    cds_list = RHUICLI.list(CONNECTION, "cds")
    # the reinstalled CDS is now the last one in the list; the list may not be the same, sort it!
    cds_list.sort()
    nose.tools.eq_(cds_list, CDS_HOSTNAMES)

def test_07_readd_cds_noforce():
    '''
    check if rhui refuses to add a CDS again if no extra parameter is used
    '''
    # again choose a random CDS hostname from the list
    cds = random.choice(CDS_HOSTNAMES)
    status = RHUICLI.add(CONNECTION, "cds", cds, unsafe=True)
    nose.tools.ok_(not status, msg="unexpected %s readdition status: %s" % (cds, status))

def test_08_list_cds():
    '''
    check if nothing extra has been added
    '''
    cds_list = RHUICLI.list(CONNECTION, "cds")
    # the readded CDS is now the last one in the list; the list may not be the same, sort it!
    cds_list.sort()
    nose.tools.eq_(cds_list, CDS_HOSTNAMES)

def test_09_readd_cds():
    '''
    add one of the CDSs again by using force
    '''
    # again choose a random CDS hostname from the list
    cds = random.choice(CDS_HOSTNAMES)
    status = RHUICLI.add(CONNECTION, "cds", cds, force=True, unsafe=True)
    nose.tools.ok_(status, msg="unexpected %s readdition status: %s" % (cds, status))

def test_10_list_cds():
    '''
    check if the CDSs are still tracked, and nothing extra has appeared
    '''
    cds_list = RHUICLI.list(CONNECTION, "cds")
    # the readded CDS is now the last one in the list; the list may not be the same, sort it!
    cds_list.sort()
    nose.tools.eq_(cds_list, CDS_HOSTNAMES)

def test_11_delete_cds_noforce():
    '''
    check if rhui refuses to delete the node when it's the only/last one and force isn't used
    '''
    # delete all but the first node (if there are more nodes to begin with)
    if len(CDS_HOSTNAMES) > 1:
        RHUICLI.delete(CONNECTION, "cds", CDS_HOSTNAMES[1:])
    status = RHUICLI.delete(CONNECTION, "cds", [CDS_HOSTNAMES[0]])
    nose.tools.ok_(not status, msg="unexpected deletion status: %s" % status)

def test_12_list_cds():
    '''
    check if the last CDS really hasn't been deleted
    '''
    cds_list = RHUICLI.list(CONNECTION, "cds")
    nose.tools.eq_(cds_list, [CDS_HOSTNAMES[0]])


def test_13_delete_cds_force():
    '''
    delete the last CDS forcibly
    '''
    status = RHUICLI.delete(CONNECTION, "cds", [CDS_HOSTNAMES[0]], force=True)
    nose.tools.ok_(status, msg="unexpected deletion status: %s" % status)

def test_14_list_cds():
    '''
    check if the last CDS has been deleted
    '''
    cds_list = RHUICLI.list(CONNECTION, "cds")
    nose.tools.eq_(cds_list, [])

def test_15_add_bad_cds():
    '''
    try adding an incorrect CDS hostname, expect trouble and nothing added
    '''
    status = RHUICLI.add(CONNECTION, "cds", "foo" + CDS_HOSTNAMES[0])
    nose.tools.ok_(not status, msg="unexpected addition status: %s" % status)
    cds_list = RHUICLI.list(CONNECTION, "cds")
    nose.tools.eq_(cds_list, [])

# currently broken, see RHBZ#1409697
# def test_16_delete_bad_cds():
#     '''
#     try deleting a non-existing CDS hostname, expect trouble
#     '''
#     status = RHUICLI.delete(CONNECTION, "cds", ["bar" + CDS_HOSTNAMES[0]], force=True)
#     nose.tools.ok_(not status, msg="unexpected deletion status: %s" % status)

def test_17_add_cds_changed_case():
    '''
    add and delete a CDS with uppercase characters, should work
    '''
    # for RHBZ#1572623
    # choose a random CDS hostname from the list
    cds_up = random.choice(CDS_HOSTNAMES).replace("cds", "CDS")
    status = RHUICLI.add(CONNECTION, "cds", cds_up, unsafe=True)
    nose.tools.ok_(status, msg="unexpected %s addition status: %s" % (cds_up, status))
    cds_list = RHUICLI.list(CONNECTION, "cds")
    nose.tools.eq_(cds_list, [cds_up])
    status = RHUICLI.delete(CONNECTION, "cds", [cds_up], force=True)
    nose.tools.ok_(status, msg="unexpected %s deletion status: %s" % (cds_up, status))

def test_18_add_safe_unknown_key():
    '''
    try adding a CDS whose SSH key is unknown, without using --unsafe; should fail
    '''
    # for RHBZ#1409460
    # choose a random CDS hostname from the list
    cds = random.choice(CDS_HOSTNAMES)
    # make sure its key is unknown
    Expect.expect_retval(CONNECTION,
                         "if [ -f ~/.ssh/known_hosts ]; then ssh-keygen -R %s; fi" % cds)
    # try adding the CDS
    status = RHUICLI.add(CONNECTION, "cds", cds)
    nose.tools.ok_(not status, msg="unexpected %s addition status: %s" % (cds, status))
    cds_list = RHUICLI.list(CONNECTION, "cds")
    nose.tools.eq_(cds_list, [])

def test_19_add_safe_known_key():
    '''
    add and delete a CDS whose SSH key is known, without using --unsafe; should work
    '''
    # for RHBZ#1409460
    # choose a random CDS hostname from the list
    cds = random.choice(CDS_HOSTNAMES)
    # accept the host's SSH key
    Expect.expect_retval(CONNECTION, "ssh-keyscan -t rsa %s >> /root/.ssh/known_hosts" % cds)
    # actually add and delete the host
    status = RHUICLI.add(CONNECTION, "cds", cds)
    nose.tools.ok_(status, msg="unexpected %s addition status: %s" % (cds, status))
    cds_list = RHUICLI.list(CONNECTION, "cds")
    nose.tools.eq_(cds_list, [cds])
    status = RHUICLI.delete(CONNECTION, "cds", [cds], force=True)
    nose.tools.ok_(status, msg="unexpected %s deletion status: %s" % (cds, status))
    # clean up the SSH key
    Expect.expect_retval(CONNECTION, "ssh-keygen -R %s" % cds)

def teardown():
    '''
    announce the end of the test run
    '''
    print("*** Finished running %s. *** " % basename(__file__))