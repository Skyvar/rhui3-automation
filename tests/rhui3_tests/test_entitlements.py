'''Entitlement management tests'''

from os.path import basename

import logging
import nose
import stitches

from rhui3_tests_lib.rhuimanager import RHUIManager
from rhui3_tests_lib.rhuimanager_entitlement import RHUIManagerEntitlements, \
                                                    BadCertificate, \
                                                    IncompatibleCertificate
from rhui3_tests_lib.rhuimanager_repo import RHUIManagerRepo

logging.basicConfig(level=logging.DEBUG)

CONNECTION = stitches.Connection("rhua.example.com", "root", "/root/.ssh/id_rsa_test")

class TestEntitlement(object):
    '''
       class for entitlement tests
    '''

    @staticmethod
    def setup_class():
        '''
           announce the beginning of the test run
        '''
        print("*** Running %s: *** " % basename(__file__))

    @staticmethod
    def test_01_initial_run():
        '''
            log in to RHUI
        '''
        RHUIManager.initial_run(CONNECTION)

    @staticmethod
    def test_02_list_rh_entitlements():
        '''
           list Red Hat content certificate entitlements
        '''
        entitlements = RHUIManagerEntitlements.list_rh_entitlements(CONNECTION)
        nose.tools.eq_(isinstance(entitlements, list), True)

    @staticmethod
    def test_03_list_cus_entitlements():
        '''
           list custom content certificate entitlements, expect none
        '''
        entlist = RHUIManagerEntitlements.list_custom_entitlements(CONNECTION)
        nose.tools.assert_equal(len(entlist), 0)

    @staticmethod
    def test_04_upload_rh_certificate():
        '''
           upload a new or updated Red Hat content certificate
        '''
        entlist = RHUIManagerEntitlements.upload_rh_certificate(CONNECTION)
        nose.tools.assert_not_equal(len(entlist), 0)

    @staticmethod
    def test_05_list_rh_entitlements():
        '''
           list Red Hat content certificate entitlements
        '''
        entitlements = RHUIManagerEntitlements.list_rh_entitlements(CONNECTION)
        nose.tools.eq_(isinstance(entitlements, list), True)

    @staticmethod
    def test_06_add_custom_repo():
        '''
           add a custom repo to protect by a client entitlement certificate
        '''
        RHUIManagerRepo.add_custom_repo(CONNECTION, "custom-enttest", "", "", "1", "y")

    @staticmethod
    def test_07_list_cust_entitlements():
        '''
           list custom content certificate entitlements, expect one
        '''
        entlist = RHUIManagerEntitlements.list_custom_entitlements(CONNECTION)
        nose.tools.assert_equal(len(entlist), 1)

    @staticmethod
    def test_08_remove_custom_repo():
        '''
           remove the custom repo
        '''
        RHUIManagerRepo.delete_repo(CONNECTION, ["custom-enttest"])
        nose.tools.assert_equal(RHUIManagerRepo.list(CONNECTION), [])

    @staticmethod
    def test_09_list_cust_entitlements():
        '''
           list custom content certificate entitlements, expect none
        '''
        entlist = RHUIManagerEntitlements.list_custom_entitlements(CONNECTION)
        nose.tools.assert_equal(len(entlist), 0)

    @staticmethod
    def test_10_remove_certificates():
        '''
            clean up uploaded entitlement certificates
        '''
        RHUIManager.remove_rh_certs(CONNECTION)

    @staticmethod
    def test_11_upload_exp_cert():
        '''
           upload an expired certificate, expect a proper refusal
        '''
        nose.tools.assert_raises(BadCertificate,
                                 RHUIManagerEntitlements.upload_rh_certificate,
                                 CONNECTION,
                                 "/tmp/extra_rhui_files/rhcert_expired.pem")

    @staticmethod
    def test_12_upload_incompat_cert():
        '''
           upload an incompatible certificate, expect a proper refusal
        '''
        nose.tools.assert_raises(IncompatibleCertificate,
                                 RHUIManagerEntitlements.upload_rh_certificate,
                                 CONNECTION,
                                 "/tmp/extra_rhui_files/rhcert_incompatible.pem")

    @staticmethod
    def test_13_upload_semi_bad_cert():
        '''
           upload a certificate containing a mix of valid and invalid repos
        '''
        # for RHBZ#1588931 & RHBZ#1584527
        RHUIManagerEntitlements.upload_rh_certificate(CONNECTION,
                                                      "/tmp/extra_rhui_files/" +
                                                      "rhcert_partially_invalid.pem")

    @staticmethod
    def test_14_remove_semi_bad_cert():
        '''
            remove the certificate
        '''
        RHUIManager.remove_rh_certs(CONNECTION)

    @staticmethod
    def teardown_class():
        '''
           announce the end of the test run
        '''
        print("*** Finished running %s. *** " % basename(__file__))
