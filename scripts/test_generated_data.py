from common import load_all_pickled_files
from os.path import join

"""
San_Francisco: ALLCOORDS in 138/820 rows (means multiple vertex lists,
= paths with multiple arcs?)
"""


SVNROOT="C:/Documents and Settings/Amar/My Documents\svn/"
DATADIR=join(SVNROOT, "data/IntermediateData")
#NAMES=['stclines_streets_wgs', 'stclines_arterial', 'stintersections_wgs', 'San_Francisco', 'stintersections', 'dpt_speedlimits', 'dpt_bike_network_wgs',
#'stclines_highways', 'stnodes', 'stclines_streets', 'stclines', 'stclines_freeways', 'SF_Tiger_Roads', 'dpt_bike_network']

datasets = load_all_pickled_files(DATADIR)
NAMES = datasets.keys()

def get(i):
    try:
        name = NAMES[int(i)]
        global d, n
        d = datasets[name]
        n = name
        print 'set d and n'
    except Exception, e:
        print e
        
def info():
    for i, name in enumerate(NAMES):
        print "%d) %s" % (i, name)
    i = raw_input("> ")
    try:
        name = NAMES[int(i)]
        detail(name)
        return True
    except Exception, e:
        print e
    return False

def detail(name):
    if name in datasets:
        data = datasets[name]
        print '%s has %d rows.' % (name, len(data))
        row = data[0]
        sortedkeys = row.keys()
        sortedkeys.sort()
        for key in sortedkeys:
            value = row[key]
            t = str(type(value))
            if type(value) == list and len(value) > 3:
                value = value[0:3] + ['...']
            print "%s: %s (%s)" % (key, value, t[7:t.find("'>")])
    elif name:
        print '%s not found' % name

def check_allcoords():        
    for name, dataset in datasets.iteritems():
        allcoords = [row for row in dataset if 'ALLCOORDS' in row]
        if len(allcoords):
            print '%s: ALLCOORDS in %d/%d rows' % (name, len(allcoords),len(dataset))
        else:
            print '%s has no ALLCOORDS, yay' % name
                
if __name__ == "__main__":
    #check_allcoords()
    pass                                              
    

