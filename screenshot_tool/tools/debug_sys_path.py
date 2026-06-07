import os, sys
print('cwd', os.getcwd())
print('sys.path[0:10]')
for p in sys.path[:10]:
    print(' ', p)
