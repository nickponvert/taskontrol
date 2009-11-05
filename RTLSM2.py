#!/usr/bin/env python

'''
Create a new RTLinux state machine handle
based on .../Modules/@RTLSM2/RTLSM2.m

Protocol with FSM server:
Command, NumberOfOutpuLines, OK, Notes
'NOOP',                 0,   1,   No operation
'VERSION',              1,   1,   Request version of server
'CLIENTVERSION %u',     0,   1,   Send version of client
'SET STATE MACHINE %d', 0,   1,   Define state machine ID
'INITIALIZE',           0,   1,   Initialize state machine
'RUN',                  0,   1,   Resume state machine
'HALT',                 0,   1,   Pause the state machine

 


To fix:
- Sometimes it will give raise 'timeout' exception


Author: Santiago
'''

import string
VERBOSE = True

def verbosePrint(msg):
    if(VERBOSE):
        print(msg)

def UrlEncode(onestring):
    # FIX: Check validity of input 'UrlEncode only works on strings!'
    out = ''
    for xl in onestring:
        if (((xl >= 65)  and (xl <= 90)) or
            ((xl <= 57)  and (xl >= 48)) or
            ((xl <= 122) and (xl >= 97))):
            out += xl
        else:
            out += '%%%02x'%xl

class orouting:
    def __init__(self,type='',data=''):
        self.type = type
        self.data = data

