class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def warn(msg):
    print(f'{bcolors.WARNING}{msg}{bcolors.ENDC}')


def info(msg):
    print(f'{bcolors.OKBLUE}{msg}{bcolors.ENDC}')


def error(msg):
    print(f'{bcolors.FAIL}{msg}{bcolors.ENDC}')
