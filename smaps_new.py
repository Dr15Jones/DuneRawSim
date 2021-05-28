#!/usr/bin/env python

import sys, os, time, commands
from optparse import OptionParser
from multiprocessing import Process

# This script will collect and collate all of the data for one PID in the /proc filesystem.
# What we want is the amount of Private/Shared Code/Data ... so there are four outputs.
# We may also measure the amount of P/S using the permissions instead of the Private_Clean, etc. measurements
# We may also obtain the name of the library allocating the memory

# Keep in mind that the page size is obtained by 
# > getconf PAGESIZE 
# and the default is 4096, or 4Kb, or 1000 in Hex, which is how the size is displayed in smaps header line

DEFAULT_USERNAME = 'esmith'

def permission( path, username ) :
    '''
    Check if user "username" has permssion to read the smaps file at path
    '''
    stat, out = commands.getstatusoutput( 'ls -la %s'%(path) )
    if stat : 
        print "ERROR in using ls to read details at %s"%(path)
        return False
    else : 
        fields = out.split()
        perms = fields[0]
        user  = fields[2]
        group = fields[3]
        # print "Permissions/user/group : ", perms, user, group
        if username == user : 
            # print "Permission OK!"
            return True
        else : 
            # print "User %s has no access to smaps file : %s"%(username, out)
            return False

class Pid : 
    def __init__( self, pid, name=None, head=False ) :
        self.pid = pid
        self.path = '/proc/%s/smaps'%(self.pid)
        if name : self.name = name
        else    : self.getProcessName()
        if head : self.ppid = 0
        else    : self.ppid = self.getPPID()
        
        stat, out = commands.getstatusoutput( 'whoami' )
        if not stat : self.username = out
        else : self.username = "Undetermined"
        
        self.permission = False   
        # Is there a smaps file at this path?
        if os.path.exists(self.path) :
            self.valid = True
            self.permission = permission(self.path, self.username) 
        else :
            self.valid = False
                   
        
    def getProcessName( self ) : 
        stat, out = commands.getstatusoutput('ps %s | grep :'%(self.pid))
        # print 'DETERMINING PROCESS NAME : ', out
        # Extract the name, including arguments        
        try    : self.name = ' '.join(out.split()[4:])
        except : self.name = 'Not Determined'
    def getPPID( self ) : 
        stat, out = commands.getstatusoutput( 'ps l %s | grep -'%(self.pid) )
        try    : ppid = int(out.split()[3]) # ; print 'Parent Pid is : ', ppid
        except : ppid = 'Not Determined'    # ; print 'No PPID found'
        return ppid
    def check( self ) :
        if os.path.exists( self.path ) :         
            try    : 
                f = open(self.path, 'r')
                f.close()
                return True
            except :
                return False                
        else : 
            return False

class smap :
  # a smap is a class representing one block of data in the /proc/PID/smaps file
  # There's a header line, and then N lines of data
  # Example : 
  # 
  #
  # 3c64e15000-3c64f15000 ---p 00015000 08:02 1888169                        /usr/lib64/libgssapi_krb5.so.2.2
  # Size:              1024 kB
  # Rss:                  0 kB
  # Shared_Clean:         0 kB
  # Shared_Dirty:         0 kB
  # Private_Clean:        0 kB
  # Private_Dirty:        0 kB
  # 
  def __init__( self, lines=None ) : 
    if not lines:
      self.address     = None
      self.permissions = None
      self.module      = None
      self.shared      = False
    else :
      header = lines[0].split()                         
      self.address     = header[0]
      self.permissions = header[1]
      if self.permissions[-1] == 's' : self.shared = True
      self.module      = header[-1]
      for line in lines[1:]:
        elems = line.split()
        if elems[0][:-1] != 'VmFlags':
            setattr(self, elems[0][:-1], int(elems[1]))
  def __iadd__(self, map):
    for k in dir(map):
      if k[0] == '_' or k in ('address', 'permissions', 'module' ) : continue
      if not hasattr(self, k) : setattr(self, k, getattr(map ,k))
      else                    : setattr(self, k, getattr(self, k) + getattr(map, k))
    return self
  def __repr__(self):
    return 'smap: %s'% (str(self.__dict__),)
    
    
