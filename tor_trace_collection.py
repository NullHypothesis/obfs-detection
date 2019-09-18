import os
import sys
import argparse
import subprocess
import signal
import platform
import time
import logging
import random
from stem.control import Controller
from stem import CircStatus
import stem.process
from stem.util import term
from selenium import webdriver
from selenium.webdriver.firefox.firefox_binary import FirefoxBinary
from selenium.webdriver.firefox.webdriver import FirefoxProfile
from selenium.webdriver import firefox
from selenium.webdriver import DesiredCapabilities
from selenium.webdriver.common.alert import Alert
from selenium.webdriver.common.utils import free_port
from selenium.webdriver.firefox import extension_connection
from conf import *

IS_WINDOWS = platform.system().lower().startswith('windows')
os.environ['LD_LIBRARY_PATH'] =  os.path.join(TBB_DIR, "TorBrowser", "Tor")
TOR_DATA_DIR = os.path.join(TBB_DIR, 'TorBrowser', 'Data', 'Tor')
TOR_PLUG_DIR = os.path.join(TBB_DIR, 'TorBrowser', 'Tor', 'PluggableTransports')
TOR_PROFILE_DIR = os.path.join(TBB_DIR, 'TorBrowser', 'Data', 'Browser')


class BasicTorrc(dict):
    """
    A class represents the torcc file
    """
    def __init__(self):
        self['AvoidDiskWrites'] = '1'
        self['Log'] = 'notice stdout'
        self['SocksPort'] = '9150'
        self['ControlPort'] = '9151'
        self['CookieAuthentication'] = '1'
        self['SocksTimeout'] = '60'
        self['CircuitBuildTimeout'] = '60'
        self['DataDirectory'] = TOR_DATA_DIR
        self['DirReqStatistics'] = '0'
        self['GeoIPFile'] = os.path.join(TOR_DATA_DIR, 'Tor', 'geoip')
        self['GeoIPv6File'] = os.path.join(TOR_DATA_DIR, 'Tor', 'geoip6')
        #: set it to 1 only you can not connect tor at first
        self['UseBridges'] = '1'

class FteTorrc(BasicTorrc):
    """Configure FTE proxy"""
    def __init__(self):
        super(FteTorrc, self).__init__()
        # fteproxy configuration
        if IS_WINDOWS: prog = os.path.join(TOR_PLUG_DIR, 'fteproxy.exe')
        else: prog = os.path.join(TOR_PLUG_DIR, 'fteproxy.bin')
        # the path and parameters of the executed pluggable transport
        self['ClientTransportPlugin'] = 'fte exec %s --managed' % (prog)
        # change the proxy bridges
        self['Bridge'] = [
            'fte 50.7.176.114:80 2BD466989944867075E872310EBAD65BC88C8AEF',
            'fte 192.240.101.106:80 B629B0B607C8AC9349B5646C24E9D242184F5B6E',
            'fte 128.105.214.163:8080 A17A40775FBD2CA1184BF80BFC330A77ECF9D0E9',
            'fte 131.252.210.150:8080 0E858AC201BF0F3FA3C462F64844CBFFC7297A42',
            'fte 128.105.214.162:8080 FC562097E1951DCC41B7D7F324D88157119BB56D',
            'fte 128.105.214.161:8080 1E326AAFB3FCB515015250D8FCCC8E37F91A153B',
            'fte 185.13.37.104:25547 FA894ED57753A4F34C22CA0117EC692B4C8EEC3C',
            'fte 194.132.208.208:10851 26F0C37408E9656134940EEB8506E3C7A842AC3F',
        ]     