class sm:
    '''
    Create a new RTLinux state machine that connects to the state
    machine server running on host, port.  Since a state machine
    server can handle more than one virtual state machine, fsm_id
    specifies which of the 6 state machines on the server to use.  See
    method GetStateMachine() for more details.

    The new state machine will have the following default properties:
    Output Routing:
        'type': 'dout', 'data': '0-15'
        'type', 'sound', 'data', str(which_state_machine)
    Input Events: 6

    The sm will not have any SchedWave matrix, or any state matrix.
    '''
    def __init__(self, host='localhost', port=3333, fsm_id=0):
        self.MIN_SERVER_VERSION = 220080319  # Update this on protocol change
        self.host = host
        self.port = port
        self.fsm_id = fsm_id
        self.in_chan_type = 'ai'             # Use analog input for input
        self.sched_waves = [] #zeros(0,8)    # Default to no scheduled waves
        self.sched_waves_ao = [] #cell(0,4)  # Default to no ao sched waves
        self.input_event_mapping = []        # Written-to by SetInputEvents
        self.ready_for_trial_jumpstate = 35  

        # 'ext' means sound
        self.output_routing = [ orouting(type='dout',data='0-15'),
                                orouting(type='ext',data=str(self.fsm_id)) ]

        self.handleFSMClient = FSMClient(self.host, self.port);
        self.handleFSMClient.connect()

        self.ChkConn()
        self.ChkVersion()
        self.SetStateMachine();
        self.SetInputEvents(6, 'ai') # 6 input events, two for each nosecone


    def ChkConn(self):
        '''Check connection to FSM server
           This should probably be implented by catching exceptions.
           And it should not repeat code from DoSimpleCmd+ReceiveOK
        '''
        verbosePrint('Checking connection to FSM server')
        self.DoQueryCmd('NOOP')

    def ChkVersion(self):
        verbosePrint('Checking version of FSM server')
        verstr = self.DoQueryCmd('VERSION')
        ver = int(verstr.split()[0])
        if (ver >= self.MIN_SERVER_VERSION):
            okversion = True
            verbosePrint('FSM server protocol version %s\n'%verstr.split('\n')[0])
        else:
            # --- FIX: This should raise an exception --
            okversion = False
            verbosePrint('The FSM server does not meet the minimum protocol'+\
                  ' version requirement of %u'%self.MIN_SERVER_VERSION)
        self.DoQueryCmd('CLIENTVERSION %u'%self.MIN_SERVER_VERSION)

    def SetStateMachine(self):
        '''
        Assign an ID on the FSM server to the current state machine.

        The ID is a value from 0 to 5 to indicate which of the 6 state
        machines on the FSM server we are going to use.  It is
        important to also make sure the number of the state machine
        corresponds to the number of the soundcard used for sound
        triggering.
        '''
        self.DoQueryCmd('SET STATE MACHINE %d'%self.fsm_id)

        '''
    def DoSimpleCmd(self,cmd):
        self.ChkConn()
        self.handleFSMClient.sendString(cmd+'\n')
        self.ReceiveOK(cmd)
        '''

    def ReceiveOK(self,cmd,result):
        if result[-3:]=='OK\n':
            verbosePrint('Reveiced OK after %s'%cmd)
        else:
            # --- FIX: This should raise an exception --
            verbosePrint('WARNING: RTLinux FSM Server did not send OK after %s command.'%cmd)
            verbosePrint('RESULT: %s'%result)

    def SetInputEvents(self,val,channeltype):
        ### FIX check .../Modules/@RTLSM2/SetInputEvents.m for what should go here
        # Check validity of 'val': positive scalar or ?
        # Check validity of 'channeltype': either 'ai' or 'dio'
        '''
        From .../Modules/@RTLSM2/SetInputEvents.m 
        Specifies the input events that are caught by the state
        machine and how they relate to the state matrix.
        The first simple usage of this function just tells the 
        state machine that there are SCALAR number of input
        events, so there should be this many columns used in the
        state matrix for input events.  The last parameter to 
        these function(s) is a string specifying either: 'ai' or
        'dio'.  The string 'ai' signifies we are monitoring AI
        lines for input events.  'dio' signifies we are monitoring
        DIO lines for input events.  (All other strings will
        generate an error, of course.)

        The second usage of this function actually specifies how
        the state machine should route physical input channels to 
        state matrix columns.  Each position in the vector 
        corresponds to a state matrix column, and the value of 
        each vector position is the channel number to use for that
        column.  Positive values indicate a rising edge event, and
        negative indicate a falling edge event (or OUT event). A
        value of 0 indicates that this is a 'virtual event' that
        gets its input from the Scheduled Wave specification.

        So [1, -1, 2, -2, 3, -3] tells the state machine to route
        channel 1 to the first column as a rising edge input
        event, channel 1 to the second column as a falling edge
        input event, channel 2 to the third column as a rising
        edge input event, and so on.  Each scalar in the vector
        indicates a channel id, and its sign whether the input
        event is rising edge or falling edge.  Note that channel
        id's are numbered from 1, unlike the internal id's NI
        boards would use (they are numbered from 0), so keep that
        in mind as your id's might be offset by 1 if you are used
        to thinking about channel id's as 0-indexed.
        
        The first usage of this function is shorthand and will
        create a vector that contains SCALAR entries as follows:
        [1, -1, 2, -2, ... SCALAR/2, -(SCALAR/2) ] 

        Note: this new input event mapping does not take effect
        immediately and requires a call to SetStateMatrix().
        '''
        if type(val)==type(0):
            # Create a vector of val entries [1,-1, 2,-2,...]
            f = lambda x : (x/2+1)*(2*(x%2)-1)
            val = map(f,range(10))
        # Assign vector of input events
        self.input_event_mapping = val
        self.in_chan_type = channeltype


    def DoQueryCmd(self,cmd):
        self.handleFSMClient.sendString(cmd+'\n')
        result = self.handleFSMClient.readLines()
        self.ReceiveOK(cmd,result)
        '''
        --- SHOULD I SPLIT LINES HERE? ---
        results = lines.splitlines()
        for ind in results: print results
        if results[-1]=='OK':
            print results
        else:
            print 'WARNING: FSM did not return OK at the end of query: %s'%cmd
        '''
        return result

    def Initialize(self):
        '''
        Clear all variables, including the state matrices, and
        initializes the state machine.

        Initialize() does not start the StateMachine running.  It is
        necessary to call Run() to do that.
        '''
        self.DoQueryCmd('INITIALIZE')

    def Run(self):
        '''
        Resume a halted StateMachine, so that events have an effect
        again.

        After an Initialize(), Run() starts the machine in state
        0. After a Halt(), Run() restarts the machine in whatever
        state is was halted. Note that calling Run() before the state
        matrices have been defined produces undefined behavior and
        should be avoided.
        '''
        self.DoQueryCmd('RUN')

    def Halt(self):
        '''
        Pauses the StateMachine, putting it in a halted state.

        In this state, input events do not have any effect and state
        transitions are not made.  Variables are not cleared, however,
        and so they can be read by other programs.
        Calling Run() will resume a halted state machine.
        '''
        self.DoQueryCmd('HALT')

    def SetStateMatrix(self, state_matrix, pend_sm_swap=False):
        '''
        Define the state matrix that governs the control algorithm
        during behavior trials.

        The matrix is M x N, where M is the number of states (so each
        row corresponds to a state) and N is the number of input
        events + output events per state.
        This state_matrix can have nearly unlimited rows (i.e.,
        states), and has a variable number of columns, depending on
        how many input events are defined.
        To specify the number of input events, see SetInputEvents().
        The default number of input events is 6 (CIN, COUT, LIN, LOUT,
        RIN, ROUT).  In addition to the input event columns, the state
        matrix also has 4 or 5 additional columns:
         TIMEOUT_STATE    TIMEOUT_TIME    CONT_OUT    TRIG_OUT
         and the optional SCHED_WAVE.

        The second usage of this function specifies an optional flag.
        If the flag is True, then the state machine will not swap
        state matrices right away, but rather, will wait for the next
        jump to state 0 in the current FSM before swapping state
        matrices.  This is so that one can cleanly exit one FSM by
        jumping to state 0 of another, and thus have cleaner
        inter-trial interval handling.

        Notes:
        - The part of the state matrix that is being run during
          intertrial intervals should remain constant in between any
          two calls of Initialize()
        - SetStateMatrix() should only be called in-between trials.
        '''

        # Check the validity of the matris
        # Get size of state_matrix
        nStates = len(state_matrix)
        nEvents = len(state_matrix[0])
        nInputEvents = len(self.input_event_mapping)
        # Define orouting as output_routing
        endCols = 2 + len(self.output_routing)  # 2 columns for timer
                                                # at the end, plus output cols

        if(len(self.sched_waves)>0 or len(self.sched_waves_ao)>0):
            # FIX
            # Do stuff about sche_waves
            # Check ~/tmp/newbcontrol/Modules/@RTLSM2/SetStateMatrix.m
            pass

        # Verify matrix is sane with respect to number of columns
        if(nEvents != nInputEvents+endCols):
            raise Error
            # FIX: define this exception (add description)

        # Concatenate the input_event_mapping vector as the last row
        #  of the matrix, server side will deconcatenate it.
        extraVector = nEvents*[0]
        extraVector[0:nInputEvents] = self.input_event_mapping
        state_matrix.append(extraVector)

        # For each scheduled wave, simply add the spec as elements to
        # the matrix -- note these elements are not at all row-aligned
        # and you can end up with multiple sched_waves per matrix row,
        # or one sched_wave taking up more than one matrix row.  The
        # server-side will just pop these out in FIFO order to build
        # its own sched_waves data structure.  It just knows there are
        # 8 columns per scheduled wave.
        #
        # FIX finish this section
        # Check ~/tmp/newbcontrol/Modules/@RTLSM2/SetStateMatrix.m

        # Format and urlencode the output_spec_str with format:
        # \1.type\2.data\1.type\2.data... where everything is
        # urlencoded (so \1 becomes %01, \2 becomes %02, etc)
        hasSound = False
        output_spec_str = ''
        for oneoutput in self.output_routing:
            if oneoutput.type in ['tcp', 'udp']:
                # Force trailing newline for tcp/udp text packets.
                # FIX: need to add '\n' at the end of data
                pass
            elif oneoutput.type in ['sound', 'ext']:
                hasSound = True
            output_spec_str += '\\1%s\\2%s'%(oneoutput.type,oneoutput.data)
        # FIX:  do output_spec_str = UrlEncode(sm, output_spec_str);
        output_spec_str = UrlEncode(output_spec_str)

        