class SmapsFile :
    def __init__( self, pidclass ):
      self.pid  = pidclass.pid
      self.name = pidclass.name
      self.ppid = pidclass.ppid
      self._pid = pidclass
      # fill out the smaps with data
      # It will acquire the attributes : 
      # - all  : all.Private_Clean , all.Private_Dirty    
      # - code : code.Private_Clean, code.Private_Dirty
      # - data : data.Private_Clean, data.Private_Dirty
      self.valid = self.read() 
      # Collate the data into meaningful figures
      self.collate()
        
    def refresh( self ) : 
        r = self.read()
        if r : self.collate()
        else : self.zero()
        
    def read( self ):
        try :
            self.lines    = open( '/proc/%s/smaps'%(self.pid), 'r' ).readlines()
        except IOError : 
            # print '\tsmaps file : /proc/%s/smaps (for %s) not found in /proc folder!\n\tExiting...\n'%(self.pid, self.name)
            self.smaps = []
            return None
        self.blockLen = self.blockLength(self.lines)
        self.smaps    = [smap(self.lines[i:i+self.blockLen]) for i in range(0,len(self.lines),self.blockLen)]
        return 1
  
    def blockLength( self, lines ):         
        # return the length (in lines) of a single block entry in smaps
        # first line is a header line : count the number of fields
        headLineFields = len(self.lines[0].split())
        # print 'Header line has fields : %i'%(headLineFields)
        ct = 0
        for l in self.lines[1:] :
          ct += 1                                             
          if len(l.split()) == headLineFields : 
              return ct
          elif ct == 100 : # crude error catch
              raise AttributeError , "ERROR: Should have found a second header line, quitting smaps"
  
    def sum( self, permissions=() ):
        # Sum the memory values for all smaps with the specified Permissions
        # for example, sum over all smaps with permissions=('r-xp')
        #  = readable, executable, private (i.e. code)
        # Default permissions=() sums all of the data in the smaps file
        t_smap = smap()
        for s in self.smaps:
            if permissions and s.permissions not in permissions: continue
            t_smap += s
        return t_smap 
        
    def zero( self ) : 
        self.privCode = 0
        self.sharCode = 0
        self.privData = 0
        self.sharData = 0
        self.Rss  = 0
        self.Size = 0
        
    def collate( self ) : 
        all  = self.sum( )
        code = self.sum(permissions=('r-xp',))
        if hasattr( all, "Private_Clean" ) and hasattr( code, "Private_Clean" ) : 
            self.privCode = code.Private_Clean + code.Private_Dirty
            self.sharCode = code.Shared_Clean  + code.Shared_Dirty
            self.privData = all.Private_Clean  + all.Private_Dirty  - self.privCode
            self.sharData = all.Shared_Clean   + all.Shared_Dirty   - self.sharCode
            self.Rss  = all.Rss
            self.Size = all.Size 
        else :
            self.zero()
        
    def collectLibraries( self ) : 
        d = {}
        for s in self.smaps : 
          if s.module in d.keys() :
              d[s.module]['Size'] += s.Size
              d[s.module]['Rss' ] += s.Rss
              d[s.module]['Shared_Clean' ] += s.Shared_Clean
              d[s.module]['Shared_Dirty' ] += s.Shared_Dirty
              d[s.module]['Private_Clean'] += s.Private_Clean
              d[s.module]['Private_Dirty'] += s.Private_Dirty
          else :
              d[s.module] = {'Size':s.Size, 'Rss':s.Rss, 'Shared_Clean':s.Shared_Clean, 
                            'Shared_Dirty':s.Shared_Dirty, 'Private_Clean':s.Private_Clean, 'Private_Dirty':s.Private_Dirty}
        self.libdict = d
        
    def displayLibraries( self, sort='Rss' ) : 
        self.collectLibraries()
        self.sortLibraries( field=sort )
        maxlen = max( [len(k) for k in self.libdict.keys()] )
        # print self.order, self.libdict.keys()
        for k in self.order :
            extra = ' '*(maxlen-len(k))
            print k+extra, self.libdict[k]
            
    def sortLibraries( self, field='Rss') : 
        arr = [ (k, self.libdict[k][field]) for k in self.libdict.keys() ]
        arr.sort(cmp=self.mycmp)
        self.order = list( [a[0] for a in arr] )
        
    def mycmp( self, tupa, tupb ) :
        key = 1
        if   tupa[key] > tupb[key] : return -1
        elif tupa[key] < tupb[key] : return  1
        else : return 0
    
    def __repr__( self ) : 
        string = '%10s %i - Rss : %i - Size : %i - Code(priv/shar) : %i / %i - Data(priv/shar) : %i / %i '%(self.name, int(self.pid), self.Rss, self.Size, self.privCode, self.sharCode, self.privData, self.sharData)
        return string
        
    def write( self, outfile ) :
        string = '%s\t%i\t%i\t%i\t%i\t%i\t%i\t%i\n'%(self.name,int(self.pid),self.Rss,self.Size,self.privCode,self.sharCode,self.privData, self.sharData)
        outfile.write( string )