class Obfs3Torrc(BasicTorrc):
    """Configure Obfs3 proxy"""
    def __init__(self):
        super(Obfs3Torrc, self).__init__()
     
        if IS_WINDOWS: prog = os.path.join(TOR_PLUG_DIR, 'obfsproxy.exe')
        else: prog = os.path.join(TOR_PLUG_DIR, 'obfsproxy.bin')

        self['ClientTransportPlugin'] = 'obfs3 exec %s managed' % (prog)

        self['Bridge'] = [
            'obfs3 169.229.59.74:31493 AF9F66B7B04F8FF6F32D455F05135250A16543C9',
            'obfs3 83.212.101.3:80 A09D536DD1752D542E1FBB3C9CE4449D51298239',
            'obfs3 169.229.59.75:46328 AF9F66B7B04F8FF6F32D455F05135250A16543C9',
            'obfs3 109.105.109.163:47779 4C331FA9B3D1D6D8FB0D8FBBF0C259C360D97E6A',
            'obfs3 109.105.109.163:38980 1E05F577A0EC0213F971D81BF4D86A9E4E8229ED',
        ]

class Obfs4Torrc(BasicTorrc):
    """Configure Obfs4 proxy"""
    def __init__(self):
        super(Obfs4Torrc, self).__init__()

        if IS_WINDOWS: prog = os.path.join(TOR_PLUG_DIR, 'obfs4proxy.exe')
        else: prog = os.path.join(TOR_PLUG_DIR, 'obfs4proxy.bin')

        self['ClientTransportPlugin'] = 'obfs4 exec %s managed' % (prog)

        self['Bridge'] = [
            'obfs4 38.229.1.78:80 C8CBDB2464FC9804A69531437BCF2BE31FDD2EE4 cert=Hmyfd2ev46gGY7NoVxA9ngrPF2zCZtzskRTzoWXbxNkzeVnGFPWmrTtILRyqCTjHR+s9dg iat-mode=1',
            'obfs4 192.95.36.142:443 CDF2E852BF539B82BD10E27E9115A31734E378C2 cert=qUVQ0srL1JI/vO6V6m/24anYXiJD3QP2HgzUKQtQ7GRqqUvs7P+tG43RtAqdhLOALP7DJQ iat-mode=1',
            'obfs4 37.218.240.34:40035 88CD36D45A35271963EF82E511C8827A24730913 cert=eGXYfWODcgqIdPJ+rRupg4GGvVGfh25FWaIXZkit206OSngsp7GAIiGIXOJJROMxEqFKJg iat-mode=1',
        ]

class MeekATorrc(BasicTorrc):
    """Configure meek-amazon"""
    def __init__(self):
        super(MeekATorrc, self).__init__()
        if IS_WINDOWS:
            term_buf = os.path.join(TOR_PLUG_DIR, 'terminateprocess-buffer.exe')
            meek_client = os.path.join(TOR_PLUG_DIR, 'meek-client.exe')
            meek_browser = os.path.join(TOR_PLUG_DIR, 'meek-client-torbrowser.exe')
            self['ClientTransportPlugin'] = 'meek exec %s %s --exit-on-stdin-eof -- %s' % (term_buf, meek_browser, meek_client)
        else:
            meek_client = os.path.join(TOR_PLUG_DIR, 'meek-client')
            meek_browser = os.path.join(TOR_PLUG_DIR, 'meek-client-torbrowser')
            self['ClientTransportPlugin'] = 'meek exec %s -- %s' % (meek_browser, meek_client)
        
        self['Bridge'] = [
            'meek 0.0.2.0:2 url=https://d2zfqthxsdq309.cloudfront.net/ front=a0.awsstatic.com',
        ]

class MeekGTorrc(BasicTorrc):
    """Configure meek-google"""
    def __init__(self):
        super(MeekGTorrc, self).__init__()

        if IS_WINDOWS:
            term_buf = os.path.join(TOR_PLUG_DIR, 'terminateprocess-buffer.exe')
            meek_client = os.path.join(TOR_PLUG_DIR, 'meek-client.exe')
            meek_browser = os.path.join(TOR_PLUG_DIR, 'meek-client-torbrowser.exe')
            self['ClientTransportPlugin'] = 'meek exec %s %s --exit-on-stdin-eof -- %s' % (term_buf, meek_browser, meek_client)
        else:
            meek_client = os.path.join(TOR_PLUG_DIR, 'meek-client')
            meek_browser = os.path.join(TOR_PLUG_DIR, 'meek-client-torbrowser')
            self['ClientTransportPlugin'] = 'meek exec %s -- %s' % (meek_browser, meek_client)

        self['Bridge'] = [
            'meek 0.0.2.0:1 url=https://meek-reflect.appspot.com/ front=www.google.com',
        ]
        print self['ClientTransportPlugin']


