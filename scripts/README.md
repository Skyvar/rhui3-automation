# RHUI3 automation - scripts

## Create Stack script

Script creates ec2 instance machines (m3.large) according to specification.

Instances are named `$user_$fstype_$name_$role` (*user_nfs_77betatests_rhua*)

The script produces an output config file suitable for the RHUI3 ansible installation. [Example](#output-configuration-file) of the output file. Default
name of the file is `hosts_$fstype_$name.cfg` (*hosts_nfs_77betatests.cfg*)

New security group is created. Its name contains stack id. <br />
Inbound rules:

  ```
  22 TCP (SSH)
  53 TCP (DNS)
  53 UDP (DNS)
  80 TCP (HTTP)
  443 TCP (HTTPS)
  2049 TCP (NFS)
  5000 TCP (containers)
  5671 TCP (Qpid)
  8140 TCP (puppet)
  24007 TCP (gluster)
  49152-49154 (gluster)
```

### Requirements

* yaml config file with ec2 credentials - default path is `/etc/rhui_ec2.yaml` [(example)](#input-configuration-file)
* up-to-date lists of AMIs in `*mapping.json` files - the files should be up to date in Git, but you can regenerate them locally with the `scripts/get_amis_list.py` script
* the following modules for your Python version: boto, paramiko; install them using your distribution's package manager, or using pip

### Usage

Run `scripts/create-cf-stack.py [optional parameters]` [(example)](#usage-example)

Default configuration: 
  * NFS filesystem
  * RHEL7 instances (basic RHUI 3 requirement)
  * eu-west-1 region
  * instances: 1xRHUA (NFS, DNS), 1xCDS, 1xHAProxy

#### Main parameters

  * **--name [name]** - common name for the instances in the stack (as in $user_$fstype_$name_$role); also affects the `hosts` file name (unless overridden). `default = rhui`
  * **--gluster** - use GlusterFS instead of NFS
  * **--dns** - if specified, a separate machine for dns, `default = the same as RHUA`
  * **--cds [number]** - number of CDS machines, `default = 1` (if Gluster filesystem, `default = 3`)
  * **--haproxy [number]** - number of HAProxies, `default = 1`
  * **--input-conf [name]** - the name of input conf file, `default = "/etc/rhui_ec2.yaml"`
  * **--output-conf [name]** - the name of output conf file, `default = "hosts_$fstype_$name.cfg"`
  * **--cli5/6/7/8 [number]** - number of CLI machines, `default = 0`, use `-1` to get machines for all architectures (one machine per architecture)
  * **--cli7/8-arch [arch]** - CLI machines' architectures (comma-separated list), `default = x86_64 for all of them`, `cli`_N_ set to `-1` will populate the list with all architectures automatically, so this parameter is unnecessary then
  * **--atomic-cli [number]** - number of ATOMIC CLI machines, `default = 0`
  * **--test** - if specified, TEST/MASTER machine running RHEL 7, `default = 0`
  * **--test8** - if specified, TEST/MASTER machine running RHEL 8, `default = 0`
  * **--region [name]** - `default = eu-west-1`
  * **--ansible-ssh-extra-args [args]** - optional SSH arguments for Ansible

Run the script with `-h` or `--help` to get a list of all parameters.

Note that RHEL-5 AMIs are not available in all regions;
see the [RHEL 5 mapping file](RHEL5mapping.json).
Attempts to launch a RHEL-5 client in a region that does not have a RHEL-5 AMI will fail.

Moreover, with Ansible 2.4 and newer, it is no longer possible to manage machines with Python older
than 2.6. RHEL 5 has Python 2.4. To avoid failures, the hosts configuration file will be created
with the RHEL-5 client hostname and other data commented out so that it is all visible to you but
ignored by `ansible-playbook`. Other than that, you are free to use the launched RHEL-5 client any
way you want, just be sure to log in as root directly.

Note that RHEL-8 AMIs are missing the unversioned `python` command. This does not affect
the deployment because the _platform Python_ is automatically set in the case of RHEL 8 hosts.

If you specify a non-x86\_64 client architecture, a suitable instance type will be selected
automatically. You may need to supply a VPC and a subnet ID with some instance types,
e.g. with a1.large, which will be selected for arm64.

Mutually exclusive options: 

  * **--nfs** - if specified, nfs filesystem with separate machine and NFS volume (100 GB) attached to this machine
  * **--gluster** - if specified, gluster filesystem with an extra volume attached to each CDS (100 GB)
  
Other options:
  * **--debug** - debug info

### Configuration possibilities

#### NFS filesystem

Configuration with NFS filesystem needs at least 1 CDS, 1 HAProxy and RHUA machine. <br />
If there is a separate NFS machine, an extra 100 GB volume is attached to this machine. If not, an extra 100 GB volume is attached to the RHUA machine.
Either way, a 50 GB volume is attached for MongoDB on the RHUA.

![NFS setup](img/rhui-storage-nfs.png)

#### Gluster filesystem

Configuration with Gluster filesystem needs at least 3 CDS, 1 HAProxy and RHUA machine. <br />
There is an extra 100 GB volume attached to each CDS machine.
In addition, a 50 GB volume is attached for MongoDB on the RHUA.

![GlusterFS setup](img/rhui-storage-gluster.png)

### Examples

#### Usage example

* `scripts/create-cf-stack.py`
  * basic NFS configuration
  * 1xRHUA=DNS=NFS, 1xCDS, 1xHAProxy
* `scripts/create-cf-stack.py --test --gluster --name playpit`
  * Gluster configuration
  * 1xRHUA=DNS, 3xCDS, 1xHAProxy, 1xtest_machine
* `scripts/create-cf-stack.py --region eu-central-1 --nfs cli6 2 --haproxy 2 --name rhui31wip`
  * NFS configuration in the eu-central-1 region
  * 1xRHUA=DNS, 1xNFS, 2xCLI6, 2xHAProxy
* `scripts/create-cf-stack.py --dns --cds 2 --cli6 1 --cli7 1 --input-conf /etc/rhui_amazon.yaml --output-conf my_new_hosts_config_file.cfg --name cdsdebug`
  * NFS configuration
  * 1xRHUA=NFS, 1xDNS, 2xCDS, 1xCLI6, 1xCLI7, 1xHAProxy
* `scripts/create-cf-stack.py --input-conf rhui_ec2.yaml --name rhel8clients --cli8 -1 --test --vpcid vpc-012345678 --subnetid subnet-89abcdef`
  * NFS configuration
  * custom input configuration file in the current working directory
  * 1xRHUA=NFS=DNS, 1xCDS, 1xHAProxy, 2xCLI8 (x86_64 and ARM64), 1xTEST, custom VPC and subnet (needed by the `a1` instance type used with ARM64)

#### Input configuration file

Change `ec2-key` and `ec2-secret-key` values to your keys. Change `user` to your username and update path to your pem keys. If region is missing, add it according to the pattern.

```
ec2: {ec2-key: AAAAAAAAAAAAAAAAAAAA, ec2-secret-key: B0B0B0B0B0B0B0B0B0B0a1a1a1a1a1a1a1a1a1a1}
ssh:
  ap-northeast-1: [user-ap-northeast-1, /home/user/.pem/user-ap-northeast-1.pem]
  ap-southeast-1: [user-ap-southeast-1, /home/user/.pem/user-ap-southeast-1.pem]
  ap-southeast-2: [user-ap-southeast-2, /home/user/.pem/user-ap-southeast-2.pem]
  eu-central-1: [user-eu-central-1, /home/user/.pem/user-eu-central-1.pem]
  eu-west-1: [user-eu-west-1, /home/user/.pem/user-eu-west-1.pem]
  sa-east-1: [user-sa-east-1, /home/user/.pem/user-sa-east-1.pem]
  us-east-1: [user-us-east-1, /home/user/.pem/user-us-east-1.pem]
  us-west-1: [user-us-west-1, /home/user/.pem/user-us-west-1.pem]
  us-west-2: [user-us-west-2, /home/user/.pem/user-us-west-2.pem]

```

#### Output configuration file

The output configuration file is needed for the rhui3 ansible installation.

Example of an output file with Gluster configuration (1xRHUA=DNS, 3xCDS, 2xCLI, 1xtest_machine, 1xHAProxy):

```
[RHUA]
ec2-54-170-205-98.eu-west-1.compute.amazonaws.com ansible_ssh_user=ec2-user ansible_become=True ansible_ssh_private_key_file=/home/user/.ssh/user-eu-west-1.pem

[GLUSTER]
ec2-54-78-213-201.eu-west-1.compute.amazonaws.com ansible_ssh_user=ec2-user ansible_become=True ansible_ssh_private_key_file=/home/user/.ssh/user-eu-west-1.pem
ec2-54-78-165-67.eu-west-1.compute.amazonaws.com ansible_ssh_user=ec2-user ansible_become=True ansible_ssh_private_key_file=/home/user/.ssh/user-eu-west-1.pem
ec2-54-155-142-185.eu-west-1.compute.amazonaws.com ansible_ssh_user=ec2-user ansible_become=True ansible_ssh_private_key_file=/home/user/.ssh/user-eu-west-1.pem

[CDS]
ec2-54-78-213-201.eu-west-1.compute.amazonaws.com ansible_ssh_user=ec2-user ansible_become=True ansible_ssh_private_key_file=/home/user/.ssh/user-eu-west-1.pem
ec2-54-78-165-67.eu-west-1.compute.amazonaws.com ansible_ssh_user=ec2-user ansible_become=True ansible_ssh_private_key_file=/home/user/.ssh/user-eu-west-1.pem
ec2-54-155-142-185.eu-west-1.compute.amazonaws.com ansible_ssh_user=ec2-user ansible_become=True ansible_ssh_private_key_file=/home/user/.ssh/user-eu-west-1.pem

[DNS]
ec2-54-170-205-98.eu-west-1.compute.amazonaws.com ansible_ssh_user=ec2-user ansible_become=True ansible_ssh_private_key_file=/home/user/.ssh/user-eu-west-1.pem

[CLI]
ec2-54-155-178-68.eu-west-1.compute.amazonaws.com ansible_ssh_user=ec2-user ansible_become=True ansible_ssh_private_key_file=/home/user/.ssh/user-eu-west-1.pem
ec2-54-228-24-150.eu-west-1.compute.amazonaws.com ansible_ssh_user=ec2-user ansible_become=True ansible_ssh_private_key_file=/home/user/.ssh/user-eu-west-1.pem

[TEST]
ec2-54-73-34-96.eu-west-1.compute.amazonaws.com ansible_ssh_user=ec2-user ansible_become=True ansible_ssh_private_key_file=/home/user/.ssh/user-eu-west-1.pem

[HAPROXY]
ec2-54-73-134-159.eu-west-1.compute.amazonaws.com ansible_ssh_user=ec2-user ansible_become=True ansible_ssh_private_key_file=/home/user/.ssh/user-eu-west-1.pem

```

### How to delete stack

Stack can be deleted "all in one" with CloudFormation. On the AWS amazon web page go to the CloudFormation service, mark the stack -> Actions -> Delete stack.

Stack is deleted with all its instances, volumes and the security group.