def getProcesses( pidList=[] ):
    """Takes a sequence of strings which are the output lines of "ps aux",
      and returns a sequence of integer pids that correspond to the
      current user's processes in the form of a dictionary: d[pid]=processName 
      If a pidList is present, Pids are removed or added as necessary
      If a parent is present, all the returned Pids must have either pid or ppid == parent"""
    try :  
        stat, username = commands.getstatusoutput('whoami')
        # print 'Username %s obtained from whoami command'%(username)
    except :
        username = DEFAULT_USERNAME
        print 'WARNING : using "whoami" to obtain user name failed!!!  Using DEFAULT_USERNAME from smaps script'
    status, output = commands.getstatusoutput('ps aux | grep %s'%(username))
    # print 'Output of ps au| grep %s : '%(username) , output
    if os.WIFEXITED(status) and os.WEXITSTATUS(status) == 0 :      
        lines = output.splitlines()                                 
    else : lines = None
    
    my_pid   = os.getpid()   # gets pid of currently running smaps process
    
    # first, check that any in update are still alive
    gone = []
    for p in pidList : 
        if p.check() : pass
        else         : gone.append(p)
    [ pidList.remove(g) for g in gone ]
    
    existing = [ p.pid for p in pidList ]
    for l in lines:                                               
        fields = l.split() 
        pid = int( fields[1] )                                     
        if pid == my_pid : continue
        path = '/proc/%s/smaps'%(pid)
        if os.path.exists(path) :
            if pid in existing : pass
            else : pidList.append( Pid(pid) )
    # print '-'*60
    # for p in pidList : print p.pid
    # print '-'*60 
    return pidList
      

def run( pid ) :
    p = Pid(pid)
    if not p.valid :
        print '\t%s %s smaps file : Invalid PID\n'%(p.name, p.pid)
        sys.exit(0)
    if not p.permission :
        print '\t%s %s smaps file : Permission Denied\n'%(p.name, p.pid)
        sys.exit(0)
    else :
        instance = SmapsFile(p)   # one snapshot of a /proc/PID/smaps file      
        print '\tProcess Name : %s'%(instance.name)
        print '\tPrivate Code : %i'%(instance.privCode)
        print '\tShared  Code : %i'%(instance.sharCode)
        print '\tPrivate Data : %i'%(instance.privData)
        print '\tShared  Data : %i'%(instance.sharData)
        print '\t-----------------'
        print '\tVSize        : %i'%(instance.Size)
        print '\tRSS          : %i'%(instance.Rss)
        print '\t-----------------'    
        # print instance
        # instance.displayLibraries(sort='Rss')    
    
def snapShot() :
    procs = getProcesses()
    
    totalRss  = 0
    totalSize = 0
    line  = '-'*100
    dline = '='*100
    print dline
    print 'Process Summary at : %s'%(time.ctime())
    print line
    for p in procs : 
        if p.permission : 
            s = SmapsFile( p )
            totalRss  += s.Rss
            totalSize += s.Size
            print '\t', s
        else :
            print '\t%s %s smaps file : Permission Denied'%(p.name, p.pid)
          
    print line
    
    mb = 1024
    if   totalSize > mb : tsz = str('%5.2f Mb'%(totalSize/float(mb)))
    else : tsz = str('%i Kb'%(totalSize))
    print '\tTotal Size : %s'%(tsz)    
    if   totalRss > mb : trss = str('%5.2f Mb'%(totalRss/float(mb)))
    else : trss = str('%i Kb'%(totalRss))
    print '\tTotal Rss  : %s'%(trss)

    print dline   
    

def updateSmaps ( plist, slist, parent=None ) : 
    procs = getProcesses( plist )
    currentpids = []
    for p in procs :
        if p.permission :
            currentpids.append(p.pid)
    gone = []
    # remove old ones
    for s in slist : 
        if s.pid not in currentpids : gone.append(s)
    [ slist.remove(g) for g in gone ] 
    # now add new ones
    currentsmaps = [s.pid for s in slist ]
    for c in currentpids : 
        if c not in currentsmaps :
            if c.permission : 
                slist.append(SmapsFile(Pid(c)))
    return procs, slist 
      
