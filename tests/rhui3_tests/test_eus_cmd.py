'''EUS Tests (for the CLI)'''

import logging
from os.path import basename
import re

import nose
import stitches
from stitches.expect import Expect
import yaml

from rhui3_tests_lib.rhui_cmd import RHUICLI
from rhui3_tests_lib.rhuimanager import RHUIManager
from rhui3_tests_lib.rhuimanager_cmdline import RHUIManagerCLI
from rhui3_tests_lib.rhuimanager_instance import RHUIManagerInstance
from rhui3_tests_lib.util import Util

logging.basicConfig(level=logging.DEBUG)

RHUA = stitches.Connection("rhua.example.com", "root", "/root/.ssh/id_rsa_test")
CLI = stitches.Connection("cli01.example.com", "root", "/root/.ssh/id_rsa_test")

CONF_RPM_NAME = "eus-rhui"

class TestEUSCLI(object):
    '''
    class to test EUS repos via the CLI
    '''

    def __init__(self):
        self.cli_version = Util.get_rhel_version(CLI)["major"]
        with open("/usr/share/rhui3_tests_lib/config/tested_repos.yaml") as configfile:
            doc = yaml.load(configfile)
            try:
                self.repo_id = doc["EUS_repos"][self.cli_version]["id"]
                self.repo_label = doc["EUS_repos"][self.cli_version]["label"]
                self.repo_name = doc["EUS_repos"][self.cli_version]["name"]
                self.repo_path = doc["EUS_repos"][self.cli_version]["path"]
                self.test_package = doc["EUS_repos"][self.cli_version]["test_package"]
            except KeyError as version:
                raise nose.SkipTest("No test repo defined for RHEL %s" % version)

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
        RHUIManager.initial_run(RHUA)

    @staticmethod
    def test_02_add_hap():
        '''
        add a CDS
        '''
        RHUICLI.add(RHUA, "cds", "cds01.example.com", unsafe=True)
        # check that
        cds_list = RHUICLI.list(RHUA, "cds")
        nose.tools.eq_(cds_list, ["cds01.example.com"])

    @staticmethod
    def test_03_add_hap():
        '''
        add an HAProxy Load-Balancer
        '''
        RHUICLI.add(RHUA, "haproxy", "hap01.example.com", unsafe=True)
        # check that
        hap_list = RHUICLI.list(RHUA, "haproxy")
        nose.tools.eq_(hap_list, ["hap01.example.com"])

    @staticmethod
    def test_04_upload_certificate():
        '''
        upload an entitlement certificate
        '''
        RHUIManagerCLI.cert_upload(RHUA,
                                   "/tmp/extra_rhui_files/rhcert.pem",
                                   "Extended Update Support")

    def test_05_add_repo(self):
        '''
        add the tested repo
        '''
        RHUIManagerCLI.repo_add_by_repo(RHUA, [self.repo_id])

    def test_06_sync_repo(self):
        '''
        sync the repo
        '''
        RHUIManagerCLI.repo_sync(RHUA, self.repo_id, self.repo_name)

    def test_07_generate_certificate(self):
        '''
        generate an entitlement certificate
        '''
        RHUIManagerCLI.client_cert(RHUA,
                                   [self.repo_label],
                                   CONF_RPM_NAME,
                                   365,
                                   "/tmp")

    @staticmethod
    def test_08_create_cli_config_rpm():
        '''
        create a client configuration RPM
        '''
        RHUIManagerCLI.client_rpm(RHUA,
                                  ["/tmp/%s.key" % CONF_RPM_NAME,
                                   "/tmp/%s.crt" % CONF_RPM_NAME],
                                  ["1.0",
                                   CONF_RPM_NAME],
                                  "/tmp")

    @staticmethod
    def test_09_rm_amazon_rhui_cf_rpm():
        '''
        remove Amazon RHUI configuration from the client
        '''
        Util.remove_amazon_rhui_conf_rpm(CLI)

    @staticmethod
    def test_10_install_conf_rpm():
        '''
        install the client configuration RPM
        '''
        Util.install_pkg_from_rhua(RHUA,
                                   CLI,
                                   "/tmp/%s-1.0/build/RPMS/noarch/%s-1.0-1.noarch.rpm" % \
                                   (CONF_RPM_NAME, CONF_RPM_NAME))

    def test_11_set_eus_release(self):
        '''
        set the tested EUS release in Yum configuration
        '''
        # the repo id is ...rpms-X.Y-ARCH,
        # so the release between the next-to-last and the last dash
        eus_release = self.repo_id.split("-")[-2]
        Expect.expect_retval(CLI, "rhui-set-release --set %s" % eus_release)

    def test_12_check_package_url(self):
        '''
        check if Yum is now working with the EUS URL
        '''
        # the name of the test package contains plus signs, which must be escaped in REs
        # also, the URL can be .../os/NVR or .../os//NVR, so let's tolerate the extra slash
        test_package_escaped = re.escape(self.test_package)
        Expect.ping_pong(CLI,
                         "yumdownloader --url %s" % test_package_escaped,
                         "https://cds.example.com/pulp/repos/%s//?%s" % \
                         (self.repo_path, test_package_escaped))

    def test_13_install_test_rpm(self):
        '''
        install the test package (from the test repo)
        '''
        Expect.expect_retval(CLI, "yum install -y %s" % self.test_package, timeout=20)
        # check it
        Expect.expect_retval(CLI, "rpm -q %s" % self.test_package)

    def test_99_cleanup(self):
        '''clean up'''
        RHUIManagerCLI.repo_delete(RHUA, self.repo_id)
        RHUIManager.remove_rh_certs(RHUA)
        # HAProxy deletion in the CLI is currently broken (RHBZ#1409695):
        # RHUICLI.delete(RHUA, "haproxy", ["hap01.example.com"], force=True)
        # work around that:
        RHUIManagerInstance.delete(RHUA, "loadbalancers", ["hap01.example.com"])
        RHUICLI.delete(RHUA, "cds", ["cds01.example.com"], force=True)
        Expect.expect_retval(RHUA, "rm -rf /tmp/%s*" % CONF_RPM_NAME)
        Expect.expect_retval(CLI, "rhui-set-release --unset")
        Util.remove_rpm(CLI, [self.test_package, CONF_RPM_NAME])

    @staticmethod
    def teardown_class():
        '''
           announce the end of the test run
        '''
        print("*** Finished running %s. *** " % basename(__file__))