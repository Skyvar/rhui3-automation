""" Utility functions """

import os
import random
import re
import string
import tempfile
import time
import yaml

from stitches.expect import Expect, ExpectFailed


class Util(object):
    '''
    Utility functions for instances
    '''
    @staticmethod
    def uncolorify(instr):
        """ Remove colorification """
        res = instr.replace("\x1b", "")
        res = res.replace("[91m", "")
        res = res.replace("[92m", "")
        res = res.replace("[93m", "")
        res = res.replace("[0m", "")
        return res

    @staticmethod
    def generate_gpg_key(connection,
                         keydata="",
                         ownerdata="",
                         comment="comment"):
        '''
        Generate GPG keypair

        WARNING!!!
        It takes too long to wait for this operation to complete... use pre-created keys instead!
        '''
        # keydata = [type, length, expire date]
        # ownerdata = [real name, email]
        if len(keydata) != 3:
            keydata = ["DSA", "1024", "0"]
        if len(ownerdata) != 2:
            ownerdata = ["Key Owner", "kowner@example.com"]
        Expect.enter(connection, "cat > /tmp/gpgkey << EOF")
        Expect.enter(connection, "Key-Type: " + keydata[0])
        Expect.enter(connection, "Key-Length: " + keydata[1])
        Expect.enter(connection, "Subkey-Type: ELG-E")
        Expect.enter(connection, "Subkey-Length: " + keydata[1])
        Expect.enter(connection, "Name-Real: " + ownerdata[0])
        Expect.enter(connection, "Name-Comment: " + comment)
        Expect.enter(connection, "Name-Email: " + ownerdata[1])
        Expect.enter(connection, "Expire-Date: " + keydata[2])
        Expect.enter(connection, "%commit")
        Expect.enter(connection, "%echo done")
        Expect.enter(connection, "EOF")
        Expect.expect(connection, "root@")

        Expect.enter(connection, "gpg --gen-key --no-random-seed-file --batch /tmp/gpgkey")
        for _ in range(1, 200):
            Expect.enter(connection,
                         ''.join(random.choice(string.ascii_lowercase) for x in range(200)))
            time.sleep(1)
            try:
                Expect.expect(connection, "gpg: done")
                break
            except ExpectFailed:
                continue

    @staticmethod
    def remove_amazon_rhui_conf_rpm(connection):
        '''
        Remove Amazon RHUI config rpm (owning /usr/sbin/choose_repo.py) from instance
        downlad the rpm first, though, so the configuration can be restored if needed
        (but don't fail if the download is unsuccessful, just try your luck)
        note that more than one rpm can actually own the file, typically on beta AMIs
        the rpm(s) is/are saved in /root
        '''
        Expect.expect_retval(connection,
                             "file=/usr/sbin/choose_repo.py; " +
                             "if [ -f $file ]; then" +
                             "  package=`rpm -qf --queryformat '%{NAME} ' $file`;" +
                             "  yumdownloader $package;" +
                             "  rpm -e $package;" +
                             "fi",
                             timeout=60)

    @staticmethod
    def disable_beta_repos(connection):
        '''
        Disable RHEL Beta repos that might have been created during the deployment
        if testing RHUI on/with an unreleased compose.
        '''
        Expect.expect_retval(connection,
                             "if [ -f /etc/yum.repos.d/rhel*_beta.repo ]; then" +
                             "  yum-config-manager --disable 'rhel*_beta*';" +
                             "fi")

    @staticmethod
    def remove_rpm(connection, rpmlist, pedantic=False):
        '''
        Remove RPMs from a remote host.
        If "pedantic", fail if the rpmlist contains one or more packages that are not installed.
        Otherwise, ignore such packages, remove whatever *is* installed (if anything).
        '''
        installed = [rpm for rpm in rpmlist if connection.recv_exit_status("rpm -q %s" % rpm) == 0]
        if installed:
            Expect.expect_retval(connection, "rpm -e %s" % ' '.join(installed), timeout=60)
        if pedantic and installed != rpmlist:
            raise OSError("%s: not installed, could not remove" % (set(rpmlist) - set(installed)))

    @staticmethod
    def install_pkg_from_rhua(rhua_connection, connection, pkgpath, allow_update=False):
        '''
        Transfer package from RHUA host to the instance and install it
        @param pkgpath: path to package on RHUA node
        @param allow_update: allow an updated version/release to be installed; if not, `rpm' fails
        '''
        tfile = tempfile.NamedTemporaryFile(delete=False)
        tfile.close()
        rhua_connection.sftp.get(pkgpath, tfile.name)
        file_extension = os.path.splitext(pkgpath)[1]
        if file_extension == '.rpm':
            option = "U" if allow_update else "i"
            connection.sftp.put(tfile.name, tfile.name + file_extension)
            os.unlink(tfile.name)
            Expect.expect_retval(connection, "rpm -%s %s%s" % (option, tfile.name, file_extension))
        else:
            connection.sftp.put(tfile.name, tfile.name + '.tar.gz')
            os.unlink(tfile.name)
            Expect.expect_retval(connection, "tar -xzf" + tfile.name + ".tar.gz && ./install.sh")

    @staticmethod
    def get_initial_password(connection):
        '''
        Read rhui-manager password from the rhui-installer answers file
        '''
        answers_file = "/etc/rhui-installer/answers.yaml"
        _, stdout, _ = connection.exec_command("cat %s" % answers_file)
        try:
            answers = yaml.load(stdout)
            return answers["rhua"]["rhui_manager_password"]
        except (KeyError, TypeError, yaml.scanner.ScannerError):
            return None

    @staticmethod
    def get_rpm_details(rpmpath):
        '''
        Get (name-version-release, name) pair for local rpm file
        '''
        if rpmpath:
            rpmnvr = os.popen("basename " + rpmpath).read()[:-1]
            rpmname = os.popen("rpm -qp --queryformat '%{NAME}\n' " +
                               rpmpath +
                               " 2>/dev/null").read()[:-1]
            return (rpmnvr, rpmname)
        return (None, None)

    @staticmethod
    def get_rhel_version(connection):
        '''
        get RHEL X.Y version (dict with two integers representing the major and minor version)
        '''
        _, stdout, _ = connection.exec_command(r"egrep -o '[0-9]+\.[0-9]+' /etc/redhat-release")
        with stdout as output:
            version = output.read().decode().strip().split(".")
        try:
            version_dict = {"major": int(version[0]), "minor": int(version[1])}
            return version_dict
        except ValueError:
            return None

    @staticmethod
    def get_arch(connection):
        '''
        get machine architecture; note that ARM64 is presented as aarch64.
        '''
        _, stdout, _ = connection.exec_command("arch")
        with stdout as output:
            arch = output.read().decode().strip()
        return arch

    @staticmethod
    def esc_parentheses(name):
        '''
        helper method to escape parentheses so they can be safely used inside
        regular expressions in Expect methods
        '''
        return name.replace("(", r"\(").replace(")", r"\)")

    @staticmethod
    def format_repo(name, version="", kind=""):
        '''
        helper method to put together a repo name, version, and kind
        the way RHUI repos are called in rhui-manager
        '''
        repo = name
        if version:
            repo += " (%s)" % version
        if kind:
            repo += " (%s)" % kind
        return repo

    @staticmethod
    def get_cds_hostnames():
        '''
        read CDS hostnames from /etc/hosts and return a list of them
        '''
        cds_pattern = r"cds[0-9]+\.example\.com"
        with open("/etc/hosts") as hostsfile:
            all_hosts = hostsfile.read()
        return re.findall(cds_pattern, all_hosts)

    @staticmethod
    def get_rpms_in_dir(connection, directory):
        '''
        return a list of RPM files in the directory
        '''
        _, stdout, _ = connection.exec_command("cd %s && ls -w1 *.rpm" % directory)
        with stdout as output:
            rpms = output.read().decode().splitlines()
            return rpms

    @staticmethod
    def restart_if_present(connection, service):
        '''
        restart a systemd service if it exists
        '''
        Expect.expect_retval(connection,
                             "if [ -f /usr/lib/systemd/system/%s.service ]; then " % service +
                             "systemctl restart %s; fi" % service)

    @staticmethod
    def check_package_url(connection, package, path="", lb_hostname="cds.example.com"):
        '''
        verify that the package is available from the RHUI (and not from an unwanted repo)
        '''
        # The name of the test package may contain characters which must be escaped in REs.
        # In modern pulp-rpm versions, packages are in .../Packages/<first letter (lowercase)>/,
        # and the URL can be .../os/...NVR or .../os//...NVR, so let's tolerate anything between
        # the path and the package name. The path is optional, though; if you don't know it or
        # don't care about it, call this method with the mandatory arguments only.
        package_escaped = re.escape(package)
        Expect.ping_pong(connection,
                         "yumdownloader --url %s" % package_escaped,
                         "https://%s/pulp/repos/%s.*%s" % \
                         (lb_hostname, path, package_escaped))

    @staticmethod
    def cert_expired(connection, cert):
        '''
        check if the certificate has already expired, return true if so
        '''
        file_exists = connection.recv_exit_status("test -f %s" % cert) == 0
        if not file_exists:
            raise OSError("%s does not exist" % cert)
        return connection.recv_exit_status("openssl x509 -checkend -noout -in %s" % cert) == 1

    @staticmethod
    def fetch(connection, source, dest):
        '''
        fetch a file from the remote host
        '''
        connection.sftp.get(source, dest)

    @staticmethod
    def safe_pulp_repo_name(name):
        '''
        replace prohibited characters in repo names with safe ones (as per rhui-manager)
        '''
        return name.replace("/", "_").replace(".", "_")

    @staticmethod
    def mktemp_remote(connection, extension=""):
        '''
        create a temporary file on the remote host and return its path
        '''
        _, stdout, _ = connection.exec_command("mktemp /tmp/XXXX%s" % extension)
        path = stdout.read().decode().strip()
        return path