def updateProfile( plist, parent, slist ) :

    plist   = getProcesses( plist )      # update the list of processes
    # print 'Updating Profile : pidlist is : ', [ p.pid for p in plist  ]
    active  = procTree( parent, plist )  # discard those which are not part of the monitored process
    # print 'Updating Profile : active are : ', [ p.pid for p in active ]

    # remove smapsFiles for processes which had died
    gone = []
    for s in slist : 
        if s._pid.check() : pass
        else : gone.append(s)
    [ slist.remove(g) for g in gone ]

    # add new smapsFiles for freshly forked processes
    slistpids  = [ s.pid for s in slist  ]        
    for a in active : 
      if a.pid in slistpids : pass
      else : slist.append( SmapsFile(a) )
    
    # Finally, refresh the data and return
    [ s.refresh() for s in slist ]      
    # print 'slist is for pids : ', [s.pid  for s in slist]
    # print 'with parents      : ', [s.ppid for s in slist]
    return slist
    
def procTree( parent, plist ) :
    # return a list containing the specified parent, and all 
    # subprocesses, including sub-sub-processes and so on 
    allpids = [ parent.pid ]
    kept = [parent]
    while True :
      gone = []
      for p in plist :
        if p.ppid in allpids : 
          allpids.append(p.pid)
          kept.append(p)
          gone.append(p)
      if gone : [ plist.remove(g) for g in gone ]
      else : break  # no more pids to add, this is the termination criteria
    return kept
    
def monitor( pid, nIters, outputFile ) : 
    # monitor one process for N iterations
    timestep = 1
    f = open( '%s'%(outputFile), 'w' )
    f.write( "#NAME\tPID\tRSS\tSIZE\tPRIV_CODE\tSHAR_CODE\tPRIV_DATA\tSHAR_DATA\n" )    
    p = Pid( pid )
    sf = SmapsFile( p )
    if not sf.valid : 
        print '\tWARNING : Could not read a valid /proc/%i/smaps file!\n'%(pid)
        print '\t        : Closing output file'
        f.close()
        print '\t        : Exiting smaps with exit code 0' 
        sys.exit(0)
    for i in xrange(nIters) :
       f.write('# %s\n'%(time.ctime()))
       sf.write(f)
       time.sleep(timestep)
       sf.refresh()
    f.close()
    print 'Single Process Monitor Complete'    
    
def monitorAll( nIters, outputFile ) : 
    # monitor all processes for N iterations
    timestep = 1
    pids = getProcesses()
    f = open( '%s'%(outputFile), 'w' )
    f.write( "#NAME\tPID\tRSS\tSIZE\tPRIV_CODE\tSHAR_CODE\tPRIV_DATA\tSHAR_DATA\n" )    
    allsmaps = []
    for p in pids : 
        if p.permission : 
            allsmaps.append( SmapsFile(p) )

    for i in xrange(nIters) :
        totRss = 0 ; totSz  = 0
        f.write('# %s\n'%(time.ctime()))
        for s in allsmaps : s.write(f) ; totRss += s.Rss ; totSz += s.Size
        f.write( '# Totals(Rss/Size) : %i\t%i\n\n'%(totRss, totSz) )
        time.sleep( timestep )
        updateSmaps(pids, allsmaps)
        for s in allsmaps : s.refresh() 
    f.close()
    print 'Monitor Complete'   

    
def runCommand( commandString ) : 
    # simple method which can be forked off on a separate process
    # executes a given command string
    os.system( commandString )
    
