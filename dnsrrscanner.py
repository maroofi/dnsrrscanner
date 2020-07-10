import json
import sys
import os
import time
try:
    import dns.resolver
except: 
    print("You need to have dnspython installed")
    print("pip3 install dnspython")
    exit(1)
#end try
from threading import Thread
from queue import Queue
from threading import Lock
from threading import get_ident
from multiprocessing import cpu_count
import argparse
from argparse import RawTextHelpFormatter


class DNS_RR_Scanner():
    def __init__(self,num_of_threads = None, verbose = False, qtype = 'A'):
        self.qtype_error_msg = "Qtype must be a valid type: A, NS, AAAA, TXT, SOA, MX"
        self.output = None
        self.valid_qtypes = ['AAAA','A','NS','TXT','SOA','MX']
        if not isinstance(qtype,str):
            raise Exception(qtype_error_msg)
        self.qtype = qtype.upper()
        if self.qtype not in self.valid_qtypes:
            raise Exception(qtype_error_msg)
        self.load_queue = Queue()
        self.st_time = time.time()
        self.global_lock = Lock()
        self.is_debug = verbose
        self.num_of_threads = num_of_threads
        if self.num_of_threads == None:
            self.num_of_threads = cpu_count() * 20
    # end def
    
    def get_resource_record(self,domain,q_type):
        """
            Returns the Qtype record of the domain name.
        """
        try:
            tm = time.strftime("%Y-%m-%d %H:%M:%S",time.localtime())
            result = dns.resolver.query(domain,rdtype=q_type,lifetime=10)
            return json.dumps({'name':domain,'time':tm,'status':"NOERROR",'answers':[x.to_text() for x in result]})
        except dns.resolver.NoAnswer:
            return json.dumps({'name':domain,'time':tm,'status':'NOANSWER','answers':[]})
        except dns.resolver.NXDOMAIN:
            return json.dumps({'name':domain,'time':tm,'status':'NXDOMAIN','answers':[]})
        except dns.resolver.Timeout:
            return json.dumps({'name':domain,'time':tm,'status':'TIMEOUT','answers':[]})
        except Exception as e:
            return json.dumps({'name':domain,'time':tm,'status':'EXCEPTION','answers':[]})
    # end def
    
    def thread_callback(self,result,*args, **kwargs):
        """
            You can rewrite this method to get the result from each thread.
            This method is safe in terms of race conditioning since we call it inside
            the lock.
            Based on the result you get as parameter, you can push the load back to the queue
            by calling 'add_task(load)' method and then return False to re-evaluate the 'load'.
        """
        self.output.write(result + "\n")
    # end def
    
    def run_thread(self,load):
        try:
            return self.get_resource_record(load,self.qtype)
        except Exception as e:
            tm = time.strftime("%Y-%m-%d %H:%M:%S",time.localtime())
            return json.dumps({'name':load,'time':tm,'status':'EXCEPTION','answers':[]})
        return (False,None)
    # end def
    
    def _internal_run_method(self,*args,**kwargs):
        "Do not call this method directly. This is an internal implementation."
        while True:
            if self.load_queue.empty():
                return True
            load = self.load_queue.get()
            try:
                # Run user-defined run_thread method
                result = self.run_thread(load)
                with self.global_lock:
                    cb_result = self.thread_callback(result)
            except Exception as e:
                return False
            if self.load_queue.empty():
                return True
        #end while
    #end def
            
    def start(self):
        workerlist = list()
        for i in range(self.num_of_threads):
            workerlist.append(Thread(target = self._internal_run_method))
        for worker in workerlist:
            worker.daemon = True
            worker.start()
        [worker.join() for worker in workerlist]
    #end def

    def add_task(self,task):
        self.load_queue.put(task)
        return True
    #end def
#end class

def main():
    VERSION = '0.1'
    AUTHOR = 'S.MAROOFI'
    AUTHOR_EMAIL = 'maroofi@gmail.com'
    desc = '''DNS resource record scanner.\nWritten by {} ({})\nVersion {}'''.format(AUTHOR,AUTHOR_EMAIL,VERSION)

    parser = argparse.ArgumentParser(description=desc,formatter_class=RawTextHelpFormatter)    
    
    parser.add_argument('-v','--version',
                        action='version',
                        version='DNS resource record scanner. Use --help to see logn description.'.format(VERSION)
    )

    parser.add_argument('-o','--output',
                        action='store',
                        default='',
                        dest='output_file',
                        help="Specifies the output file to store the final results"
    )
    
    parser.add_argument('-t','--threads',
                        action='store',
                        default='',
                        dest='num_of_threads',
                        help="Specifies the number of threads. Default is (# of CPU(s) * 20)"
    )
    parser.add_argument("file",
                        action='store',
                        default=sys.stdin,
                        nargs='?',
                        help="Input file (i.e., list of domain names).")   
       
    parser.add_argument('-n', '--nameserver',
                        action='store',
                        dest='nameserver',
                        default='',
                        help='Nameserver to use (IP address) as the resolver (default is os resolver)'
    )
    parser.add_argument('-q', '--query',
                        action='store',
                        dest='qtype',
                        default='A',
                        help='Query type: A, NS, AAAA, TXT, SOA, MX'
    )
    pargs = parser.parse_args(sys.argv[1:])
    return pargs
# end main

def open_file(filename,mode):
    if filename == sys.stdin:
        return sys.stdin
    if filename == sys.stdout:
        return sys.stdout
    else:
        return open(filename,mode)
        
if __name__ == "__main__":
    pargs = main()
    input_file = open_file(pargs.file,'r')
    output_file = sys.stdout if pargs.output_file == '' else pargs.output_file
    output_file = open_file(output_file,'w')
    num_of_threads = None
    if pargs.num_of_threads != '':
        try:
            num_of_threads = int(pargs.num_of_threads)
            if num_of_threads < 1: raise Exception("Wrong number of threads")
        except:
            print("Error: Number of threads must be an integer > 0")
            exit(-1)
    # end if
    if pargs.nameserver != '':
        dns.resolver.default_resolver = dns.resolver.Resolver(configure=False)
        dns.resolver.default_resolver.nameservers = [pargs.nameserver]
    #end if

    qtype = pargs.qtype
    a = DNS_RR_Scanner(num_of_threads = num_of_threads,verbose = verbose,qtype = qtype)
    a.output = output_file
    for line in input_file:
        line = line.strip()
        if line == '':continue
        a.add_task(line)
    a.start()

