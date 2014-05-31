#!/usr/bin/env python

'''
This example shows how to control the state matrix from a graphical interface.
It uses the module 'dispatcher' to provide an interface for starting
and stopping the state machine.
'''

__author__ = 'Santiago Jaramillo <jara@cshl.edu>'
__created__ = '2013-03-17'

import sys
from PySide import QtCore 
from PySide import QtGui 
from taskontrol.settings import rigsettings
from taskontrol.core import dispatcher
from taskontrol.core import statematrix
import signal

# -- Create main window --
signal.signal(signal.SIGINT, signal.SIG_DFL) # Enable Ctrl-C (to close window)
app = QtGui.QApplication(sys.argv)
form = QtGui.QDialog()

# -- Create dispatcher and upload state transition matrix --
dispatcherModel = dispatcher.Dispatcher(parent=form,
                                        serverType=rigsettings.STATE_MACHINE_TYPE,
                                        interval=0.5,
                                        nInputs=3, nOutputs=3)

#                Ci  Co  Li  Lo  Ri  Ro  Timer
stateMatrix = [ [ 0,  0,  0,  0,  0,  0,  1 ] ,
                [ 2,  1,  1,  1,  1,  1,  2 ] ,
                [ 2,  2,  1,  2,  2,  2,  1 ] ]
stateOutputs = [[0,0,0], [1,1,1], [0,0,0]]
stateTimers  = [  0.1,    2 ,    2  ]

sM=statematrix.StateMatrix() #Create the statematrix object to upload
sM.stateMatrix=stateMatrix
sM.stateOutputs=stateOutputs
sM.stateTimers=stateTimers

dispatcherModel.set_state_matrix(sM)

# -- Create dispatcher GUI and connect signals --
dispatcherView = dispatcher.DispatcherGUI(model=dispatcherModel)

# -- Create layout and run --
layout = QtGui.QVBoxLayout()
layout.addWidget(dispatcherView)
form.setLayout(layout)
form.show()
app.exec_()