def print_bootstrap_lines(line):
    if "Bootstrapped " in line:
        print term.format(line, term.Color.BLUE)

def execute(cmd):
    return os.system(cmd)


def kill_proc(process_name):
    """kill a process"""
    if IS_WINDOWS:
        res = execute("taskkill /t /im %s" % process_name)
        if res != 128: # process not found
            print 'return code: %s: force killing %s' % (res, process_name)
            res = execute("taskkill /f /t /im %s" % process_name)
        return res
    else:
        execute("kill_all %s" % process_name)

def kill_all():
    """clean all processes"""
    if IS_WINDOWS:
        for i in ['tor.exe','terminateprocess-buffer.exe', 'meek-client-torbrowser.exe', 'firefox.exe', 'windump.exe', 'fteproxy.exe', 'obfsproxy.exe', 'meek-client.exe', 'obfs4proxy.exe']:
            kill_proc(i)
    else:
        for i in ['firefox', 'tor', 'Xvfb', 'tcpdump']:
            kill_proc(i)

def kill_tor():
    """clean all processes related with Tor"""
    if IS_WINDOWS:
        for pt in ['tor.exe','terminateprocess-buffer.exe', 'meek-client-torbrowser.exe', 'fteproxy.exe', 'obfsproxy.exe', 'meek-client.exe', 'obfs4proxy.exe']:
            kill_proc(pt)
    else:
        for pt in ["fteproxy.bin", "obfsproxy.bin", "obfs4proxy.bin", "meek-client", "meek-client-torbrowser"]:
            os.popen("pkill -f %s" % pt)

def clear_dns_cache():
    """
    clear DNS cache to make sure the program will issue new DNS 
    before each new connection in Windows. In Ubuntu the system 
    will clear the cache by default. 
    """
    if IS_WINDOWS:
        os.popen("ipconfig /flushdns")
    else:
        pass

def random_sec():
    """generate a random number within a range"""
    # change to  5-15 in practice
    return random.randint(1, 3)