def monitorCommand( command, filename=None, timestep=None ) :
    # first : issue the command
    #         and collect the initial details
    p = Process(target=runCommand, args=(command,))
    p.start()
    worker = int(p.pid)
    parentProc = Pid(worker)
    print 'SMAPS : Command issued on Process %i, executed on Process %i'%( parentProc.ppid, parentProc.pid )

    # second : prepare the output file    
    f    = open( filename, 'w' ) 
    f.write( "#COMMAND : %s\n"%(command) )
    f.write( "#NAME\tPID\tRSS\tSIZE\tPRIV_CODE\tSHAR_CODE\tPRIV_DATA\tSHAR_DATA\n" )
    
    # third : set up the smaps monitoring details
    #         including finding all subprocesses associated with the lead process
    pids     = [ parentProc ]
    allsmaps = [ SmapsFile(parentProc) ]
    allsmaps = updateProfile( pids, parentProc, allsmaps )
    
    # fourth : the monitoring loop
    #          write a line for each process in the format :
    #          name - pid - rss - size - privCode - sharCode - privData - sharData
    #          Also write the time, and Totals at beginning and end of block
    #          And update the processes data at end of each iteration
    while True :
        totRss = 0 ; totSz  = 0
        f.write('# %s\n'%(time.ctime()))
        for s in allsmaps : 
            s.write(f)
            totRss += s.Rss
            totSz += s.Size
        f.write( '# Totals(Rss/Size) kB : %i\t%i\n\n'%(totRss, totSz) )        
        time.sleep(timestep)
        if parentProc.check() : pass
        else : print 'Parent Process has terminated' ; break 
        allsmaps = updateProfile( pids, parentProc, allsmaps )
    
    # Close output file and complete
    f.close()
    print 'Process Monitor Complete for Commmand  : %s'%(command)    
    
    
def displayOptions( opts ) :
    print 'Options Summary'
    if opts.command : 
      print '\tContinuous Switch : Not used; command mode'
    else : 
      print '\tContinuous Switch : %s'%(opts.cts)      
    print '\tOutput Filename   : %s'%(opts.filename)
    if not opts.command : 
        if opts.pid :  
            print '\tPID to monitor    : %i'%(opts.pid)
        else : 
            print '\tPID to monitor    : %s (Monitoring existing processes)'%(None) 
    if opts.command : 
        print '\tCommand provided  : %s'%(opts.command)
    else : 
        print '\tCommand provided  : %s (Monitoring existing processes)'%(opts.command)    
    print '\ttimestep          : %5.2f'%(opts.timestep)
    if not opts.command : 
        print '\titerations        : %i'%(opts.iters)
    else : 
        print '\titerations        : Command mode - will monitor until completion'
    print '\n'

if __name__ == '__main__' :
    parser = OptionParser()
    parser.add_option( "-C", "--command"   , action="store", type="string", dest="command" , default=None,
                        help='Specify a command (in quotation marks) to monitor.  Smaps automatically follows the command until completion, including forked subprocesses.  Automatically overrides -c, -p, -i options. Example : ./smaps.py -C "python someScript.py"')    
    parser.add_option( "-f", "--file"      , action="store", type="string", dest="filename", default='smaps_default_output.log',
                        help="Specify an output file for the continuous monitoring.  (Default=smaps_default_output.log)" )                            
    parser.add_option( '-c', "--continuous", action='store_true',           dest='cts'     , default=False,
                        help="Continuous switch.  Sets smaps running in continuous monitoring mode.  Runs for N iters (default=5, see -i option) Directs output to log file (default=smaps_default_output.log, see -f option)" )
    parser.add_option( "-p", "--pid"       , action="store", type="int"   , dest="pid"     , default=None,
                        help="Specify a process ID to follow (will be used as an integer). (Default=None : all processes followed)" )    
    parser.add_option( "-i", "--iters"     , action="store", type="int"   , dest="iters",    default=5,
                        help="Integer specifying the number of iterations for a continuous smaps monitoring run (default=5)" )  
    parser.add_option( "-t", "--timestep"  , action="store", type="float" , dest="timestep", default=1.0,
                        help="Float specifyting the smaps continuous monitoring timestep (default=1.0)" )                                        
    
    opts, args = parser.parse_args()
    
    if opts.command : 
        print '-'*80
        print '\tsmaps.py Command Mode : %s'%(opts.command)
        print '-'*80    
        displayOptions(opts)
        monitorCommand( opts.command, opts.filename, opts.timestep )
        print 'smaps.py complete'
        sys.exit(0)
                
    if opts.cts : 
        if opts.pid : 
            displayOptions( opts )
            monitor( opts.pid, opts.iters, opts.filename )
        else        : 
            displayOptions( opts )
            monitorAll( opts.iters, opts.filename )
    else  :
        if opts.pid : 
            print '\n'+'-'*80
            print '\tSingle Snapshot : Process %i at %s'%(opts.pid, time.ctime())
            print '-'*80
            run( opts.pid )
        else        : 
            print '\n'+'-'*80
            print '\tSingle Snapshot : All processes'
            print '-'*80
            snapShot()