import socket   ### FIX: Move this to the top later ###
class FSMClient:
    ''' .../Modules/NetClient/FSMClient.cpp starting on line 321'''
    def __init__(self, host, port):
        self.host = host
        self.port = port
        verbosePrint('Creating FSMClient')
        #createNewClient
        self.NetClient = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.NetClient.setsockopt(socket.IPPROTO_TCP,socket.TCP_NODELAY,True)
        # -- Set timeout to 10ms for self.readLines() (it failed if 1ms) --
        self.NetClient.settimeout(0.1)
        '''
        NetClient *nc = new NetClient(hostStr, portNum);
        mxFree(hostStr);
        nc->setSocketOption(Socket::TCPNoDelay, true);
        int h = handleId++;
        MapPut(h, nc);
        RETURN(h);
        '''
        pass
    def destroy(self):
        #destroyClient,
        pass
    def connect(self):
        verbosePrint('Connecting FSMClient')
        #tryConnection
        self.NetClient.connect( (self.host,self.port) )
        pass
    def disconnect(self):
        #closeSocket
        pass
    def sendString(self,stringToSend):
        self.NetClient.send(stringToSend)
    def sendMatrix(self):
        pass
    def OLDreadLine(self):
        '''Receive one line from socket, one char at a time.'''
        line = ''
        lastchar = ''
        while(lastchar!='\n'):
            line += lastchar
            lastchar = self.NetClient.recv(1)
        return line
        
    def OLDreadLines(self):
        ### FIX THIS! what's the right length of message? ###
        #lines = self.NetClient.recv(1024)
        lines = []
        while True:
            try:
                lines.append(self.readLine())
            except socket.timeout:
                break
        return lines
        '''
        NOTES: readLines() uses NetClient::receiveLines() uses
                NetClient::receiveLine() uses NetClient::receiveData
        '''
    def readLines(self):
        lines = ''
        lastchar = ''
        while True:
            try:
                lines += lastchar
                lastchar = self.NetClient.recv(1)
            except socket.timeout:
                break
        return lines

    def readMatrix(self):
        pass
    def notifyEvents(self):
        pass
    def stopNotifyEvents(self):
        pass

if __name__ == "__main__":

    mySM = sm('soul')

    #mySM.DoQueryCmd('SET STATE MACHINE %d'%mySM.fsm_id)
    #mySM.DoQueryCmd('CLIENTVERSION %u'%mySM.MIN_SERVER_VERSION)
    #mySM.handleFSMClient.sendString('VERSION\n')
    #mySM.handleFSMClient.readLine()
    #mySM.handleFSMClient.NetClient.recv(1024)
    #lines = mySM.handleFSMClient.readLines()
    #lines = mySM.DoQueryCmd('VERSION')
    #
    #mySM.handleFSMClient.NetClient.setblocking(False)
    #mySM.handleFSMClient.NetClient.settimeout(1)
