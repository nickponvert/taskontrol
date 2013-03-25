#!/usr/bin/env python

'''
Classes for graphical protocol parameters.

Two parameters classes are defined:
- NumericParam: For a numeric entry and its label.
- StringParam: For entry of a string.
- MenuParam: For a menu entry and its label.

TODO:
- Make both label and text expanding horizontally

'''


__version__ = '0.1.1'
__author__ = 'Santiago Jaramillo <jara@cshl.edu>'
__created__ = '2012-08-27'

from PySide import QtCore 
from PySide import QtGui 

# FIXME: Add validation of numbers
#NUMERIC_REGEXP = 

class Container(dict):
    def __init__(self):
        super(Container, self).__init__()        
        self._groups = {}
        self._paramsToKeepHistory = []
        self.history = {}

    def __setitem__(self, paramName, paramInstance):
        # -- Check if there is already a parameter with that name --
        if paramName in self:
            print 'There is already a parameter named %s'%paramName
            raise ValueError
        # -- Check if paramInstance is of valid type and has a group --
        try:
            groupName = paramInstance.get_group()
            historyEnabled = paramInstance.history_enabled()
        except AttributeError:
            print 'Container cannot hold items of type %s'%type(paramInstance)
            raise
        # -- Append name of parameter to group list --
        try:
            self._groups[groupName].append(paramName)
        except KeyError:  # If group does not exist yet
            self._groups[groupName] = [paramName]
        # -- Append name of parameter to list of params to keep history --
        if historyEnabled:
            try:
                self._paramsToKeepHistory.append(paramName)
            except KeyError:  # If group does not exist yet
                self._paramsToKeepHistory = [paramName]
             
        # -- Add paramInstance to Container --
        dict.__setitem__(self, paramName, paramInstance)

    def print_items(self):
        for key,item in self.iteritems():
            print '[%s] %s : %s'%(type(item),key,str(item.get_value()))

    def layout_group(self,groupName):
        '''Create box and layout with all parameters of a given group'''
        groupBox = QtGui.QGroupBox(groupName)
        self.layoutForm = ParamGroupLayout()
        for paramkey in self._groups[groupName]:
            self.layoutForm.add_row(self[paramkey].labelWidget,self[paramkey].editWidget)

        groupBox.setLayout(self.layoutForm)
        return groupBox

    def update_history(self):
        '''Append the value of each parameter (to track) for this trial.'''
        for key in self._paramsToKeepHistory:
            try:
                self.history[key].append(self[key].get_value())
            except KeyError: # If the key does not exist yet (e.g. first trial)
                self.history[key] = [self[key].get_value()]

    def append_to_file(self,h5file):
        dataParent = 'trialData'      # Parameters from each trial
        itemsParent = 'menuItems'     # Items in menu parameters
        sessionParent = 'sessionData' # Parameters for the whole session
        descriptionAttr = 'Description'
        # FIXME: the contents of description should not be the label, but the
        #        description of the parameter (including its units)
        trialDataGroup = h5file.create_group(dataParent)
        menuItemsGroup = h5file.create_group(itemsParent)
        sessionDataGroup = h5file.create_group(sessionParent)
        for key,item in self.iteritems():
            # -- Store parameters with history --
            if item.history_enabled():
                #h5file.createDataset(trialDataGroup, key, self.history[key], paramLabel)
                dset = trialDataGroup.create_dataset(key, data=self.history[key])
                dset.attrs['Description'] = item.get_label()
                # FIXME: not very ObjectOriented to use getType
                #        the object should be able to save itself
                if item.get_type()=='menu':
                    #h5file.createArray(menuItemsGroup, key, item.get_items(),
                    #                   '%s menu items'%paramLabel)
                    menuItemsGroup.create_dataset(key, data=item.get_items())
                    dset.attrs['Description'] = '%s menu items'%item.get_label()
            else: # -- Store parameters without history (Session parameters) --
                dset = sessionDataGroup.create_dataset(sessionDataGroup, key, data=item.get_value())
                dset.attrs['Description'] = item.get_label()

class ParamGroupLayout(QtGui.QGridLayout):
    def __init__(self,parent=None):
        super(ParamGroupLayout, self).__init__(parent)
        self.setVerticalSpacing(0)
    def add_row(self,labelWidget,editWidget):
        currentRow = self.rowCount()
        self.addWidget(labelWidget,currentRow,0,QtCore.Qt.AlignRight)
        self.addWidget(editWidget,currentRow,1,QtCore.Qt.AlignLeft)


