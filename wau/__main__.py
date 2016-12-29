import os
from wau import WebAppUpdater

if __name__ == '__main__':
	rootdir = os.path.dirname(os.path.realpath(__file__))
	rootdir = os.path.dirname(rootdir)
	myWau = WebAppUpdater(rootdir)
	myWau.run()