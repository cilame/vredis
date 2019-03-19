class NotInDefaultsSetting(Exception):
    pass

class NotInDefaultCommand(Exception):
	pass

class NotInDefaultType(Exception):
    pass

class MustDictType(Exception):
	pass

class MustInSubcommandList(Exception):
	pass

class MustInCommandList(Exception):
	pass

class UndevelopmentSubcommand(Exception):
	pass

class SenderAlreadyStarted(Exception):
    pass

class PathNotExists(Exception):
    pass

class SettingError(Exception):
    pass