class GenericParam(QtGui.QWidget):
    def __init__(self, labelText='', value=0, group=None,
                 history=True, labelWidth=80, parent=None):
        super(GenericParam, self).__init__(parent)
        self._group = group
        self._historyEnabled = history
        self._type = None
        self._value = None
        self.labelWidget = QtGui.QLabel(labelText)
        self.labelWidget.setObjectName('ParamLabel')
        self.editWidget = None

    def get_type(self):
        return self._type

    def get_label(self):
        return str(self.labelWidget.text())

    def get_group(self):
        return self._group

    def in_group(self,groupName):
        return self._group==groupName

    def history_enabled(self):
        return self._historyEnabled


class StringParam(GenericParam):
    def __init__(self, labelText='', value='', group=None,
                 history=False, labelWidth=80, parent=None):
        super(StringParam, self).__init__(labelText, value, group,
                                           history, labelWidth,  parent)
        self._type = 'string'
        if self._historyEnabled:
            raise ValueError('String parameters are not allowed to keep a history.\n'
                             +'When creating the instance use: history=False')

        # -- Define graphical interface --
        self.editWidget = QtGui.QLineEdit()
        self.editWidget.setObjectName('ParamEdit')

        # -- Define value --
        self.set_value(value)

    def set_value(self,value):
        self._value = value
        self.editWidget.setText(str(value))

    def get_value(self):
        return str(self.editWidget.text())


class NumericParam(GenericParam):
    def __init__(self, labelText='', value=0, group=None,
                 history=True, labelWidth=80, parent=None):
        super(NumericParam, self).__init__(labelText, value, group,
                                           history, labelWidth,  parent)
        self._type = 'numeric'

        # -- Define graphical interface --
        self.editWidget = QtGui.QLineEdit()
        self.editWidget.setObjectName('ParamEdit')

        # -- Define value --
        self.set_value(value)

    def set_value(self,value):
        self._value = value
        self.editWidget.setText(str(value))

    def get_value(self):
        return float(self.editWidget.text())


class MenuParam(GenericParam):
    def __init__(self, labelText='', menuItems=(), value=0, group=None,
                 history=True, labelWidth=80, parent=None):
        super(MenuParam, self).__init__(labelText, value, group,
                                        history, labelWidth, parent)
        self._type = 'menu'

        # -- Define graphical interface --
        self.editWidget = QtGui.QComboBox()
        self.editWidget.addItems(menuItems)
        self.editWidget.setObjectName('ParamMenu')

        # -- Define value --
        self._items = menuItems
        self.set_value(value)

    def set_value(self,value):
        self._value = value
        self.editWidget.setCurrentIndex(value)

    def set_string(self,newstring):
        # FIXME: graceful warning if wrong string (ValueError exception)
        value = self._items.index(newstring)
        self._value = value
        self.editWidget.setCurrentIndex(value)

    def get_value(self):
        return self.editWidget.currentIndex()

    def get_string(self):
        return str(self.editWidget.currentText())

    def get_items(self):
        return self._items

    #def appendToFile(self,h5file,dataParent,itemsParent):
    #    h5file.createArray(dataParent, key, paramContainer.history[key], paramLabel)
    #    h5file.createArray(menuItemsGroup, key, paramContainer[key].get_items(),
    #                               '%s menu items'%paramLabel)


if __name__ == "__main__":
    import signal
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    import sys
    try:
      app = QtGui.QApplication(sys.argv)
    except RuntimeError:
      app = QtCore.QCoreApplication.instance()
    form = QtGui.QDialog()
    params = Container()
    params['value1'] = NumericParam('OneParam',value=2,group='First group')
    params['value2'] = NumericParam('AnotherParam',value=3,group='First group')
    params['value3'] = NumericParam('ParamThree',value=2,group='Second group')
    params['value4'] = NumericParam('ParamFour',value=3,group='Second group')
    firstGroup = params.layout_group('First group')
    secondGroup = params.layout_group('Second group')
    layoutMain = QtGui.QHBoxLayout()
    layoutMain.addWidget(firstGroup)
    layoutMain.addWidget(secondGroup)
    form.setLayout(layoutMain)
    form.show()
    app.exec_()


    # To get the item (as string) of a menuparam for the last trial in the history:
    #protocol.params['chooseNumber'].get_items()[protocol.params.history['chooseNumber'][-1]]
