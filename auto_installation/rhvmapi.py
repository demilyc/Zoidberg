import logging
import base64
import requests
import shutil
from time import sleep

log = logging.getLogger('bender')

class RhevmAction:
    """a rhevm rest-client warpper class
   currently can registe a rhvh to rhevm
   example:
   RhevmAction("rhevm-40-1.englab.nay.redhat.com").add_new_host("10.66.8.217", "autotest01", "redhat")
   """

    auth_format = "{user}@{domain}:{password}"
    api_url = "https://{rhevm_fqdn}/ovirt-engine/api/{item}"

    headers = {
        "Prefer": "persistent-auth",
        "Accept": "application/json",
        "Content-type": "application/xml"
    }

    cert_url = ("https://{rhevm_fqdn}/ovirt-engine/services"
                "/pki-resource?resource=ca-certificate&format=X509-PEM-CA")

    rhevm_cert = "/tmp/rhevm.cert"

    def __init__(self,
                 rhevm_fqdn,
                 user="admin",
                 password="password",
                 domain="internal"):

        self.rhevm_fqdn = rhevm_fqdn
        self.user = user
        self.password = password
        self.domain = domain
        self.token = base64.b64encode(
            self.auth_format.format(
                user=self.user, domain=self.domain, password=self.password))
        self.headers.update({
            "Authorization":
            "Basic {token}".format(token=self.token)
        })
        self._get_rhevm_cert_file()
        self.req = requests.Session()

    def _get_rhevm_cert_file(self):
        r = requests.get(
            self.cert_url.format(rhevm_fqdn=self.rhevm_fqdn),
            stream=True,
            verify=False)

        if r.status_code == 200:
            with open(self.rhevm_cert, 'wb') as f:
                r.raw.decode_content = True
                shutil.copyfileobj(r.raw, f)
        else:
            raise RuntimeError("Can not get the cert file from %s" %
                               self.rhevm_fqdn)

    ###################################
    # Datacenter related functions
    ###################################
    def add_datacenter(self, dc_name, is_local=False):
        api_url = self.api_url.format(
            rhevm_fqdn=self.rhevm_fqdn, item="datacenters")

        new_dc_post_body = '''
        <data_center>
            <name>{dc_name}</name>
            <local>{is_local}</local>
        </data_center>
       '''
        body = new_dc_post_body.format(dc_name=dc_name, is_local=is_local)

        r = self.req.post(
            api_url, headers=self.headers, verify=self.rhevm_cert, data=body)

        if r.status_code != 201:
            log.error(r.text)
            raise RuntimeError("Failed to add new data center %s" % dc_name)

    def remove_datacenter(self, dc_name, force=False):
        api_url_base = self.api_url.format(
            rhevm_fqdn=self.rhevm_fqdn, item="datacenters")
        dc = self.list_datacenter(dc_name)

        if not dc:
            log.info("data_center %s doesn't exist, no need to remove.", dc_name)
            return

        dc_id = dc.get('id')
        api_url = api_url_base + '/{}'.format(dc_id)

        r = self.req.delete(
            api_url,
            headers=self.headers,
            verify=self.rhevm_cert,
            params={'force': force})

        if r.status_code != 200:
            log.error(r.text)
            raise RuntimeError("Failed to remove datacenter %s" % dc_name)

    def list_datacenter(self, dc_name):
        api_url = self.api_url.format(
            rhevm_fqdn=self.rhevm_fqdn, item="datacenters")

        r = self.req.get(api_url, headers=self.headers, verify=self.rhevm_cert)

        if r.status_code != 200:
            raise RuntimeError("Can not list datacenters from %s" %
                               self.rhevm_fqdn)

        dcs = r.json()
        if dcs:
            for dc in dcs['data_center']:
                if dc['name'] == dc_name:
                    return dc
        else:
            return

    ##################################
    # Cluster related functions
    ##################################
    def add_cluster(self, dc_name, cluster_name, cpu_type):
        api_url = self.api_url.format(
            rhevm_fqdn=self.rhevm_fqdn, item="clusters")

        new_cluster_post_body = '''
        <cluster>
            <name>{cluster_name}</name>
            <cpu>
                <type>{cpu_type}</type>
            </cpu>
            <data_center>
                <name>{dc_name}</name>
            </data_center>
        </cluster>
       '''
        body = new_cluster_post_body.format(
            dc_name=dc_name, cluster_name=cluster_name, cpu_type=cpu_type)

        r = self.req.post(
            api_url, headers=self.headers, verify=self.rhevm_cert, data=body)

        if r.status_code != 201:
            log.error(r.text)
            raise RuntimeError("Failed to add new cluster")

    def remove_cluster(self, cluster_name):
        api_url_base = self.api_url.format(
            rhevm_fqdn=self.rhevm_fqdn, item="clusters")
        cluster = self.list_cluster(cluster_name)

        if not cluster:
            log.info("Cluster %s doesn't exist, no need to remove.", cluster_name)
            return

        cluster_id = cluster.get('id')
        api_url = api_url_base + '/{}'.format(cluster_id)

        r = self.req.delete(
            api_url, headers=self.headers, verify=self.rhevm_cert)

        if r.status_code != 200:
            log.error(r.text)
            raise RuntimeError("Failed to remove cluster %s" % cluster_name)

    def list_cluster(self, cluster_name):
        api_url = self.api_url.format(
            rhevm_fqdn=self.rhevm_fqdn, item="clusters")

        r = self.req.get(api_url, headers=self.headers, verify=self.rhevm_cert)

        if r.status_code != 200:
            raise RuntimeError("Can not list clusters from %s" %
                               self.rhevm_fqdn)

        clusters = r.json()
        if clusters:
            for cluster in clusters['cluster']:
                if cluster['name'] == cluster_name:
                    return cluster
        else:
            return

    def update_cluster_cpu(self, cluster_name, cpu_type):
        api_url_base = self.api_url.format(
            rhevm_fqdn=self.rhevm_fqdn, item="clusters")
        cluster_id = self.list_cluster(cluster_name)['id']
        api_url = api_url_base + "/%s" % cluster_id

        cluster_cpu_post_body = '''
        <cluster>
            <cpu>
                <type>{cpu_type}</type>
            </cpu>
        </cluster>
        '''
        body = cluster_cpu_post_body.format(cpu_type=cpu_type)

        r = self.req.put(
            api_url, headers=self.headers, verify=self.rhevm_cert, data=body)

        if r.status_code != 200:
            raise RuntimeError("Failed to update cluster cpu type")

    ############################################
    # Host related functions
    ############################################
    def _deactive_host(self, host_id):
        api_url_base = self.api_url.format(
            rhevm_fqdn=self.rhevm_fqdn, item='hosts')
        api_url = api_url_base + "/%s/deactivate" % host_id

        r = self.req.post(
            api_url,
            headers=self.headers,
            verify=self.rhevm_cert,
            data="<action/>")
        ret = r.json()
        if ret['status'] != 'complete':
            raise RuntimeError(ret['fault']['detail'])

    def add_host(self, ip, host_name, password, cluster_name='Default'):
        api_url = self.api_url.format(rhevm_fqdn=self.rhevm_fqdn, item="hosts")

        new_host_post_body = '''
        <host>
            <name>{host_name}</name>
            <address>{ip}</address>
            <root_password>{password}</root_password>
            <cluster>
              <name>{cluster_name}</name>
            </cluster>
        </host>
       '''
        body = new_host_post_body.format(
            host_name=host_name,
            ip=ip,
            password=password,
            cluster_name=cluster_name)

        r = self.req.post(
            api_url, data=body, headers=self.headers, verify=self.rhevm_cert)

        if r.status_code != 201:
            log.error(r.text)
            raise RuntimeError(
                "Failed to add new host, may be host already imported")

    def remove_host(self, host_name):
        api_url_base = self.api_url.format(
            rhevm_fqdn=self.rhevm_fqdn, item="hosts")
        host = self.list_host(key="name", value=host_name)

        if host:
            host_id = host.get('id')

            if host.get('status') != 'maintenance':
                self._deactive_host(host_id)
                sleep(10)

            api_url = api_url_base + '/%s' % host_id

            r = self.req.delete(
                api_url,
                headers=self.headers,
                verify=self.rhevm_cert,
                params={"async": "false"})

            if r.status_code != 200:
                log.error(r.text)
                raise RuntimeError("Delete host %s failed" % host_name)
        else:
            log.info("Host %s doesn't exist, no need to delete.", host_name)

    def list_host(self, key=None, value=None):
        api_url = self.api_url.format(rhevm_fqdn=self.rhevm_fqdn, item="hosts")
        r = self.req.get(api_url, headers=self.headers, verify=self.rhevm_cert)

        if r.status_code != 200:
            raise RuntimeError("Can not list hosts from %s" % self.rhevm_fqdn)

        hosts = r.json()
        if hosts:
            for host in hosts['host']:
                if host.get(key) == value:
                    return host
        else:
            return

    def _update_available_check(self, host_id):
        rhvm_version = self.rhevm_fqdn.split('-')[0]

        if rhvm_version == "rhvm41":
            api_url_base = self.api_url.format(
                rhevm_fqdn=self.rhevm_fqdn, item="hosts")
            api_url = api_url_base + '/%s' % host_id + '/upgradecheck'

            r = self.req.post(
                api_url,
                data="<action/>",
                headers=self.headers,
                verify=self.rhevm_cert,
                params={"async": "false"})

            if r.status_code != 200:
                raise RuntimeError("Failed to execute upgradecheck.")

        count_max = 6
        sleep_time = 300
        if rhvm_version == "rhvm41":
            count_max = 10
            sleep_time = 30

        count = 0
        while (count < count_max):
            sleep(sleep_time)
            update_available = self.list_host(
                key="id", value=host_id)['update_available']
            if update_available == 'true':
                break
            count = count + 1
        else:
            log.error("update is not available.")
            return False

        return True

    def _get_host_event(self, host_name, description):
        api_url = self.api_url.format(
            rhevm_fqdn=self.rhevm_fqdn, item="events")

        params = {'search': "event_host={}".format("host_name")}
        r = self.req.get(api_url, headers=self.headers, verify=self.rhevm_cert, params=params)

        if r.status_code != 200:
            log.error("Can not list events of host %s on %s" , host_name, self.rhevm_fqdn)
            return False
        events = r.json()
        if events:
            for event in events.get('event'):
                if description in event.get('description'):
                    return True
            else:
                return False
        else:
            return False

    def upgrade_host(self, host_name):
        api_url_base = self.api_url.format(
            rhevm_fqdn=self.rhevm_fqdn, item="hosts")
        host = self.list_host(key="name", value=host_name)

        if host:
            host_id = host.get('id')

            # check host update available
            if not self._update_available_check(host_id):
                raise RuntimeError("Update is not available for host %s" %
                                   host_name)
            # try to trigger upgrade
            api_url = api_url_base + '/%s' % host_id + '/upgrade'
            r = self.req.post(
                api_url,
                headers=self.headers,
                verify=self.rhevm_cert,
                data="<action/>",
                params={"async": "false"})

            if r.status_code != 200:
                raise RuntimeError("Failed to execute upgrade on host %s" %
                                   host_name)

            # check upgrade status
            description = 'Host {} upgrade was completed successfully'.format(
                host_name)
            count = 0
            while (count < 3):
                sleep(300)
                if self._get_host_event(host_name, description):
                    log.info(description)
                    break
                count = count + 1
            else:
                raise RuntimeError("Upgrade host %s failed." % host_name)
        else:
            raise RuntimeError("Can't find host with name %s" % host_name)

    ######################################
    # Storage related functions
    ######################################
    def add_plain_storage_domain(self, domain_name, domain_type, storage_type,
                                 storage_addr, storage_path, host):
        api_url = self.api_url.format(
            rhevm_fqdn=self.rhevm_fqdn, item="storagedomains")

        storage_domain_post_body = '''
        <storage_domain>
            <name>{domain_name}</name>
            <type>{domain_type}</type>
            <storage>
                <type>{storage_type}</type>
                <address>{storage_addr}</address>
                <path>{storage_path}</path>
            </storage>
            <host>
                <name>{host}</name>
            </host>
        </storage_domain>
        '''
        body = storage_domain_post_body.format(
            domain_name=domain_name,
            domain_type=domain_type,
            storage_type=storage_type,
            storage_addr=storage_addr,
            storage_path=storage_path,
            host=host)

        r = self.req.post(
            api_url, data=body, headers=self.headers, verify=self.rhevm_cert)

        if r.status_code != 201:
            raise RuntimeError("Failed to add new storage domain" %
                               domain_name)

    def attach_sd_to_datacenter(self, sd_name, dc_name):
        api_url_base = self.api_url.format(
            rhevm_fqdn=self.rhevm_fqdn, item="datacenters")
        api_url = api_url_base + '/%s/storagedomains' % dc_name

        new_storage_post_body = '''
        <storage_domain>
            <name>{storage_name}</name>
        </storage_domain>
       '''
        body = new_storage_post_body.format(storage_name=sd_name)

        r = self.req.post(
            api_url, data=body, headers=self.headers, verify=self.rhevm_cert)

        if r.status_code != 201:
            log.error(r.text)
            raise RuntimeError("Failed to attach storage %s to datacenter %s" %
                               (sd_name, dc_name))

    ##########################################
    # VM related functions
    ##########################################
    def create_vm(self, vm_name, tpl_name="blank", cluster="default"):
        api_url_base = self.api_url.format(
            rhevm_fqdn=self.rhevm_fqdn, item="vms")

        new_vm_body = '''
        <vm>
            <name>{vm_name}</name>
            <description>{vm_name}</description>
            <cluster>
                <name>{cluster_name}</name>
            </cluster>
            <template>
                <name>{tpl_name}</name>
            </template>
        </vm>
       '''
        body = new_vm_body.format(
            vm_name=vm_name, tpl_name=tpl_name, cluster_name=cluster)

        r = self.req.post(
            api_url_base,
            data=body,
            headers=self.headers,
            verify=self.rhevm_cert)

        if r.status_code != 202:
            raise RuntimeError("Failed to create viratual machine")
        else:
            return r.json()["id"]

    def start_vm(self, vm_id):
        api_url_base = self.api_url.format(
            rhevm_fqdn=self.rhevm_fqdn, item="vms")
        api_url = api_url_base + '/%s/start' % vm_id

        vm_action = '''
        <action>
            <vm>
                <os>
                    <boot>
                        <devices>
                            <device>hd</device>
                        </devices>
                    </boot>
                </os>
            </vm>
        </action>
       '''
        r = self.req.post(
            api_url,
            data=vm_action,
            headers=self.headers,
            verify=self.rhevm_cert)
        log.info(r.status_code)

    ##########################################
    # Network related functions
    ##########################################
    def list_network(self, dc_name, nw_name):
        api_url = self.api_url.format(
            rhevm_fqdn=self.rhevm_fqdn, item="networks")
        dc_id = self.list_datacenter(dc_name).get('id')

        r = self.req.get(api_url, headers=self.headers, verify=self.rhevm_cert)
        if r.status_code != 200:
            raise RuntimeError("Can not list networks from %s" %
                               self.rhevm_fqdn)

        networks = r.json()
        if networks:
            for network in networks.get('network'):
                if network.get('name') == nw_name and network.get(
                        'data_center').get('id') == dc_id:
                    return network
        else:
            return

    def update_network(self,
                       dc_name,
                       param_name,
                       param_vlue,
                       nw_name="ovirtmgmt"):
        api_url_base = self.api_url.format(
            rhevm_fqdn=self.rhevm_fqdn, item="networks")
        network = self.list_network(dc_name, nw_name)

        if not network:
            raise RuntimeError("Can't find network %s in data center %s" %
                               (nw_name, dc_name))

        network_id = network.get('id')
        api_url = api_url_base + '/%s' % network_id

        if param_name == "vlan":
            update_network_body = '''
            <network>
                <vlan id="{value}"/>
            </network>
            '''
        else:
            update_network_body = '''
            <network>
                <{key}>{value}</{key}>
            </network>
            '''

        body = update_network_body.format(key=param_name, value=param_vlue)

        r = self.req.put(
            api_url,
            headers=self.headers,
            verify=self.rhevm_cert,
            data=body,
            params={"async": "false"})

        if r.status_code != 200:
            log.error(r.text)
            raise RuntimeError(
                "Update network %s with %s=%s in data center %s failed" %
                (nw_name, param_name, param_vlue, dc_name))


if __name__ == '__main__':
    rhvm = RhevmAction("rhvm41-vdsm-auto.lab.eng.pek2.redhat.com")
    # rhvm.add_datacenter("upgrade_test")
    # rhvm.add_cluster("upgrade_test", "Intel Conroe Family", "upgrade_test")
    # rhvm.add_host("10.73.75.235", "atu_amd", "redhat", "atu_amd")
    # rhvm.remove_datacenter("upgrade_test")
    # rhvm.remove_host("atu_amd")
    # rhvm.upgrade_host("test")
    # rhvm.update_network("test", "vlan", "50")