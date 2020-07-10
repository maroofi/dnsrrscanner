# dnsrrscanner
Multi-Thread Python 3 DNS Resource Record Scanner

### Installation

```bash
git clone https://github.com/maroofi/dnsrrscanner.git
cd dnsrrscanner
pip3 install -r requirements.txt
```

### Usage

```bash
# to see the help
python3 dnsrrscanner.py -h

# scan google.com for mx record
echo google.com | python3 dnsrrscanner.py -q mx

# scan the 'A' record of all the domains in input.txt
# save the output to output.txt
python3 dnsrrscanner.py -q A -o output.txt input.txt

# scan with 200 threads and using google nameserver for TXT records
python3 dnsrrscanner.py -q TXT -o output.txt -t 200 -n 8.8.8.8
```

#### Note
1. The default number of thread is: \<number of CPU\> * 20