class TorTraceCollector(object):
    """
    Collect the Tor PluggableTransport traces

    :param str pt_name: the code of the PT
    :param int round_no: an ID specified 
    """
    def __init__(self, pt_name, round_no):
        super(TorTraceCollector, self).__init__()
        self.pt = pt_name
        self.IS_NORM = False
        if self.pt == "norm":
            self.IS_NORM = True
        self.round_no = str(round_no)
        self.home_path = os.getcwd()
        self.trace_dir = os.path.join(TRACE_ROOT_DIR, self.round_no)
        
        if not os.path.exists(self.trace_dir):
            os.mkdir(self.trace_dir)

        self.trace_dir = os.path.join(self.trace_dir, self.pt)
        if not os.path.exists(self.trace_dir):
            os.mkdir(self.trace_dir)

        self.profile_dir = os.path.join(TOR_PROFILE_DIR, "profile.default")
        self.profile = self.get_profile()
        self.driver = None
        self.tor_process = None
        self.dump_process = None
        if self.IS_NORM: self.handler = self.collect_normal_trace 
        else:  self.handler = self.collect_tor_trace_with_handshake 

    def get_profile(self):
        profile = FirefoxProfile(self.profile_dir)
        profile.set_preference('startup.homepage_welcome_url', "about:blank")
        profile.set_preference('browser.startup.homepage', "about:blank")
        # profile.set_preference('extensions.firebug.netexport.defaultLogDir', self.netlog_dir)

        #set socks proxy
        profile.set_preference( "network.proxy.type", 1 )
        profile.set_preference( "network.proxy.socks_version", 5 )
        profile.set_preference( "network.proxy.socks", '127.0.0.1' )
        profile.set_preference( "network.proxy.socks_port", 9150)

        profile.set_preference( "network.proxy.socks_remote_dns", True )
        profile.set_preference( "places.history.enabled", False )
        profile.set_preference( "privacy.clearOnShutdown.offlineApps", True )
        profile.set_preference( "privacy.clearOnShutdown.passwords", True )
        profile.set_preference( "privacy.clearOnShutdown.siteSettings", True )
        profile.set_preference( "privacy.sanitize.sanitizeOnShutdown", True )
        profile.set_preference( "signon.rememberSignons", False )
        profile.set_preference( "network.dns.disablePrefetch", True )

        profile.set_preference("extensions.firebug.netexport.pageLoadedTimeout", 10000)
        profile.set_preference("extensions.firebug.netexport.showPreview", False)
        profile.set_preference("extensions.firebug.netexport.alwaysEnableAutoExport", False)
        profile.set_preference("extensions.firebug.DBG_STARTER", False)
        profile.set_preference("extensions.firebug.onByDefault", False)
        profile.set_preference("extensions.firebug.allPagesActivation", "off")
        
        profile.update_preferences()
        return profile

    def driver_init(self):
        """open a selenium web browser"""
        if self.IS_NORM:
            self.driver = webdriver.Firefox()
        else:
            self.driver = webdriver.Firefox(firefox_profile=self.profile)
        self.driver.set_page_load_timeout(PAGE_TIMEOUT)
        # other configurations

    def driver_close(self):
        """close a selenium web browser"""
        self.driver.close()

    def tor_start(self):
        """star a tor process with the specified PT"""
        if self.pt == 'fte':
            config = FteTorrc()
        if self.pt == "obfs3":
            config = Obfs3Torrc()
        if self.pt == "meek-amazon":
            config = MeekATorrc()
        if self.pt == "meek-google":
            config = MeekGTorrc()
        if self.pt == "obfs4":
            config = Obfs4Torrc()

        # the default tor connection timeout is 60
        self.tor_process = stem.process.launch_tor_with_config(
            config = config,
            init_msg_handler = print_bootstrap_lines,
            timeout = TOR_TIMEOUT)

    def tor_end(self):
        """kill the tor process"""
        self.tor_process.kill()

    def dump_start(self, filename):
        """
        start tcpdump (windump)
        :param str filename: the name of the output pcap file
        """
        if IS_WINDOWS:
            cmd = "windump -s 0 -w %s not udp port 1900" % (filename)
            self.dump_process = subprocess.Popen(cmd.split(), shell=False)
        else:
            cmd = "echo '%s' | sudo -S tcpdump -w %s &" % (USER_PASSWORD, filename)
            self.dump_process = subprocess.Popen(cmd, shell=True,  preexec_fn=os.setsid)

    def dump_end(self):
        """kill tcpdump (windump)"""
        if IS_WINDOWS:
            self.dump_process.kill()
            os.kill(self.dump_process.pid, signal.SIGTERM)
        else:
            os.killpg(self.dump_process.pid, signal.SIGINT)
            cmd = "echo '%s' | sudo kill_all -9 tcpdump" % USER_PASSWORD
            self.dump_process = subprocess.Popen(cmd, shell=True,  preexec_fn=os.setsid)

    def pt_clean(self, key):
        for pt in ["fteproxy.bin", "obfsproxy.bin", "obfs4proxy.bin", "meek-client", "meek-client-torbrowser"]:
            os.popen("pkill -f %s" % pt)


    def collect_normal_trace(self, no, url):
        default_url = "about:blank"
        fn = os.path.join(self.trace_dir, "%s_%s_%s.pcap" % (no, self.pt, self.round_no))
        print fn
        self.dump_start(fn)
        time.sleep(random_sec())
        try:
            self.driver.get(url)
        except:
            pass
        time.sleep(random_sec())
        self.driver.get(default_url)
        time.sleep(random_sec())
        self.dump_end()


    def collect_tor_trace_with_handshake(self, no, url):
        default_url = "about:blank"
        fn = os.path.join(self.trace_dir, "%s_%s_%s.pcap" % (no, self.pt, self.round_no))
        print fn
        self.dump_start(fn)
        time.sleep(random_sec())
        self.tor_start()
        time.sleep(random_sec())
        try:
            self.driver.get(url)
        except:
            pass
        time.sleep(random_sec())
        self.driver.get(default_url)
        time.sleep(random_sec())
        self.tor_end()
        time.sleep(random_sec())
        # self.dump_end()
        kill_tor()

        
