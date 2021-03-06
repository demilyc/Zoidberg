### Language ###
lang en_US.UTF-8

### Timezone ###
timezone Asia/Shanghai --utc --ntpservers=clock02.util.phx2.redhat.com

### Keyboard ###
keyboard --vckeymap=us --xlayouts='us'

### Kdump ###
%addon com_redhat_kdump --enable --reserve-mb=200
%end

### Security ###
%addon org_fedora_oscap
content-type=scap-security-guide
profile=standard
%end

### User ###
rootpw --plaintext redhat
auth --enableshadow --passalgo=sha512
user --name=test --password=redhat --plaintext

### Misc ###
services --enabled=sshd

### Installation mode ###
install
#liveimg url will be substitued by autoframework
liveimg --url=http://10.66.10.22:8090/rhvh_ngn/squashimg/redhat-virtualization-host-4.1-20170202.0/redhat-virtualization-host-4.1-20170202.0.x86_64.liveimg.squashfs
text
reboot

### Network ###
network --device=enp2s0 --bootproto=static --ip=10.66.148.9 --netmask=255.255.252.0 --gateway=10.66.151.254
network --device=enp6s1f0 --bootproto=dhcp --activate --onboot=no
network --hostname=localtest.redhat.com

### Partitioning ###
ignoredisk --only-use=sda
zerombr
clearpart --all
bootloader --location=mbr
part /boot --fstype=ext4 --size=1024
part pv.01 --size=20000 --grow
volgroup rhvh pv.01 --reserved-percent=5
logvol swap --fstype=swap --name=swap --vgname=rhvh --size=8000
logvol none --name=pool --vgname=rhvh --thinpool --size=200000 --grow
logvol / --fstype=ext4 --name=root --vgname=rhvh --thin --poolname=pool --size=130000
logvol /var --fstype=ext4 --name=var --vgname=rhvh --thin --poolname=pool --size=15360
logvol /home --fstype=xfs --name=home --vgname=rhvh --thin --poolname=pool --size=50000

### Pre deal ###

### Post deal ###
%post --erroronfail
compose_check_data(){
python << ES
import pickle
import commands
import os
    
#define filename and dirs
REMOTE_TMP_FILE_DIR = '/boot/autotest'
    
CHECKDATA_MAP_PKL = 'checkdata_map.pkl'
REMOTE_CHECKDATA_MAP_PKL = os.path.join(REMOTE_TMP_FILE_DIR, CHECKDATA_MAP_PKL)
    
#create autotest dir under /boot
os.mkdir(REMOTE_TMP_FILE_DIR)
    
#run ip cmd to get nic status during installation
cmd = "nmcli -t -f DEVICE,STATE dev |grep 'enp6s1f0:connected'"
status = commands.getstatusoutput(cmd)[0]
    
#compose checkdata_map and write it to the pickle file
checkdata_map = {}

checkdata_map['lang'] = 'en_US.UTF-8'
checkdata_map['timezone'] = 'Asia/Shanghai'
checkdata_map['ntpservers'] = 'clock02.util.phx2.redhat.com'
checkdata_map['keyboard'] = {'vckeymap': 'us', 'xlayouts': 'us'}
checkdata_map['kdump'] = {'reserve-mb': '200'}
checkdata_map['user'] = {'name': 'test'}

checkdata_map['network'] = {
    'static': {
        'DEVICE': 'enp2s0',
        'BOOTPROTO': 'static',
        'IPADDR': '10.66.148.9',
        'NETMASK': '255.255.252.0',
        'GATEWAY': '10.66.151.254',
        'ONBOOT': 'yes'
    },
    'nic': {
        'DEVICE': 'enp6s1f0',
        'BOOTPROTO': 'dhcp',
        'status': status,
        'ONBOOT': 'no'
    },
    'hostname': 'localtest.redhat.com'
}

checkdata_map['partition'] = {
    '/boot': {
        'lvm': False,
        'device_alias': '/dev/sda1',
        'device_wwid': '/dev/sda1',
        'fstype': 'ext4',
        'size': '1024'
    },
    'volgroup': {
        'lvm': True,
        'name': 'rhvh'
    },
    'pool': {
        'lvm': True,
        'name': 'pool',
        'size': '200000',
        'grow': True
    },
    '/': {
        'lvm': True,
        'name': 'root',
        'fstype': 'ext4',
        'size': '130000'
    },
    '/var': {
        'lvm': True,
        'name': 'var',
        'fstype': 'ext4',
        'size': '15360'
    },
    '/home': {
        'lvm': True,
        'name': 'home',
        'fstype': 'xfs',
        'size': '50000'
    },
    'swap': {
        'lvm': True,
        'name': 'swap',
        'size': '8000'
    },
    '/var/log': {
        'lvm': True,
        'name': 'var_log',
        'fstype': 'ext4',
        'size': '8192'
    },
    '/var/log/audit': {
        'lvm': True,
        'name': 'var_log_audit',
        'fstype': 'ext4',
        'size': '2048'
    },
    '/tmp': {
        'lvm': True,
        'name': 'tmp',
        'fstype': 'ext4',
        'size': '1024'
    }
}

fp = open(REMOTE_CHECKDATA_MAP_PKL, 'wb')
pickle.dump(checkdata_map, fp)
fp.close()
ES
}

coverage_check(){
cd /tmp
curl -o coveragepy-master.zip http://10.73.73.23:7788/coveragepy-master.zip
unzip coveragepy-master.zip
cd coveragepy-master
python setup.py install
cd /usr/lib/python2.7/site-packages/
coverage run -p -m --branch --source=imgbased imgbased layout --init
mkdir /boot/coverage
cp .coverage* /boot/coverage
}

coverage_check
#imgbase layout --init
compose_check_data
%end
