import FWCore.ParameterSet.Config as dune

#load the prototype description of the MemoryUseProd EDProducer
from DuneRawSim.Modules.memoryUseProd_cfi import memoryUseProd as _memoryUseProd

process = dune.Process("RAW")

process.source = dune.Source("EmptySource")


checkClusters = []
interactionFinders =[]

deleteEarlyList = []

seq = None

def generateProductName(moduleName):
    return "chars_"+moduleName+"__RAW"
def generateMightGet(moduleNames):
    return [ generateProductName(mod) for mod in moduleNames]

#create per APA modules
for x in range(1,151):
    #this module simulates reading one APA's data from storage on demand
    apaName = "apa"+str(x)
    prod = _memoryUseProd.clone(dataSizes = [40*1000*1000], consume = [])
    setattr(process, "apa"+str(x), prod)
    #want to setup to delete the memory
    deleteEarlyList.extend(generateMightGet([apaName]))
    if seq is None:
        seq = dune.wait(prod)
    else:
        seq += dune.wait(prod)

    #this module simulates timeToSpace conversion
    time2SpaceName = "time2Space"+str(x)

    prod = _memoryUseProd.clone( dataSizes= [40*1000*1000],
                                  consume = [apaName],
                                  uSleeps = [100],
                                  mightGet = generateMightGet([apaName])
                              )
    setattr(process, time2SpaceName, prod) 
    deleteEarlyList.extend(generateMightGet([time2SpaceName]))
    seq += dune.wait(prod)

    #this module simulates finding clusters in one given APA
    clusterName = "cluster"+str(x)
    prod = _memoryUseProd.clone( dataSizes= [400*1000], 
                                  consume = [time2SpaceName],
                                  uSleeps = [100],
                                  mightGet = generateMightGet([time2SpaceName])
                              )
    setattr(process, clusterName, prod)
    deleteEarlyList.extend(generateMightGet([clusterName]))
    seq += dune.wait(prod)

    #for each nearest neighbor APAs we want to create a InteractionFinder
    # which simulates handling an interaction which crosses an APA boundaries
    checkClusters.append(clusterName)
    if len(checkClusters) > 3:
        checkClusters.pop(0)
    if len(checkClusters) == 3:
        interactionFinderName="interaction"+str(x-1)
        prod = _memoryUseProd.clone( consume = checkClusters,
                                     dataSizes=[400*1000],
                                     mightGet = generateMightGet(checkClusters))
        setattr(process, interactionFinderName, prod)
        seq += dune.wait(prod)
        interactionFinders.append(interactionFinderName)

#This module looks at all APA triplets and simulates finding the best interactions
process.interactions = _memoryUseProd.clone( consume = interactionFinders,
                                             mightGet = generateMightGet(interactionFinders) )

#This simulates the time it takes to do the rest of the processing on the interactions
process.processInteraction = _memoryUseProd.clone( uSleeps = [20000],
                                                   consume = ["interactions"],
                                                   mightGet = generateMightGet(["interactions"]) )

process.p = dune.Path(seq+dune.wait(process.interactions)+dune.wait(process.processInteraction))

#######################
#parameters to change

nThreads = 1

process.maxEvents.input = 10*nThreads
process.options.numberOfThreads = nThreads
process.options.numberOfStreams = nThreads

#delete each APA data once it is no longer needed
process.options.canDeleteEarly = deleteEarlyList

process.options.wantSummary = True

###################
#helpful for debugging

#process.out = dune.EDAnalyzer("EventContentAnalyzer")
#process.o = dune.EndPath(process.out)

#print(process.dumpPython()        )
    
#process.add_(dune.Service("Tracer"))
