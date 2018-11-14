#! /usr/bin/python -tt
''' Repository management tests '''

from os.path import basename

import logging
import nose
import stitches
from stitches.expect import Expect
import yaml

from rhui3_tests_lib.rhuimanager import RHUIManager
from rhui3_tests_lib.rhuimanager_entitlement import RHUIManagerEntitlements
from rhui3_tests_lib.rhuimanager_repo import AlreadyExistsError, RHUIManagerRepo
from rhui3_tests_lib.util import Util

logging.basicConfig(level=logging.DEBUG)

CONNECTION = stitches.Connection("rhua.example.com", "root", "/root/.ssh/id_rsa_test")
# side channel for hacking
CONNECTION_2 = stitches.Connection("rhua.example.com", "root", "/root/.ssh/id_rsa_test")

CUSTOM_REPOS = ["custom-i386-x86_64", "custom-x86_64-x86_64", "custom-i386-i386"]
CUSTOM_PATHS = [repo.replace("-", "/") for repo in CUSTOM_REPOS]
CUSTOM_RPMS_DIR = "/tmp/extra_rhui_files"

class TestRepo(object):
    '''
       class for repository manipulation tests
    '''

    def __init__(self):
        self.custom_rpms = Util.get_rpms_in_dir(CONNECTION, CUSTOM_RPMS_DIR)
        if not self.custom_rpms:
            raise RuntimeError("No custom RPMs to test in %s" % CUSTOM_RPMS_DIR)
        rhel_version = Util.get_rhel_version(CONNECTION)["major"]
        with open("/usr/share/rhui3_tests_lib/config/tested_repos.yaml") as configfile:
            doc = yaml.load(configfile)
            try:
                self.yum_repo_name = doc["yum_repos"][rhel_version]["name"]
                self.yum_repo_version = doc["yum_repos"][rhel_version]["version"]
                self.yum_repo_kind = doc["yum_repos"][rhel_version]["kind"]
                self.yum_repo_path = doc["yum_repos"][rhel_version]["path"]
                self.docker_container_name = doc["docker_container1"]["name"]
                self.docker_container_displayname = doc["docker_container1"]["displayname"]
            except KeyError as version:
                raise nose.SkipTest("No test repo defined for RHEL %s" % version)

    @staticmethod
    def setup_class():
        '''
           announce the beginning of the test run
        '''
        print("*** Running %s: *** " % basename(__file__))

    @staticmethod
    def test_01_repo_setup():
        '''log in to RHUI, upload cert, check if no repo exists'''
        RHUIManager.initial_run(CONNECTION)
        entlist = RHUIManagerEntitlements.upload_rh_certificate(CONNECTION)
        nose.tools.ok_(entlist)
        nose.tools.ok_(not RHUIManagerRepo.list(CONNECTION))

    @staticmethod
    def test_02_create_3_custom_repos():
        '''create 3 custom repos (protected, unprotected, no RH GPG check) '''
        RHUIManagerRepo.add_custom_repo(CONNECTION,
                                        CUSTOM_REPOS[0],
                                        "",
                                        CUSTOM_PATHS[0],
                                        "1",
                                        "y")
        RHUIManagerRepo.add_custom_repo(CONNECTION,
                                        CUSTOM_REPOS[1],
                                        "",
                                        CUSTOM_PATHS[1],
                                        "1",
                                        "n")
        RHUIManagerRepo.add_custom_repo(CONNECTION,
                                        CUSTOM_REPOS[2],
                                        "",
                                        CUSTOM_PATHS[2],
                                        "1",
                                        "y",
                                        "",
                                        "n")

    @staticmethod
    def test_03_check_custom_repo_list():
        '''check if the repolist contains the 3 custom repos'''
        nose.tools.eq_(RHUIManagerRepo.list(CONNECTION), sorted(CUSTOM_REPOS))

    @staticmethod
    def test_04_repo_id_uniqueness():
        '''verify that rhui-manager refuses to create a custom repo whose name already exists'''
        nose.tools.assert_raises(AlreadyExistsError,
                                 RHUIManagerRepo.add_custom_repo,
                                 CONNECTION,
                                 CUSTOM_REPOS[0])

    def test_05_upload_one_rpm(self):
        '''upload one rpm to the custom repo'''
        RHUIManagerRepo.upload_content(CONNECTION,
                                       [CUSTOM_REPOS[0]],
                                       "%s/%s" % (CUSTOM_RPMS_DIR, self.custom_rpms[0]))

    @staticmethod
    def test_06_upload_several_rpms():
        '''upload several rpms to the custom repo from a directory'''
        RHUIManagerRepo.upload_content(CONNECTION,
                                       [CUSTOM_REPOS[0]],
                                       CUSTOM_RPMS_DIR)

    def test_07_check_for_package(self):
        '''check package lists'''
        test_rpm_name = self.custom_rpms[0].rsplit('-', 2)[0]
        nose.tools.eq_(RHUIManagerRepo.check_for_package(CONNECTION,
                                                         CUSTOM_REPOS[0],
                                                         ""),
                       self.custom_rpms)
        nose.tools.eq_(RHUIManagerRepo.check_for_package(CONNECTION,
                                                         CUSTOM_REPOS[0],
                                                         test_rpm_name),
                       [self.custom_rpms[0]])
        nose.tools.eq_(RHUIManagerRepo.check_for_package(CONNECTION,
                                                         CUSTOM_REPOS[0],
                                                         "test"),
                       [])
        nose.tools.eq_(RHUIManagerRepo.check_for_package(CONNECTION,
                                                         CUSTOM_REPOS[1],
                                                         ""),
                       [])

    def test_08_display_custom_repos(self):
        '''check detailed information on the custom repos'''
        RHUIManagerRepo.check_detailed_information(CONNECTION,
                                                   [CUSTOM_REPOS[0], CUSTOM_PATHS[0]],
                                                   [True, True],
                                                   [True, None, True],
                                                   len(self.custom_rpms))
        RHUIManagerRepo.check_detailed_information(CONNECTION,
                                                   [CUSTOM_REPOS[1], CUSTOM_PATHS[1]],
                                                   [True, False],
                                                   [True, None, True],
                                                   0)
        RHUIManagerRepo.check_detailed_information(CONNECTION,
                                                   [CUSTOM_REPOS[2], CUSTOM_PATHS[2]],
                                                   [True, True],
                                                   [False],
                                                   0)

    def test_09_add_rh_repo_by_repo(self):
        '''add a Red Hat repo by its name'''
        RHUIManagerRepo.add_rh_repo_by_repo(CONNECTION, [Util.format_repo(self.yum_repo_name,
                                                                          self.yum_repo_version,
                                                                          self.yum_repo_kind)])
        repo_list = RHUIManagerRepo.list(CONNECTION)
        nose.tools.ok_(Util.format_repo(self.yum_repo_name, self.yum_repo_version) in repo_list,
                       msg="The repo wasn't added. Actual repolist: %s" % repo_list)

    def test_10_display_rh_repo(self):
        '''check detailed information on the Red Hat repo'''
        RHUIManagerRepo.check_detailed_information(CONNECTION,
                                                   [Util.format_repo(self.yum_repo_name,
                                                                     self.yum_repo_version),
                                                    self.yum_repo_path],
                                                   [False],
                                                   [True, None, True],
                                                   0)

    def test_11_delete_one_repo(self):
        '''remove the Red Hat repo'''
        RHUIManagerRepo.delete_repo(CONNECTION, [self.yum_repo_name + ".*"])
        repo_list = RHUIManagerRepo.list(CONNECTION)
        nose.tools.ok_(Util.format_repo(self.yum_repo_name, self.yum_repo_version) not in repo_list,
                       msg="The repo wasn't removed. Actual repolist: %s" % repo_list)

    def test_12_add_rh_repo_by_product(self):
        '''add a Red Hat repo by the product that contains it, remove it'''
        RHUIManagerRepo.add_rh_repo_by_product(CONNECTION, [self.yum_repo_name])
        repo_list = RHUIManagerRepo.list(CONNECTION)
        nose.tools.ok_(Util.format_repo(self.yum_repo_name, self.yum_repo_version) in repo_list,
                       msg="The repo wasn't added. Actual repolist: %s" % repo_list)
        RHUIManagerRepo.delete_all_repos(CONNECTION)
        nose.tools.ok_(not RHUIManagerRepo.list(CONNECTION))

    @staticmethod
    def test_13_add_all_rh_repos():
        '''add all Red Hat repos, remove them (takes a lot of time!)'''
        RHUIManagerRepo.add_rh_repo_all(CONNECTION)
        # it's not feasible to get the repo list if so many repos are present; skip the check
        #nose.tools.ok_(len(RHUIManagerRepo.list(CONNECTION)) > 100)
        RHUIManagerRepo.delete_all_repos(CONNECTION)
        nose.tools.ok_(not RHUIManagerRepo.list(CONNECTION))

    def test_14_add_docker_container(self):
        '''add a Docker container'''
        RHUIManagerRepo.add_docker_container(CONNECTION,
                                             self.docker_container_name,
                                             "",
                                             self.docker_container_displayname)
        repo_list = RHUIManagerRepo.list(CONNECTION)
        nose.tools.ok_(self.docker_container_displayname in repo_list,
                       msg="The container wasn't added. Actual repolist: %s" % repo_list)

    def test_15_display_docker_cont(self):
        '''check detailed information on the Docker container'''
        RHUIManagerRepo.check_detailed_information(CONNECTION,
                                                   [self.docker_container_displayname,
                                                    "https://cds.example.com/pulp/docker/%s/" % \
                                                    self.docker_container_name.replace("/", "_")],
                                                   [False],
                                                   [True, None, True],
                                                   0)

    @staticmethod
    def test_16_delete_docker_container():
        '''delete the Docker container'''
        RHUIManagerRepo.delete_all_repos(CONNECTION)
        nose.tools.ok_(not RHUIManagerRepo.list(CONNECTION))

    @staticmethod
    def test_17_missing_cert_handling():
        '''check if rhui-manager can handle the loss of the RH cert'''
        # for RHBZ#1325390
        RHUIManagerEntitlements.upload_rh_certificate(CONNECTION)
        # launch rhui-manager in one connection, delete the cert in the other
        RHUIManager.screen(CONNECTION, "repo")
        RHUIManager.remove_rh_certs(CONNECTION_2)
        Expect.enter(CONNECTION, "a")
        # a bit strange response to see in this context, but eh, no == all if you're a geek
        Expect.expect(CONNECTION, "All entitled products are currently deployed in the RHUI")
        Expect.enter(CONNECTION, "q")
        # an error message should be logged, though
        Expect.ping_pong(CONNECTION,
                         "tail /root/.rhui/rhui.log",
                         "The entitlement.*has no associated certificate")

    @staticmethod
    def teardown_class():
        '''
           announce the end of the test run
        '''
        print("*** Finished running %s. *** " % basename(__file__))