def get_finished(pt, round_no):
    if not os.path.exists(TRACE_ROOT_DIR):
        os.mkdir(TRACE_ROOT_DIR)
    trace_dir = os.path.join(TRACE_ROOT_DIR, str(round_no))
    if not os.path.exists(trace_dir):
        if IS_WINDOWS:
            raise Exception("You mush create directories %s on Windows" % trace_dir)
        os.mkdir(trace_dir)
    trace_dir = os.path.join(trace_dir, pt)
    if not os.path.exists(trace_dir):
        if IS_WINDOWS:
            raise Exception("You mush create directories %s on Windows" % trace_dir)
        os.mkdir(trace_dir)
    nos = os.listdir(trace_dir)
    nos = [int(v.split("_")[0]) for v in nos]
    return nos

def run_with(pt, domain_list, start, end, round_no):
    turls = open(domain_list).readlines()
    urls = {}

    for v in turls:
        urls[int(v.strip("\n").split(",")[0])] = v.strip("\n").split(",")[1] 
    for tno in get_finished(pt, round_no):
        urls.pop(tno)

    for no in range(start, end):
        if no not in urls:
            continue

        kill_all()
        clear_dns_cache()

        tc = TorTraceCollector(pt, round_no)
        tc.driver_init()
        u = urls[no]
        url = "http://www." + u
        print no, url
        try:
            tc.handler(no, url)
        except:
            f = open("error.log", "a")
            f.write("%s, %s\n" % (no, u))
            f.close()

        if IS_WINDOWS:
            kill_tor()
            tc.driver_close()
        else:
            try:
                tc.tor_end()
            except:
                pass
            kill_tor()
            tc.driver_close()
            os.popen("echo '%s' | sudo rm -rf /tmp/tmp*" % USER_PASSWORD)
        time.sleep(1)
        try:
            tc.dump_end()
        except:
            pass

def test():
    for pt in ["norm", "obfs3", "obfs4", "fte", "meek-google", "meek-amazon"]:
    # for pt in ["norm"]:
    # pt = "meek-amazon"
        run_with("top-1m.csv", pt, 1, 5, 0)

def pt_type_check(v):
    if v not in ["norm", "obfs3", "obfs4", "fte", "meek-google", "meek-amazon"]:
        raise argparse.ArgumentTypeError("Unknown PTs")
    return v 

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-t", "--type", type=pt_type_check, help="name of the support Tor Pluggable Transports, the options are \
        'obfs3', 'obfs4', 'fte', 'meek-google', 'meek-amazon' and 'norm'", required=True)
    parser.add_argument("-d", "--domain", help="path of the input domain list", required=True)
    parser.add_argument("-s", "--start", type=int, help="start ID", required=True)
    parser.add_argument("-e", "--end", type=int, help="end ID", required=True)
    parser.add_argument("-r", "--round", type=int, help="round number", required=True)
    args = parser.parse_args()
    # print args.type, args.domain, args.start, args.end
    run_with(args.type, args.domain, args.start, args.end, args.round)

if __name__ == '__main__':
    main()

